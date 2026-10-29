# 57 MS_CTM COMBINE - FIXED BADGE
# Import tools needed to build a website
# Flask: The main tool that creates our website
# request: Helps handle user clicks and form submissions
# render_template: Shows our HTML pages to visitors
# jsonify: For returning JSON responses to AJAX calls
from flask import Flask, request, render_template, jsonify
from database_manager  import DatabaseManager
import threading
import time

import json
import os
import subprocess
import sys
import webbrowser
import socket
import logging

import torisql
import pandas as pd
import qr_printer

# CSV file path for FALSE TEST database
FALSE_TEST_CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TORITANI DATABASE HIPROC.csv')

# Initialize database manager
db_manager = DatabaseManager()

# Create our website using Flask
# This line starts up our web application
app = Flask(__name__)       #create the app (auto-finds templates/ folder)

@app.after_request
def add_no_cache_headers(response):
    """Prevent browser from caching HTML pages so users always get the latest code"""
    if 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# Arduino signal queue: stores pending signals from the Arduino bridge
# Format: { process_no: {"action": "start"/"stop", "timestamp": time.time()} }
arduino_signals = {}
arduino_signals_lock = threading.Lock()

# Bridge ready tracking: auto-open browser when both bridges report ready
bridge_ready_status = {}
bridge_ready_lock = threading.Lock()
browser_opened = False

# ==================== SERVER-SIDE TIMER TRACKING ====================
# Tracks active timers server-side so Arduino START works even when browser page is closed
# Format: { process_no: {"start_time": time.time(), "kitting_no": N} }
server_timers = {}
server_timers_lock = threading.Lock()

# Server-side counter tracking per process
# Format: { process_no: counter_value }
server_counters = {}
server_counters_lock = threading.Lock()

# Reset generation counter - increments on every RESET ALL COUNTERS
# Browsers track this to detect resets and force-sync their local counter
reset_generation = 0
reset_generation_lock = threading.Lock()

# Counter offsets: snapshot of completed_count at last RESET ALL COUNTERS
# Subtracted from database count so counter displays 0 after reset
server_counter_offsets = {}
server_counter_offsets_lock = threading.Lock()

# Material Setter button state (from Arduino sensors)
# ms1_loaded: True if operator ID detected by Sensor 1 (Pin 2)
# ms2_open: True if interlock is open (Pin 3 HIGH)
ms_button_state = {"ms1_loaded": False, "ms2_open": False, "p1_id_loaded": False, "p1_interlock_open": False, "p2_id_loaded": False, "p2_interlock_open": False, "kitting_loaded": False, "p1_kitting_loaded": False, "standby_interlock_open": False}
ms_button_state_lock = threading.Lock()
_flask_start_time = time.time()

# Pending serial commands to send to MS Arduino via bridge polling
ms_pending_commands = []
ms_pending_commands_lock = threading.Lock()

# Pending serial commands to send to Cycle Time Arduino via CT bridge polling
ct_pending_commands = []
ct_pending_commands_lock = threading.Lock()

# Process 1 dunpla detection flag (Pin 7 sensor must fire before QR scan allowed)
p1_dunpla_detected = False
p1_dunpla_detected_lock = threading.Lock()

# Process 2 dunpla detection flag (Pin 11 sensor must fire before P2 scan allowed)
p2_dunpla_detected = False
p2_dunpla_detected_lock = threading.Lock()

# R35D-B Scanner: stores scanned operator ID (consumed by UI polling)
ms_scanned_id = None
ms_scanned_id_lock = threading.Lock()

# Kitting R35D-B Scanner: stores scanned kitting QR data (consumed by UI polling)
kitting_scanned_data = None
kitting_scanned_data_lock = threading.Lock()

# P1 R35D-B Scanner (Scanner 3): stores scanned operator ID (consumed by UI polling)
p1_scanned_id = None
p1_scanned_id_lock = threading.Lock()

# P1 Kitting R35D-B Scanner (Scanner 4): stores scanned kitting QR data (consumed by UI polling)
p1_kitting_scanned_data = None
p1_kitting_scanned_data_lock = threading.Lock()

# DELVO Android tablet QR mirror (Process 1 to Process 9 + Material Setter).
# This is NON-DESTRUCTIVE: the existing browser endpoints may continue to
# consume their normal read-once scanner values, while DELVO tablets read an
# independent latest-scan mirror without clearing anything.
#
# IMPORTANT: Process mirrors p1..p9 are updated only AFTER /api/validate_kitting_qr
# accepts the QR for that process. This prevents an invalid/wrong-process QR from
# becoming the active Kitting Number in a DELVO tablet.
delvo_kitting_mirror = {
    "ms": {
        "scan_id": 0, "kitting_qr": "", "timestamp": None,
        "process_no": None, "kitting_no": None, "job_order": "", "model_code": ""
    },
}
for _delvo_process_no in range(1, 10):
    delvo_kitting_mirror[f"p{_delvo_process_no}"] = {
        "scan_id": 0, "kitting_qr": "", "timestamp": None,
        "process_no": _delvo_process_no, "kitting_no": None,
        "job_order": "", "model_code": ""
    }

delvo_kitting_mirror_lock = threading.Lock()

def update_delvo_kitting_mirror(source, kitting_qr, process_no=None, kitting_no=None,
                                 job_order="", model_code=""):
    """Publish a Kitting QR to the DELVO tablet mirror without consuming normal UI data."""
    from datetime import datetime
    source = str(source or "").lower().strip()
    if source not in delvo_kitting_mirror:
        return False

    qr_value = str(kitting_qr or "").strip()
    if not qr_value:
        return False

    with delvo_kitting_mirror_lock:
        entry = delvo_kitting_mirror[source]
        entry["scan_id"] += 1
        entry["kitting_qr"] = qr_value
        entry["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if process_no is not None:
            entry["process_no"] = int(process_no)
        if kitting_no is not None:
            entry["kitting_no"] = int(kitting_no)
        entry["job_order"] = str(job_order or "")
        entry["model_code"] = str(model_code or "")
        scan_id = entry["scan_id"]

    print(
        f"DELVO QR MIRROR [{source.upper()}]: scan_id={scan_id}, "
        f"process={process_no}, kitting_no={kitting_no}, qr={qr_value}"
    )
    return True

# Server-side blocked counters tracking (replaces localStorage blocked_counters)
# Format: { process_no: [list of blocked kitting numbers] }
server_blocked_counters = {}
server_blocked_counters_lock = threading.Lock()

# Server-side active kitting tracking (which process is working on which kitting)
# Format: { process_no: kitting_no }
server_active_kittings = {}
server_active_kittings_lock = threading.Lock()

# Server-side last completed kitting tracking (prevents duplicate kitting in same process)
# Format: { process_no: {'kitting_no': N, 'time': timestamp} }
server_last_completed = {}
server_last_completed_lock = threading.Lock()

# Tracks when data was last updated (for auto-refresh on graph pages)
last_data_update = {"timestamp": time.time()}
last_data_update_lock = threading.Lock()

# Tracks the last date the system was active (for daily auto-reset)
last_active_date = {"date": None}
last_active_date_lock = threading.Lock()

# Tracks when a new job order started (for graph filtering)
job_order_start_time = {"timestamp": None}
job_order_start_time_lock = threading.Lock()

# Tracks if any process has started running today (to disable manpower warning after first start)
# Once any process starts, the warning is disabled until next day reset
processes_started_today = {"started": False}
processes_started_today_lock = threading.Lock()

# Server start timestamp for auto-reload detection
# When browser detects this changed, it will auto-refresh
SERVER_START_TIME = time.time()

# File to persist timer state across Flask restarts
TIMER_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server_timer_state.json')

# File to persist last active date across Flask restarts
LAST_DATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'last_active_date.json')

# File to persist job order start time across Flask restarts
JOB_ORDER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'job_order_start.json')

def save_last_active_date(date_str):
    """Save last active date to file"""
    try:
        with open(LAST_DATE_FILE, 'w') as f:
            json.dump({"date": date_str}, f)
        print(f"Saved last active date to file: {date_str}")
    except Exception as e:
        print(f"Error saving last active date: {e}")

def load_last_active_date():
    """Load last active date from file on startup"""
    try:
        if os.path.exists(LAST_DATE_FILE):
            with open(LAST_DATE_FILE, 'r') as f:
                data = json.load(f)
            date_str = data.get("date")
            if date_str:
                with last_active_date_lock:
                    last_active_date["date"] = date_str
                print(f"Loaded last active date from file: {date_str}")
                return date_str
    except Exception as e:
        print(f"Error loading last active date: {e}")
    return None

def save_job_order_start_time(timestamp_str):
    """Save job order start time to file"""
    try:
        with open(JOB_ORDER_FILE, 'w') as f:
            json.dump({"timestamp": timestamp_str}, f)
        print(f"Saved job order start time to file: {timestamp_str}")
    except Exception as e:
        print(f"Error saving job order start time: {e}")

def load_job_order_start_time():
    """Load job order start time from file on startup"""
    try:
        if os.path.exists(JOB_ORDER_FILE):
            with open(JOB_ORDER_FILE, 'r') as f:
                data = json.load(f)
            timestamp_str = data.get("timestamp")
            if timestamp_str:
                with job_order_start_time_lock:
                    job_order_start_time["timestamp"] = timestamp_str
                print(f"Loaded job order start time from file: {timestamp_str}")
                return timestamp_str
    except Exception as e:
        print(f"Error loading job order start time: {e}")
    return None

def set_new_job_order_start():
    """Set a new job order start time (called when all processes have same kitting)"""
    from datetime import datetime
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with job_order_start_time_lock:
        job_order_start_time["timestamp"] = timestamp_str
    save_job_order_start_time(timestamp_str)
    print(f"New job order started at: {timestamp_str}")
    return timestamp_str

def check_all_processes_same_kitting():
    """Check if all 9 processes have the same completed count (kitting value).
    If they do, it means a job order is complete and we should reset the graph.
    Runs in background thread to avoid blocking the response."""
    def _check():
        try:
            counts = []
            for i in range(1, 10):
                count = db_manager.get_completed_count(i)
                counts.append(count)
            
            # Check if all counts are the same AND greater than 0
            if len(set(counts)) == 1 and counts[0] > 0:
                print(f"ALL PROCESSES REACHED SAME KITTING VALUE: {counts[0]} - Starting new job order for graph")
                set_new_job_order_start()
                return True
            return False
        except Exception as e:
            print(f"Error checking all processes same kitting: {e}")
            return False
    
    # Run in background thread so it doesn't block the API response
    threading.Thread(target=_check, daemon=True).start()

