"""
Arduino Serial Bridge for Cycle Time Monitoring
================================================
Reads serial data from Arduino and sends HTTP POST requests
to the Flask web server to trigger START/STOP buttons in the browser.
Also handles P1 Kitting Scanner 4 data (P1_KITSCAN) via Serial1 on this Arduino.

Usage:
  python arduino_bridge.py
  python arduino_bridge.py --port COM3
  python arduino_bridge.py --port COM3 --baud 9600
"""

import serial
import serial.tools.list_ports
import requests
import time
import sys
import argparse
import threading

# Flask server URL (default)
FLASK_URL = "http://127.0.0.1:5001"

def find_arduino_port(no_prompt=False):
    """Auto-detect Arduino COM port"""
    ports = serial.tools.list_ports.comports()
    print("\n=== Available COM Ports ===")
    for port in ports:
        print(f"  {port.device} - {port.description}")
    
    # Try to find Arduino automatically
    for port in ports:
        desc = port.description.lower()
        if 'arduino' in desc or 'ch340' in desc or 'usb serial' in desc or 'usb-serial' in desc:
            print(f"\n>>> Auto-detected Arduino on: {port.device}")
            return port.device
    
    # If no Arduino found, ask user (skip prompt in auto mode)
    if ports:
        print("\n>>> Could not auto-detect Arduino.")
        print(">>> Available ports:", [p.device for p in ports])
        if no_prompt:
            print(">>> Running in auto mode (--no-prompt), skipping interactive prompt.")
            return None
        port_input = input(">>> Enter COM port (e.g. COM3): ").strip()
        return port_input if port_input else None
    
    return None

RECONNECT_DELAY = 5

