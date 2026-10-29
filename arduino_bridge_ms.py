"""
Arduino Serial Bridge for Material Setter (Arduino UNO)
========================================================
Bidirectional serial bridge:
  - Reads sensor signals from Arduino and forwards to Flask server.
  - Polls Flask for pending relay commands and sends them to Arduino.

Usage:
  python arduino_bridge_ms.py
  python arduino_bridge_ms.py --port COM5
  python arduino_bridge_ms.py --port COM5 --baud 9600
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

def find_arduino_ms_port(no_prompt=False):
    """Auto-detect Arduino UNO COM port for Material Setter"""
    ports = serial.tools.list_ports.comports()
    print("\n=== Available COM Ports ===")
    for port in ports:
        print(f"  {port.device} - {port.description}")
    
    # Try to find Arduino automatically
    for port in ports:
        desc = port.description.lower()
        if 'arduino' in desc or 'ch340' in desc or 'cp210' in desc or 'usb serial' in desc or 'usb-serial' in desc:
            print(f"\n>>> Auto-detected Arduino on: {port.device}")
            return port.device
    
    # If not found, ask user
    if ports:
        print("\n>>> Could not auto-detect Arduino UNO.")
        print(">>> Available ports:", [p.device for p in ports])
        if no_prompt:
            print(">>> Running in auto mode (--no-prompt), skipping interactive prompt.")
            return None
        port_input = input(">>> Enter COM port for Arduino UNO (e.g. COM5): ").strip()
        return port_input if port_input else None
    
    return None

def send_ms_signal_to_flask(signal_type):
    """Send Material Setter button signal to Flask server"""
    try:
        url = f"{FLASK_URL}/api/ms_arduino_signal"
        payload = {"signal": signal_type}
        response = requests.post(url, json=payload, timeout=2)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"  -> MS Signal sent OK: {signal_type} (state: {result.get('state')})")
            else:
                print(f"  -> Server error: {result.get('error', 'Unknown')}")
        else:
            print(f"  -> HTTP Error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"  -> ERROR: Cannot connect to Flask server at {FLASK_URL}")
        print(f"           Make sure cycleTimeMoni.py is running!")
    except Exception as e:
        print(f"  -> ERROR sending MS signal: {e}")

def send_scan_to_flask(scanned_data):
    """Send scanned ID data from R35D-B scanner to Flask server"""
    try:
        url = f"{FLASK_URL}/api/ms_scanner_data"
        payload = {"scanned_id": scanned_data}
        response = requests.post(url, json=payload, timeout=2)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"  -> Scanner data sent OK: {scanned_data}")
            else:
                print(f"  -> Server error: {result.get('error', 'Unknown')}")
        else:
            print(f"  -> HTTP Error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"  -> ERROR: Cannot connect to Flask server at {FLASK_URL}")
    except Exception as e:
        print(f"  -> ERROR sending scan data: {e}")

def send_kitting_scan_to_flask(scanned_data):
    """Send scanned Kitting QR data from 2nd R35D-B scanner to Flask server"""
    try:
        url = f"{FLASK_URL}/api/ms_kitting_scanner_data"
        payload = {"kitting_qr": scanned_data}
        response = requests.post(url, json=payload, timeout=2)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"  -> Kitting scan data sent OK: {scanned_data}")
            else:
                print(f"  -> Server error: {result.get('error', 'Unknown')}")
        else:
            print(f"  -> HTTP Error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"  -> ERROR: Cannot connect to Flask server at {FLASK_URL}")
    except Exception as e:
        print(f"  -> ERROR sending kitting scan data: {e}")

def send_p1_scan_to_flask(scanned_data):
    """Send scanned ID data from P1 Scanner 3 (Serial3) to Flask server"""
    try:
        url = f"{FLASK_URL}/api/p1_scanner_data"
        payload = {"scanned_id": scanned_data}
        response = requests.post(url, json=payload, timeout=2)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"  -> P1 scanner data sent OK: {scanned_data}")
            else:
                print(f"  -> Server error: {result.get('error', 'Unknown')}")
        else:
            print(f"  -> HTTP Error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"  -> ERROR: Cannot connect to Flask server at {FLASK_URL}")
    except Exception as e:
        print(f"  -> ERROR sending P1 scan data: {e}")

def parse_ms_message(message):
    """
    Parse Arduino serial message for Material Setter.
    Expected: MS_LOAD_ID, MS_UNLOAD_ID, STANDBY_MS, MS_SCAN:<data>, MS_KITSCAN:<data>,
              P1_SCAN:<data>, etc. (P1_KITSCAN goes via CT bridge, P2_SCAN via Delvo bridge)
    Returns signal string or None if invalid.
    """
    stripped = message.strip()
    # Check for scanner data (case-sensitive, preserve original data)
    if stripped.upper().startswith("MS_SCAN:"):
        return stripped  # Return full message with data
    if stripped.upper().startswith("MS_KITSCAN:"):
        return stripped  # Return full kitting scan message with data
    if stripped.upper().startswith("P1_SCAN:"):
        return stripped  # Return full P1 scan message with data
    message_upper = stripped.upper()
    if message_upper in ("MS_LOAD_ID", "MS_UNLOAD_ID", "MS2OPEN", "STANDBY_MS", "P1_DONE", "P2_DONE",
                   "MS_OPEN_INTERLOCK", "MS_CLOSE_INTERLOCK",
                   "P1_ID_LOAD", "P1_ID_UNLOAD",
                   "P1_OPEN_INTERLOCK", "P1_CLOSE_INTERLOCK",
                   "P2_ID_LOAD", "P2_ID_UNLOAD",
                   "P2_OPEN_INTERLOCK", "P2_CLOSE_INTERLOCK",
                   "STANDBY_OPEN_INTERLOCK", "STANDBY_CLOSE_INTERLOCK",
                   "MS_SCANNER_RELAY_ON_CONFIRM", "MS_SCANNER_RELAY_OFF_CONFIRM",
                   "MS_SCANNER_READY",
                   "MS_KITTING_LOAD", "MS_KITTING_UNLOAD",
                   "MS_KIT_SCANNER_READY",
                   "MS_KIT_RELAY_ON_CONFIRM", "MS_KIT_RELAY_OFF_CONFIRM",
                   "P1_SCANNER_READY",
                   "P1_SCANNER_RELAY_ON_CONFIRM", "P1_SCANNER_RELAY_OFF_CONFIRM",
                   "P1_KITTING_LOAD", "P1_KITTING_UNLOAD",
                   "P1_KIT_SCANNER_READY",
                   "P1_KIT_RELAY_ON_CONFIRM", "P1_KIT_RELAY_OFF_CONFIRM",
                   "P1_KIT_SCAN_DONE_CONFIRM", "P1_KIT_SCAN_TIMEOUT",
                   "P2_SCANNER_READY",
                   "P2_SCANNER_RELAY_ON_CONFIRM", "P2_SCANNER_RELAY_OFF_CONFIRM",
                   "DELVO_ON_CONFIRM", "DELVO_OFF_CONFIRM"):
        return message_upper
    return None

def poll_pending_commands(ser, stop_event):
    """Poll Flask server for pending relay commands and send to Arduino via serial.
    Runs in a daemon thread."""
    while not stop_event.is_set():
        try:
            resp = requests.get(f"{FLASK_URL}/api/ms_get_pending_command", timeout=2)
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
        stop_event.wait(0.2)  # Poll every 200ms; stop with this connection

def reset_for_startup(ser):
    """Produce a definite reset edge; do not discard queued startup messages."""
    ser.dtr = False
    time.sleep(0.1)
    ser.dtr = True
    time.sleep(2)

def main():
    global FLASK_URL
    # Show existing messages immediately when auto-launched with redirected output.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True, write_through=True)
    
    parser = argparse.ArgumentParser(description="Arduino UNO Serial Bridge for Material Setter")
    parser.add_argument("--port", type=str, help="COM port (e.g. COM5)")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate (default: 9600)")
    parser.add_argument("--url", type=str, default=FLASK_URL, help=f"Flask server URL (default: {FLASK_URL})")
    parser.add_argument("--no-prompt", action="store_true", help="Skip interactive COM port prompt")
    args = parser.parse_args()
    
    FLASK_URL = args.url
    
    print("=" * 50)
    print("  ARDUINO UNO SERIAL BRIDGE")
    print("  Material Setter Button Controller")
    print("=" * 50)
    print(f"  Flask Server: {FLASK_URL}")
    
    # Find Arduino port
    com_port = args.port if args.port else find_arduino_ms_port(no_prompt=args.no_prompt)
    
    if not com_port:
        print("\nERROR: No COM port found. Please connect Arduino UNO and try again.")
        print("       Or specify port manually: python arduino_bridge_ms.py --port COM5")
        sys.exit(1)
    
    print(f"\n>>> Connecting to Arduino UNO on {com_port} at {args.baud} baud...")
    
    # Retry connection indefinitely (never give up — port may be temporarily busy)
    RETRY_DELAY = 5
    ser = None
    attempt = 0
    
    while ser is None:
        attempt += 1
        try:
            ser = serial.Serial(com_port, args.baud, timeout=1, write_timeout=2)
            reset_for_startup(ser)
            print(f">>> Connected successfully to {com_port}!")
        except serial.SerialException as e:
            if ser is not None:
                ser.close()
                ser = None
            timestamp = time.strftime("%H:%M:%S")
            print(f"    [{timestamp}] {com_port} busy ({e}) - retrying in {RETRY_DELAY}s... (attempt {attempt})")
            time.sleep(RETRY_DELAY)

    print(f">>> Listening for Material Setter signals...\n")
    print("-" * 50)
    
    # Start background thread to poll Flask for pending relay commands
    stop_event = threading.Event()
    cmd_thread = threading.Thread(target=poll_pending_commands, args=(ser, stop_event), daemon=True)
    cmd_thread.start()
    receive_buffer = bytearray()
    
    RECONNECT_DELAY = 5
    while True:
        try:
            while True:
                if ser.in_waiting > 0:
                    try:
                        receive_buffer.extend(ser.readline())
                        if not receive_buffer.endswith(b'\n'):
                            continue  # A serial timeout may return only part of a message
                        line = receive_buffer.decode('utf-8').strip()
                    except UnicodeDecodeError:
                        receive_buffer.clear()
                        continue
                    receive_buffer.clear()
                    
                    if not line:
                        continue
                    
                    # Print raw serial data
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"[{timestamp}] Received: {line}")
                    
                    # Skip Arduino ready message
                    if line in ("ESP_READY", "ARDUINO_READY"):
                        print("  -> Arduino is ready!")
                        # Notify Flask that this bridge is ready
                        try:
                            requests.post(f"{FLASK_URL}/api/bridge_ready", json={"bridge": "material_setter"}, timeout=3)
                        except:
                            pass
                        continue
                    
                    # Parse and forward signal
                    signal = parse_ms_message(line)
                    if signal:
                        if signal.upper().startswith("MS_SCAN:"):
                            # Extract scanned data after "MS_SCAN:" prefix
                            scanned_data = signal[8:]  # Everything after "MS_SCAN:"
                            send_scan_to_flask(scanned_data)
                        elif signal.upper().startswith("MS_KITSCAN:"):
                            # Extract kitting scanned data after the first colon and preserve its content.
                            kitting_data = signal.split(":", 1)[1].strip()
                            print(f"  -> MS_KITSCAN detected from Arduino: {kitting_data}")
                            send_kitting_scan_to_flask(kitting_data)
                        elif signal.upper().startswith("P1_SCAN:"):
                            # Extract P1 scanned data after "P1_SCAN:" prefix
                            scanned_data = signal[8:]  # Everything after "P1_SCAN:"
                            send_p1_scan_to_flask(scanned_data)
                        else:
                            send_ms_signal_to_flask(signal)
                    else:
                        print(f"  -> Unknown message (ignored)")
                
                time.sleep(0.01)
        except serial.SerialException as e:
            stop_event.set()
            timestamp = time.strftime("%H:%M:%S")
            print(f"\n[{timestamp}] Serial connection lost: {e}")
            print(f"    Auto-reconnecting in {RECONNECT_DELAY}s...")
            try:
                ser.close()
            except:
                pass
            cmd_thread.join()  # Retire the old command consumer before reconnecting
            receive_buffer.clear()  # Never join fragments across board resets
            # Auto-reconnect loop
            while True:
                time.sleep(RECONNECT_DELAY)
                try:
                    ser = serial.Serial(com_port, args.baud, timeout=1, write_timeout=2)
                    reset_for_startup(ser)
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"[{timestamp}] Reconnected to {com_port}!")
                    print("-" * 50)
                    # Restart pending command thread with new serial connection
                    stop_event = threading.Event()
                    cmd_thread = threading.Thread(target=poll_pending_commands, args=(ser, stop_event), daemon=True)
                    cmd_thread.start()
                    break
                except serial.SerialException:
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"[{timestamp}] Reconnect failed - retrying in {RECONNECT_DELAY}s...")
        except KeyboardInterrupt:
            stop_event.set()
            print("\n\n>>> MS Bridge stopped by user (Ctrl+C)")
            if ser:
                ser.close()
            sys.exit(0)

if __name__ == "__main__":
    main()