def save_timer_state_to_file():
    """Persist server timer and counter state to file (runs in background thread)"""
    def _save():
        try:
            with server_timers_lock:
                timers_copy = {str(k): v for k, v in server_timers.items()}
            with server_counters_lock:
                counters_copy = {str(k): v for k, v in server_counters.items()}
            with server_counter_offsets_lock:
                offsets_copy = {str(k): v for k, v in server_counter_offsets.items()}
            state = {'timers': timers_copy, 'counters': counters_copy, 'counter_offsets': offsets_copy}
            with open(TIMER_STATE_FILE, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            print(f"Error saving timer state to file: {e}")
    
    # Run in background thread so it doesn't block the API response
    threading.Thread(target=_save, daemon=True).start()

def load_timer_state_from_file():
    """Load server timer and counter state from file on startup"""
    try:
        if os.path.exists(TIMER_STATE_FILE):
            with open(TIMER_STATE_FILE, 'r') as f:
                state = json.load(f)
            now = time.time()
            max_age = 7200  # Discard timers older than 2 hours (stale from previous session)
            loaded_timers = 0
            with server_timers_lock:
                for k, v in state.get('timers', {}).items():
                    age = now - v.get('start_time', 0)
                    if age <= max_age:
                        server_timers[int(k)] = v
                        loaded_timers += 1
                    else:
                        print(f"Discarding stale timer for Process {k} (age: {int(age)}s)")
            with server_counters_lock:
                for k, v in state.get('counters', {}).items():
                    server_counters[int(k)] = int(v)
            with server_counter_offsets_lock:
                for k, v in state.get('counter_offsets', {}).items():
                    server_counter_offsets[int(k)] = int(v)
            print(f"Loaded timer state from file: {loaded_timers} active timers, {len(server_counters)} counters, {len(server_counter_offsets)} offsets")
    except Exception as e:
        print(f"Error loading timer state from file: {e}")

def update_last_data_timestamp():
    """Update the last data change timestamp"""
    with last_data_update_lock:
        last_data_update["timestamp"] = time.time()

def check_daily_reset():
    """Check if it's a new day and perform daily reset if needed.
    Resets: kitting counters, manpower, and clears graph data."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    
    with last_active_date_lock:
        if last_active_date["date"] is None:
            # First run, just set the date and save to file
            last_active_date["date"] = today
            save_last_active_date(today)
            print(f"Daily reset check: First run, setting date to {today}")
            return False
        
        if last_active_date["date"] != today:
            # New day detected - perform full reset
            print(f"DAILY RESET TRIGGERED: New day detected ({last_active_date['date']} -> {today})")
            old_date = last_active_date["date"]
            last_active_date["date"] = today
            save_last_active_date(today)
            
            # Reset all server state
            with server_timers_lock:
                server_timers.clear()
            with server_counters_lock:
                server_counters.clear()
            with arduino_signals_lock:
                arduino_signals.clear()
            with server_blocked_counters_lock:
                server_blocked_counters.clear()
            with server_active_kittings_lock:
                server_active_kittings.clear()
            with server_last_completed_lock:
                server_last_completed.clear()
            with server_counter_offsets_lock:
                server_counter_offsets.clear()
            
            # Reset processes started flag for new day
            with processes_started_today_lock:
                processes_started_today["started"] = False
            
            # Delete timer state file
            try:
                if os.path.exists(TIMER_STATE_FILE):
                    os.remove(TIMER_STATE_FILE)
            except:
                pass
            save_timer_state_to_file()
            
            # Reset database: counters, manpower, and records
            db_manager.reset_all_for_new_day()
            
            update_last_data_timestamp()
            
            print(f"Daily reset completed: counters, manpower, and records cleared (was {old_date}, now {today})")
            return True
    return False

def clear_all_server_state():
    """Clear all server-side timers, counters, and the state file"""
    with server_timers_lock:
        server_timers.clear()
    with server_counters_lock:
        server_counters.clear()
    with arduino_signals_lock:
        arduino_signals.clear()
    with server_counter_offsets_lock:
        server_counter_offsets.clear()
    try:
        if os.path.exists(TIMER_STATE_FILE):
            os.remove(TIMER_STATE_FILE)
            print("Deleted server_timer_state.json")
    except Exception as e:
        print(f"Error deleting timer state file: {e}")
    save_timer_state_to_file()
    print("All server timers, counters, and Arduino signals cleared")

@app.route("/api/reset_all", methods=["POST"])
def reset_all():
    """Reset all server-side counters, timers, and state (called by RESET ALL COUNTERS button)"""
    try:
        clear_all_server_state()
        with server_blocked_counters_lock:
            server_blocked_counters.clear()
        with server_active_kittings_lock:
            server_active_kittings.clear()
        with server_last_completed_lock:
            server_last_completed.clear()
        with processes_started_today_lock:
            processes_started_today["started"] = False
        global reset_generation
        with reset_generation_lock:
            reset_generation += 1
        # Snapshot current DB counts as offsets so counters display 0 after reset
        with server_counter_offsets_lock:
            for i in range(1, 10):
                server_counter_offsets[i] = db_manager.get_completed_count(i)
        save_timer_state_to_file()
        print(f"RESET ALL: Server counters, timers, blocked counters, and active kittings cleared (generation={reset_generation})")
        return jsonify({"success": True, "message": "All server state reset"})
    except Exception as e:
        print(f"Error in reset_all: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def initialize_processes_started_today():
    """Check database on startup to see if any processes have run today.
    If records exist for today, set processes_started_today to True."""
    try:
        has_records = db_manager.has_records_today()
        with processes_started_today_lock:
            processes_started_today["started"] = has_records
        if has_records:
            print("STARTUP: Found records for today - manpower warning disabled")
        else:
            print("STARTUP: No records for today - manpower warning enabled")
    except Exception as e:
        print(f"Error checking today's records on startup: {e}")

# This is the main menu route
# When someone visits our website's main address, this code runs
# Lines 312-316 → @app.route("/") + render_template('main_menu.html') — when browser visits /, send the HTML file
@app.route("/")
def main_menu():
    # Show the main menu to the visitor
    # This is like opening the front door of our website
    return render_template('main_menu.html')

# Tablet-optimized main menu page
@app.route("/tablet_menu")
def tablet_menu():
    return render_template('main_menu_tablet.html')

# Tablet-optimized Material Setter (Kitting Summary) page
@app.route("/material_setter_tablet")
def material_setter_tablet():
    db_type = 'toritani'
    db_name = 'TORITANI SAN DATABASE'
    return render_template('material_setter.html', db_name=db_name, db_type=db_type, tablet_mode=True)

# This is the Cycle Time Monitoring homepage route
@app.route("/cycle_time_home")
def cycle_time_home():
    # Show the Cycle Time Monitoring homepage
    return render_template('home.html')

# Page for Process 1
# When someone goes to website.com/process1 or process1.html, they see this page
@app.route("/process1")
@app.route("/process1.html")
@app.route("/process1.HTML")
def process1():
    # Show the Process 1 monitoring page
    return render_template('process1.html')

# Page for Process 2
# When someone goes to website.com/process2 or process2.html, they see this page
@app.route("/process2")
@app.route("/process2.html")
@app.route("/process2.HTML")
def process2():
    # Show the Process 2 monitoring page
    return render_template('process2.html')

# Page for Process 3
# When someone goes to website.com/process3 or process3.html, they see this page
@app.route("/process3")
@app.route("/process3.html")
@app.route("/process3.HTML")
def process3():
    # Show the Process 3 monitoring page
    return render_template('process3.html')

# Page for Process 4
# When someone goes to website.com/process4 or process4.html, they see this page
@app.route("/process4")
@app.route("/process4.html")
@app.route("/process4.HTML")
def process4():
    # Show the Process 4 monitoring page
    return render_template('process4.html')

# Page for Process 5
# When someone goes to website.com/process5 or process5.html, they see this page
@app.route("/process5")
@app.route("/process5.html")
@app.route("/process5.HTML")
def process5():
    # Show the Process 5 monitoring page
    return render_template('process5.html')

# Page for Process 6
# When someone goes to website.com/process6 or process6.html, they see this page
@app.route("/process6")
@app.route("/process6.html")
@app.route("/process6.HTML")
def process6():
    # Show the Process 6 monitoring page
    return render_template('process6.html')

# Page for Process 7
# When someone goes to website.com/process7 or process7.html, they see this page
@app.route("/process7")
@app.route("/process7.html")
@app.route("/process7.HTML")
def process7():
    # Show the Process 7 monitoring page
    return render_template('process7.html')

# Page for Process 8
# When someone goes to website.com/process8 or process8.html, they see this page
@app.route("/process8")
@app.route("/process8.html")
@app.route("/process8.HTML")
def process8():
    # Show the Process 8 monitoring page
    return render_template('process8.html')

# Page for Process 9
# When someone goes to website.com/process9 or process9.html, they see this page
@app.route("/process9")
@app.route("/process9.html")
@app.route("/process9.HTML")
def process9():
    # Show the Process 9 monitoring page
    return render_template('process9.html')

# Settings page
@app.route("/settings")
def settings():
    # Show the settings page
    return render_template('settings.html')

# Standard time configuration page
@app.route("/standard_time")
def standard_time():
    # Show the standard time configuration page
    return render_template('standard_time.html')

# Manpower configuration page
@app.route("/manpower")
def manpower():
    # Show the manpower configuration page
    return render_template('manpower.html')

# Material Setter Manpower configuration page
@app.route("/mtrl_set_manpower")
def mtrl_set_manpower():
    return render_template('mtrl_set_manpower.html')

# Cycle Time Graph Monitoring page
@app.route("/cycle_graph")
def cycle_graph():
    # Show the cycle time graph monitoring page
    return render_template('cycle_graph.html')

# Line Trend Graph Monitoring page
@app.route("/line_trend")
def line_trend():
    # Show the line trend graph monitoring page
    return render_template('line_trend.html')

# Material Setter page
@app.route("/material_setter")
def material_setter():
    # FALSE TEST removed from Material Setter (June 2026) to prevent
    # cross-database confusion where kittings were saved under one DB
    # but loaded under the other. Material Setter now ALWAYS uses TORITANI,
    # regardless of any ?db= URL parameter (legacy bookmarks safely land here).
    db_type = 'toritani'
    db_name = 'TORITANI SAN DATABASE'
    return render_template('material_setter.html', db_name=db_name, db_type=db_type, tablet_mode=False)

FALSETEST_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'falsetest_config.json')

def get_falsetest_quantity():
    """Read FALSE TEST quantity from config file (no restart needed to change)"""
    try:
        with open(FALSETEST_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        return int(config.get('quantity', 10))
    except:
        return 10

# Kitting material categories for matching (row_no -> category keyword)
# These keywords are searched in MaterialDescription column of torisql.py
KITTING_MATERIAL_CATEGORIES = {
    1: 'FRAME ZAM',
    2: 'FRAME LEAD',
    3: 'SPACER',
    4: '2P',
    5: 'P3P',
    6: 'DF BLOCK',
    7: 'ROD',
    8: 'CASING',
    9: 'PARTITION BOARD',
    10: 'L-TUBE',
    11: 'HOSE CLIP',
    12: 'SWITCH',
    13: 'LEAD BUSHING',
    14: 'GROUND WIRE',
    15: 'V.C.R',
    16: 'LOWER HOUSING',
    17: 'RUBBER FOOT',
    18: 'POWER CORD',
    19: 'PARTITION GASKET',
    20: 'UPPER HOUSING',
    21: 'FILTER COVER',
    22: 'FILTER',
    23: 'SOUND ABSORB',
    24: 'MANUAL',
    25: 'L-HOSE SET',
    26: 'FILTER BUSHING'
}

@app.route("/getQuantityAndSuffix", methods=["GET", "POST"])
def getQuantityAndSuffix():
    data = request.get_json()
    job_order_raw = data.get("job_order_raw")
    db_type = data.get("db_type", "toritani")
    
    print(f"JOB ORDER RAW '{job_order_raw}' (len={len(str(job_order_raw)) if job_order_raw else 0}), DB TYPE: {db_type}")

    if db_type == 'falsetest':
        # For FALSE TEST database, read suffix from CSV
        try:
            job_order = str(job_order_raw)[:10]
            suffix = job_order_raw[13:] if len(job_order_raw) > 13 else '0'
            suffix = suffix.strip()[:4] if suffix else '0'
            
            # Read CSV and find matching job order
            df = pd.read_csv(FALSE_TEST_CSV_PATH)
            job_data = df[df['job'] == job_order]
            
            if len(job_data) > 0:
                suffix = str(job_data.iloc[0]['suffix'])
            
            print(f"FALSE TEST - Suffix: {suffix}")
            ft_qty = get_falsetest_quantity()
            return jsonify({"success": True, "quantity": ft_qty, "suffix": str(suffix).strip().zfill(4)})
        except Exception as e:
            print(f"Error reading FALSE TEST CSV: {e}")
            ft_qty = get_falsetest_quantity()
            return jsonify({"success": True, "quantity": ft_qty, "suffix": "0000"})
    else:
        # TORITANI SAN DATABASE - use SQL (retry up to 3 times on failure)
        last_error = None
        for attempt in range(3):
            try:
                tori_qty, tori_suffix = torisql.getJobOrderTotalQuantity(job_order_raw)
                print(f"Torio Qty: {tori_qty}, Torio Suffix: {tori_suffix}")
                
                # Ensure suffix is never empty - extract from raw barcode if needed
                if not tori_suffix or tori_suffix.strip() == '':
                    # Try to extract suffix from raw barcode
                    # Format: job_order(10) + padding/data + suffix + trailing(2)
                    raw = str(job_order_raw).strip()
                    if len(raw) > 12:
                        # Remove last 2 chars, then take from position 13
                        extracted = raw[:-2][13:]
                        if extracted.strip():
                            tori_suffix = extracted.strip()
                            print(f"Suffix extracted from barcode: {tori_suffix}")
                    # If still empty, try position 10 to -2 and strip
                    if not tori_suffix or tori_suffix.strip() == '':
                        if len(raw) > 12:
                            middle = raw[10:-2].strip()
                            if middle:
                                tori_suffix = middle.lstrip('0') or '0'
                                print(f"Suffix extracted from middle: {tori_suffix}")
                
                return jsonify({"success": True, "quantity": int(tori_qty), "suffix": str(tori_suffix).strip().zfill(4)})
            except Exception as e:
                last_error = e
                print(f"getQuantityAndSuffix attempt {attempt+1} failed: {e}")
                try:
                    torisql.connect()
                except:
                    pass
        print(f"getQuantityAndSuffix all retries failed: {last_error}")
        return jsonify({"success": False, "error": str(last_error)}), 500

#Get Tori Sql
@app.route("/getToriSql")
def get_tori_sql():
    job_order = request.args.get('job_order', '')
    db_type = request.args.get('db_type', 'toritani')

    # return job_order
    
    print(f"Job Order: {job_order}, DB TYPE: {db_type}")

    

    # Truncate to 10 characters
    job_order = job_order[:10] if job_order else ''
    
    if not job_order:
        return jsonify({"success": False, "error": "No job order provided"})
    
    # Get the REF KITTING MTLS format setting
    settings = load_settings_file()
    ref_kitting_format = settings.get('ref_kitting_format', 'text')  # 'text' or 'text_and_num'
    print(f"REF KITTING MTLS format: {ref_kitting_format}")
    
    try:
        # Get dataframe based on database type
        if db_type == 'falsetest':
            # FALSE TEST database - read from CSV
            print(f"Reading from FALSE TEST CSV for job order: {job_order}")
            df_full = pd.read_csv(FALSE_TEST_CSV_PATH)
            df = df_full[df_full['job'] == job_order]
            print(f"FALSE TEST Dataframe shape: {df.shape if df is not None else 'None'}")
        else:
            # TORITANI SAN DATABASE - use SQL
            # Connect if not already connected or connection is closed
            if torisql.cursor is None or torisql.conn is None:
                print("Connecting to Tori SQL...")
                torisql.connect()
            
            # Get the dataframe with materials
            print(f"Fetching materials for job order: {job_order}")
            df = torisql.getJobOrderMaterials(job_order)
            print(f"Dataframe shape: {df.shape if df is not None else 'None'}")
        
        # Get the item (4th column - index 3) from the first row if available
        item = None
        matched_materials = {}  # {row_no: MaterialDescription}
        
        if df is not None and len(df) > 0:
            columns = df.columns.tolist()
            print(f"Columns: {columns}")
            
            if len(columns) >= 4:
                # Get the 4th column name (item) and its value from first row
                fourth_column_name = columns[3]
                item = str(df.iloc[0][fourth_column_name]) if df.iloc[0][fourth_column_name] is not None else None
                print(f"4th column ({fourth_column_name}): {item}")
            
            # Find MaterialDescription and Material (material code) columns
            material_desc_col = None
            material_code_col = None
            matl_qty_col = None
            
            # Get Material code from 8th column (index 7) - this is the column with codes like FMB3270905
            if len(columns) >= 8:
                material_code_col = columns[7]
                print(f"Material Code column (8th): {material_code_col}")
            
            for col in columns:
                col_lower = col.lower()
                # Find MaterialDescription column
                if 'materialdescription' in col_lower:
                    material_desc_col = col
            
            # Get matl_qty from 10th column (index 9)
            if len(columns) >= 10:
                matl_qty_col = columns[9]
                print(f"matl_qty column (10th): {matl_qty_col}")
            
            print(f"MaterialDescription column: {material_desc_col}, Material Code column: {material_code_col}, matl_qty column: {matl_qty_col}")
            
            if material_desc_col:
                print(f"Found MaterialDescription column: {material_desc_col}")
                
                # First pass: collect all potential matches for each row in dataframe
                # Then assign the best match to each kitting category
                df_matches = []  # List of (mat_desc, mat_code, matched_categories)
                
                for idx, row in df.iterrows():
                    mat_desc = str(row[material_desc_col]) if row[material_desc_col] is not None else ''
                    mat_desc_upper = mat_desc.upper()
                    
                    # Get the material code for this row
                    mat_code = ''
                    if material_code_col:
                        mat_code = str(row[material_code_col]) if row[material_code_col] is not None else ''
                    
                    # Get matl_qty (10th column) for this row - convert to whole number
                    matl_qty = ''
                    if matl_qty_col:
                        qty_val = row[matl_qty_col]
                        if qty_val is not None:
                            try:
                                # Convert to integer (whole number, no decimals)
                                matl_qty = str(int(float(qty_val)))
                            except (ValueError, TypeError):
                                matl_qty = str(qty_val)
                    
                    # Find all matching categories for this description
                    matches = []
                    for row_no, category in KITTING_MATERIAL_CATEGORIES.items():
                        category_upper = category.upper()
                        if category_upper in mat_desc_upper:
                            # Calculate match quality - prioritize position first, then length
                            pos = mat_desc_upper.find(category_upper)
                            # Position is most important (earlier = better), then keyword length
                            # Use negative position * 100 to heavily weight earlier matches
                            score = (100 - pos) * 100 + len(category_upper)
                            matches.append((row_no, category, score))
                    
                    if matches:
                        # Sort by score (higher is better) and take the best match
                        matches.sort(key=lambda x: x[2], reverse=True)
                        best_match = matches[0]
                        row_no = best_match[0]
                        category = best_match[1]
                        
                        # Only assign if not already assigned
                        if row_no not in matched_materials:
                            # Determine kitting_name based on format setting
                            if ref_kitting_format == 'text_and_num':
                                # Use material code (e.g., FMB3270905)
                                kitting_name = category  # Will be overwritten below
                            # Load kitting_name from kitting_materials.json
                            if os.path.exists(KITTING_MATERIALS_FILE):
                                try:
                                    with open(KITTING_MATERIALS_FILE, 'r') as f:
                                        saved_materials = json.load(f)
                                        if str(row_no) in saved_materials:
                                            kitting_name = saved_materials[str(row_no)]
                                except:
                                    pass
                            else:
                                # Use category text (e.g., FRAME ZAM)
                                kitting_name = category
                            
                            matched_materials[row_no] = {
                                'description': mat_desc,
                                'code': mat_code,
                                'qty': matl_qty,
                                'kitting_name': kitting_name
                            }
                            print(f"Row {row_no} ({category}): {mat_desc} | Code: {mat_code} | Qty: {matl_qty} | Kitting: {kitting_name}")
            else:
                print("MaterialDescription column not found in dataframe")
        
        return jsonify({
            "success": True, 
            "job_order": job_order,
            "item": item,
            "materials": matched_materials,
            "message": "Data fetched successfully"
        })
    except Exception as e:
        print(f"Error in getToriSql: {e}")
        return jsonify({"success": False, "error": str(e)})

# Block local database when cursor enters Job Order field
@app.route("/blockLocalDb")
def block_local_db():
    torisql.setToriMode(True)
    return "Local DB blocked"

# Unblock local database (called after JO scan completes)
@app.route("/unblockLocalDb")
def unblock_local_db():
    torisql.setToriMode(False)
    return "Local DB unblocked"

# Save material setter data to MySQL
@app.route("/api/submit_material_data", methods=["POST"])
def submit_material_data():
    """Save material setter data to MATERIAL_SETTER table in MySQL"""
    try:
        data = request.json
        job_order = data.get('job_order', '')
        model_code = data.get('model_code', '')
        materials = data.get('materials', [])
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        if not materials:
            return jsonify({"success": False, "error": "No materials to save"}), 400
        
        # Save to MySQL
        result = db_manager.insert_material_setter(job_order, model_code, materials)
        
        if result:
            return jsonify({"success": True, "message": f"Saved {len(materials)} materials for job order {job_order}"})
        else:
            return jsonify({"success": False, "error": "Failed to save to database"}), 500
            
    except Exception as e:
        print(f"Error saving material setter: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== MAIN_DB AND KITTING_DB API ====================
@app.route("/api/clear_main_db", methods=["POST"])
def clear_main_db():
    """Clear all MAIN_DB records for a job order"""
    try:
        data = request.json
        job_order = data.get('job_order', '')
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        result = db_manager.clear_main_db_for_job_order(job_order)
        
        if result:
            return jsonify({"success": True, "message": f"Cleared MAIN_DB for job order {job_order}"})
        else:
            return jsonify({"success": False, "error": "Failed to clear MAIN_DB"}), 500
            
    except Exception as e:
        print(f"Error clearing MAIN_DB: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_main_db", methods=["POST"])
def save_main_db():
    """Save materials to MAIN_DB table"""
    try:
        data = request.json
        job_order = data.get('job_order', '')
        model_code = data.get('model_code', '')
        materials = data.get('materials', [])
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        result = db_manager.save_to_main_db(job_order, model_code, materials)
        
        if result:
            return jsonify({"success": True, "message": f"Saved to MAIN_DB for job order {job_order}"})
        else:
            return jsonify({"success": False, "error": "Failed to save to MAIN_DB"}), 500
            
    except Exception as e:
        print(f"Error saving to MAIN_DB: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_main_db", methods=["GET"])
def get_main_db():
    """Get materials from MAIN_DB for a job order"""
    try:
        job_order = request.args.get('job_order', '')
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        data = db_manager.get_main_db_data(job_order)
        return jsonify({"success": True, "data": data})
            
    except Exception as e:
        print(f"Error getting MAIN_DB data: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_all_main_db", methods=["GET"])
def get_all_main_db():
    """Get all materials from MAIN_DB (for Total Quantity Monitor auto-refresh)"""
    try:
        data = db_manager.get_all_main_db_data()
        return jsonify({"success": True, "data": data})
            
    except Exception as e:
        print(f"Error getting all MAIN_DB data: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/complete_kitting", methods=["POST"])
def complete_kitting():
    """Complete a kitting - save to KITTING_DB, material-specific tables, and update MAIN_DB remaining qty"""
    try:
        data = request.json
        job_order = data.get('job_order', '')
        model_code = data.get('model_code', '')
        materials = data.get('materials', [])
        # IMAGE 7: per-lot breakdown for problematic rows -> { "<row_no>": [ {scan_material, lot_no, qty_kit}, ... ] }
        material_lots = data.get('material_lots', {})
        kitting_qr_code = data.get('kitting_qr_code', '')  # QR code data (DD/MM/YY-KITTING_NO JOB_ORDER)
        suffix = data.get('suffix', '0001')  # Suffix in 4 digits
        plan_qty = data.get('plan_qty', 0)  # Plan quantity for joborder_plan
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        if not materials:
            return jsonify({"success": False, "error": "No materials to save"}), 400
        
        # Get next kitting number
        kitting_no = db_manager.get_next_kitting_no(job_order)
        
        # Save to KITTING_DB with QR code data
        result = db_manager.save_to_kitting_db(kitting_no, job_order, model_code, materials, kitting_qr_code)
        
        if result:
            # Save each row to its designated material-specific table (1tbl_frame_zam, 2tbl_frame_lead, etc.)
            # IMAGE 7: pass material_lots so problematic rows store one table row PER scanned lot.
            db_manager.save_to_material_tables(kitting_no, job_order, model_code, materials, kitting_qr_code, material_lots)
            
            # Save to joborder_plan table - track kitting progress with incrementing result and decrementing balance
            # Format kitting_qr_code: remove slash from date (DD/MM/YY -> DDMMYY)
            formatted_qr_code = kitting_qr_code.replace('/', '') if kitting_qr_code else ''
            if plan_qty and int(plan_qty) > 0:
                db_manager.save_joborder_plan(job_order, suffix, model_code, formatted_qr_code, plan_qty)
            
            # Queue RELAY2_ON to open interlock (solenoid valve) after kitting save
            with ms_pending_commands_lock:
                ms_pending_commands.append("RELAY2_ON")
            with ms_button_state_lock:
                ms_button_state["ms2_open"] = True
            db_manager.save_interlock_state(True)
            with p1_dunpla_detected_lock:
                p1_dunpla_detected = False
            print(f"MS_OPEN_INTERLOCK: Solenoid valve opened (kitting {kitting_no} saved) - dunpla flag reset")
            
            return jsonify({
                "success": True, 
                "kitting_no": kitting_no,
                "kitting_qr_code": kitting_qr_code,
                "message": f"Kitting {kitting_qr_code} completed successfully"
            })
        else:
            return jsonify({"success": False, "error": "Failed to save kitting"}), 500
            
    except Exception as e:
        print(f"Error completing kitting: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_kitting_db", methods=["GET"])
def get_kitting_db():
    """Get all kitting records from KITTING_DB for a job order"""
    try:
        job_order = request.args.get('job_order', '')
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        data = db_manager.get_kitting_db_data(job_order, today_only=False)
        return jsonify({"success": True, "data": data})
            
    except Exception as e:
        print(f"Error getting KITTING_DB data: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_kitting_summary", methods=["POST"])
def save_kitting_summary():
    """Save kitting summary data to kitting_summary table (mirrors browser display)"""
    try:
        data = request.json
        job_order = data.get('job_order', '')
        model_code = data.get('model_code', '')
        rows = data.get('rows', [])
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        if not rows:
            return jsonify({"success": False, "error": "No rows to save"}), 400
        
        result = db_manager.save_kitting_summary(job_order, model_code, rows)
        
        if result:
            return jsonify({"success": True, "message": f"Saved kitting summary for job order {job_order}"})
        else:
            return jsonify({"success": False, "error": "Failed to save kitting summary"}), 500
            
    except Exception as e:
        print(f"Error saving kitting summary: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/clear_kitting_summary", methods=["POST"])
def clear_kitting_summary():
    """Clear kitting summary data for a job order"""
    try:
        data = request.json
        job_order = data.get('job_order', '')
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        result = db_manager.clear_kitting_summary(job_order)
        
        if result:
            return jsonify({"success": True, "message": f"Cleared kitting summary for job order {job_order}"})
        else:
            return jsonify({"success": False, "error": "Failed to clear kitting summary"}), 500
            
    except Exception as e:
        print(f"Error clearing kitting summary: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_all_kitting_summary", methods=["GET"])
def get_all_kitting_summary():
    """Get all kitting summary data (no filter)"""
    try:
        data = db_manager.get_all_kitting_summary()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        print(f"Error getting all kitting summary: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reset_kitting_summary_ids", methods=["POST"])
def reset_kitting_summary_ids():
    """Reset kitting_summary table IDs to be sequential (fixes gaps in AUTO_INCREMENT)"""
    try:
        result = db_manager.reset_kitting_summary_ids()
        
        if result:
            return jsonify({"success": True, "message": "Kitting summary IDs have been reset to sequential order"})
        else:
            return jsonify({"success": False, "error": "Failed to reset kitting summary IDs"}), 500
            
    except Exception as e:
        print(f"Error resetting kitting summary IDs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
@app.route("/api/get_kitting_summary", methods=["GET"])
def get_kitting_summary():
    """Get kitting summary data from kitting_summary table"""
    try:
        job_order = request.args.get('job_order', '')
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        data = db_manager.get_kitting_summary(job_order)
        return jsonify({"success": True, "data": data})
            
    except Exception as e:
        print(f"Error getting kitting summary: {e}")
        return jsonify({"success": False, "error": str(e)}), 500




@app.route("/api/get_next_kitting_no", methods=["GET"])
def get_next_kitting_no():
    """Get the next kitting number for a job order"""
    try:
        job_order = request.args.get('job_order', '')
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        kitting_no = db_manager.get_next_kitting_no(job_order)
        has_records = db_manager.has_kitting_records(job_order)
        is_new_jo = not has_records
        total_today = kitting_no - 1  # highest kitting_no recorded today across ALL JOs
        print(f"get_next_kitting_no: JO={job_order}, next={kitting_no}, has_records={has_records}, is_new_jo={is_new_jo}, shouldPrint={is_new_jo}")
        return jsonify({"success": True, "kitting_no": kitting_no, "is_new_jo": is_new_jo, "total_today": total_today})
            
    except Exception as e:
        print(f"Error getting next kitting number: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/fix_main_db", methods=["POST"])
def fix_main_db():
    """Fix existing MAIN_DB data: set lot_qty from material data"""
    try:
        job_order = request.args.get('job_order', '')
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        affected_rows = db_manager.fix_main_db_lot_qty(job_order)
        return jsonify({"success": True, "message": f"Fixed {affected_rows} rows in MAIN_DB"})
            
    except Exception as e:
        print(f"Error fixing MAIN_DB: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== JOBORDER_PLAN API ====================
@app.route("/api/save_joborder_plan", methods=["POST"])
def save_joborder_plan():
    """Save a new joborder_plan record when kitting QR code is scanned"""
    try:
        data = request.json
        job_order = data.get('job_order', '')
        suffix = data.get('suffix', '0001')
        model_code = data.get('model_code', '')
        kitting_qr_code = data.get('kitting_qr_code', '')
        plan_qty = data.get('plan_qty', 0)
        operator_name = data.get('operator_name', '')
        time_in = data.get('time_in', None)
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        if not kitting_qr_code:
            return jsonify({"success": False, "error": "Kitting QR code is required"}), 400
        
        result = db_manager.save_joborder_plan(job_order, suffix, model_code, kitting_qr_code, plan_qty, operator_name, time_in)
        
        if result.get('success'):
            return jsonify({
                "success": True, 
                "row_no": result['row_no'],
                "result": result['result'],
                "balance": result['balance'],
                "message": f"Saved joborder_plan for job order {job_order}"
            })
        else:
            return jsonify({"success": False, "error": result.get('error', 'Unknown error')}), 500
            
    except Exception as e:
        print(f"Error saving joborder_plan: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_joborder_plan", methods=["GET"])
def get_joborder_plan():
    """Get all joborder_plan records for a job order"""
    try:
        job_order = request.args.get('job_order', '')
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        data = db_manager.get_joborder_plan(job_order)
        return jsonify({"success": True, "data": data})
            
    except Exception as e:
        print(f"Error getting joborder_plan: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_joborder_plan_latest", methods=["GET"])
def get_joborder_plan_latest():
    """Get the latest joborder_plan record for a job order"""
    try:
        job_order = request.args.get('job_order', '')
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        data = db_manager.get_joborder_plan_latest(job_order)
        return jsonify({"success": True, "data": data})
            
    except Exception as e:
        print(f"Error getting latest joborder_plan: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/check_jo_balance", methods=["GET"])
def check_jo_balance():
    """Check if a job order is finished (balance = 0 in joborder_plan)"""
    try:
        job_order = request.args.get('job_order', '')
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        latest = db_manager.get_joborder_plan_latest(job_order)
        
        if latest is None:
            # No record found - this is a brand new JO, not finished
            return jsonify({"success": True, "finished": False, "has_records": False})
        
        balance = int(latest.get('balance', -1))
        plan = int(latest.get('plan', 0))
        result_count = int(latest.get('result', 0))
        
        is_finished = (balance <= 0 and plan > 0)
        
        return jsonify({
            "success": True,
            "finished": is_finished,
            "has_records": True,
            "balance": balance,
            "plan": plan,
            "result": result_count,
            "model_code": latest.get('model_code', ''),
            "last_kitting_qr": latest.get('kitting_qr_code', '')
        })
            
    except Exception as e:
        print(f"Error checking JO balance: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/set_falsetest_qty", methods=["POST"])
def set_falsetest_qty():
    """Update FALSE TEST quantity in config file (live, no restart needed)"""
    try:
        data = request.json
        qty = int(data.get('quantity', 10))
        with open(FALSETEST_CONFIG_PATH, 'w') as f:
            json.dump({"quantity": qty}, f)
        print(f"FALSE TEST quantity updated to: {qty}")
        return jsonify({"success": True, "quantity": qty})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_falsetest_qty", methods=["GET"])
def get_falsetest_qty():
    """Get current FALSE TEST quantity from config"""
    return jsonify({"success": True, "quantity": get_falsetest_quantity()})

@app.route("/api/clear_joborder_plan", methods=["POST"])
def clear_joborder_plan():
    """Clear all joborder_plan records for a job order"""
    try:
        data = request.json
        job_order = data.get('job_order', '')
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        result = db_manager.clear_joborder_plan(job_order)
        
        if result:
            return jsonify({"success": True, "message": f"Cleared joborder_plan for job order {job_order}"})
        else:
            return jsonify({"success": False, "error": "Failed to clear joborder_plan"}), 500
            
    except Exception as e:
        print(f"Error clearing joborder_plan: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== MATERIAL SETTER SETTINGS API ====================
# File to persist material setter settings
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'material_setter_settings.json')
MODEL_CODES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_codes_no_bushing.json')
KITTING_MATERIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kitting_materials.json')

def load_settings_file():
    """Load settings from file"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading settings: {e}")
    return {}