def send_p1_kitting_scan_to_flask(scanned_data):
    """Send scanned Kitting QR data from P1 Scanner 4 (Serial1) to Flask server"""
    try:
        url = f"{FLASK_URL}/api/p1_kitting_scanner_data"
        payload = {"kitting_qr": scanned_data}
        response = requests.post(url, json=payload, timeout=2)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"  -> P1 kitting scan data sent OK: {scanned_data}")
            else:
                print(f"  -> Server error: {result.get('error', 'Unknown')}")
        else:
            print(f"  -> HTTP Error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"  -> ERROR: Cannot connect to Flask server at {FLASK_URL}")
    except Exception as e:
        print(f"  -> ERROR sending P1 kitting scan data: {e}")

def send_signal_to_flask(process_no, action):
    """Send Arduino signal to Flask server"""
    try:
        url = f"{FLASK_URL}/api/arduino_signal"
        payload = {
            "process_no": process_no,
            "action": action  # "start" or "stop"
        }
        response = requests.post(url, json=payload, timeout=2)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"  -> Signal sent OK: Process {process_no} {action.upper()}")
            else:
                print(f"  -> Server error: {result.get('error', 'Unknown')}")
        else:
            print(f"  -> HTTP Error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"  -> ERROR: Cannot connect to Flask server at {FLASK_URL}")
        print(f"           Make sure cycleTimeMoni.py is running!")
    except Exception as e:
        print(f"  -> ERROR sending signal: {e}")

def parse_serial_message(message):
    """
    Parse Arduino serial message.
    Expected format: P1START, P1STOP, P2START, ... P9STOP, P1_KITSCAN:<data>
    Returns (process_no, action) or (None, None) if invalid.
    For P1_KITSCAN, returns ("P1_KITSCAN", <data>).
    """
    stripped = message.strip()
    
    # Check for P1 kitting scan data
    if stripped.upper().startswith("P1_KITSCAN:"):
        kitting_data = stripped.split(":", 1)[1].strip()
        return "P1_KITSCAN", kitting_data
    
    message_upper = stripped.upper()
    
    if not message_upper.startswith("P"):
        return None, None
    
    # Try to extract process number and action
    for i in range(1, 10):
        prefix = f"P{i}"
        if message_upper.startswith(prefix):
            remainder = message_upper[len(prefix):]
            if remainder == "START":
                return i, "start"
            elif remainder == "STOP":
                return i, "stop"
    
    return None, None

def poll_pending_commands(ser):
    """Poll Flask server for pending commands and send to Arduino via serial.
    Runs in a daemon thread."""
    while True:
        try:
            resp = requests.get(f"{FLASK_URL}/api/ct_get_pending_command", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                cmd = data.get("command")
                if cmd:
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"[{timestamp}] Sending to Arduino: {cmd}")
                    ser.write((cmd + "\n").encode('utf-8'))
        except requests.exceptions.ConnectionError:
            pass
        except Exception:
            pass
        time.sleep(0.2)  # Poll every 200ms

def main():
    global FLASK_URL
    
    parser = argparse.ArgumentParser(description="Arduino Serial Bridge for Cycle Time Monitoring")
    parser.add_argument("--port", type=str, help="COM port (e.g. COM3)")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate (default: 9600)")
    parser.add_argument("--url", type=str, default=FLASK_URL, help=f"Flask server URL (default: {FLASK_URL})")
    parser.add_argument("--no-prompt", action="store_true", help="Skip interactive COM port prompt (for auto-launch mode)")
    args = parser.parse_args()
    
    FLASK_URL = args.url
    
    print("=" * 50)
    print("  ARDUINO SERIAL BRIDGE")
    print("  Cycle Time Monitoring System")
    print("=" * 50)
    print(f"  Flask Server: {FLASK_URL}")
    
    # Find Arduino port
    com_port = args.port if args.port else find_arduino_port(no_prompt=args.no_prompt)
    
    if not com_port:
        print("\nERROR: No COM port found. Please connect Arduino and try again.")
        print("       Or specify port manually: python arduino_bridge.py --port COM3")
        sys.exit(1)
    
    print(f"\n>>> Connecting to Arduino on {com_port} at {args.baud} baud...")
    
    #  (1A START) Retry connection indefinitely (never give up — port may be temporarily busy)
    ser = None
    attempt = 0
    
    while ser is None:
        attempt += 1
        try:
            ser = serial.Serial(com_port, args.baud, timeout=1)
            time.sleep(2)  # Wait for Arduino to reset after serial connection
            print(f">>> Connected successfully to {com_port}!")
        except serial.SerialException as e:
            timestamp = time.strftime("%H:%M:%S")
            print(f"    [{timestamp}] {com_port} busy ({e}) - retrying in {RECONNECT_DELAY}s... (attempt {attempt})")
            time.sleep(RECONNECT_DELAY)
    #  (1A END)

    # Start command polling thread (for P1_KIT_SCAN_TRIGGER from Flask)
    cmd_thread = threading.Thread(target=poll_pending_commands, args=(ser,), daemon=True)
    cmd_thread.start()

    print(f">>> Listening for button presses...\n")
    print("-" * 50)
    
    try:
        while True:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('utf-8').strip()
                except UnicodeDecodeError:
                    continue
                
                if not line:
                    continue
                
                # Print raw serial data
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] Received: {line}")
                
                # Skip Arduino ready message
                if line == "ARDUINO_READY":
                    print("  -> Arduino is ready!")
                    # Notify Flask that this bridge is ready
                    try:
                        requests.post(f"{FLASK_URL}/api/bridge_ready", json={"bridge": "cycle_time"}, timeout=3)
                    except:
                        pass
                    continue
                
                # Parse and forward signal
                process_no, action = parse_serial_message(line)
                if process_no == "P1_KITSCAN" and action:
                    print(f"  -> P1_KITSCAN detected from Arduino: {action}")
                    send_p1_kitting_scan_to_flask(action)
                elif process_no and action:
                    send_signal_to_flask(process_no, action)
                else:
                    print(f"  -> Unknown message (ignored)")
            
            time.sleep(0.01)  # Small delay to prevent CPU spinning
    except serial.SerialException as e:
        timestamp = time.strftime("%H:%M:%S")
        print(f"\n[{timestamp}] Serial connection lost: {e}")
        print(f"    Auto-reconnecting in {RECONNECT_DELAY}s...")
        try:
            ser.close()
        except:
            pass
        # Auto-reconnect loop
        while True:
            time.sleep(RECONNECT_DELAY)
            try:
                ser = serial.Serial(com_port, args.baud, timeout=1)
                time.sleep(2)
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] Reconnected to {com_port}!")
                print("-" * 50)
                # Restart pending command thread with new serial connection
                cmd_thread = threading.Thread(target=poll_pending_commands, args=(ser,), daemon=True)
                cmd_thread.start()
                break
            except serial.SerialException:
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] Reconnect failed - retrying in {RECONNECT_DELAY}s...")
    except KeyboardInterrupt:
        print("\n\n>>> Bridge stopped by user (Ctrl+C)")
        if ser:
            ser.close()
        sys.exit(0)

if __name__ == "__main__":
    main()
