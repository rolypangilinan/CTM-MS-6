"""
Arduino Serial Bridge for Delvo Driver Interlocking (COM6)
==========================================================
Reads serial data from Delvo Arduino Mega and sends HTTP POST requests
to the Flask web server. Also polls Flask for pending commands to send
to the Arduino (DELVO_RESET_PULSE).

Usage:
  python arduino_bridge_delvo.py
  python arduino_bridge_delvo.py --port COM6
  python arduino_bridge_delvo.py --port COM6 --no-prompt
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

RECONNECT_DELAY = 5

def find_arduino_port(no_prompt=False):
    """Auto-detect Arduino COM port"""
    ports = serial.tools.list_ports.comports()
    print("\n=== Available COM Ports ===")
    for port in ports:
        print(f"  {port.device} - {port.description}")

    for port in ports:
        desc = port.description.lower()
        if 'arduino' in desc or 'ch340' in desc or 'usb serial' in desc or 'usb-serial' in desc:
            print(f"\n>>> Auto-detected Arduino on: {port.device}")
            return port.device

    if ports:
        print("\n>>> Could not auto-detect Arduino.")
        print(">>> Available ports:", [p.device for p in ports])
        if no_prompt:
            print(">>> Running in auto mode (--no-prompt), skipping interactive prompt.")
            return None
        port_input = input(">>> Enter COM port (e.g. COM6): ").strip()
        return port_input if port_input else None

    return None

def send_p2_scan_to_flask(scanned_data):
    """Send scanned ID data from P2 Scanner (Serial3 on COM6) to Flask server"""
    try:
        url = f"{FLASK_URL}/api/p2_scanner_data"
        payload = {"scanned_id": scanned_data}
        response = requests.post(url, json=payload, timeout=2)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"  -> P2 scanner data sent OK: {scanned_data}")
            else:
                print(f"  -> Server error: {result.get('error', 'Unknown')}")
        else:
            print(f"  -> HTTP Error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"  -> ERROR: Cannot connect to Flask server at {FLASK_URL}")
    except Exception as e:
        print(f"  -> ERROR sending P2 scan data: {e}")

def send_signal_to_flask(signal):
    """Send Delvo Arduino signal to Flask server"""
    try:
        url = f"{FLASK_URL}/api/delvo_signal"
        payload = {"signal": signal}
        response = requests.post(url, json=payload, timeout=2)
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print(f"  -> Signal sent OK: {signal}")
            else:
                print(f"  -> Server error: {result.get('error', 'Unknown')}")
        else:
            print(f"  -> HTTP Error: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"  -> ERROR: Cannot connect to Flask server at {FLASK_URL}")
    except Exception as e:
        print(f"  -> ERROR sending signal: {e}")

def poll_pending_commands(ser):
    """Poll Flask server for pending commands and send to Arduino via serial.
    Runs in a daemon thread."""
    while True:
        try:
            resp = requests.get(f"{FLASK_URL}/api/delvo_get_pending_command", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                cmd = data.get("command")
                if cmd:
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"[{timestamp}] Sending to Delvo Arduino: {cmd}")
                    ser.write((cmd + "\n").encode('utf-8'))
        except requests.exceptions.ConnectionError:
            pass
        except Exception:
            pass
        time.sleep(0.2)  # Poll every 200ms

def main():
    global FLASK_URL

    parser = argparse.ArgumentParser(description="Arduino Serial Bridge for Delvo Driver Interlocking")
    parser.add_argument("--port", type=str, help="COM port (e.g. COM6)")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate (default: 9600)")
    parser.add_argument("--url", type=str, default=FLASK_URL, help=f"Flask server URL (default: {FLASK_URL})")
    parser.add_argument("--no-prompt", action="store_true", help="Skip interactive COM port prompt (for auto-launch mode)")
    args = parser.parse_args()

    FLASK_URL = args.url

    print("=" * 50)
    print("  DELVO ARDUINO SERIAL BRIDGE")
    print("  Delvo Driver Interlocking Control")
    print("=" * 50)
    print(f"  Flask Server: {FLASK_URL}")

    # Find Arduino port
    com_port = args.port if args.port else find_arduino_port(no_prompt=args.no_prompt)

    if not com_port:
        print("\nERROR: No COM port found. Please connect Delvo Arduino and try again.")
        print("       Or specify port manually: python arduino_bridge_delvo.py --port COM6")
        sys.exit(1)

    print(f"\n>>> Connecting to Delvo Arduino on {com_port} at {args.baud} baud...")

    # Retry connection indefinitely
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

    # Start command polling thread
    cmd_thread = threading.Thread(target=poll_pending_commands, args=(ser,), daemon=True)
    cmd_thread.start()

    print(f">>> Listening for Delvo Arduino signals...\n")
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

                # Handle known signals
                if line == "DELVO_ARDUINO_READY":
                    print("  -> Delvo Arduino is ready!")
                    try:
                        requests.post(f"{FLASK_URL}/api/bridge_ready", json={"bridge": "delvo"}, timeout=3)
                    except:
                        pass
                    send_signal_to_flask("DELVO_ARDUINO_READY")
                elif line == "DELVO_RESET_DONE":
                    send_signal_to_flask("DELVO_RESET_DONE")
                elif line == "DELVO_SCREW_OK":
                    send_signal_to_flask("DELVO_SCREW_OK")
                elif line.startswith("P2_SCAN:"):
                    scanned_data = line[8:]  # Everything after "P2_SCAN:"
                    print(f"DELVO COM6: P2 scanner data received: {scanned_data}")
                    send_p2_scan_to_flask(scanned_data)
                else:
                    print(f"  -> Unknown message (ignored)")

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\n>>> Bridge stopped by user.")
    except serial.SerialException as e:
        print(f"\n>>> Serial connection lost: {e}")
        print(">>> Please check the Arduino connection and restart the bridge.")
    finally:
        if ser and ser.is_open:
            ser.close()
            print(">>> Serial port closed.")

if __name__ == "__main__":
    main()