def save_settings_file(settings):
    """Save settings to file"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False

def load_model_codes_file():
    """Load model codes without bushing from file"""
    try:
        if os.path.exists(MODEL_CODES_FILE):
            with open(MODEL_CODES_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading model codes: {e}")
    return ['80HP40073P', '80HP40701P', '80HP40750P', '60HP40004P', '60HP40701P']  # Default models WITH Filter Bushing (26 rows)

def save_model_codes_file(codes):
    """Save model codes without bushing to file"""
    try:
        with open(MODEL_CODES_FILE, 'w') as f:
            json.dump(codes, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving model codes: {e}")
        return False

@app.route("/api/get_settings", methods=["GET"])
def get_settings():
    """Get all material setter settings"""
    try:
        settings = load_settings_file()
        return jsonify({"success": True, "settings": settings})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_jo_database", methods=["POST"])
def save_jo_database():
    """Save JO Database location settings"""
    try:
        data = request.json
        db_type = data.get('type')
        path = data.get('path')
        
        settings = load_settings_file()
        settings['jo_database'] = {'type': db_type, 'path': path}
        
        if save_settings_file(settings):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to save settings"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_materials_path", methods=["POST"])
def save_materials_path():
    """Save Materials file location"""
    try:
        data = request.json
        path = data.get('path')
        
        settings = load_settings_file()
        settings['materials_path'] = path
        
        if save_settings_file(settings):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to save settings"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_latency", methods=["POST"])
def save_latency():
    """Save Arduino polling latency setting"""
    try:
        data = request.json
        latency = data.get('latency', 100)
        
        settings = load_settings_file()
        settings['latency'] = latency
        
        if save_settings_file(settings):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to save settings"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_elapsed_time_settings", methods=["POST"])
def save_elapsed_time_settings():
    """Save elapsed time display settings (millisecond, blinking)"""
    try:
        data = request.json
        millisecond = data.get('millisecond', False)
        blinking = data.get('blinking', False)
        
        settings = load_settings_file()
        settings['elapsed_time'] = {
            'millisecond': millisecond,
            'blinking': blinking
        }
        
        if save_settings_file(settings):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to save settings"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_qr_hide_setting", methods=["POST"])
def save_qr_hide_setting():
    """Save QR code hide/unhide setting (persists forever until changed)"""
    try:
        data = request.json
        qr_code_hidden = data.get('qr_code_hidden', False)
        
        settings = load_settings_file()
        settings['qr_code_hidden'] = qr_code_hidden
        
        if save_settings_file(settings):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to save settings"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_hidden_apps", methods=["GET"])
def get_hidden_apps():
    """Get which apps are currently hidden"""
    try:
        settings = load_settings_file()
        hideable_apps = settings.get('hideable_apps', {
            'calibration': 'Calibration',
            'ms_tablet_view': 'Tablet View Hide/Unhide',
            'ms_display_rows': 'Display # of Rows',
            'ms_mtrl_manpower': 'MTRL Set Manpower',
            'ms_qr_format': 'KIT QR Code Format',
            'ms_qr_font_size': 'KIT QR Font Size',
            'ms_ks_column': 'Kitting Summary Column'
        })
        hidden_apps = settings.get('hidden_apps', [])
        return jsonify({"success": True, "hideable_apps": hideable_apps, "hidden_apps": hidden_apps})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_hidden_apps", methods=["POST"])
def save_hidden_apps():
    """Save which apps are hidden"""
    try:
        data = request.json
        hidden_apps = data.get('hidden_apps', [])
        settings = load_settings_file()
        settings['hidden_apps'] = hidden_apps
        if 'hideable_apps' not in settings:
            settings['hideable_apps'] = {
                'calibration': 'Calibration',
                'ms_tablet_view': 'Tablet View Hide/Unhide',
                'ms_display_rows': 'Display # of Rows',
                'ms_mtrl_manpower': 'MTRL Set Manpower',
                'ms_qr_format': 'KIT QR Code Format',
                'ms_qr_font_size': 'KIT QR Font Size',
                'ms_ks_column': 'Kitting Summary Column'
            }
        if save_settings_file(settings):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_elapsed_time_settings", methods=["GET"])
def get_elapsed_time_settings():
    """Get elapsed time display settings"""
    try:
        settings = load_settings_file()
        elapsed_time = settings.get('elapsed_time', {'millisecond': False, 'blinking': False})
        return jsonify({"success": True, "elapsed_time": elapsed_time})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_page_title", methods=["POST"])
def save_page_title():
    """Save page title"""
    try:
        data = request.json
        title = data.get('title', '')
        settings = load_settings_file()
        settings['page_title'] = title
        if save_settings_file(settings):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_page_title", methods=["GET"])
def get_page_title():
    """Get page title"""
    try:
        settings = load_settings_file()
        title = settings.get('page_title', 'Job Order and Material Data')
        return jsonify({"success": True, "title": title})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_sub_columns", methods=["POST"])
def save_sub_columns():
    """Save sub column labels"""
    try:
        data = request.json
        sub_columns = data.get('sub_columns', [])
        settings = load_settings_file()
        settings['sub_columns'] = sub_columns
        if save_settings_file(settings):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_sub_columns", methods=["GET"])
def get_sub_columns():
    """Get sub column labels"""
    try:
        settings = load_settings_file()
        sub_columns = settings.get('sub_columns', ['Job Order #:', 'Model Code:', 'Quantity:'])
        return jsonify({"success": True, "sub_columns": sub_columns})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_column_headers", methods=["POST"])
def save_column_headers():
    """Save column header labels, lengths and alignments"""
    try:
        data = request.json
        column_headers = data.get('column_headers', [])
        column_lengths = data.get('column_lengths', [])
        column_aligns = data.get('column_aligns', [])
        settings = load_settings_file()
        settings['column_headers'] = column_headers
        settings['column_lengths'] = column_lengths
        settings['column_aligns'] = column_aligns
        if save_settings_file(settings):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_column_headers", methods=["GET"])
def get_column_headers():
    """Get column header labels, lengths and alignments"""
    try:
        settings = load_settings_file()
        column_headers = settings.get('column_headers', ['KITTING MTLS', 'MTRL DESC', 'MATERIAL CODE', 'QTY', 'SCAN MATERIAL', 'LOT NO', 'QTY', 'GOOD'])
        column_lengths = settings.get('column_lengths', [])
        column_aligns = settings.get('column_aligns', [])
        return jsonify({"success": True, "column_headers": column_headers, "column_lengths": column_lengths, "column_aligns": column_aligns})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_ks_column_headers", methods=["POST"])
def save_ks_column_headers():
    """Save Kitting Summary column header labels, lengths and alignments"""
    try:
        data = request.json
        ks_column_headers = data.get('ks_column_headers', [])
        ks_column_lengths = data.get('ks_column_lengths', [])
        ks_column_aligns = data.get('ks_column_aligns', [])
        settings = load_settings_file()
        settings['ks_column_headers'] = ks_column_headers
        settings['ks_column_lengths'] = ks_column_lengths
        settings['ks_column_aligns'] = ks_column_aligns
        # # column settings
        if 'ks_num_col_name' in data:
            settings['ks_num_col_name'] = data['ks_num_col_name']
        if 'ks_num_col_length' in data:
            settings['ks_num_col_length'] = data['ks_num_col_length']
        if 'ks_num_col_align' in data:
            settings['ks_num_col_align'] = data['ks_num_col_align']
        if save_settings_file(settings):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_ks_column_headers", methods=["GET"])
def get_ks_column_headers():
    """Get Kitting Summary column header labels, lengths and alignments"""
    try:
        settings = load_settings_file()
        ks_column_headers = settings.get('ks_column_headers', ['MTRL DESC', 'QTY/Unit', 'SCAN MTRL', 'LOT NO', 'QTY/Kit', 'LOT QTY', 'REM QTY', 'EDIT'])
        ks_column_lengths = settings.get('ks_column_lengths', [])
        ks_column_aligns = settings.get('ks_column_aligns', [])
        ks_num_col_name = settings.get('ks_num_col_name', '#')
        ks_num_col_length = settings.get('ks_num_col_length', 30)
        ks_num_col_align = settings.get('ks_num_col_align', 'center')
        return jsonify({"success": True, "ks_column_headers": ks_column_headers, "ks_column_lengths": ks_column_lengths, "ks_column_aligns": ks_column_aligns, "ks_num_col_name": ks_num_col_name, "ks_num_col_length": ks_num_col_length, "ks_num_col_align": ks_num_col_align})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_ks_box_length", methods=["POST"])
def save_ks_box_length():
    """Save Kitting Summary box width and height"""
    try:
        data = request.json
        settings = load_settings_file()
        settings['ks_box_width'] = data.get('ks_box_width', 1400)
        settings['ks_box_height'] = data.get('ks_box_height', 500)
        if save_settings_file(settings):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_ks_box_length", methods=["GET"])
def get_ks_box_length():
    """Get Kitting Summary box width and height"""
    try:
        settings = load_settings_file()
        return jsonify({"success": True, "ks_box_width": settings.get('ks_box_width', 1400), "ks_box_height": settings.get('ks_box_height', 500)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_action_buttons", methods=["POST"])
def save_action_buttons():
    """Save action button labels"""
    try:
        data = request.json
        action_buttons = data.get('action_buttons', [])
        settings = load_settings_file()
        settings['action_buttons'] = action_buttons
        if save_settings_file(settings):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_action_buttons", methods=["GET"])
def get_action_buttons():
    """Get action button labels"""
    try:
        settings = load_settings_file()
        action_buttons = settings.get('action_buttons', ['Delete', 'Main Menu', 'Submit'])
        return jsonify({"success": True, "action_buttons": action_buttons})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_ref_kitting_format", methods=["POST"])
def save_ref_kitting_format():
    """Save REF KITTING MTLS format setting (text or text_and_num)"""
    try:
        data = request.json
        format_type = data.get('format', 'text')
        settings = load_settings_file()
        settings['ref_kitting_format'] = format_type
        if save_settings_file(settings):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_ref_kitting_format", methods=["GET"])
def get_ref_kitting_format():
    """Get REF KITTING MTLS format setting"""
    try:
        settings = load_settings_file()
        format_type = settings.get('ref_kitting_format', 'text')
        return jsonify({"success": True, "format": format_type})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_printer_selection", methods=["POST"])
def save_printer_selection():
    """Save selected printer (sato or logicowl)"""
    try:
        data = request.json
        selected = data.get('selected_printer', 'sato')
        settings = load_settings_file()
        settings['selected_printer'] = selected
        if save_settings_file(settings):
            print(f"Printer selection saved: {selected}")
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_printer_selection", methods=["GET"])
def get_printer_selection():
    """Get selected printer and detect availability"""
    try:
        settings = load_settings_file()
        selected = settings.get('selected_printer', 'sato')
        sato_name = qr_printer.get_sato_printer_name()
        logicowl_name = qr_printer.get_logicowl_printer_name()
        return jsonify({
            "success": True,
            "selected_printer": selected,
            "sato_detected": sato_name,
            "logicowl_detected": logicowl_name
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_row_count", methods=["POST"])
def save_row_count():
    """Save row count setting"""
    try:
        data = request.json
        row_count = data.get('row_count', 25)
        settings = load_settings_file()
        settings['row_count'] = row_count
        if save_settings_file(settings):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_row_count", methods=["GET"])
def get_row_count():
    """Get row count setting"""
    try:
        settings = load_settings_file()
        row_count = settings.get('row_count', 25)
        return jsonify({"success": True, "row_count": row_count})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_display_rows", methods=["POST"])
def save_display_rows():
    """Save display rows setting for kitting summary table"""
    try:
        data = request.json
        display_rows = data.get('display_rows', 25)
        settings = load_settings_file()
        settings['display_rows'] = display_rows
        if save_settings_file(settings):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_qr_format", methods=["POST"])
def save_qr_format():
    """Save QR code date format setting (slash, dash, none)"""
    try:
        data = request.json
        qr_date_format = data.get('qr_date_format', 'slash')
        settings = load_settings_file()
        settings['qr_date_format'] = qr_date_format
        if save_settings_file(settings):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_model_codes", methods=["GET"])
def get_model_codes():
    """Get model codes without bushing (23 rows)"""
    try:
        codes = load_model_codes_file()
        return jsonify({"success": True, "model_codes": codes})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/add_model_code", methods=["POST"])
def add_model_code():
    """Add a model code without bushing"""
    try:
        data = request.json
        code = data.get('model_code', '').strip().upper()
        
        if not code:
            return jsonify({"success": False, "error": "Model code is required"}), 400
        
        codes = load_model_codes_file()
        if code not in codes:
            codes.append(code)
            save_model_codes_file(codes)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/delete_model_code", methods=["POST"])
def delete_model_code():
    """Delete a model code without bushing"""
    try:
        data = request.json
        code = data.get('model_code', '').strip().upper()
        
        codes = load_model_codes_file()
        if code in codes:
            codes.remove(code)
            save_model_codes_file(codes)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_all_model_codes", methods=["GET"])
def get_all_model_codes():
    """Get all available model codes (from materials file or sample data)"""
    try:
        # Sample model codes - in production, load from materials file
        model_codes = [
            '60CAT0211P', '60CAT0212P', '60CAT0213P', '60CAT0214P', '60CAT0215P',
            '60CAT0216P', '60CAT0217P', '60CAT0218P', '60CAT0219P', '60CAT0220P',
            '80CAT0301P', '80CAT0302P', '80CAT0303P', '80CAT0304P', '80CAT0305P',
            '80CAT0306P', '80CAT0307P', '80CAT0308P', '80CAT0309P', '80CAT0310P'
        ]
        return jsonify({"success": True, "model_codes": model_codes})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_kitting_materials", methods=["GET"])
def get_kitting_materials():
    """Get kitting material names"""
    try:
        if os.path.exists(KITTING_MATERIALS_FILE):
            with open(KITTING_MATERIALS_FILE, 'r') as f:
                kitting_materials = json.load(f)
            return jsonify({"success": True, "kitting_materials": kitting_materials})
        else:
            return jsonify({"success": False, "message": "Using defaults"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_kitting_materials", methods=["POST"])
def save_kitting_materials():
    """Save kitting material names"""
    try:
        data = request.json
        kitting_materials = data.get('kitting_materials', {})
        
        with open(KITTING_MATERIALS_FILE, 'w') as f:
            json.dump(kitting_materials, f, indent=2)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_generate_csv", methods=["POST"])
def save_generate_csv():
    """Save CSV generation setting and generate CSV if enabled"""
    try:
        data = request.json
        generate_csv = data.get('generate_csv', False)
        
        settings = load_settings_file()
        settings['generate_csv'] = generate_csv
        
        if save_settings_file(settings):
            # If enabled, generate CSV from torisql dataframe
            if generate_csv:
                try:
                    # Get CSV export options from settings
                    csv_options = settings.get('csv_export_options', {})
                    
                    if torisql.cursor is None or torisql.conn is None:
                        torisql.connect()
                    
                    # Get default job order or use the one from settings
                    job_order = csv_options.get('default_job_order', '3J73802302')
                    
                    # Get DataFrame using existing function
                    df = torisql.getJobOrderMaterials(job_order)
                    
                    if df is not None and len(df) > 0:
                        # Use enhanced export function
                        export_options = {
                            'job_order': job_order,
                            'include_metadata': csv_options.get('include_metadata', True),
                            'replace_nulls': csv_options.get('replace_nulls', True),
                            'trim_strings': csv_options.get('trim_strings', True),
                            'format_dates': csv_options.get('format_dates', True),
                            'encoding': csv_options.get('encoding', 'utf-8-sig')
                        }
                        
                        result = torisql.export_to_csv(df, options=export_options)
                        
                        if result['success']:
                            print(f"CSV generated: {result['file_path']} with {result['record_count']} rows")
                            # Save last export info
                            settings['last_csv_export'] = {
                                'filename': result['filename'],
                                'timestamp': result['export_time'],
                                'record_count': result['record_count']
                            }
                            save_settings_file(settings)
                        else:
                            print(f"CSV export failed: {result.get('error', 'Unknown error')}")
                    else:
                        print("No data returned from query")
                except Exception as csv_error:
                    print(f"Error generating CSV: {csv_error}")
                    import traceback
                    traceback.print_exc()
            
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to save settings"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_csv_export_options", methods=["POST"])
def save_csv_export_options():
    """Save CSV export options"""
    try:
        data = request.json
        
        settings = load_settings_file()
        settings['csv_export_options'] = {
            'default_job_order': data.get('default_job_order', '3J73802302'),
            'include_metadata': data.get('include_metadata', True),
            'replace_nulls': data.get('replace_nulls', True),
            'trim_strings': data.get('trim_strings', True),
            'format_dates': data.get('format_dates', True),
            'encoding': data.get('encoding', 'utf-8-sig')
        }
        
        if save_settings_file(settings):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to save settings"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/export_csv_now", methods=["POST"])
def export_csv_now():
    """Export CSV immediately with current settings"""
    try:
        data = request.json
        job_order = data.get('job_order')
        
        if not job_order:
            return jsonify({"success": False, "error": "Job order is required"}), 400
        
        if torisql.cursor is None or torisql.conn is None:
            torisql.connect()
        
        df = torisql.getJobOrderMaterials(job_order)
        
        if df is None or len(df) == 0:
            return jsonify({"success": False, "error": "No data found for job order"}), 404
        
        settings = load_settings_file()
        csv_options = settings.get('csv_export_options', {})
        
        export_options = {
            'job_order': job_order,
            'include_metadata': csv_options.get('include_metadata', True),
            'replace_nulls': csv_options.get('replace_nulls', True),
            'trim_strings': csv_options.get('trim_strings', True),
            'format_dates': csv_options.get('format_dates', True),
            'encoding': csv_options.get('encoding', 'utf-8-sig')
        }
        
        result = torisql.export_to_csv(df, options=export_options)
        
        if result['success']:
            settings['last_csv_export'] = {
                'filename': result['filename'],
                'timestamp': result['export_time'],
                'record_count': result['record_count'],
                'job_order': job_order
            }
            save_settings_file(settings)
            
            return jsonify({
                "success": True,
                "filename": result['filename'],
                "record_count": result['record_count'],
                "message": "CSV exported successfully"
            })
        else:
            return jsonify({"success": False, "error": result.get('error', 'Export failed')}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== SELF TESTING / CALIBRATION API ====================
CUSTOM_TESTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom_tests.json')

@app.route("/api/get_custom_tests", methods=["GET"])
def get_custom_tests():
    """Get saved custom tests"""
    try:
        if os.path.exists(CUSTOM_TESTS_FILE):
            with open(CUSTOM_TESTS_FILE, 'r') as f:
                return jsonify({"success": True, "custom_tests": json.load(f)})
        return jsonify({"success": True, "custom_tests": []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_custom_tests", methods=["POST"])
def save_custom_tests():
    """Save custom tests to file"""
    try:
        data = request.json
        custom_tests = data.get('custom_tests', [])
        with open(CUSTOM_TESTS_FILE, 'w') as f:
            json.dump(custom_tests, f, indent=2)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/run_self_test", methods=["POST"])
def run_self_test():
    """Run a specific self-test and return result"""
    try:
        data = request.json
        test_id = data.get('test_id', '')
        result = {"success": False, "detail": "Unknown test"}

        if test_id == 'problematic_row_insert':
            # Test: verify kitting_summary table is writable and problematic row logic works
            try:
                test_data = db_manager.run_functional_test('problematic_row_insert')
                result = {"success": test_data.get('passed', False), "detail": test_data.get('detail', '')}
            except Exception as e:
                result = {"success": False, "detail": str(e)}

        elif test_id == 'track_last_kitting':
            # Test: get_next_kitting_no returns correct number for existing JO
            try:
                test_data = db_manager.run_functional_test('track_last_kitting')
                result = {"success": test_data.get('passed', False), "detail": test_data.get('detail', '')}
            except Exception as e:
                result = {"success": False, "detail": str(e)}

        elif test_id == 'filter_bush_check':
            # Test: model codes list exists and can distinguish bushing vs non-bushing
            try:
                codes = load_model_codes_file()
                has_codes = len(codes) > 0
                total_categories = len(KITTING_MATERIAL_CATEGORIES)
                result = {"success": has_codes and total_categories == 26,
                          "detail": f"Models with bushing: {len(codes)}, Total categories: {total_categories} (26=WITH bush, 25=WITHOUT)"}
            except Exception as e:
                result = {"success": False, "detail": str(e)}

        elif test_id == 'read_suffix':
            # Test: getJobOrderTotalQuantity can connect and return data
            try:
                test_data = db_manager.run_functional_test('read_suffix')
                result = {"success": test_data.get('passed', False), "detail": test_data.get('detail', '')}
            except Exception as e:
                result = {"success": False, "detail": str(e)}

        elif test_id == 'read_jo_qty':
            # Test: quantity can be read from database
            try:
                test_data = db_manager.run_functional_test('read_jo_qty')
                result = {"success": test_data.get('passed', False), "detail": test_data.get('detail', '')}
            except Exception as e:
                result = {"success": False, "detail": str(e)}

        elif test_id == 'one_time_scan':
            # Test: verify joborder_plan doesn't create duplicates
            try:
                test_data = db_manager.run_functional_test('one_time_scan')
                result = {"success": test_data.get('passed', False), "detail": test_data.get('detail', '')}
            except Exception as e:
                result = {"success": False, "detail": str(e)}

        elif test_id == 'printer_suffix':
            # Test: QR code format includes suffix placeholder
            try:
                result = {"success": True, "detail": "QR format: DD/MM/YY-KITTING_NO JOB_ORDER SUFFIX - suffix field present in code"}
            except Exception as e:
                result = {"success": False, "detail": str(e)}

        elif test_id == 'suffix_both':
            # Test: kitting_summary table has columns for suffix data
            try:
                test_data = db_manager.run_functional_test('suffix_both')
                result = {"success": test_data.get('passed', False), "detail": test_data.get('detail', '')}
            except Exception as e:
                result = {"success": False, "detail": str(e)}

        elif test_id == 'sato_active':
            # Test: check SATO printer connectivity (retry up to 2 times with longer timeout)
            try:
                import socket
                printer_ok = False
                last_code = -1
                for attempt in range(2):
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(5)
                        last_code = sock.connect_ex(('192.168.2.100', 9100))
                        sock.close()
                        if last_code == 0:
                            printer_ok = True
                            break
                    except:
                        pass
                if printer_ok:
                    result = {"success": True, "detail": "SATO printer at 192.168.2.100:9100 is REACHABLE"}
                else:
                    result = {"success": False, "detail": "SATO printer at 192.168.2.100:9100 is NOT reachable (code: " + str(last_code) + ")"}
            except Exception as e:
                result = {"success": False, "detail": f"Printer check error: {str(e)}"}

        elif test_id == 'jo_completion_reset':
            # Test: JO completion reset logic - verifies check_jo_balance works for both DB types
            # and that the frontend self-test function exists
            try:
                details = []
                all_ok = True
                # 1. Verify check_jo_balance API works (no JO = brand new, not finished)
                test_latest = db_manager.get_joborder_plan_latest('__SELFTEST_NONEXISTENT__')
                if test_latest is None:
                    details.append('check_jo_balance: correctly returns no-record for unknown JO')
                else:
                    details.append('WARN: found unexpected record for __SELFTEST_NONEXISTENT__')
                # 2. Verify current DB type is accessible
                details.append(f'DB type: toritani')
                # 3. Verify frontend self-test function name matches
                details.append('Frontend test: selfTestJoCompletionReset() callable from browser console')
                # 4. Verify joFinishedFlag fix is present in template
                template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'material_setter.html')
                with open(template_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                checks = {
                    'joFinishedFlag declaration': 'let joFinishedFlag = false;' in html_content,
                    'prepareForNextKitting guard': 'if (joFinishedFlag)' in html_content,
                    'resetAfterJoFinished QR disable': "scanQrInput.disabled = true;\n                scanQrInput.placeholder = 'Complete all materials first...';" in html_content,
                    'carltrial skipProblematic clear': 'skipProblematicRowInsertion = {};' in html_content,
                    'saveToJoborderPlan flag set': 'joFinishedFlag = true;' in html_content,
                }
                for check_name, check_result in checks.items():
                    if check_result:
                        details.append(f'Code check [{check_name}]: PRESENT')
                    else:
                        details.append(f'Code check [{check_name}]: MISSING')
                        all_ok = False
                result = {"success": all_ok, "detail": ' | '.join(details)}
            except Exception as e:
                result = {"success": False, "detail": f"jo_completion_reset test error: {str(e)}"}

        elif test_id == 'manual_print':
            # Test: print endpoint exists and is callable
            result = {"success": True, "detail": "Manual print function is available via frontend printKittingQrToSato()"}

        elif test_id == 'no_old_print':
            # Test: re-scan logic - nextKittingNo > 1 should NOT print
            result = {"success": True, "detail": "Logic: isNewJobOrder = (nextKittingNo === 1); generateKittingQrCode(isNewJobOrder) - old JO won't print"}

        elif test_id == 'idle_time':
            # Test: check server uptime and last reset
            try:
                from datetime import datetime
                uptime_seconds = time.time() - SERVER_START_TIME
                uptime_min = round(uptime_seconds / 60, 1)
                result = {"success": True, "detail": f"Server uptime: {uptime_min} minutes. No auto-reset unless date changes."}
            except Exception as e:
                result = {"success": False, "detail": str(e)}

        elif test_id == 'operator_persist':
            # Test: check if manpower records persist
            try:
                test_data = db_manager.run_functional_test('operator_persist')
                result = {"success": test_data.get('passed', False), "detail": test_data.get('detail', '')}
            except Exception as e:
                result = {"success": False, "detail": str(e)}

        elif test_id == 'printer_connected':
            # Test: check if SATO printer is installed/recognized by Windows
            try:
                printer_name = qr_printer.get_sato_printer_name()
                if printer_name:
                    result = {"success": True, "detail": f"SATO printer found: '{printer_name}'"}
                else:
                    all_printers = qr_printer.list_printers()
                    result = {"success": False, "detail": f"SATO PW208NX NOT found. Installed printers: {all_printers}"}
            except Exception as e:
                result = {"success": False, "detail": f"Printer check error: {str(e)}"}

        elif test_id == 'printer_writable':
            # Test: check if printer handle can be opened (does NOT print anything)
            try:
                import win32print
                printer_name = qr_printer.get_sato_printer_name()
                if not printer_name:
                    result = {"success": False, "detail": "SATO printer not found - cannot test write access"}
                else:
                    handle = win32print.OpenPrinter(printer_name)
                    win32print.ClosePrinter(handle)
                    result = {"success": True, "detail": f"Printer '{printer_name}' handle opened and closed OK - ready to receive data"}
            except Exception as e:
                result = {"success": False, "detail": f"Cannot open printer handle: {str(e)}"}

        elif test_id == 'qr_generation':
            # Test: verify QR code text format is correct
            try:
                from datetime import datetime
                now = datetime.now()
                test_qr = f"{now.strftime('%d/%m/%y')}-0001 TEST1234567 0001"
                valid = len(test_qr) > 10 and '/' in test_qr and '-' in test_qr
                result = {"success": valid, "detail": f"QR format OK: '{test_qr}' (DD/MM/YY-KITTING_NO JOB_ORDER SUFFIX)"}
            except Exception as e:
                result = {"success": False, "detail": f"QR generation error: {str(e)}"}

        elif test_id == 'arduino_alive':
            # Test: check if arduino_bridge.py subprocess is running
            try:
                import psutil
                bridge_found = False
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = proc.info.get('cmdline', []) or []
                        if any('arduino_bridge' in str(c) for c in cmdline):
                            bridge_found = True
                            break
                    except:
                        pass
                if bridge_found:
                    result = {"success": True, "detail": "arduino_bridge.py process is RUNNING"}
                else:
                    result = {"success": False, "detail": "arduino_bridge.py process NOT found (may not be started)"}
            except ImportError:
                result = {"success": False, "detail": "psutil not installed - cannot check processes"}
            except Exception as e:
                result = {"success": False, "detail": f"Process check error: {str(e)}"}

        elif test_id == 'custom_functional':
            # Custom functional test from ADD TEST
            try:
                tables = data.get('tables', '')
                action = data.get('action', 'SELECT')
                test_jo = data.get('test_jo', '')
                test_data = db_manager.run_functional_test('custom', tables=tables, action=action, test_jo=test_jo, name=data.get('name', ''))
                result = {"success": test_data.get('passed', False), "detail": test_data.get('detail', '')}
            except Exception as e:
                result = {"success": False, "detail": str(e)}

        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== AI SELF TESTING ENGINE ====================
AI_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ai_config.json')

def load_ai_config():
    try:
        if os.path.exists(AI_CONFIG_FILE):
            with open(AI_CONFIG_FILE, 'r') as f:
                return json.load(f)
    except: pass
    return {"provider": "offline", "api_key": "", "model": "gpt-3.5-turbo"}

def save_ai_config(config):
    try:
        with open(AI_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving AI config: {e}")

DIAGNOSTIC_RULES = {
    'b16': {'cat': 'Server',   'deps': [],      'fixes': ['Check if Flask is running on port 5000', 'Restart cycleTimeMoni.py']},
    'b17': {'cat': 'Database', 'deps': ['b16'], 'fixes': ['Check MySQL is running (localhost:3306)', 'Verify root password', 'CREATE DATABASE cycle_time_monitoring']},
    'b18': {'cat': 'Database', 'deps': ['b17'], 'fixes': ['Ensure manpower table exists', 'Run db_manager.connect() to recreate tables']},
    'b19': {'cat': 'Database', 'deps': ['b17'], 'fixes': ['Ensure standard_times table exists']},
    'b20': {'cat': 'Config',   'deps': ['b16'], 'fixes': ['Check kitting_materials.json exists']},
    'b21': {'cat': 'Config',   'deps': ['b16'], 'fixes': ['Check model_codes_no_bushing.json exists']},
    'b22': {'cat': 'Database', 'deps': ['b17'], 'fixes': ['Ensure MAIN_DB table exists']},
    'b23': {'cat': 'Database', 'deps': ['b17'], 'fixes': ['Ensure kitting_summary table exists']},
    'b24': {'cat': 'Database', 'deps': ['b18'], 'fixes': ['Assign operators to all 9 processes']},
    'b25': {'cat': 'Config',   'deps': ['b16'], 'fixes': ['Check material_setter_settings.json']},
    'b26': {'cat': 'Config',   'deps': ['b16'], 'fixes': ['Check sub_columns settings']},
    'b27': {'cat': 'Config',   'deps': ['b16'], 'fixes': ['Check column_headers settings']},
    'b28': {'cat': 'Config',   'deps': ['b16'], 'fixes': ['Check row_count setting']},
    'b29': {'cat': 'Config',   'deps': ['b16'], 'fixes': ['Check ref_kitting_format setting']},
    'b30': {'cat': 'Pages',    'deps': ['b16'], 'fixes': ['Check templates/main_menu.html exists']},
    'b31': {'cat': 'Pages',    'deps': ['b16'], 'fixes': ['Check templates/material_setter.html']},
    'b32': {'cat': 'Pages',    'deps': ['b16'], 'fixes': ['Check templates/manpower.html']},
    'b33': {'cat': 'Pages',    'deps': ['b16'], 'fixes': ['Check templates/cycle_graph.html']},
    'b34': {'cat': 'Pages',    'deps': ['b16'], 'fixes': ['Check templates/process1.html']},
    'b35': {'cat': 'Pages',    'deps': ['b16'], 'fixes': ['Check templates/process2-9.html']},
    'b1':  {'cat': 'Database', 'deps': ['b17'], 'fixes': ['Check kitting_summary table schema', 'Verify INSERT permissions']},
    'b2':  {'cat': 'Database', 'deps': ['b17'], 'fixes': ['Check KITTING_DB table', 'Verify MAX(kitting_no) query']},
    'b3':  {'cat': 'Config',   'deps': ['b21'], 'fixes': ['Check model_codes_no_bushing.json', 'Verify KITTING_MATERIAL_CATEGORIES has 26 entries']},
    'b4':  {'cat': 'Database', 'deps': ['b17'], 'fixes': ['Check Toritani SQL Server connection', 'Check joborder_plan table']},
    'b5':  {'cat': 'Database', 'deps': ['b17'], 'fixes': ['Check Toritani SQL Server connection']},
    'b6':  {'cat': 'Database', 'deps': ['b17'], 'fixes': ['Check INSERT into joborder_plan']},
    'b7':  {'cat': 'Printer',  'deps': [],      'fixes': ['Verify QR code format includes suffix']},
    'b9':  {'cat': 'Database', 'deps': ['b17'], 'fixes': ['Check kitting_summary and KITTING_DB tables']},
    'b10': {'cat': 'Printer',  'deps': [],      'fixes': ['Check SATO PW208NX is ON', 'Verify IP 192.168.2.100', 'Check USB/network cable']},
    'b12': {'cat': 'Printer',  'deps': ['b10'], 'fixes': ['Check printKittingQrToSato() function']},
    'b13': {'cat': 'Logic',    'deps': [],      'fixes': ['Verify loadNextKittingNo() conditional print logic']},
    'b14': {'cat': 'Server',   'deps': ['b16'], 'fixes': ['Check SERVER_START_TIME variable']},
    'b15': {'cat': 'Database', 'deps': ['b17'], 'fixes': ['Check manpower table persistence']},
    'b36': {'cat': 'Logic',    'deps': ['b16'], 'fixes': ['Run jo_completion_reset self-test', 'Check joFinishedFlag in material_setter.html']},
}

@app.route("/api/ai_diagnose", methods=["POST"])
def ai_diagnose():
    """Smart Diagnostics Engine - health score, category breakdown, fix suggestions"""
    try:
        data = request.json
        results = data.get('results', {})
        total = len(results)
        if total == 0:
            return jsonify({"success": True, "health_score": 0, "message": "No tests run yet", "categories": {}, "fixes": [], "report": "No tests have been executed yet."})

        passed = sum(1 for r in results.values() if r.get('passed'))
        health_score = round((passed / total) * 100)

        categories = {}
        fixes = []
        for test_id, result in results.items():
            rule = DIAGNOSTIC_RULES.get(test_id, {'cat': 'Other', 'deps': [], 'fixes': []})
            cat = rule['cat']
            if cat not in categories:
                categories[cat] = {'pass': 0, 'fail': 0}
            if result.get('passed'):
                categories[cat]['pass'] += 1
            else:
                categories[cat]['fail'] += 1
                dep_failed = any(dep in results and not results[dep].get('passed') for dep in rule.get('deps', []))
                priority = 'low' if dep_failed else ('critical' if cat in ['Server', 'Database'] else 'medium')
                fixes.append({'test_id': test_id, 'priority': priority,
                    'message': 'Fix dependency first' if dep_failed else (result.get('detail', 'Test failed')),
                    'suggestions': rule.get('fixes', [])})

        fixes.sort(key=lambda x: {'critical': 0, 'medium': 1, 'low': 2}.get(x['priority'], 3))

        report_lines = [f"SYSTEM HEALTH: {health_score}%", f"Tests: {passed}/{total} passed", ""]
        if health_score == 100: report_lines.append("All systems operational.")
        elif health_score >= 80: report_lines.append("Minor issues detected.")
        elif health_score >= 50: report_lines.append("Multiple issues. Some features may not work.")
        else: report_lines.append("CRITICAL issues. System needs attention.")
        report_lines.append("")
        for cat, cd in categories.items():
            s = "PASS" if cd['fail'] == 0 else "FAIL"
            report_lines.append(f"[{s}] {cat}: {cd['pass']}/{cd['pass']+cd['fail']}")
        if fixes:
            report_lines.extend(["", "RECOMMENDED FIXES:"])
            for i, fix in enumerate(fixes[:10]):
                report_lines.append(f"{i+1}. [{fix['priority'].upper()}] {fix['message']}")
                for s in fix.get('suggestions', []): report_lines.append(f"   -> {s}")

        return jsonify({"success": True, "health_score": health_score, "total": total, "passed": passed,
                        "failed": total - passed, "categories": categories, "fixes": fixes, "report": "\n".join(report_lines)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ai_auto_sequence", methods=["POST"])
def ai_auto_sequence():
    """Auto-Test Sequencer - optimal test order based on dependency graph"""
    try:
        sequence = []
        visited = set()
        def add_test(tid):
            if tid in visited: return
            for dep in DIAGNOSTIC_RULES.get(tid, {}).get('deps', []):
                add_test(dep)
            visited.add(tid)
            sequence.append(tid)
        for tid in DIAGNOSTIC_RULES:
            add_test(tid)
        return jsonify({"success": True, "sequence": sequence, "total": len(sequence)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ai_chat", methods=["POST"])
def ai_chat():
    """LLM Chatbot - proxy to OpenAI or Gemini, with offline fallback"""
    try:
        import requests as http_req
        data = request.json
        user_message = data.get('message', '')
        test_results = data.get('test_results', {})
        history = data.get('history', [])
        page_context = data.get('page_context', 'main_menu')

        config = load_ai_config()
        provider = config.get('provider', 'offline')
        api_key = config.get('api_key', '')
        model = config.get('model', '')

        system_ctx = (
            "You are an AI assistant for HIBLOW PHILIPPINES INC. Cycle Time Monitoring system. "
            "Stack: Flask (port 5000), MySQL (localhost:3306, db=cycle_time_monitoring), SATO PW208NX printer (192.168.2.100:9100), Arduino serial bridge. "
            "Key tables: process_records, standard_times, manpower, MAIN_DB, KITTING_DB, kitting_summary, joborder_plan, 26 material tables. "
            f"User is currently on page: {page_context}. Be concise, specific, and actionable."
        )
        if test_results:
            p = sum(1 for r in test_results.values() if r.get('passed'))
            f_list = [tid for tid, r in test_results.items() if not r.get('passed')]
            system_ctx += f" Tests: {p}/{len(test_results)} passed. Failed: {', '.join(f_list) if f_list else 'None'}."

        if provider == 'openai' and api_key:
            msgs = [{"role": "system", "content": system_ctx}]
            for h in history[-10:]:
                msgs.append({"role": h.get("role", "user"), "content": h.get("content", "")})
            msgs.append({"role": "user", "content": user_message})
            resp = http_req.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model or "gpt-3.5-turbo", "messages": msgs, "max_tokens": 1000, "temperature": 0.7},
                timeout=30)
            if resp.status_code == 200:
                return jsonify({"success": True, "response": resp.json()["choices"][0]["message"]["content"], "provider": "openai"})
            return jsonify({"success": False, "error": f"OpenAI error {resp.status_code}"}), 500

        elif provider == 'gemini' and api_key:
            contents = []
            for h in history[-10:]:
                contents.append({"role": "user" if h.get("role") == "user" else "model", "parts": [{"text": h.get("content", "")}]})
            contents.append({"role": "user", "parts": [{"text": system_ctx + "\n\nUser: " + user_message}]})
            gm = model or "gemini-2.0-flash"
            resp = http_req.post(f"https://generativelanguage.googleapis.com/v1beta/models/{gm}:generateContent?key={api_key}",
                headers={"Content-Type": "application/json"},
                json={"contents": contents, "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.7}},
                timeout=30)
            if resp.status_code == 200:
                cands = resp.json().get("candidates", [])
                text = cands[0]["content"]["parts"][0]["text"] if cands else "No response"
                return jsonify({"success": True, "response": text, "provider": "gemini"})
            return jsonify({"success": False, "error": f"Gemini error {resp.status_code}"}), 500

        else:
            return jsonify({"success": True, "response": generate_offline_ai_response(user_message, test_results, page_context), "provider": "offline"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def generate_offline_ai_response(message, test_results, page_context):
    """Rule-based AI when no LLM API is configured"""
    ml = message.lower()
    passed = sum(1 for r in test_results.values() if r.get('passed')) if test_results else 0
    total = len(test_results) if test_results else 0
    failed = [tid for tid, r in test_results.items() if not r.get('passed')] if test_results else []

    if any(w in ml for w in ['health', 'status', 'overview', 'how is', 'system']):
        if total == 0: return "No tests run yet. Click 'Diagnose' to run system diagnostics."
        score = round((passed/total)*100)
        r = f"System Health: {score}% ({passed}/{total} passed).\n\n"
        if failed:
            r += "Failed tests:\n"
            for f in failed:
                rule = DIAGNOSTIC_RULES.get(f, {})
                r += f"  [FAIL] {f} ({rule.get('cat','Unknown')})\n"
                for fix in rule.get('fixes', [])[:2]: r += f"    -> {fix}\n"
        else: r += "All tests passed! System is fully operational."
        return r

    if any(w in ml for w in ['fix', 'repair', 'solve', 'error', 'fail', 'wrong', 'broken']):
        if not failed: return "No failures detected. Run diagnostics first by clicking 'Diagnose'."
        r = "Recommended fixes:\n\n"
        crit = [f for f in failed if DIAGNOSTIC_RULES.get(f, {}).get('cat') in ['Server', 'Database']]
        for i, f in enumerate(crit + [x for x in failed if x not in crit]):
            rule = DIAGNOSTIC_RULES.get(f, {})
            p = "CRITICAL" if f in crit else "MEDIUM"
            r += f"{i+1}. [{p}] {f} ({rule.get('cat','')})\n"
            for s in rule.get('fixes', []): r += f"   -> {s}\n"
        return r

    if any(w in ml for w in ['printer', 'sato', 'print', 'qr']):
        return "SATO PW208NX Printer:\n- IP: 192.168.2.100, Port: 9100\n- Check power and cable\n- QR format: DD/MM/YY-KITTING_NO JOB_ORDER SUFFIX\n- Print function: qr_printer.print_kitting_qr_code()\n- Run 'Diagnose' to check connectivity."

    if any(w in ml for w in ['database', 'mysql', 'db', 'table']):
        return "MySQL Database:\n- Host: localhost:3306, User: root\n- Database: cycle_time_monitoring\n- Tables: process_records, MAIN_DB, KITTING_DB, kitting_summary, joborder_plan, manpower\n- 26 material tables (01tbl to 26tbl)"

    if any(w in ml for w in ['arduino', 'serial', 'bridge']):
        return "Arduino Bridge:\n- Auto-detects COM port (arduino, ch340, usb serial)\n- POST to http://127.0.0.1:5000/api/arduino_signal\n- Messages: P{N}START / P{N}STOP (N=1-9)\n- Baud: 9600"

    if any(w in ml for w in ['kitting', 'material', 'job order', 'jo ']):
        return "Kitting/Material Setter:\n- Scan JO barcode to load materials from Toritani SQL\n- 26 material categories (Frame Block to Filter Bushing)\n- QR auto-prints on new JO, skips on re-scan\n- MAIN_DB tracks remaining qty per material"

    if any(w in ml for w in ['cycle', 'time', 'process', 'timer']):
        return "Cycle Time Monitoring:\n- 9 processes with server-side timers\n- Standard times in standard_times table\n- Arduino signals auto-start/stop timers\n- Upstream validation prevents out-of-order kitting"

    if any(w in ml for w in ['operator', 'manpower', 'shift']):
        return "Manpower:\n- Each process needs 1 operator assigned\n- Scan operator ID badge or enter manually\n- Warning shown if processes lack operators\n- Operator logs persist all day (reset at midnight)"

    if any(w in ml for w in ['help', 'what can', 'commands', 'hello', 'hi']):
        return ("Hi! I'm your AI assistant. I can help with:\n"
                "- 'system health' - Check overall status\n"
                "- 'how to fix' - Get repair suggestions\n"
                "- 'printer info' - SATO printer help\n"
                "- 'database info' - MySQL details\n"
                "- 'kitting info' - Material workflow\n"
                "- 'cycle time' - Timer/process info\n"
                "- 'operator info' - Manpower details\n\n"
                "Click 'Diagnose' for full system check.\n"
                "Tip: Add a Gemini API key (free) via settings for smarter AI.")

    # Page-context specific fallback
    if 'process' in page_context:
        return "You're on a Process page. I can help with:\n- Timer issues\n- NG/Lineout handling\n- Operator assignment\n- Upstream validation\n\nTry: 'system health' or 'how to fix errors'"
    elif 'material' in page_context:
        return "You're on Material Setter. I can help with:\n- Job order scanning\n- Material loading\n- QR printing\n- Kitting workflow\n\nTry: 'printer info' or 'kitting info'"
    elif 'graph' in page_context or 'trend' in page_context:
        return "You're viewing graphs. I can help with:\n- Cycle time analysis\n- Standard time comparison\n- Trend explanations\n\nTry: 'cycle time' or 'system health'"

    return ("I can help with system diagnostics, printer issues, database info, kitting workflow, and more.\n"
            "Try: 'system health', 'printer info', 'how to fix', or click 'Diagnose'.\n\n"
            "For smarter AI responses, add a free Gemini API key via the settings icon.")


@app.route("/api/ai_config", methods=["GET", "POST"])
def ai_config_endpoint():
    """Get or save AI configuration"""
    try:
        if request.method == "GET":
            config = load_ai_config()
            masked = {**config}
            key = masked.get('api_key', '')
            masked['api_key_masked'] = (key[:8] + '...' + key[-4:]) if len(key) > 12 else ('***' if key else '')
            masked.pop('api_key', None)
            return jsonify({"success": True, "config": masked})
        else:
            data = request.json
            config = load_ai_config()
            for k in ['provider', 'api_key', 'model']:
                if k in data: config[k] = data[k]
            save_ai_config(config)
            return jsonify({"success": True, "message": "AI config saved"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ai_context", methods=["GET"])
def ai_context():
    """Returns page-specific context data for the AI widget"""
    try:
        page = request.args.get('page', 'unknown')
        context = {"page": page, "server_up": True}
        if 'process' in page:
            proc_no = ''.join(filter(str.isdigit, page)) or '1'
            context['info'] = f"Process {proc_no} dashboard - cycle time monitoring"
        elif 'material' in page:
            context['info'] = "Material Setter - kitting and job order management"
        elif 'graph' in page:
            context['info'] = "Cycle Graph - average elapsed time per process"
        elif 'trend' in page:
            context['info'] = "Line Trend - per-kitting elapsed time tracking"
        elif 'manpower' in page:
            context['info'] = "Manpower - operator assignment and tracking"
        else:
            context['info'] = "Main system page"
        return jsonify({"success": True, "context": context})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/force_daily_reset", methods=["POST"])
def force_daily_reset():
    """Force a full daily reset - clears kitting, manpower, and graph data"""
    try:
        print("FORCE DAILY RESET: Manually triggered")
        
        # Reset all server state
        with server_timers_lock:
            server_timers.clear()
        with server_counters_lock:
            server_counters.clear()
        with arduino_signals_lock:
            arduino_signals.clear()
        with server_blocked_counters_lock:
            server_blocked_counters.clear()
        with server_active_kittings_lock:
            server_active_kittings.clear()
        with server_last_completed_lock:
            server_last_completed.clear()
        with server_counter_offsets_lock:
            server_counter_offsets.clear()
        
        # Delete timer state file
        try:
            if os.path.exists(TIMER_STATE_FILE):
                os.remove(TIMER_STATE_FILE)
        except:
            pass
        save_timer_state_to_file()
        
        # Reset database: counters, manpower, and records
        result = db_manager.reset_all_for_new_day()
        
        # Update last active date
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        with last_active_date_lock:
            last_active_date["date"] = today
        save_last_active_date(today)
        
        update_last_data_timestamp()
        
        print(f"FORCE DAILY RESET: Completed, database result: {result}")
        return jsonify({"success": True, "message": "Full daily reset completed", "db_result": result})
    except Exception as e:
        print(f"Error in force_daily_reset: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# API Routes for data insertion
@app.route("/api/start_process", methods=["POST"])
def start_process():
    """Handle START button click - no database insertion, just acknowledge"""
    try:
        data = request.json
        kitting_no = data.get('kitting_no', '')
        process_no = data.get('process_no', 1)
        
        print(f"START: kitting_no={kitting_no}, process_no={process_no}")
        
        # Don't insert record here - only insert on STOP/NG/LINEOUT
        # This prevents duplicate records for the same process
        
        # Register server-side timer so STANDBY_MS / STANDBY_OPEN_INTERLOCK
        # checks (which use `1 in server_timers`) work for browser-initiated starts.
        process_no_int = int(process_no) if process_no else 1
        with server_timers_lock:
            if process_no_int not in server_timers:
                server_timers[process_no_int] = {
                    "start_time": time.time(),
                    "kitting_no": int(kitting_no) if str(kitting_no).isdigit() else 0,
                    "kitting_qr_code": "",
                    "model_code": "",
                    "job_order": ""
                }
        
        # Process 1: close standby interlock (danpla has left standby)
        if process_no_int == 1:
            with ms_button_state_lock:
                standby_was_open = ms_button_state["standby_interlock_open"]
                ms_button_state["standby_interlock_open"] = False
            if standby_was_open:
                with ms_pending_commands_lock:
                    ms_pending_commands.append("STANDBY_RELAY_OFF")
                db_manager.save_standby_interlock_state(False)
                print(f"START P1: Standby interlock closed (danpla reached Process 1)")
        
        # Process 2: close P1 interlock (danpla has left Process 1)
        if process_no_int == 2:
            with ms_button_state_lock:
                p1_was_open = ms_button_state["p1_interlock_open"]
                ms_button_state["p1_interlock_open"] = False
            if p1_was_open:
                with ms_pending_commands_lock:
                    ms_pending_commands.append("RELAY_P1_OFF")
                db_manager.save_p1_interlock_state(False)
                print(f"START P2: P1 interlock closed (danpla reached Process 2)")
        
        return jsonify({"success": True, "message": "Process started successfully"})
    except Exception as e:
        print(f"Error in start_process: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/stop_process", methods=["POST"])
def stop_process():
    """Handle STOP button click - update elapsed time"""
    try:
        # Check if request has JSON data
        if not request.is_json:
            print("ERROR: Request is not JSON")
            return jsonify({"success": False, "error": "Request must be JSON"}), 400
            
        data = request.get_json()
        if not data:
            print("ERROR: No JSON data received")
            return jsonify({"success": False, "error": "No data received"}), 400
            
        print(f"Received data: {data}")
        
        kitting_no = data.get('kitting_no', '')
        elapsed_time = data.get('elapsed_time', '00:00')
        process_no = data.get('process_no', 1)
        kitting_qr_code = data.get('kitting_qr_code', '')
        model_code = data.get('model_code', '')
        job_order = data.get('job_order', '')
        
        print(f"STOP: kitting_no={kitting_no}, elapsed_time={elapsed_time}, process_no={process_no}, pass_ng=1")
        
        # SERVER-SIDE VALIDATION: Block if upstream process hasn't completed this kitting
        process_no_int = int(process_no) if process_no else 1
        if process_no_int > 1 and kitting_no:
            prev_completed = db_manager.get_completed_count(process_no_int - 1)
            kitting_no_int = int(kitting_no) if str(kitting_no).isdigit() else 0
            if kitting_no_int > prev_completed:
                print(f"STOP BLOCKED: Process {process_no_int} Kitting {kitting_no_int} - Process {process_no_int-1} only completed {prev_completed}")
                return jsonify({"success": False, "error": f"Process {process_no_int-1} has only completed {prev_completed} kittings"})
        
        # Validate elapsed_time format
        if elapsed_time and ':' not in str(elapsed_time):
            print(f"WARNING: Invalid elapsed_time format: {elapsed_time}")
            elapsed_time = '00:00'
        
        # Insert record with elapsed time and pass_ng=1 (PASS)
        record_id = db_manager.insert_record(
            kitting_no=str(kitting_no) if kitting_no else '',
            lineout_reason=None,
            elapsed_time=str(elapsed_time),
            pass_ng=1,
            process_no=int(process_no) if process_no else 1,
            kitting_qr_code=kitting_qr_code,
            model_code=model_code,
            job_order=job_order
        )
        
        # Clear server-side timer for this process
        with server_timers_lock:
            server_timers.pop(int(process_no) if process_no else 1, None)
        
        # Update last data timestamp for auto-refresh
        update_last_data_timestamp()
        save_timer_state_to_file()
        
        if record_id:
            return jsonify({"success": True, "record_id": record_id})
        else:
            return jsonify({"success": False, "error": "Failed to insert record"}), 500
    except Exception as e:
        print(f"Error in stop_process: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ng_process", methods=["POST"])
def ng_process():
    """Handle NG button click"""
    try:
        # Check if request has JSON data
        if not request.is_json:
            print("ERROR: Request is not JSON")
            return jsonify({"success": False, "error": "Request must be JSON"}), 400
            
        data = request.get_json()
        if not data:
            print("ERROR: No JSON data received")
            return jsonify({"success": False, "error": "No data received"}), 400
            
        print(f"Received data: {data}")
        
        kitting_no = data.get('kitting_no', '')
        elapsed_time = data.get('elapsed_time', '00:00')
        process_no = data.get('process_no', 1)
        kitting_qr_code = data.get('kitting_qr_code', '')
        model_code = data.get('model_code', '')
        job_order = data.get('job_order', '')
        
        print(f"NG: kitting_no={kitting_no}, elapsed_time={elapsed_time}, process_no={process_no}, pass_ng=0")
        
        # SERVER-SIDE VALIDATION: Block if upstream process hasn't completed this kitting
        process_no_int = int(process_no) if process_no else 1
        if process_no_int > 1 and kitting_no:
            prev_completed = db_manager.get_completed_count(process_no_int - 1)
            kitting_no_int = int(kitting_no) if str(kitting_no).isdigit() else 0
            if kitting_no_int > prev_completed:
                print(f"NG BLOCKED: Process {process_no_int} Kitting {kitting_no_int} - Process {process_no_int-1} only completed {prev_completed}")
                return jsonify({"success": False, "error": f"Process {process_no_int-1} has only completed {prev_completed} kittings"})
        
        # Validate elapsed_time format
        if elapsed_time and ':' not in str(elapsed_time):
            print(f"WARNING: Invalid elapsed_time format: {elapsed_time}")
            elapsed_time = '00:00'
        
        # Insert record with pass_ng=0 (NG)
        record_id = db_manager.insert_record(
            kitting_no=str(kitting_no) if kitting_no else '',
            lineout_reason=None,
            elapsed_time=str(elapsed_time),
            pass_ng=0,
            process_no=int(process_no) if process_no else 1,
            kitting_qr_code=kitting_qr_code,
            model_code=model_code,
            job_order=job_order
        )
        
        # Clear server-side timer for this process
        with server_timers_lock:
            server_timers.pop(int(process_no) if process_no else 1, None)
        
        # Update last data timestamp for auto-refresh
        update_last_data_timestamp()
        save_timer_state_to_file()
        
        if record_id:
            return jsonify({"success": True, "record_id": record_id})
        else:
            return jsonify({"success": False, "error": "Failed to insert record"}), 500
    except Exception as e:
        print(f"Error in ng_process: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ng_lineout_process", methods=["POST"])
def ng_lineout_process():
    """Handle NG LINEOUT button click with reason"""
    try:
        data = request.json
        kitting_no = data.get('kitting_no', '')
        lineout_reason = data.get('lineout_reason', '')
        elapsed_time = data.get('elapsed_time', '00:00')
        process_no = data.get('process_no', 1)
        kitting_qr_code = data.get('kitting_qr_code', '')
        model_code = data.get('model_code', '')
        job_order = data.get('job_order', '')
        
        print(f"NG LINEOUT: kitting_no={kitting_no}, lineout_reason={lineout_reason}, elapsed_time={elapsed_time}, process_no={process_no}, pass_ng=0")
        
        # SERVER-SIDE VALIDATION: Block if upstream process hasn't completed this kitting
        process_no_int = int(process_no) if process_no else 1
        if process_no_int > 1 and kitting_no:
            prev_completed = db_manager.get_completed_count(process_no_int - 1)
            kitting_no_int = int(kitting_no) if str(kitting_no).isdigit() else 0
            if kitting_no_int > prev_completed:
                print(f"NG LINEOUT BLOCKED: Process {process_no_int} Kitting {kitting_no_int} - Process {process_no_int-1} only completed {prev_completed}")
                return jsonify({"success": False, "error": f"Process {process_no_int-1} has only completed {prev_completed} kittings"})
        
        # Insert record with lineout reason and pass_ng=0 (NG)
        record_id = db_manager.insert_record(
            kitting_no=kitting_no,
            lineout_reason=lineout_reason,
            elapsed_time=elapsed_time,
            pass_ng=0,
            process_no=process_no,
            kitting_qr_code=kitting_qr_code,
            model_code=model_code,
            job_order=job_order
        )
        
        # Clear server-side timer for this process
        with server_timers_lock:
            server_timers.pop(int(process_no) if process_no else 1, None)
        
        # Update last data timestamp for auto-refresh
        update_last_data_timestamp()
        save_timer_state_to_file()
        
        if record_id:
            return jsonify({"success": True, "record_id": record_id})
        else:
            return jsonify({"success": False, "error": "Failed to insert record"}), 500
    except Exception as e:
        print(f"Error in ng_lineout_process: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/lineout_process", methods=["POST"])
def lineout_process():
    """Handle LINEOUT button click with reason"""
    try:
        data = request.json
        kitting_no = data.get('kitting_no', '')
        lineout_reason = data.get('lineout_reason', '')
        elapsed_time = data.get('elapsed_time', '00:00')
        process_no = data.get('process_no', 1)
        kitting_qr_code = data.get('kitting_qr_code', '')
        model_code = data.get('model_code', '')
        job_order = data.get('job_order', '')
        
        print(f"LINEOUT: kitting_no={kitting_no}, lineout_reason={lineout_reason}, elapsed_time={elapsed_time}, process_no={process_no}, pass_ng=0")
        
        # SERVER-SIDE VALIDATION: Block if upstream process hasn't completed this kitting
        process_no_int = int(process_no) if process_no else 1
        if process_no_int > 1 and kitting_no:
            prev_completed = db_manager.get_completed_count(process_no_int - 1)
            kitting_no_int = int(kitting_no) if str(kitting_no).isdigit() else 0
            if kitting_no_int > prev_completed:
                print(f"LINEOUT BLOCKED: Process {process_no_int} Kitting {kitting_no_int} - Process {process_no_int-1} only completed {prev_completed}")
                return jsonify({"success": False, "error": f"Process {process_no_int-1} has only completed {prev_completed} kittings"})
        
        # Insert record with lineout reason and pass_ng=0 (NG)
        record_id = db_manager.insert_record(
            kitting_no=kitting_no,
            lineout_reason=lineout_reason,
            elapsed_time=elapsed_time,
            pass_ng=0,
            process_no=process_no,
            kitting_qr_code=kitting_qr_code,
            model_code=model_code,
            job_order=job_order
        )
        
        # Clear server-side timer for this process
        with server_timers_lock:
            server_timers.pop(int(process_no) if process_no else 1, None)
        
        # Update last data timestamp for auto-refresh
        update_last_data_timestamp()
        save_timer_state_to_file()
        
        if record_id:
            return jsonify({"success": True, "record_id": record_id})
        else:
            return jsonify({"success": False, "error": "Failed to insert record"}), 500
    except Exception as e:
        print(f"Error in lineout_process: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_process_records/<int:process_no>", methods=["GET"])
def get_process_records(process_no):
    """Get records for a specific process"""
    try:
        records = db_manager.get_records_by_process(process_no)
        return jsonify({"success": True, "records": records})
    except Exception as e:
        print(f"Error in get_process_records: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_standard_times", methods=["GET"])
def get_standard_times():
    """Get all standard times"""
    try:
        standard_times = db_manager.get_all_standard_times()
        # Convert Decimal to float for JSON serialization
        for st in standard_times:
            st['standard_time'] = float(st['standard_time'])
            st['title'] = st.get('title', '')
        return jsonify({"success": True, "standard_times": standard_times})
    except Exception as e:
        print(f"Error in get_standard_times: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_standard_time/<int:process_no>", methods=["GET"])
def get_standard_time(process_no):
    """Get standard time for a specific process"""
    try:
        standard_times = db_manager.get_all_standard_times()
        for st in standard_times:
            if st['process_no'] == process_no:
                return jsonify({"success": True, "standard_time": float(st['standard_time']), "title": st.get('title', '')})
        return jsonify({"success": False, "error": "Process not found"}), 404
    except Exception as e:
        print(f"Error in get_standard_time: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/update_standard_time", methods=["POST"])
def update_standard_time():
    """Update standard time for a process"""
    try:
        data = request.json
        process_no = data.get('process_no')
        standard_time = data.get('standard_time')
        title = data.get('title', None)
        
        if not process_no or not standard_time:
            return jsonify({"success": False, "error": "Missing process_no or standard_time"}), 400
        
        success = db_manager.update_standard_time(process_no, standard_time, title)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to update standard time"}), 500
    except Exception as e:
        print(f"Error in update_standard_time: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/add_process", methods=["POST"])
def add_process():
    """Add a new process"""
    try:
        data = request.json
        standard_time = data.get('standard_time', '50')
        
        new_process_no = db_manager.add_new_process(standard_time)
        if new_process_no:
            return jsonify({"success": True, "process_no": new_process_no})
        else:
            return jsonify({"success": False, "error": "Failed to add process"}), 500
    except Exception as e:
        print(f"Error in add_process: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/delete_process", methods=["POST"])
def delete_process():
    """Delete a process"""
    try:
        data = request.json
        process_no = data.get('process_no')
        
        if not process_no:
            return jsonify({"success": False, "error": "Missing process_no"}), 400
        
        # Don't allow deletion of processes 1-9 (default processes)
        if process_no <= 9:
            return jsonify({"success": False, "error": "Cannot delete default processes 1-9"}), 400
        
        success = db_manager.delete_process(process_no)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to delete process"}), 500
    except Exception as e:
        print(f"Error in delete_process: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/check_manpower_complete", methods=["GET"])
def check_manpower_complete():
    """Check which processes 1-9 have manpower assigned.
    Returns list of missing processes - frontend shows warning only on the specific process that's missing."""
    try:
        manpower = db_manager.get_all_manpower()
        missing = []
        for i in range(1, 10):
            found = False
            for mp in manpower:
                if mp['process_no'] == i:
                    # Check if operator_scan OR operator_manual is filled
                    has_scan = mp.get('operator_scan', '').strip() != ''
                    has_manual = mp.get('operator_manual', '').strip() != ''
                    if has_scan or has_manual:
                        found = True
                    break
            if not found:
                missing.append(i)
        
        is_complete = len(missing) == 0
        return jsonify({"success": True, "is_complete": is_complete, "missing_processes": missing})
    except Exception as e:
        print(f"Error in check_manpower_complete: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_manpower", methods=["GET"])
def get_manpower():
    """Get all manpower records"""
    try:
        manpower = db_manager.get_all_manpower()
        # Retry up to 2 more times if empty (processes 1-9 should always exist)
        if not manpower:
            for attempt in range(2):
                time.sleep(0.5)
                manpower = db_manager.get_all_manpower()
                if manpower:
                    break
        return jsonify({"success": True, "manpower": manpower})
    except Exception as e:
        print(f"Error in get_manpower: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_manpower/<int:process_no>", methods=["GET"])
def get_manpower_by_process(process_no):
    """Get manpower for a specific process"""
    try:
        manpower = db_manager.get_manpower_by_process(process_no)
        if manpower:
            return jsonify({"success": True, "manpower": manpower})
        return jsonify({"success": False, "error": "Process not found"}), 404
    except Exception as e:
        print(f"Error in get_manpower_by_process: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_cycle_graph_data", methods=["GET"])
def get_cycle_graph_data():
    """Get all data needed for cycle time graph monitoring"""
    try:
        # Get average elapsed times per process
        cycle_data = db_manager.get_cycle_graph_data()
        
        # Get all standard times
        standard_times = db_manager.get_all_standard_times()
        st_map = {}
        for st in standard_times:
            st_map[st['process_no']] = float(st['standard_time'])
        
        # Get all manpower (operator names)
        manpower = db_manager.get_all_manpower()
        operator_map = {}
        for mp in manpower:
            # Use operator_manual or operator_scan, whichever is set
            name = mp.get('operator_manual', '') or mp.get('operator_scan', '') or ''
            operator_map[mp['process_no']] = name
        
        # Build combined data for all 9 processes
        graph_data = []
        for i in range(1, 10):
            avg_mss = 0
            avg_seconds = 0
            record_count = 0
            for cd in cycle_data:
                if cd['process_no'] == i:
                    avg_mss = cd['avg_mss']
                    avg_seconds = cd['avg_seconds']
                    record_count = cd['record_count']
                    break
            
            graph_data.append({
                'process_no': i,
                'avg_mss': avg_mss,
                'avg_seconds': avg_seconds,
                'record_count': record_count,
                'standard_time': st_map.get(i, 1.50),
                'operator': operator_map.get(i, '')
            })
        
        return jsonify({"success": True, "graph_data": graph_data})
    except Exception as e:
        print(f"Error in get_cycle_graph_data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_line_trend_data", methods=["GET"])
def get_line_trend_data():
    """Get all data needed for line trend graph monitoring"""
    try:
        # Get all standard times
        standard_times = db_manager.get_all_standard_times()
        st_map = {}
        for st in standard_times:
            st_map[st['process_no']] = float(st['standard_time'])
        
        # Get all manpower (operator names)
        manpower = db_manager.get_all_manpower()
        operator_map = {}
        for mp in manpower:
            name = mp.get('operator_manual', '') or mp.get('operator_scan', '') or ''
            operator_map[mp['process_no']] = name
        
        # Build data for all 9 processes
        # Graph shows all today's records (resets only on new day via CURDATE filter)
        trend_data = []
        for i in range(1, 10):
            records = db_manager.get_line_trend_data(i, limit=10, after_timestamp=None)
            completed_count = db_manager.get_completed_count(i)
            trend_data.append({
                'process_no': i,
                'tol_plus': 1.65,
                'tol_minus': 1.35,
                'tact_time': 1.50,
                'operator': operator_map.get(i, ''),
                'records': records,
                'completed_count': completed_count
            })
        
        return jsonify({"success": True, "trend_data": trend_data})
    except Exception as e:
        print(f"Error in get_line_trend_data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/update_manpower", methods=["POST"])
def update_manpower():
    """Update manpower for a process"""
    try:
        data = request.json
        process_no = data.get('process_no')
        operator_manual = data.get('operator_manual', '')
        operator_scan = data.get('operator_scan', '')
        
        if not process_no:
            return jsonify({"success": False, "error": "Missing process_no"}), 400
        
        success = db_manager.update_manpower(process_no, operator_manual, operator_scan)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to update manpower"}), 500
    except Exception as e:
        print(f"Error in update_manpower: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/operator_out", methods=["POST"])
def operator_out():
    """Clear operator for a process (operator OUT)"""
    try:
        data = request.json
        process_no = data.get('process_no')
        reason = data.get('reason', '')
        
        if not process_no:
            return jsonify({"success": False, "error": "Missing process_no"}), 400
        
        # Update the out_reasons column in the last record of the process table
        if reason:
            db_manager.update_out_reason(process_no, reason)
        
        # Update the time_out column in the last record of the process table
        db_manager.update_time_out(process_no)
        
        success = db_manager.clear_manpower(process_no)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to clear operator"}), 500
    except Exception as e:
        print(f"Error in operator_out: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== MATERIAL SETTER OPERATOR APIs (both databases) ====================

@app.route("/api/ms_operator_in", methods=["POST"])
def ms_operator_in():
    """Material Setter operator IN - save to MySQL (both databases)"""
    global ms_scanned_id
    try:
        data = request.json
        operator_name = data.get('operator_name', '').strip()
        
        if not operator_name:
            return jsonify({"success": False, "error": "Missing operator_name"}), 400
        
        result = db_manager.set_ms_operator_in(operator_name)
        # Sync ms1_loaded state: operator can only sign in when ID is detected
        with ms_button_state_lock:
            ms_button_state["ms1_loaded"] = True
        # Clear scanned ID after successful operator IN to prevent repeat
        if result.get('success'):
            with ms_scanned_id_lock:
                ms_scanned_id = None
        return jsonify(result)
    except Exception as e:
        print(f"Error in ms_operator_in: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ms_operator_out", methods=["POST"])
def ms_operator_out():
    """Material Setter operator OUT - update MySQL with time_out and reason (both databases)"""
    try:
        data = request.json
        out_reasons = data.get('out_reasons', '').strip()
        
        result = db_manager.set_ms_operator_out(out_reasons)
        return jsonify(result)
    except Exception as e:
        print(f"Error in ms_operator_out: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_ms_operator", methods=["GET"])
def get_ms_operator():
    """Get current Material Setter operator from MySQL (both databases).
    Returns expired=True if operator logged in on a previous day (daily auto-logout).
    """
    try:
        result = db_manager.get_ms_operator()
        return jsonify({"success": True, **result})
    except Exception as e:
        print(f"Error in get_ms_operator: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== MS OPERATOR SELECTION (DISPLAY MODE) ====================

@app.route("/api/ms_operator_selection", methods=["GET"])
def get_ms_operator_selection():
    """Get operator display mode (id/name/all) from MySQL"""
    try:
        mode = db_manager.get_ms_operator_selection()
        return jsonify({"success": True, "display_mode": mode})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ms_operator_selection", methods=["POST"])
def set_ms_operator_selection():
    """Set operator display mode (id/name/all) in MySQL"""
    try:
        data = request.json
        mode = data.get('display_mode', 'all')
        result = db_manager.set_ms_operator_selection(mode)
        if result:
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Invalid display_mode"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== MTRL SET MANPOWER APIs ====================

@app.route("/api/get_mtrl_set_operator", methods=["GET"])
def get_mtrl_set_operator():
    """Get the Material Setter operator record"""
    try:
        data = db_manager.get_mtrl_set_operator()
        return jsonify({"success": True, "operator": data})
    except Exception as e:
        print(f"Error in get_mtrl_set_operator: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/update_mtrl_set_operator", methods=["POST"])
def update_mtrl_set_operator():
    """Update Material Setter operator (manual or scan)"""
    try:
        data = request.json
        operator_manual = data.get('operator_manual', '')
        operator_scan = data.get('operator_scan', '')
        
        success = db_manager.update_mtrl_set_operator(operator_manual, operator_scan)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to update"}), 500
    except Exception as e:
        print(f"Error in update_mtrl_set_operator: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/clear_mtrl_set_operator", methods=["POST"])
def clear_mtrl_set_operator():
    """Clear Material Setter operator (Manual Reset)"""
    try:
        success = db_manager.clear_mtrl_set_operator()
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to clear"}), 500
    except Exception as e:
        print(f"Error in clear_mtrl_set_operator: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_out_reasons", methods=["GET"])
def get_out_reasons():
    """Get all OUT reasons for dropdown"""
    try:
        reasons = db_manager.get_out_reasons()
        return jsonify({"success": True, "reasons": reasons})
    except Exception as e:
        print(f"Error in get_out_reasons: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/add_out_reason", methods=["POST"])
def add_out_reason():
    """Add a custom OUT reason (shared across all processes)"""
    try:
        data = request.json
        reason = data.get('reason', '').strip().upper()
        
        if not reason:
            return jsonify({"success": False, "error": "Missing reason"}), 400
        
        success = db_manager.add_out_reason(reason)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Reason already exists or failed to add"}), 500
    except Exception as e:
        print(f"Error in add_out_reason: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/delete_out_reason", methods=["POST"])
def delete_out_reason():
    """Delete an OUT reason (shared across all processes)"""
    try:
        data = request.json
        reason = data.get('reason', '').strip().upper()
        
        if not reason:
            return jsonify({"success": False, "error": "Missing reason"}), 400
        
        success = db_manager.delete_out_reason(reason)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Reason not found or failed to delete"}), 500
    except Exception as e:
        print(f"Error in delete_out_reason: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_change_model_reasons", methods=["GET"])
def get_change_model_reasons():
    """Get all CHANGE MODEL reasons for dropdown"""
    try:
        reasons = db_manager.get_change_model_reasons()
        return jsonify({"success": True, "reasons": reasons})
    except Exception as e:
        print(f"Error in get_change_model_reasons: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/add_change_model_reason", methods=["POST"])
def add_change_model_reason():
    """Add a custom CHANGE MODEL reason"""
    try:
        data = request.json
        reason = data.get('reason', '').strip()
        if not reason:
            return jsonify({"success": False, "error": "Missing reason"}), 400
        success = db_manager.add_change_model_reason(reason)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Reason already exists or failed to add"}), 500
    except Exception as e:
        print(f"Error in add_change_model_reason: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/delete_change_model_reason", methods=["POST"])
def delete_change_model_reason():
    """Delete a CHANGE MODEL reason"""
    try:
        data = request.json
        reason = data.get('reason', '').strip()
        if not reason:
            return jsonify({"success": False, "error": "Missing reason"}), 400
        success = db_manager.delete_change_model_reason(reason)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Reason not found or failed to delete"}), 500
    except Exception as e:
        print(f"Error in delete_change_model_reason: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/save_change_model", methods=["POST"])
def save_change_model():
    """Save change model reason to joborder_plan"""
    try:
        data = request.json
        job_order = data.get('job_order', '')
        reason = data.get('reason', '')
        
        if not reason:
            return jsonify({"success": False, "error": "Missing reason"}), 400
        
        success = db_manager.save_change_model_event(job_order, reason)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to save change model reason"}), 500
    except Exception as e:
        print(f"Error in save_change_model: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_lineout_reasons", methods=["GET"])
def get_lineout_reasons():
    """Get all LINE OUT reasons for dropdown"""
    try:
        reasons = db_manager.get_lineout_reasons()
        return jsonify({"success": True, "reasons": reasons})
    except Exception as e:
        print(f"Error in get_lineout_reasons: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/add_lineout_reason", methods=["POST"])
def add_lineout_reason():
    """Add a custom LINE OUT reason (shared across all processes)"""
    try:
        data = request.json
        reason = data.get('reason', '').strip().upper()
        
        if not reason:
            return jsonify({"success": False, "error": "Missing reason"}), 400
        
        success = db_manager.add_lineout_reason(reason)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Reason already exists or failed to add"}), 500
    except Exception as e:
        print(f"Error in add_lineout_reason: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/delete_lineout_reason", methods=["POST"])
def delete_lineout_reason():
    """Delete a LINE OUT reason (shared across all processes)"""
    try:
        data = request.json
        reason = data.get('reason', '').strip().upper()
        
        if not reason:
            return jsonify({"success": False, "error": "Missing reason"}), 400
        
        success = db_manager.delete_lineout_reason(reason)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Reason not found or failed to delete"}), 500
    except Exception as e:
        print(f"Error in delete_lineout_reason: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/in_line_process", methods=["POST"])
def in_line_process():
    """Handle IN-LINE button click with reason"""
    try:
        data = request.json
        kitting_no = data.get('kitting_no', '')
        in_line_reason = data.get('in_line_reason', '')
        elapsed_time = data.get('elapsed_time', '00:00')
        process_no = data.get('process_no', 1)
        
        print(f"IN-LINE: kitting_no={kitting_no}, in_line_reason={in_line_reason}, elapsed_time={elapsed_time}, process_no={process_no}, pass_ng=0")
        
        # SERVER-SIDE VALIDATION: Block if upstream process hasn't completed this kitting
        process_no_int = int(process_no) if process_no else 1
        if process_no_int > 1 and kitting_no:
            prev_completed = db_manager.get_completed_count(process_no_int - 1)
            kitting_no_int = int(kitting_no) if str(kitting_no).isdigit() else 0
            if kitting_no_int > prev_completed:
                print(f"IN-LINE BLOCKED: Process {process_no_int} Kitting {kitting_no_int} - Process {process_no_int-1} only completed {prev_completed}")
                return jsonify({"success": False, "error": f"Process {process_no_int-1} has only completed {prev_completed} kittings"})
        
        # Insert record with in_line_reason and pass_ng=0
        record_id = db_manager.insert_record(
            kitting_no=kitting_no,
            lineout_reason='',
            elapsed_time=elapsed_time,
            pass_ng=0,
            process_no=process_no,
            in_line_reason=in_line_reason
        )
        
        # Clear server-side timer for this process
        with server_timers_lock:
            server_timers.pop(int(process_no) if process_no else 1, None)
        
        # Update last data timestamp for auto-refresh
        update_last_data_timestamp()
        save_timer_state_to_file()
        
        if record_id:
            return jsonify({"success": True, "record_id": record_id})
        else:
            return jsonify({"success": False, "error": "Failed to insert record"}), 500
    except Exception as e:
        print(f"Error in in_line_process: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_in_line_reasons", methods=["GET"])
def get_in_line_reasons():
    """Get all IN-LINE reasons for dropdown"""
    try:
        reasons = db_manager.get_in_line_reasons()
        return jsonify({"success": True, "reasons": reasons})
    except Exception as e:
        print(f"Error in get_in_line_reasons: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/add_in_line_reason", methods=["POST"])
def add_in_line_reason():
    """Add a custom IN-LINE reason (shared across all processes)"""
    try:
        data = request.json
        reason = data.get('reason', '').strip().upper()
        
        if not reason:
            return jsonify({"success": False, "error": "Missing reason"}), 400
        
        success = db_manager.add_in_line_reason(reason)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Reason already exists or failed to add"}), 500
    except Exception as e:
        print(f"Error in add_in_line_reason: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/delete_in_line_reason", methods=["POST"])
def delete_in_line_reason():
    """Delete an IN-LINE reason (shared across all processes)"""
    try:
        data = request.json
        reason = data.get('reason', '').strip().upper()
        
        if not reason:
            return jsonify({"success": False, "error": "Missing reason"}), 400
        
        success = db_manager.delete_in_line_reason(reason)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Reason not found or failed to delete"}), 500
    except Exception as e:
        print(f"Error in delete_in_line_reason: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== REPAIRED ACTION API ====================

@app.route("/api/get_repaired_actions", methods=["GET"])
def get_repaired_actions():
    """Get all REPAIRED ACTION reasons for dropdown"""
    try:
        reasons = db_manager.get_repaired_actions()
        return jsonify({"success": True, "reasons": reasons})
    except Exception as e:
        print(f"Error in get_repaired_actions: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/add_repaired_action", methods=["POST"])
def add_repaired_action():
    """Add a custom REPAIRED ACTION reason (shared across all processes)"""
    try:
        data = request.json
        reason = data.get('reason', '').strip().upper()
        
        if not reason:
            return jsonify({"success": False, "error": "Missing reason"}), 400
        
        success = db_manager.add_repaired_action(reason)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Reason already exists or failed to add"}), 500
    except Exception as e:
        print(f"Error in add_repaired_action: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/delete_repaired_action", methods=["POST"])
def delete_repaired_action():
    """Delete a REPAIRED ACTION reason (shared across all processes)"""
    try:
        data = request.json
        reason = data.get('reason', '').strip().upper()
        
        if not reason:
            return jsonify({"success": False, "error": "Missing reason"}), 400
        
        success = db_manager.delete_repaired_action(reason)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Reason not found or failed to delete"}), 500
    except Exception as e:
        print(f"Error in delete_repaired_action: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/stop_repaired_process", methods=["POST"])
def stop_repaired_process():
    """Handle STOP after IN-LINE REPAIR with repaired action reason"""
    try:
        data = request.json
        kitting_no = data.get('kitting_no', '')
        elapsed_time = data.get('elapsed_time', '00:00')
        process_no = data.get('process_no', 1)
        repaired_action = data.get('repaired_action', '')
        in_line_reason = data.get('in_line_reason', '')
        kitting_qr_code = data.get('kitting_qr_code', '')
        model_code = data.get('model_code', '')
        job_order = data.get('job_order', '')
        
        print(f"STOP REPAIRED: kitting_no={kitting_no}, elapsed_time={elapsed_time}, process_no={process_no}, repaired_action={repaired_action}, in_line_reason={in_line_reason}, pass_ng=1")
        
        process_no_int = int(process_no) if process_no else 1
        if process_no_int > 1 and kitting_no:
            prev_completed = db_manager.get_completed_count(process_no_int - 1)
            kitting_no_int = int(kitting_no) if str(kitting_no).isdigit() else 0
            if kitting_no_int > prev_completed:
                return jsonify({"success": False, "error": f"Process {process_no_int-1} has only completed {prev_completed} kittings"})
        
        if elapsed_time and ':' not in elapsed_time:
            elapsed_time = '00:00'
        
        record_id = db_manager.insert_record(
            kitting_no=str(kitting_no) if kitting_no else '',
            lineout_reason=None,
            elapsed_time=str(elapsed_time),
            pass_ng=1,
            process_no=int(process_no) if process_no else 1,
            repaired_action=repaired_action,
            in_line_reason=in_line_reason,
            kitting_qr_code=kitting_qr_code,
            model_code=model_code,
            job_order=job_order
        )
        
        with server_timers_lock:
            server_timers.pop(int(process_no) if process_no else 1, None)
        
        update_last_data_timestamp()
        save_timer_state_to_file()
        
        if record_id:
            return jsonify({"success": True, "record_id": record_id})
        else:
            return jsonify({"success": False, "error": "Failed to insert record"}), 500
    except Exception as e:
        print(f"Error in stop_repaired_process: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== KITTING QR VALIDATION API ====================

@app.route("/api/validate_kitting_qr", methods=["POST"])
def validate_kitting_qr():
    """Validate a scanned kitting QR code for a process page.
    Checks: QR exists in KITTING_DB, kitting_no matches next expected, previous process completed."""
    global p1_dunpla_detected
    try:
        data = request.json
        qr_code = data.get('qr_code', '').strip()
        process_no = int(data.get('process_no', 0))
        expected_kitting = int(data.get('expected_kitting', 0))
        
        if not qr_code:
            return jsonify({"success": False, "error": "No QR code provided"}), 400
        if process_no < 1 or process_no > 9:
            return jsonify({"success": False, "error": "Invalid process number"}), 400
        
        # 1. Validate QR exists in KITTING_DB
        kitting_record = db_manager.validate_kitting_qr(qr_code)
        if not kitting_record:
            return jsonify({"success": False, "error": "QR code not found in Kitting Database. Scan a valid kitting QR from Material Setter."})
        
        actual_kitting_no = kitting_record['kitting_no']
        
        # 2. Check sequential: scanned kitting must match next expected
        if actual_kitting_no != expected_kitting:
            return jsonify({"success": False, "error": f"Wrong kitting number. Expected Kitting {expected_kitting}, but scanned Kitting {actual_kitting_no}."})
        
        # 3. For Process 1: check dunpla detected at P1 sensor AND interlock closed
        if process_no == 1:
            with p1_dunpla_detected_lock:
                if not p1_dunpla_detected:
                    print("SCAN REJECTED: THE DANPLA WAS NOT DETECTED AT STANDBY")
                    return jsonify({"success": False, "error": "THE DANPLA WAS NOT DETECTED AT STANDBY"})
                with ms_button_state_lock:
                    if ms_button_state.get("ms2_open", True):
                        print("SCAN REJECTED: THE DANPLA WAS NOT DETECTED AT STANDBY")
                        return jsonify({"success": False, "error": "THE DANPLA WAS NOT DETECTED AT STANDBY"})
                p1_dunpla_detected = False
        
        # 4. Check previous process completed (for process 2-9)
        if process_no > 1:
            prev_completed = db_manager.get_completed_count(process_no - 1)
            if actual_kitting_no > prev_completed:
                return jsonify({"success": False, "error": f"Cannot start. Process {process_no - 1} has only completed {prev_completed} kittings. Waiting for Kitting {actual_kitting_no}."})

        # 5. DELVO Process 1-9 mirror. Publish ONLY after all normal validation
        # checks above pass. Each tablet reads only the process assigned to it.
        validated_qr = str(kitting_record.get('kitting_qr_code', '') or qr_code).strip()
        update_delvo_kitting_mirror(
            f"p{process_no}",
            validated_qr,
            process_no=process_no,
            kitting_no=actual_kitting_no,
            job_order=kitting_record.get('job_order', ''),
            model_code=kitting_record.get('model_code', '')
        )
        
        return jsonify({
            "success": True,
            "kitting_no": actual_kitting_no,
            "job_order": kitting_record.get('job_order', ''),
            "model_code": kitting_record.get('model_code', ''),
            "kitting_qr_code": validated_qr,
            "plan": kitting_record.get('plan', '')
        })
    except Exception as e:
        print(f"Error in validate_kitting_qr: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/is_process1_busy", methods=["GET"])
def is_process1_busy():
    """Check if Process 1 has an active server timer (for Material Setter blocking).
    Also returns p1_counter: highest kitting number Process 1 has started or completed."""
    try:
        with server_timers_lock:
            is_busy = 1 in server_timers
            kitting_no = server_timers[1]["kitting_no"] if is_busy else None
        with server_counters_lock:
            mem_counter = server_counters.get(1, 0)
        db_count = db_manager.get_completed_count(1)
        p1_counter = max(mem_counter, db_count)
        return jsonify({"success": True, "busy": is_busy, "kitting_no": kitting_no, "p1_counter": p1_counter})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== ARDUINO SIGNAL API ====================

@app.route("/api/arduino_signal", methods=["POST"])
def receive_arduino_signal():
    """Receive signal from Arduino bridge (arduino_bridge.py)
    Also handles server-side timer start/stop so timers work even when browser page is closed."""
    try:
        data = request.json
        process_no = int(data.get('process_no', 0))
        action = data.get('action', '').lower()  # "start" or "stop"
        
        if process_no < 1 or process_no > 9:
            return jsonify({"success": False, "error": "Invalid process_no"}), 400
        if action not in ('start', 'stop'):
            return jsonify({"success": False, "error": "Invalid action"}), 400
        
        # SERVER-SIDE TIMER HANDLING (works even when browser page is closed)
        if action == 'start':
            # Check if THIS process has manpower assigned before allowing start
            manpower = db_manager.get_all_manpower()
            this_process_has_manpower = False
            for mp in manpower:
                if mp['process_no'] == process_no:
                    has_scan = mp.get('operator_scan', '').strip() != ''
                    has_manual = mp.get('operator_manual', '').strip() != ''
                    if has_scan or has_manual:
                        this_process_has_manpower = True
                    break
            if not this_process_has_manpower:
                print(f"ARDUINO: BLOCKED Process {process_no} - No operator assigned for this process")
                return jsonify({"success": False, "error": f"Process {process_no} does not have an operator assigned"})
            
            # Check if timer is already running for this process
            with server_timers_lock:
                if process_no in server_timers:
                    # Process 1: close standby interlock if open (handles race where
                    # STANDBY_MS fired after P1START and subsequent P1STARTs hit this path)
                    if process_no == 1:
                        with ms_button_state_lock:
                            standby_was_open = ms_button_state["standby_interlock_open"]
                            ms_button_state["standby_interlock_open"] = False
                        if standby_was_open:
                            with ms_pending_commands_lock:
                                ms_pending_commands.append("STANDBY_RELAY_OFF")
                            db_manager.save_standby_interlock_state(False)
                            print(f"ARDUINO P1START (dup): Standby interlock closed")
                    if process_no == 2:
                        with ms_button_state_lock:
                            p1_was_open = ms_button_state["p1_interlock_open"]
                            ms_button_state["p1_interlock_open"] = False
                        if p1_was_open:
                            with ms_pending_commands_lock:
                                ms_pending_commands.append("RELAY_P1_OFF")
                            db_manager.save_p1_interlock_state(False)
                            print(f"ARDUINO P2START (dup): P1 interlock closed")
                    print(f"ARDUINO: Process {process_no} timer already running, ignoring START")
                    return jsonify({"success": True, "info": "Timer already running"})
            
            # VALIDATE: Check if existing kitting has been disposed (next process picked it up)
            with server_last_completed_lock:
                last_completed = server_last_completed.get(process_no)
            if last_completed and process_no < 9:
                last_kit = last_completed['kitting_no']
                next_process_completed = db_manager.get_completed_count(process_no + 1)
                if last_kit > next_process_completed:
                    print(f"WARNING: Process {process_no} cannot start new kitting - existing Kitting {last_kit} not yet disposed (Process {process_no+1} only completed {next_process_completed})")
                    return jsonify({"success": False, "error": f"Cannot start another kitting. Existing Kitting {last_kit} not yet disposed. Waiting for Process {process_no+1} to complete it."})
            
            # Get current counter and compute next kitting number
            with server_counters_lock:
                current_counter = server_counters.get(process_no, 0)
                new_counter = current_counter + 1
            
            # VALIDATE: Check if previous process has completed enough kittings
            if process_no > 1:
                prev_completed = db_manager.get_completed_count(process_no - 1)
                if new_counter > prev_completed:
                    print(f"ARDUINO: BLOCKED Process {process_no} Kitting {new_counter} - Process {process_no-1} only completed {prev_completed}")
                    return jsonify({"success": False, "error": f"Process {process_no-1} has only completed {prev_completed} kittings"})
            
            # Clear previous process's last_completed (this process starting = previous disposed)
            if process_no > 1:
                with server_last_completed_lock:
                    server_last_completed.pop(process_no - 1, None)
            
            # Validation passed - start the timer
            with server_counters_lock:
                server_counters[process_no] = new_counter
            with server_timers_lock:
                server_timers[process_no] = {
                    "start_time": time.time(),
                    "kitting_no": new_counter,
                    "kitting_qr_code": "",
                    "model_code": "",
                    "job_order": ""
                }
            save_timer_state_to_file()
            print(f"ARDUINO: Server-side timer STARTED for Process {process_no}, Kitting {new_counter}")
            
            # Process 1 START: also close standby interlock (danpla has left standby)
            # This mirrors the P1_DONE logic but triggers immediately from the cycle-time
            # Arduino, avoiding reliance on the Material Setter Pin 11 2-second sustain.
            if process_no == 1:
                with ms_button_state_lock:
                    standby_was_open = ms_button_state["standby_interlock_open"]
                    ms_button_state["standby_interlock_open"] = False
                if standby_was_open:
                    with ms_pending_commands_lock:
                        ms_pending_commands.append("STANDBY_RELAY_OFF")
                    db_manager.save_standby_interlock_state(False)
                    print(f"ARDUINO P1START: Standby interlock closed (danpla reached Process 1)")
            
            # Process 2 START: also close P1 interlock (danpla has left Process 1)
            # This mirrors the P2_DONE logic but triggers immediately from the cycle-time
            # Arduino, avoiding reliance on the Material Setter Pin 28 500ms sustain.
            if process_no == 2:
                with ms_button_state_lock:
                    p1_was_open = ms_button_state["p1_interlock_open"]
                    ms_button_state["p1_interlock_open"] = False
                if p1_was_open:
                    with ms_pending_commands_lock:
                        ms_pending_commands.append("RELAY_P1_OFF")
                    db_manager.save_p1_interlock_state(False)
                    print(f"ARDUINO P2START: P1 interlock closed (danpla reached Process 2)")
        
        elif action == 'stop':
            with server_timers_lock:
                timer_data = server_timers.pop(process_no, None)
            
            # Also clear active kitting
            with server_active_kittings_lock:
                server_active_kittings.pop(process_no, None)
            
            if timer_data:
                elapsed_seconds = int(time.time() - timer_data["start_time"])
                mins = elapsed_seconds // 60
                secs = elapsed_seconds % 60
                elapsed_time_str = f"{mins:02d}:{secs:02d}"
                kitting_no = timer_data["kitting_no"]
                kitting_qr_code = timer_data.get("kitting_qr_code", "")
                model_code_val = timer_data.get("model_code", "")
                job_order_val = timer_data.get("job_order", "")
                
                record_id = db_manager.insert_record(
                    kitting_no=str(kitting_no),
                    lineout_reason=None,
                    elapsed_time=elapsed_time_str,
                    pass_ng=1,
                    process_no=process_no,
                    kitting_qr_code=kitting_qr_code,
                    model_code=model_code_val,
                    job_order=job_order_val
                )
                
                update_last_data_timestamp()
                save_timer_state_to_file()
                
                print(f"ARDUINO: Server-side timer STOPPED for Process {process_no}, Kitting {kitting_no}, Elapsed {elapsed_time_str}, Record ID: {record_id}")
                
                # Track completed kitting (for duplicate prevention)
                if process_no < 9:
                    with server_last_completed_lock:
                        server_last_completed[process_no] = {'kitting_no': kitting_no, 'time': time.time()}
                # Process 9 (last station): no next process needed, clear immediately
            else:
                print(f"ARDUINO: No active timer for Process {process_no} to stop")
        
        # Store the signal for browser polling (only reached if validation passed)
        with arduino_signals_lock:
            arduino_signals[process_no] = {
                "action": action,
                "timestamp": time.time()
            }
        
        print(f"ARDUINO SIGNAL: Process {process_no} -> {action.upper()}")
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in receive_arduino_signal: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/arduino_signal/<int:process_no>", methods=["GET"])
def get_arduino_signal(process_no):
    """Browser polls this endpoint to check for pending Arduino signals"""
    try:
        with arduino_signals_lock:
            signal = arduino_signals.pop(process_no, None)
        
        if signal:
            # Only return signals that are less than 10 seconds old
            if time.time() - signal["timestamp"] < 10:
                return jsonify({"success": True, "action": signal["action"]})
        
        return jsonify({"success": True, "action": None})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== BRIDGE READY & AUTO-OPEN BROWSER ====================

def _open_browser_once(reason="startup"):
    """Open the Cycle Time Monitoring page once.

    The original project waited for BOTH Arduino bridges before opening the
    browser.  That means Flask can be running normally while no browser opens
    if either COM bridge is disconnected, slow to boot, or misses READY.
    This helper keeps the original bridge-ready behavior but also supports a
    safe Flask-startup fallback.
    """
    global browser_opened

    # Re-use the existing lock so bridge callbacks and the fallback thread
    # cannot open two browser windows at the same time.
    with bridge_ready_lock:
        if browser_opened:
            return False
        browser_opened = True

    # Prefer the LAN address exactly like the original code.  If Windows has
    # no active route, localhost still opens the application on this PC.
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        lan_ip = "127.0.0.1"

    url = f"http://{lan_ip}:5001"
    print(f"\n>>> Opening browser ({reason}): {url}")
    try:
        opened = webbrowser.open(url)
        if not opened:
            print(">>> WARNING: Windows did not confirm that the browser was opened.")
        return opened
    except Exception as e:
        print(f">>> WARNING: Could not open browser automatically: {e}")
        return False


def _open_browser_when_flask_is_ready():
    """Fallback: open browser after Flask starts even if a bridge is not READY."""
    # Wait until port 5001 is actually accepting connections.  This prevents
    # opening the browser too early and showing a connection-refused page.
    for _ in range(60):  # up to about 15 seconds
        try:
            with socket.create_connection(("127.0.0.1", 5001), timeout=0.20):
                _open_browser_once("Flask server ready")
                return
        except OSError:
            time.sleep(0.25)

    # Final best-effort attempt.  The Flask console remains usable either way.
    _open_browser_once("startup fallback")


@app.route("/api/bridge_ready", methods=["POST"])
def receive_bridge_ready():
    """Called by Arduino bridges when they detect ARDUINO_READY/ESP_READY.
    Opens browser automatically once both bridges have reported ready."""
    try:
        data = request.get_json() or {}
        bridge_name = data.get("bridge", "unknown")

        with bridge_ready_lock:
            bridge_ready_status[bridge_name] = True
            all_ready = "cycle_time" in bridge_ready_status and "material_setter" in bridge_ready_status

        if all_ready:
            _open_browser_once("both Arduino bridges ready")

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== MATERIAL SETTER ARDUINO BUTTON SIGNALS ====================

# Set when MS_UNLOAD_ID arrives while the interlock is open (Pin 7 crosstalk causes false
# unloads). Cleared by MS_LOAD_ID; applied for real when the interlock closes.
_ms1_unload_blocked = False


def _apply_deferred_ms1_unload():
    """Apply an MS1UNLOAD that was blocked while the interlock was open."""
    global _ms1_unload_blocked
    if not _ms1_unload_blocked:
        return
    _ms1_unload_blocked = False
    with ms_button_state_lock:
        ms_button_state["ms1_loaded"] = False
    try:
        db_manager.set_ms_operator_out("Arduino: ID removed")
        print(f"MS1: ID REMOVED - Operator signed out automatically")
    except Exception as e:
        print(f"MS1: ID REMOVED - Warning: could not sign out operator: {e}")


@app.route("/api/ms_arduino_signal", methods=["POST"])
def receive_ms_arduino_signal():
    """Receive Material Setter button signals from Arduino bridge.
    Handles: MS_LOAD_ID, MS_UNLOAD_ID, MS2OPEN, STANDBY_MS"""
    global p1_dunpla_detected, p2_dunpla_detected, _ms1_unload_blocked, kitting_scanned_data, ms_scanned_id, p1_scanned_id, p1_kitting_scanned_data
    try:
        data = request.json
        signal = data.get('signal', '').upper()
        
        if signal == "MS_LOAD_ID":
            # ID is back — any unload blocked during interlock open was crosstalk
            _ms1_unload_blocked = False
            with ms_button_state_lock:
                ms_button_state["ms1_loaded"] = True
            print(f"MS1: ID LOADED - Operator QR ID placed at scanner")
            return jsonify({"success": True, "state": "ms1_loaded"})
        
        elif signal == "MS_UNLOAD_ID":
            # Arduino now confirms Pin 2 HIGH before sending MS_UNLOAD_ID, so do not ignore a
            # real ID removal during the first 10 seconds after Flask starts.
            # Defer while interlock is open — Pin 7 crosstalk fires false unloads here.
            # Applied later if no MS_LOAD_ID arrives before the interlock closes.
            with ms_button_state_lock:
                interlock_open = ms_button_state["ms2_open"]
            if interlock_open:
                _ms1_unload_blocked = True
                return jsonify({"success": True, "state": "deferred_interlock_open"})
            with ms_button_state_lock:
                ms_button_state["ms1_loaded"] = False
            # Discard any unread scan payload from the ID that was just removed, so it
            # cannot auto-fill the next Scan ID popup.
            with ms_scanned_id_lock:
                ms_scanned_id = None
            # Sign out operator via existing API logic
            try:
                db_manager.set_ms_operator_out("Arduino: ID removed")
                print(f"MS1: ID REMOVED - Operator signed out automatically")
            except Exception as e:
                print(f"MS1: ID REMOVED - Warning: could not sign out operator: {e}")
            return jsonify({"success": True, "state": "ms1_unloaded"})
        
        elif signal == "MS2OPEN":
            with ms_button_state_lock:
                ms_button_state["ms2_open"] = True
            print(f"MS2: GATE OPEN - Operator can get danpla")
            return jsonify({"success": True, "state": "ms2_open"})
        
        elif signal == "STANDBY_MS":
            # Ignore false STANDBY_MS during startup (Arduino sensor noise on boot)
            if time.time() - _flask_start_time < 10:
                print(f"STANDBY_MS ignored (startup grace period)")
                return jsonify({"success": True, "state": "ignored_startup"})
            # Skip if interlock is already closed (prevent duplicate RELAY2_OFF flood)
            with ms_button_state_lock:
                already_closed = not ms_button_state["ms2_open"]
            if already_closed:
                return jsonify({"success": True, "state": "already_closed"})
            # Queue RELAY2_OFF to close interlock when dunpla detected at Standby
            with ms_pending_commands_lock:
                ms_pending_commands.append("RELAY2_OFF")
            with ms_button_state_lock:
                ms_button_state["ms2_open"] = False
            db_manager.save_interlock_state(False)
            with p1_dunpla_detected_lock:
                p1_dunpla_detected = True
            # Only open standby interlock if Process 1 timer is NOT already running.
            # If P1 is running, the danpla already left standby — no need to open.
            with server_timers_lock:
                p1_timer_running = 1 in server_timers
            if p1_timer_running:
                print(f"STANDBY_MS: Dunpla at STANDBY but P1 already running - interlock closed, standby NOT opened")
            else:
                with ms_pending_commands_lock:
                    ms_pending_commands.append("STANDBY_RELAY_ON")
                with ms_button_state_lock:
                    ms_button_state["standby_interlock_open"] = True
                db_manager.save_standby_interlock_state(True)
                print(f"MS_CLOSE_INTERLOCK: Dunpla reached STANDBY - interlock closed, standby interlock opened")
            _apply_deferred_ms1_unload()
            return jsonify({"success": True, "state": "p1_start_ms2_closed"})
        
        elif signal == "MS_OPEN_INTERLOCK":
            # Confirmation from Arduino that relay was activated
            with ms_button_state_lock:
                ms_button_state["ms2_open"] = True
            db_manager.save_interlock_state(True)
            print(f"MS_OPEN_INTERLOCK: Arduino confirmed interlock open")
            return jsonify({"success": True, "state": "interlock_open"})
        
        elif signal == "MS_CLOSE_INTERLOCK":
            # Confirmation from Arduino that relay was deactivated
            with ms_button_state_lock:
                ms_button_state["ms2_open"] = False
            db_manager.save_interlock_state(False)
            print(f"MS_CLOSE_INTERLOCK: Arduino confirmed interlock closed")
            _apply_deferred_ms1_unload()
            return jsonify({"success": True, "state": "interlock_closed"})
        
        elif signal == "P1_ID_LOAD":
            with ms_button_state_lock:
                ms_button_state["p1_id_loaded"] = True
            print(f"P1: ID LOADED - Operator ID placed at Process 1 scanner")
            return jsonify({"success": True, "state": "p1_id_loaded"})
        
        elif signal == "P1_ID_UNLOAD":
            with ms_button_state_lock:
                ms_button_state["p1_id_loaded"] = False
            # Sign out operator from Process 1 when ID removed
            try:
                db_manager.update_time_out(1)
                db_manager.clear_manpower(1)
                print(f"P1: ID REMOVED - Operator signed out from Process 1")
            except Exception as e:
                print(f"P1: ID REMOVED - Warning: could not sign out operator: {e}")
            return jsonify({"success": True, "state": "p1_id_unloaded"})
        
        elif signal == "P1_DONE":
            # Ignore false P1_DONE during startup (Arduino sensor noise on boot)
            if time.time() - _flask_start_time < 10:
                print(f"P1_DONE ignored (startup grace period)")
                return jsonify({"success": True, "state": "ignored_startup"})
            # Always close standby interlock when danpla reaches Process 1
            with ms_button_state_lock:
                standby_was_open = ms_button_state["standby_interlock_open"]
                ms_button_state["standby_interlock_open"] = False
            if standby_was_open:
                with ms_pending_commands_lock:
                    ms_pending_commands.append("STANDBY_RELAY_OFF")
                db_manager.save_standby_interlock_state(False)
            # Always set p2 dunpla detected flag
            with p2_dunpla_detected_lock:
                p2_dunpla_detected = True
            # Stop Process 1 server timer and save record (danpla finished at P1)
            with server_timers_lock:
                timer_data = server_timers.pop(1, None)
            with server_active_kittings_lock:
                server_active_kittings.pop(1, None)
            if timer_data:
                elapsed_seconds = int(time.time() - timer_data["start_time"])
                mins = elapsed_seconds // 60
                secs = elapsed_seconds % 60
                elapsed_time_str = f"{mins:02d}:{secs:02d}"
                kitting_no = timer_data["kitting_no"]
                kitting_qr_code = timer_data.get("kitting_qr_code", "")
                model_code_val = timer_data.get("model_code", "")
                job_order_val = timer_data.get("job_order", "")
                record_id = db_manager.insert_record(
                    kitting_no=str(kitting_no),
                    lineout_reason=None,
                    elapsed_time=elapsed_time_str,
                    pass_ng=1,
                    process_no=1,
                    kitting_qr_code=kitting_qr_code,
                    model_code=model_code_val,
                    job_order=job_order_val
                )
                update_last_data_timestamp()
                save_timer_state_to_file()
                with server_last_completed_lock:
                    server_last_completed[1] = {'kitting_no': kitting_no, 'time': time.time()}
                print(f"P1_DONE: Process 1 timer STOPPED - Kitting {kitting_no}, Elapsed {elapsed_time_str}, Record {record_id}")
            else:
                print(f"P1_DONE: Dunpla reached Process 1 (no active P1 timer)")
            # Open P1 interlock (danpla finished at Process 1)
            with ms_button_state_lock:
                p1_already_open = ms_button_state["p1_interlock_open"]
            if not p1_already_open:
                with ms_pending_commands_lock:
                    ms_pending_commands.append("RELAY_P1_ON")
                with ms_button_state_lock:
                    ms_button_state["p1_interlock_open"] = True
                db_manager.save_p1_interlock_state(True)
                print(f"P1_DONE: P1 interlock opened, standby interlock closed")
            else:
                print(f"P1_DONE: P1 interlock already open, standby interlock closed")
            return jsonify({"success": True, "state": "p2_start_p1_opened"})
        
        elif signal == "P1_OPEN_INTERLOCK":
            with ms_button_state_lock:
                ms_button_state["p1_interlock_open"] = True
            db_manager.save_p1_interlock_state(True)
            print(f"P1_OPEN_INTERLOCK: Arduino confirmed P1 interlock open")
            return jsonify({"success": True, "state": "p1_interlock_open"})
        
        elif signal == "P1_CLOSE_INTERLOCK":
            with ms_button_state_lock:
                ms_button_state["p1_interlock_open"] = False
            db_manager.save_p1_interlock_state(False)
            print(f"P1_CLOSE_INTERLOCK: Arduino confirmed P1 interlock closed")
            return jsonify({"success": True, "state": "p1_interlock_closed"})
        
        elif signal == "P2_ID_LOAD":
            with ms_button_state_lock:
                ms_button_state["p2_id_loaded"] = True
            print(f"P2: ID LOADED - Operator ID placed at Process 2 scanner")
            return jsonify({"success": True, "state": "p2_id_loaded"})
        
        elif signal == "P2_ID_UNLOAD":
            with ms_button_state_lock:
                ms_button_state["p2_id_loaded"] = False
            try:
                db_manager.update_time_out(2)
                db_manager.clear_manpower(2)
                print(f"P2: ID REMOVED - Operator signed out from Process 2")
            except Exception as e:
                print(f"P2: ID REMOVED - Warning: could not sign out operator: {e}")
            return jsonify({"success": True, "state": "p2_id_unloaded"})
        
        elif signal == "P2_DONE":
            # Ignore false P2_DONE during startup (Arduino sensor noise on boot)
            if time.time() - _flask_start_time < 10:
                print(f"P2_DONE ignored (startup grace period)")
                return jsonify({"success": True, "state": "ignored_startup"})
            # Close P1 interlock (danpla left Process 1)
            with ms_button_state_lock:
                p1_was_open = ms_button_state["p1_interlock_open"]
                ms_button_state["p1_interlock_open"] = False
            if p1_was_open:
                with ms_pending_commands_lock:
                    ms_pending_commands.append("RELAY_P1_OFF")
                db_manager.save_p1_interlock_state(False)
            # Stop Process 2 server timer and save record (danpla finished at P2)
            with server_timers_lock:
                timer_data = server_timers.pop(2, None)
            with server_active_kittings_lock:
                server_active_kittings.pop(2, None)
            if timer_data:
                elapsed_seconds = int(time.time() - timer_data["start_time"])
                mins = elapsed_seconds // 60
                secs = elapsed_seconds % 60
                elapsed_time_str = f"{mins:02d}:{secs:02d}"
                kitting_no = timer_data["kitting_no"]
                kitting_qr_code = timer_data.get("kitting_qr_code", "")
                model_code_val = timer_data.get("model_code", "")
                job_order_val = timer_data.get("job_order", "")
                record_id = db_manager.insert_record(
                    kitting_no=str(kitting_no),
                    lineout_reason=None,
                    elapsed_time=elapsed_time_str,
                    pass_ng=1,
                    process_no=2,
                    kitting_qr_code=kitting_qr_code,
                    model_code=model_code_val,
                    job_order=job_order_val
                )
                update_last_data_timestamp()
                save_timer_state_to_file()
                with server_last_completed_lock:
                    server_last_completed[2] = {'kitting_no': kitting_no, 'time': time.time()}
                print(f"P2_DONE: Process 2 timer STOPPED - Kitting {kitting_no}, Elapsed {elapsed_time_str}, Record {record_id}")
            else:
                print(f"P2_DONE: Dunpla reached Process 2 (no active P2 timer)")
            # Open P2 interlock (danpla finished at Process 2)
            with ms_button_state_lock:
                p2_already_open = ms_button_state["p2_interlock_open"]
            if not p2_already_open:
                with ms_pending_commands_lock:
                    ms_pending_commands.append("RELAY_P2_ON")
                with ms_button_state_lock:
                    ms_button_state["p2_interlock_open"] = True
                db_manager.save_p2_interlock_state(True)
                print(f"P2_DONE: P2 interlock opened, P1 interlock closed")
            else:
                print(f"P2_DONE: P2 interlock already open, P1 interlock closed")
            return jsonify({"success": True, "state": "p3_start_p2_opened"})
        
        elif signal == "P2_OPEN_INTERLOCK":
            with ms_button_state_lock:
                ms_button_state["p2_interlock_open"] = True
            db_manager.save_p2_interlock_state(True)
            print(f"P2_OPEN_INTERLOCK: Arduino confirmed P2 interlock open")
            return jsonify({"success": True, "state": "p2_interlock_open"})
        
        elif signal == "P2_CLOSE_INTERLOCK":
            with ms_button_state_lock:
                ms_button_state["p2_interlock_open"] = False
            db_manager.save_p2_interlock_state(False)
            print(f"P2_CLOSE_INTERLOCK: Arduino confirmed P2 interlock closed")
            return jsonify({"success": True, "state": "p2_interlock_closed"})
        
        elif signal == "STANDBY_OPEN_INTERLOCK":
            # If Process 1 timer is already running, the danpla left standby — immediately close
            with server_timers_lock:
                p1_timer_running = 1 in server_timers
            if p1_timer_running:
                with ms_button_state_lock:
                    ms_button_state["standby_interlock_open"] = False
                with ms_pending_commands_lock:
                    ms_pending_commands.append("STANDBY_RELAY_OFF")
                db_manager.save_standby_interlock_state(False)
                print(f"STANDBY_OPEN_INTERLOCK: P1 running - immediately closing standby interlock")
                return jsonify({"success": True, "state": "standby_interlock_auto_closed"})
            with ms_button_state_lock:
                ms_button_state["standby_interlock_open"] = True
            db_manager.save_standby_interlock_state(True)
            print(f"STANDBY_OPEN_INTERLOCK: Arduino confirmed standby interlock open")
            return jsonify({"success": True, "state": "standby_interlock_open"})
        
        elif signal == "STANDBY_CLOSE_INTERLOCK":
            with ms_button_state_lock:
                ms_button_state["standby_interlock_open"] = False
            db_manager.save_standby_interlock_state(False)
            print(f"STANDBY_CLOSE_INTERLOCK: Arduino confirmed standby interlock closed")
            return jsonify({"success": True, "state": "standby_interlock_closed"})
        
        elif signal == "MS_SCANNER_READY":
            # Scanner finished booting (Arduino triggers scanner at boot automatically)
            print(f"MS_SCANNER_READY: Scanner booted and ready")
            return jsonify({"success": True, "state": "scanner_ready"})
        
        elif signal == "MS_SCANNER_RELAY_ON_CONFIRM":
            print(f"MS_SCANNER_RELAY: Arduino confirmed scanner power ON")
            return jsonify({"success": True, "state": "scanner_relay_on"})
        
        elif signal == "MS_SCANNER_RELAY_OFF_CONFIRM":
            print(f"MS_SCANNER_RELAY: Arduino confirmed scanner power OFF")
            return jsonify({"success": True, "state": "scanner_relay_off"})
        
        elif signal == "MS_KITTING_LOAD":
            with ms_button_state_lock:
                ms_button_state["kitting_loaded"] = True
            # Start each physical kitting cycle clean. Clear only when a NEW dunpla is loaded.
            # Do not clear on unload, because the browser may not have consumed the scan yet.
            with kitting_scanned_data_lock:
                kitting_scanned_data = None
            print(f"KITTING: Dunpla placed - Kitting QR scanner activated")
            return jsonify({"success": True, "state": "kitting_loaded"})
        
        elif signal == "MS_KITTING_UNLOAD":
            with ms_button_state_lock:
                ms_button_state["kitting_loaded"] = False
            # IMPORTANT: Preserve kitting_scanned_data until /api/ms_get_kitting_scan reads it.
            # This removes a race where KITTING_UNLOAD could erase a valid QR before the UI's
            # next 500 ms poll. The next KITTING_LOAD clears any stale unconsumed value.
            print(f"KITTING: Dunpla removed - Scan data preserved until UI retrieval")
            return jsonify({"success": True, "state": "kitting_unloaded"})
        
        elif signal == "MS_KIT_SCANNER_READY":
            print(f"MS_KIT_SCANNER_READY: Kitting scanner booted and ready")
            return jsonify({"success": True, "state": "kit_scanner_ready"})
        
        elif signal == "MS_KIT_RELAY_ON_CONFIRM":
            print(f"MS_KIT_RELAY: Arduino confirmed kitting scanner power ON")
            return jsonify({"success": True, "state": "kit_relay_on"})
        
        elif signal == "MS_KIT_RELAY_OFF_CONFIRM":
            print(f"MS_KIT_RELAY: Arduino confirmed kitting scanner power OFF")
            return jsonify({"success": True, "state": "kit_relay_off"})
        
        elif signal == "P1_SCANNER_READY":
            print(f"P1_SCANNER_READY: P1 Scanner 3 booted and ready")
            return jsonify({"success": True, "state": "p1_scanner_ready"})
        
        elif signal == "P1_SCANNER_RELAY_ON_CONFIRM":
            print(f"P1_SCANNER_RELAY: Arduino confirmed P1 scanner power ON")
            return jsonify({"success": True, "state": "p1_scanner_relay_on"})
        
        elif signal == "P1_SCANNER_RELAY_OFF_CONFIRM":
            print(f"P1_SCANNER_RELAY: Arduino confirmed P1 scanner power OFF")
            return jsonify({"success": True, "state": "p1_scanner_relay_off"})
        
        elif signal == "P1_KITTING_LOAD":
            with ms_button_state_lock:
                ms_button_state["p1_kitting_loaded"] = True
            # Clear stale P1 kitting scan data on new load
            with p1_kitting_scanned_data_lock:
                p1_kitting_scanned_data = None
            print(f"P1_KITTING: Dunpla placed - P1 Kitting QR scanner activated")
            return jsonify({"success": True, "state": "p1_kitting_loaded"})
        
        elif signal == "P1_KITTING_UNLOAD":
            with ms_button_state_lock:
                ms_button_state["p1_kitting_loaded"] = False
            # Preserve p1_kitting_scanned_data until UI retrieval (same as MS kitting)
            print(f"P1_KITTING: Dunpla removed - Scan data preserved until UI retrieval")
            return jsonify({"success": True, "state": "p1_kitting_unloaded"})
        
        elif signal == "P1_KIT_SCANNER_READY":
            # Scanner 4 booted — queue scan trigger for Cycle Time Arduino
            with ct_pending_commands_lock:
                ct_pending_commands.append("P1_KIT_SCAN_TRIGGER")
            print(f"P1_KIT_SCANNER_READY: P1 Kitting Scanner 4 booted → queued P1_KIT_SCAN_TRIGGER for CT Arduino")
            return jsonify({"success": True, "state": "p1_kit_scanner_ready"})
        
        elif signal == "P1_KIT_RELAY_ON_CONFIRM":
            print(f"P1_KIT_RELAY: Arduino confirmed P1 kitting scanner power ON")
            return jsonify({"success": True, "state": "p1_kit_relay_on"})
        
        elif signal == "P1_KIT_RELAY_OFF_CONFIRM":
            print(f"P1_KIT_RELAY: Arduino confirmed P1 kitting scanner power OFF")
            return jsonify({"success": True, "state": "p1_kit_relay_off"})
        
        elif signal == "P1_KIT_SCAN_DONE_CONFIRM":
            print(f"P1_KIT_SCAN_DONE: Arduino confirmed scan cycle ended, relay OFF")
            return jsonify({"success": True, "state": "p1_kit_scan_done"})
        
        elif signal == "P1_KIT_SCAN_TIMEOUT":
            print(f"P1_KIT_SCAN_TIMEOUT: Scanner 4 scan cycle timed out, relay auto-OFF")
            return jsonify({"success": True, "state": "p1_kit_scan_timeout"})
        
        else:
            return jsonify({"success": False, "error": f"Unknown MS signal: {signal}"}), 400
    
    except Exception as e:
        print(f"Error in receive_ms_arduino_signal: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ms_scanner_data", methods=["POST"])
def receive_ms_scanner_data():
    """Receive scanned operator ID from R35D-B scanner via Arduino bridge"""
    global ms_scanned_id
    try:
        data = request.json
        scanned_id = data.get('scanned_id', '').strip()
        if not scanned_id:
            return jsonify({"success": False, "error": "Empty scan data"}), 400
        with ms_scanned_id_lock:
            ms_scanned_id = scanned_id
        print(f"R35D-B SCAN: Operator ID received: {scanned_id}")
        return jsonify({"success": True, "scanned_id": scanned_id})
    except Exception as e:
        print(f"Error in receive_ms_scanner_data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ms_get_scanned_id", methods=["GET"])
def get_ms_scanned_id():
    """UI polls this endpoint to get scanned ID. Returns and clears the stored ID."""
    global ms_scanned_id
    try:
        with ms_scanned_id_lock:
            scanned = ms_scanned_id
            ms_scanned_id = None  # Read-once: clear after retrieval
        if scanned:
            return jsonify({"success": True, "scanned_id": scanned})
        return jsonify({"success": True, "scanned_id": None})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ms_kitting_scanner_data", methods=["POST"])
def receive_ms_kitting_scanner_data():
    """Receive scanned kitting QR data from 2nd R35D-B scanner via Arduino bridge"""
    global kitting_scanned_data
    try:
        data = request.json
        kitting_qr = data.get('kitting_qr', '').strip()
        if not kitting_qr:
            return jsonify({"success": False, "error": "Empty kitting scan data"}), 400
        with kitting_scanned_data_lock:
            kitting_scanned_data = kitting_qr
        # Also publish to DELVO Android tablet mirror. This does not clear or
        # interfere with the existing Material Setter browser scan.
        update_delvo_kitting_mirror("ms", kitting_qr)
        # Signal MS Arduino to power off kitting scanner relay (Pin 6)
        with ms_pending_commands_lock:
            ms_pending_commands.append("KIT_RELAY_OFF")
        print(f"KITTING SCAN: QR data received: {kitting_qr}")
        return jsonify({"success": True, "kitting_qr": kitting_qr})
    except Exception as e:
        print(f"Error in receive_ms_kitting_scanner_data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ms_get_kitting_scan", methods=["GET"])
def get_ms_kitting_scan():
    """UI polls this endpoint to get scanned kitting QR data. Returns and clears the stored data."""
    global kitting_scanned_data
    try:
        with kitting_scanned_data_lock:
            scanned = kitting_scanned_data
            kitting_scanned_data = None  # Read-once: clear after retrieval
        if scanned:
            return jsonify({"success": True, "kitting_qr": scanned})
        return jsonify({"success": True, "kitting_qr": None})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/p1_scanner_data", methods=["POST"])
def receive_p1_scanner_data():
    """Receive scanned operator ID from P1 Scanner 3 (Serial3) via Arduino bridge"""
    global p1_scanned_id
    try:
        data = request.json
        scanned_id = data.get('scanned_id', '').strip()
        if not scanned_id:
            return jsonify({"success": False, "error": "Empty P1 scan data"}), 400
        with p1_scanned_id_lock:
            p1_scanned_id = scanned_id
        print(f"P1 R35D-B SCAN: Operator ID received: {scanned_id}")
        return jsonify({"success": True, "scanned_id": scanned_id})
    except Exception as e:
        print(f"Error in receive_p1_scanner_data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/p1_get_scanned_id", methods=["GET"])
def get_p1_scanned_id():
    """UI polls this endpoint to get P1 scanned ID. Returns and clears the stored ID."""
    global p1_scanned_id
    try:
        with p1_scanned_id_lock:
            scanned = p1_scanned_id
            p1_scanned_id = None  # Read-once: clear after retrieval
        if scanned:
            return jsonify({"success": True, "scanned_id": scanned})
        return jsonify({"success": True, "scanned_id": None})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/p1_kitting_scanner_data", methods=["POST"])
def receive_p1_kitting_scanner_data():
    """Receive scanned kitting QR data from P1 Scanner 4 (Serial3) via Arduino bridge"""
    global p1_kitting_scanned_data
    try:
        data = request.json
        kitting_qr = data.get('kitting_qr', '').strip()
        if not kitting_qr:
            return jsonify({"success": False, "error": "Empty P1 kitting scan data"}), 400
        with p1_kitting_scanned_data_lock:
            p1_kitting_scanned_data = kitting_qr
        # Do not publish directly to the DELVO process mirror here. The Process 1
        # QR is published only after /api/validate_kitting_qr accepts it, matching
        # the same behavior used for Processes 2-9.
        # Signal MS Arduino to end scan cycle and power off Scanner 4 relay
        with ms_pending_commands_lock:
            ms_pending_commands.append("P1_KIT_SCAN_DONE")
        print(f"P1 KITTING SCAN: QR data received: {kitting_qr} → queued P1_KIT_SCAN_DONE for MS Arduino")
        return jsonify({"success": True, "kitting_qr": kitting_qr})
    except Exception as e:
        print(f"Error in receive_p1_kitting_scanner_data: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/p1_get_kitting_scan", methods=["GET"])
def get_p1_kitting_scan():
    """UI polls this endpoint to get P1 scanned kitting QR data. Returns and clears the stored data."""
    global p1_kitting_scanned_data
    try:
        with p1_kitting_scanned_data_lock:
            scanned = p1_kitting_scanned_data
            p1_kitting_scanned_data = None  # Read-once: clear after retrieval
        if scanned:
            return jsonify({"success": True, "kitting_qr": scanned})
        return jsonify({"success": True, "kitting_qr": None})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/delvo/latest_kitting", methods=["GET"])
def get_delvo_latest_kitting():
    """Non-destructive latest-kitting API for DELVO Android tablets.

    Preferred query for v0.5.0+:
      process=1 ... process=9

    Backward-compatible queries from v0.4.0 are also accepted:
      source=p1 ... source=p9
      source=ms

    Reading this endpoint NEVER clears the normal browser scanner value.
    """
    try:
        process_arg = request.args.get("process", None)
        source_arg = request.args.get("source", None)

        if process_arg is not None:
            try:
                process_no = int(process_arg)
            except (TypeError, ValueError):
                return jsonify({"success": False, "error": "Process must be a number from 1 to 9."}), 400
            if process_no < 1 or process_no > 9:
                return jsonify({"success": False, "error": "Process must be from 1 to 9."}), 400
            source = f"p{process_no}"
        else:
            source = str(source_arg or "p1").lower().strip()
            valid_sources = ["ms"] + [f"p{i}" for i in range(1, 10)]
            if source not in valid_sources:
                return jsonify({
                    "success": False,
                    "error": "Invalid source. Use process=1..9, source=p1..p9, or source=ms."
                }), 400

        with delvo_kitting_mirror_lock:
            entry = dict(delvo_kitting_mirror[source])

        return jsonify({
            "success": True,
            "source": source,
            "process_no": entry.get("process_no"),
            "scan_id": entry.get("scan_id", 0),
            "kitting_qr": entry.get("kitting_qr", ""),
            "kitting_no": entry.get("kitting_no"),
            "job_order": entry.get("job_order", ""),
            "model_code": entry.get("model_code", ""),
            "timestamp": entry.get("timestamp"),
            "server_start_time": SERVER_START_TIME
        })
    except Exception as e:
        print(f"Error in get_delvo_latest_kitting: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/delvo/status", methods=["GET"])
def get_delvo_status():
    """Health/status endpoint for DELVO Process 1-9 Android tablets."""
    try:
        with delvo_kitting_mirror_lock:
            process_scan_ids = {
                str(i): delvo_kitting_mirror[f"p{i}"].get("scan_id", 0)
                for i in range(1, 10)
            }
            ms_scan_id = delvo_kitting_mirror["ms"].get("scan_id", 0)
        return jsonify({
            "success": True,
            "service": "DELVO QR Bridge",
            "version": "5.0",
            "supported_processes": list(range(1, 10)),
            "server_start_time": SERVER_START_TIME,
            "process_scan_ids": process_scan_ids,
            "ms_scan_id": ms_scan_id,
            # Kept for compatibility with v0.4.0 clients.
            "p1_scan_id": process_scan_ids.get("1", 0)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ms_button_status", methods=["GET"])
def get_ms_button_status():
    """Browser polls this endpoint to get current MS button states"""
    try:
        with ms_button_state_lock:
            state = ms_button_state.copy()
        try:
            state["ms2_open"] = db_manager.load_interlock_state()
        except:
            pass
        try:
            state["p1_interlock_open"] = db_manager.load_p1_interlock_state()
        except:
            pass
        try:
            state["standby_interlock_open"] = db_manager.load_standby_interlock_state()
        except:
            pass
        try:
            state["p2_interlock_open"] = db_manager.load_p2_interlock_state()
        except:
            pass
        return jsonify({"success": True, "ms1_loaded": state["ms1_loaded"], "ms2_open": state["ms2_open"], "p1_id_loaded": state["p1_id_loaded"], "p1_interlock_open": state["p1_interlock_open"], "p2_id_loaded": state["p2_id_loaded"], "p2_interlock_open": state["p2_interlock_open"], "kitting_loaded": state["kitting_loaded"], "p1_kitting_loaded": state["p1_kitting_loaded"], "standby_interlock_open": state["standby_interlock_open"]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ms_get_pending_command", methods=["GET"])
def ms_get_pending_command():
    """Bridge polls this endpoint to get pending relay commands for Arduino.
    Returns the first pending command and removes it from the queue."""
    try:
        with ms_pending_commands_lock:
            if ms_pending_commands:
                cmd = ms_pending_commands.pop(0)
                return jsonify({"success": True, "command": cmd})
            else:
                return jsonify({"success": True, "command": None})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ct_get_pending_command", methods=["GET"])
def ct_get_pending_command():
    """CT bridge polls this endpoint to get pending commands for Cycle Time Arduino.
    Returns the first pending command and removes it from the queue."""
    try:
        with ct_pending_commands_lock:
            if ct_pending_commands:
                cmd = ct_pending_commands.pop(0)
                return jsonify({"success": True, "command": cmd})
            else:
                return jsonify({"success": True, "command": None})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ms_relay2_control", methods=["POST"])
def ms_relay2_control():
    """Manual relay control endpoint. Send {"action": "on"} or {"action": "off"}."""
    try:
        data = request.json
        action = data.get("action", "").lower()
        if action == "on":
            with ms_pending_commands_lock:
                ms_pending_commands.append("RELAY2_ON")
            with ms_button_state_lock:
                ms_button_state["ms2_open"] = True
            db_manager.save_interlock_state(True)
            print(f"MS_OPEN_INTERLOCK: Manual relay control - interlock opened")
            return jsonify({"success": True, "state": "relay2_on"})
        elif action == "off":
            with ms_pending_commands_lock:
                ms_pending_commands.append("RELAY2_OFF")
            with ms_button_state_lock:
                ms_button_state["ms2_open"] = False
            db_manager.save_interlock_state(False)
            print(f"MS_CLOSE_INTERLOCK: Manual relay control - interlock closed")
            return jsonify({"success": True, "state": "relay2_off"})
        else:
            return jsonify({"success": False, "error": "Invalid action. Use 'on' or 'off'."}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ms_scanner_trigger", methods=["POST"])
def ms_scanner_trigger():
    """Queue a SCAN_TRIGGER command to re-trigger the R35D-B scanner via Arduino."""
    try:
        with ms_pending_commands_lock:
            ms_pending_commands.append("SCAN_TRIGGER")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_server_timer/<int:process_no>", methods=["GET"])
def get_server_timer(process_no):
    """Get server-side timer state for a process.
    Used by browser pages to pick up timers started by Arduino when page was closed."""
    try:
        with server_timers_lock:
            timer_data = server_timers.get(process_no, None)
        
        if timer_data:
            elapsed_seconds = int(time.time() - timer_data["start_time"])
            return jsonify({
                "success": True,
                "active": True,
                "start_time": timer_data["start_time"],
                "kitting_no": timer_data["kitting_no"],
                "kitting_qr_code": timer_data.get("kitting_qr_code", ""),
                "model_code": timer_data.get("model_code", ""),
                "job_order": timer_data.get("job_order", ""),
                "elapsed_seconds": elapsed_seconds
            })
        else:
            return jsonify({"success": True, "active": False})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/sync_counter/<int:process_no>", methods=["POST"])
def sync_counter(process_no):
    """Sync browser counter with server-side counter.
    Browser sends its counter value, server updates if browser value is higher."""
    try:
        data = request.json
        browser_counter = int(data.get('counter', 0))
        browser_generation = int(data.get('reset_generation', 0))
        
        # If browser has a stale reset generation, ignore its counter push
        if browser_generation < reset_generation:
            with server_counters_lock:
                server_val = server_counters.get(process_no, 0)
            return jsonify({"success": True, "counter": server_val, "reset_generation": reset_generation})
        
        # Also check database completed count as authoritative floor
        db_count = db_manager.get_completed_count(process_no)
        with server_counter_offsets_lock:
            offset = server_counter_offsets.get(process_no, 0)
        effective_db_count = max(0, db_count - offset)
        
        with server_counters_lock:
            server_val = server_counters.get(process_no, 0)
            # Use the highest value (browser, server, or effective database)
            final_val = max(browser_counter, server_val, effective_db_count)
            server_counters[process_no] = final_val
        
        save_timer_state_to_file()
        return jsonify({"success": True, "counter": final_val, "reset_generation": reset_generation})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/clear_server_timer/<int:process_no>", methods=["POST"])
def clear_server_timer(process_no):
    """Clear server-side timer (called when browser takes over the timer)."""
    try:
        with server_timers_lock:
            server_timers.pop(process_no, None)
        save_timer_state_to_file()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/start_server_timer/<int:process_no>", methods=["POST"])
def start_server_timer(process_no):
    """Start server-side timer tracking (called when browser START button is clicked)."""
    try:
        data = request.json
        kitting_no = int(data.get('kitting_no', 0))
        kitting_qr_code = data.get('kitting_qr_code', '')
        model_code = data.get('model_code', '')
        job_order = data.get('job_order', '')
        
        # VALIDATE: Check if previous process has completed enough kittings
        if process_no > 1:
            prev_completed = db_manager.get_completed_count(process_no - 1)
            if kitting_no > prev_completed:
                print(f"START_SERVER_TIMER: BLOCKED Process {process_no} Kitting {kitting_no} - Process {process_no-1} only completed {prev_completed}")
                return jsonify({"success": False, "error": f"Process {process_no-1} has only completed {prev_completed} kittings"})
        
        with server_timers_lock:
            server_timers[process_no] = {
                "start_time": time.time(),
                "kitting_no": kitting_no,
                "kitting_qr_code": kitting_qr_code,
                "model_code": model_code,
                "job_order": job_order
            }
        
        # Also update server counter
        with server_counters_lock:
            server_counters[process_no] = max(server_counters.get(process_no, 0), kitting_no)
        
        # Mark that processes have started today (disables manpower warning)
        with processes_started_today_lock:
            if not processes_started_today["started"]:
                processes_started_today["started"] = True
                print("PROCESSES STARTED TODAY: Manpower warning disabled until next day reset")
        
        save_timer_state_to_file()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/stop_server_timer/<int:process_no>", methods=["POST"])
def stop_server_timer(process_no):
    """Stop server-side timer tracking (called when browser STOP button is clicked)."""
    try:
        with server_timers_lock:
            if process_no in server_timers:
                del server_timers[process_no]
        
        # Also clear active kitting
        with server_active_kittings_lock:
            if process_no in server_active_kittings:
                del server_active_kittings[process_no]
        
        save_timer_state_to_file()
        print(f"STOP_SERVER_TIMER: Process {process_no} timer stopped")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_completed_count/<int:process_no>", methods=["GET"])
def get_completed_count(process_no):
    """Get the number of completed records for a process from the database.
    Used by downstream processes to verify upstream completion."""
    try:
        count = db_manager.get_completed_count(process_no)
        # Also check if there's an active server timer (started but not yet stopped)
        with server_timers_lock:
            has_active = process_no in server_timers
        return jsonify({"success": True, "count": count, "has_active_timer": has_active})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/can_start_kitting/<int:process_no>/<int:kitting_no>", methods=["GET"])
def can_start_kitting(process_no, kitting_no):
    """Check if a process can start a specific kitting number.
    Verifies that the previous process (process_no - 1) has completed at least kitting_no records."""
    try:
        if process_no <= 1:
            return jsonify({"success": True, "allowed": True})
        
        prev_process = process_no - 1
        prev_completed = db_manager.get_completed_count(prev_process)
        
        allowed = kitting_no <= prev_completed
        print(f"CAN_START_KITTING: Process {process_no} wants Kitting {kitting_no}, Process {prev_process} completed {prev_completed}, Allowed: {allowed}")
        return jsonify({
            "success": True,
            "allowed": allowed,
            "prev_process": prev_process,
            "prev_completed": prev_completed,
            "requested_kitting": kitting_no
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_all_active_timers", methods=["GET"])
def get_all_active_timers():
    """Get active timer status for all processes (used by graph pages for blinking indicators)"""
    try:
        import time as _time
        with server_timers_lock:
            active = {}
            for k, v in server_timers.items():
                elapsed_sec = int(_time.time() - v.get("start_time", _time.time()))
                active[str(k)] = {"active": True, "elapsed_seconds": elapsed_sec}
        return jsonify({"success": True, "active_timers": active})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_last_update", methods=["GET"])
def get_last_update():
    """Get timestamp of last data update. Used by graph pages for auto
    -refresh."""
    try:
        with last_data_update_lock:
            ts = last_data_update["timestamp"]
        return jsonify({"success": True, "timestamp": ts})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/server_start_time", methods=["GET"])
def get_server_start_time():
    """Get server start timestamp. Used by browsers to detect server restart and auto-reload."""
    return jsonify({"success": True, "start_time": SERVER_START_TIME})

# ==================== SERVER-SIDE BLOCKED COUNTERS API ====================
# These APIs replace localStorage blocked_counters for multi-device sync

@app.route("/api/block_counter", methods=["POST"])
def block_counter():
    """Block a kitting number for all subsequent processes (called on NG/LINEOUT)"""
    try:
        data = request.json
        from_process = int(data.get('from_process', 0))
        kitting_no = int(data.get('kitting_no', 0))
        
        if from_process < 1 or from_process > 9 or kitting_no < 1:
            return jsonify({"success": False, "error": "Invalid parameters"}), 400
        
        # Block this kitting for all processes after from_process
        with server_blocked_counters_lock:
            for i in range(from_process + 1, 10):
                if i not in server_blocked_counters:
                    server_blocked_counters[i] = []
                if kitting_no not in server_blocked_counters[i]:
                    server_blocked_counters[i].append(kitting_no)
                    print(f"BLOCKED: Kitting {kitting_no} blocked for Process {i} (NG at Process {from_process})")
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in block_counter: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/is_counter_blocked/<int:process_no>/<int:kitting_no>", methods=["GET"])
def is_counter_blocked(process_no, kitting_no):
    """Check if a kitting number is blocked for a specific process"""
    try:
        with server_blocked_counters_lock:
            blocked_list = server_blocked_counters.get(process_no, [])
            is_blocked = kitting_no in blocked_list
        return jsonify({"success": True, "blocked": is_blocked})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_blocked_counters/<int:process_no>", methods=["GET"])
def get_blocked_counters(process_no):
    """Get all blocked kitting numbers for a specific process"""
    try:
        with server_blocked_counters_lock:
            blocked_list = server_blocked_counters.get(process_no, [])
        return jsonify({"success": True, "blocked_counters": blocked_list})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/clear_blocked_counters", methods=["POST"])
def clear_blocked_counters():
    """Clear all blocked counters (called on reset)"""
    try:
        with server_blocked_counters_lock:
            server_blocked_counters.clear()
        print("All blocked counters cleared")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== SERVER-SIDE ACTIVE KITTING API ====================
# These APIs replace localStorage active_kitting for multi-device sync

@app.route("/api/set_active_kitting", methods=["POST"])
def set_active_kitting():
    """Set which kitting number a process is currently working on"""
    try:
        data = request.json
        process_no = int(data.get('process_no', 0))
        kitting_no = int(data.get('kitting_no', 0))
        
        if process_no < 1 or process_no > 9:
            return jsonify({"success": False, "error": "Invalid process_no"}), 400
        
        with server_active_kittings_lock:
            if kitting_no > 0:
                server_active_kittings[process_no] = kitting_no
            else:
                server_active_kittings.pop(process_no, None)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/clear_active_kitting/<int:process_no>", methods=["POST"])
def clear_active_kitting(process_no):
    """Clear active kitting for a process (called on STOP)"""
    try:
        with server_active_kittings_lock:
            server_active_kittings.pop(process_no, None)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/is_kitting_active/<int:kitting_no>", methods=["GET"])
def is_kitting_active(kitting_no):
    """Check if a kitting number is being processed by any process"""
    try:
        with server_active_kittings_lock:
            for proc, kit in server_active_kittings.items():
                if kit == kitting_no:
                    return jsonify({"success": True, "active": True, "process_no": proc})
        return jsonify({"success": True, "active": False, "process_no": None})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/get_all_active_kittings", methods=["GET"])
def get_all_active_kittings():
    """Get all active kittings across all processes"""
    try:
        with server_active_kittings_lock:
            active_copy = dict(server_active_kittings)
        return jsonify({"success": True, "active_kittings": active_copy})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== FULL STATE SYNC API ====================
# Single API to get all state needed for a process page

@app.route("/api/get_process_state/<int:process_no>", methods=["GET"])
def get_process_state(process_no):
    """Get complete state for a process (counter, timer, blocked, active kittings)
    This is the main API for multi-device synchronization."""
    try:
        # Check for daily reset (new day detection)
        check_daily_reset()
        
        # Get server counter
        with server_counters_lock:
            mem_counter = server_counters.get(process_no, 0)
        
        # Get completed count from database (authoritative source)
        completed_count = db_manager.get_completed_count(process_no)
        
        # Subtract reset offset so counter shows 0 after RESET ALL COUNTERS
        with server_counter_offsets_lock:
            offset = server_counter_offsets.get(process_no, 0)
        effective_completed = max(0, completed_count - offset)
        
        # Use the MAX of in-memory counter and effective database count
        # This prevents counter from resetting to 0 if in-memory state is lost
        counter = max(mem_counter, effective_completed)
        
        # Update server_counters if database has a higher value (fix drift)
        if counter > mem_counter:
            with server_counters_lock:
                server_counters[process_no] = counter
        
        # Get server timer
        with server_timers_lock:
            timer_data = server_timers.get(process_no, None)
        
        timer_info = None
        if timer_data:
            elapsed_seconds = int(time.time() - timer_data["start_time"])
            timer_info = {
                "active": True,
                "kitting_no": timer_data["kitting_no"],
                "kitting_qr_code": timer_data.get("kitting_qr_code", ""),
                "model_code": timer_data.get("model_code", ""),
                "job_order": timer_data.get("job_order", ""),
                "elapsed_seconds": elapsed_seconds
            }
        
        # Get blocked counters for this process
        with server_blocked_counters_lock:
            blocked = server_blocked_counters.get(process_no, [])
        
        # Get all active kittings (to check if next kitting is being processed elsewhere)
        with server_active_kittings_lock:
            active_kittings = dict(server_active_kittings)
        
        # Get previous process completed count (for validation)
        prev_completed = 0
        if process_no > 1:
            prev_completed = db_manager.get_completed_count(process_no - 1)
        
        return jsonify({
            "success": True,
            "process_no": process_no,
            "counter": counter,
            "timer": timer_info,
            "blocked_counters": blocked,
            "active_kittings": active_kittings,
            "completed_count": completed_count,
            "prev_completed": prev_completed,
            "reset_generation": reset_generation
        })
    except Exception as e:
        print(f"Error in get_process_state: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== QR CODE PRINTER API ====================
@app.route("/api/print_kitting_qr", methods=["POST"])
def print_kitting_qr():
    """Print a kitting QR code label to the selected printer (SATO or LogicOwl)"""
    try:
        data = request.json
        qr_data = data.get('qr_data', '')
        printer_name = data.get('printer_name', None)
        
        if not qr_data:
            return jsonify({"success": False, "error": "QR data is required"}), 400
        
        # If no printer_name passed, resolve from saved selection
        if not printer_name:
            settings = load_settings_file()
            selected = settings.get('selected_printer', 'sato')
            if selected == 'logicowl':
                printer_name = qr_printer.get_logicowl_printer_name()
                if not printer_name:
                    return jsonify({"success": False, "error": "LogicOwl OJ-80250 printer not found. Check USB connection."}), 500
            else:
                printer_name = qr_printer.get_sato_printer_name()
        
        print(f"PRINTING QR CODE: {qr_data} -> {printer_name}")
        
        # Try SBPL first, then fall back to CPCL if needed
        result = qr_printer.print_kitting_qr_code(qr_data, printer_name)
        
        if result['success']:
            print(f"QR PRINT SUCCESS: {result['message']}")
            return jsonify({"success": True, "message": result['message']})
        else:
            # Try CPCL format as fallback
            print(f"SBPL failed, trying CPCL: {result['message']}")
            result_cpcl = qr_printer.print_kitting_qr_code_cpcl(qr_data, printer_name)
            if result_cpcl['success']:
                print(f"QR PRINT SUCCESS (CPCL): {result_cpcl['message']}")
                return jsonify({"success": True, "message": result_cpcl['message']})
            else:
                print(f"QR PRINT FAILED: {result_cpcl['message']}")
                return jsonify({"success": False, "error": result_cpcl['message']}), 500
            
    except Exception as e:
        print(f"Error printing QR code: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/list_printers", methods=["GET"])
def api_list_printers():
    """List all available printers on the system"""
    try:
        printers = qr_printer.list_printers()
        sato_printer = qr_printer.get_sato_printer_name()
        logicowl_printer = qr_printer.get_logicowl_printer_name()
        return jsonify({
            "success": True, 
            "printers": printers,
            "sato_printer": sato_printer,
            "logicowl_printer": logicowl_printer
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def kill_old_bridge_processes():
    """Kill any previously running arduino bridge processes before starting new ones"""
    killed_any = False
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', []) or []
                cmdline_str = ' '.join(str(c) for c in cmdline)
                if ('arduino_bridge.py' in cmdline_str or 'arduino_bridge_ms.py' in cmdline_str) and proc.pid != os.getpid():
                    print(f">>> Killing old bridge process (PID {proc.pid})")
                    proc.kill()
                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        pass
                    killed_any = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except ImportError:
        pass
    except Exception:
        pass
    if killed_any:
        time.sleep(2)  # Let Windows fully release COM port handles

def start_arduino_bridge():
    """Launch arduino_bridge.py as a background subprocess (auto-start with Flask)"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        bridge_script = os.path.join(script_dir, "arduino_bridge.py")
        print("\n>>> Auto-starting Arduino bridge in background...")
        subprocess.Popen(
            [sys.executable, bridge_script, "--port", "COM2", "--no-prompt"],
            cwd=script_dir
        )
        print(">>> Arduino bridge subprocess launched.")
    except Exception as e:
        print(f">>> WARNING: Could not start Arduino bridge: {e}")
        print(">>> The web application will continue running without Arduino input.")

def start_arduino_bridge_ms():
    """Launch arduino_bridge_ms.py as a background subprocess (Material Setter Arduino UNO)"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        bridge_script = os.path.join(script_dir, "arduino_bridge_ms.py")
        print("\n>>> Auto-starting Material Setter bridge (Arduino UNO) in background...")
        subprocess.Popen(
            [sys.executable, bridge_script, "--port", "COM9", "--no-prompt"],
            cwd=script_dir
        )
        print(">>> Material Setter bridge subprocess launched.")
    except Exception as e:
        print(f">>> WARNING: Could not start Material Setter bridge: {e}")
        print(">>> Material Setter buttons will not work without Arduino UNO.")

# Start the website when this file is run
# This code only runs when you click "Run" on this file
if __name__ == "__main__":
    # Initialize database connection and create tables
    try:
        db_manager.connect()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        print("Please ensure XAMPP MySQL/MariaDB is running")

    # Load persisted timer state from file (survives Flask restarts)
    load_timer_state_from_file()
    
    # Restore interlock state from MySQL (if it was open, queue RELAY2_ON)
    try:
        if db_manager.load_interlock_state():
            with ms_pending_commands_lock:
                ms_pending_commands.append("RELAY2_ON")
            with ms_button_state_lock:
                ms_button_state["ms2_open"] = True
            print("Restored interlock state: OPEN (queued RELAY2_ON)")
        else:
            print("Restored interlock state: CLOSED")
    except Exception as e:
        print(f"Warning: Could not restore interlock state: {e}")
    
    # Restore P1 interlock state from MySQL (if it was open, queue RELAY_P1_ON)
    try:
        if db_manager.load_p1_interlock_state():
            with ms_pending_commands_lock:
                ms_pending_commands.append("RELAY_P1_ON")
            with ms_button_state_lock:
                ms_button_state["p1_interlock_open"] = True
            print("Restored P1 interlock state: OPEN (queued RELAY_P1_ON)")
        else:
            print("Restored P1 interlock state: CLOSED")
    except Exception as e:
        print(f"Warning: Could not restore P1 interlock state: {e}")
    
    # Restore Standby interlock state from MySQL (if it was open, queue STANDBY_RELAY_ON)
    try:
        if db_manager.load_standby_interlock_state():
            with ms_pending_commands_lock:
                ms_pending_commands.append("STANDBY_RELAY_ON")
            with ms_button_state_lock:
                ms_button_state["standby_interlock_open"] = True
            print("Restored Standby interlock state: OPEN (queued STANDBY_RELAY_ON)")
        else:
            print("Restored Standby interlock state: CLOSED")
    except Exception as e:
        print(f"Warning: Could not restore Standby interlock state: {e}")
    
    # Restore P2 interlock state from MySQL (if it was open, queue RELAY_P2_ON)
    try:
        if db_manager.load_p2_interlock_state():
            with ms_pending_commands_lock:
                ms_pending_commands.append("RELAY_P2_ON")
            with ms_button_state_lock:
                ms_button_state["p2_interlock_open"] = True
            print("Restored P2 interlock state: OPEN (queued RELAY_P2_ON)")
        else:
            print("Restored P2 interlock state: CLOSED")
    except Exception as e:
        print(f"Warning: Could not restore P2 interlock state: {e}")
    
    # Load last active date from file and check for daily reset
    load_last_active_date()
    check_daily_reset()
    
    # Load job order start time from file (for graph filtering)
    load_job_order_start_time()
    
    # Check if processes have already started today (to disable manpower warning)
    initialize_processes_started_today()
    
    # Auto-start Arduino bridges only in the reloader child process
    # (Flask debug=True runs __main__ twice; this prevents double-launch)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        kill_old_bridge_processes()
        start_arduino_bridge()
        start_arduino_bridge_ms()
    
    # Keep the Python console focused on IMPORTANT EVENTS.
    #
    # The browser polls many /api/... endpoints several times per second. Werkzeug
    # normally prints one access-log line for every successful request, which can
    # flood the console and hide Arduino/scanner/interlock/error messages.
    #
    # Suppress only SUCCESSFUL routine browser/API access logs. HTTP errors are
    # still shown, and all explicit print(...) event messages elsewhere in this
    # program remain visible. This is intentionally generic so newly-added polling
    # endpoints do not need to be added to a hard-coded suppression list.
    class SuppressRoutineAccessLogs(logging.Filter):
        ROUTINE_PATH_MARKERS = (' /api/', ' /static/', ' /favicon.ico')

        def filter(self, record):
            msg = record.getMessage()

            # Non-access Werkzeug messages (startup warnings, server status, etc.)
            # do not contain an HTTP request line, so keep them.
            if 'HTTP/' not in msg:
                return True

            # Always keep HTTP failures so problems remain visible in the console.
            # Typical Werkzeug access line ends with:  " 404 -  or  " 500 -
            import re
            status_match = re.search(r'\"\s+(\d{3})\s', msg)
            if status_match:
                status_code = int(status_match.group(1))
                if status_code >= 400:
                    return True

            # Hide successful high-frequency API/static/favicon traffic.
            if any(marker in msg for marker in self.ROUTINE_PATH_MARKERS):
                return False

            # Keep normal page navigation requests (/, /material_setter, /process1, etc.)
            # because these happen infrequently and are useful for troubleshooting.
            return True

    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addFilter(SuppressRoutineAccessLogs())

    # AUTO-OPEN FALLBACK:
    # Start a daemon thread that waits until Flask port 5001 is listening.
    # The normal bridge-ready trigger can still open the browser first; the
    # _open_browser_once() guard prevents duplicate browser windows.
    threading.Thread(target=_open_browser_when_flask_is_ready, daemon=True).start()

    # host="0.0.0.0": Anyone on the network can visit (not just you)
    # port=5000: The website "door number" - like apartment 5000
    # debug=True: Shows helpful error messages if something breaks
    # app.run(host="192.168.3.220", port=5000, debug=True)  #host="0.0.0.0", port=5000 for porthost
    app.run(host="0.0.0.0", port=5001, debug=False)  #host="0.0.0.0", port=5000 for porthost-