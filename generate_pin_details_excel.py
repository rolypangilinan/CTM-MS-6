"""Generate MATERIAL_SETTER_PIN_DETAILS.xlsx with all 22 pins in detailed format."""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Pin Details"

# ── Styles ──
header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
low_header_fill = PatternFill(start_color="FFD966", end_color="FFD966", fill_type="solid")
low_header_font = Font(name="Calibri", size=11, bold=True)
high_header_fill = PatternFill(start_color="A9D18E", end_color="A9D18E", fill_type="solid")
high_header_font = Font(name="Calibri", size=11, bold=True)
key_header_fill = PatternFill(start_color="FFD966", end_color="FFD966", fill_type="solid")
key_header_font = Font(name="Calibri", size=11, bold=True)
data_font = Font(name="Calibri", size=10)
data_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
low_data_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
high_data_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
key_data_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
thin_border = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin")
)
wrap_center = Alignment(wrap_text=True, vertical="center", horizontal="center")
wrap_left = Alignment(wrap_text=True, vertical="center", horizontal="left")

# ── Column widths ──
col_widths = {
    "A": 10,  # Pin
    "B": 28,  # Type
    "C": 22,  # Console Display
    "D": 14,  # INPUT/OUTPUT
    "E": 16,  # Normally Open
    "F": 16,  # Normally Close
    "G": 14,  # INPUT_PULLUP
    "H": 50,  # Manual Explanation
    "I": 20,  # Signal When LOW
    "J": 60,  # What Will Happen (LOW)
    "K": 22,  # Signal When HIGH
    "L": 60,  # What Will Happen (HIGH)
    "M": 55,  # Key detail
}
for col_letter, width in col_widths.items():
    ws.column_dimensions[col_letter].width = width

# ── Header row ──
headers = [
    ("Pin", header_fill, header_font),
    ("Type", header_fill, header_font),
    ("CONSOLE DISPLAY", header_fill, header_font),
    ("INPUT\nOUTPUT", header_fill, header_font),
    ("NORMALLY\nOPEN", header_fill, header_font),
    ("NORMALLY\nCLOSE", header_fill, header_font),
    ("INPUT_\nPULLUP", header_fill, header_font),
    ("MANUAL EXPLANATION", header_fill, header_font),
    ("Signal When LOW", low_header_fill, low_header_font),
    ("WHAT WILL HAPPEN", low_header_fill, low_header_font),
    ("Signal When HIGH", high_header_fill, high_header_font),
    ("WHAT WILL HAPPEN", high_header_fill, high_header_font),
    ("Key detail", key_header_fill, key_header_font),
]
for col, (text, fill, font) in enumerate(headers, 1):
    c = ws.cell(row=1, column=col, value=text)
    c.font = font
    c.fill = fill
    c.alignment = wrap_center
    c.border = thin_border
ws.row_dimensions[1].height = 30

# ── Pin Data ──
# Each pin: dict with keys: pin, type, console, io, pullup, explanation,
#   signal_low, steps_low, signal_high, steps_high, key_detail
pins = [
    {
        "pin": "PIN 2",
        "type": "IR Sensor 1 (MS ID)",
        "console": "MS_LOAD_ID",
        "io": "INPUT",
        "no": "YES",
        "nc": "NO",
        "pullup": "YES",
        "explanation": "MS ID Detection Sensor (Sensor 1)\nDetects when an operator ID card is placed at the Material Setter scanner position",
        "signal_low": "MS_LOAD_ID",
        "steps_low": [
            "Arduino sends MS_LOAD_ID to PC",
            "Arduino turns ON Scanner 1 power relay on Pin 4 (LOW = ON, Type 1)",
            "Arduino waits 2s boot delay for scanner to power up",
            "Arduino sends trigger {0x16,0x54,0x0D,0x0A} to R35D-B via Serial1 (Pin 18 TX)",
            "Arduino sends MS_SCANNER_READY to PC",
            "R35D-B scans QR, sends data back via Serial1 (Pin 19 RX)",
            "Arduino sends MS_SCAN:<data> to PC",
            "Arduino sends stop command to scanner via Pin 18 TX",
            "Arduino turns OFF Scanner 1 relay on Pin 4 (HIGH = OFF)",
            "PC receives the scanned ID \u2192 frontend auto-fills the operator ID",
        ],
        "signal_high": "MS1UNLOAD",
        "steps_high": [
            "Arduino cancels any active scan, sends stop command to scanner",
            "Arduino turns OFF Scanner 1 relay on Pin 4 (HIGH = OFF)",
            "Arduino sends MS1UNLOAD to PC",
            "PC processes the operator ID removal",
        ],
        "key_detail": "Pin 2 uses 200ms sustained HIGH for unload detection (fast response with noise filtering).\nSensor edge detection is suppressed while interlock is open (interlockOpen flag) to prevent false triggers from relay EMI noise.\nIf ID is removed during a scan, the scan is cancelled and scanner powered off immediately.",
    },
    {
        "pin": "PIN 3",
        "type": "Relay 2 (MS Interlock)",
        "console": "RELAY2_ON / RELAY2_OFF",
        "io": "OUTPUT",
        "no": "NO",
        "nc": "YES",
        "pullup": "NO",
        "explanation": "MS Solenoid Interlock Relay\nControls the gate solenoid at Material Setter. PC-commanded relay (Type 2, Active HIGH).\nInitial state: LOW (closed)",
        "signal_low": "RELAY2_OFF",
        "steps_low": [
            "PC sends RELAY2_OFF command to Arduino",
            "Arduino sets Pin 3 LOW (interlock closes)",
            "Arduino sends MS_CLOSE_INTERLOCK to PC",
            "Gate solenoid de-energizes, dunpla cannot pass",
        ],
        "signal_high": "RELAY2_ON",
        "steps_high": [
            "PC sends RELAY2_ON command to Arduino (after kitting QR saved)",
            "Arduino sets Pin 3 HIGH (interlock opens)",
            "Arduino sends MS_OPEN_INTERLOCK to PC",
            "Gate solenoid energizes, dunpla can pass to Standby",
        ],
        "key_detail": "Type 2 relay (PC-Commanded, Active HIGH).\nInitial state: LOW (closed).\nPC queues RELAY2_ON after kitting data is saved to database.\nPC queues RELAY2_OFF when STANDBY_MS fires (dunpla reaches Standby).\nInterlock state is persisted in MySQL and restored on Flask restart.",
    },
    {
        "pin": "PIN 4",
        "type": "Relay 4 (MS ID Scanner)",
        "console": "SCANNER_RELAY_ON / SCANNER_RELAY_OFF",
        "io": "OUTPUT",
        "no": "YES",
        "nc": "NO",
        "pullup": "NO",
        "explanation": "MS ID R35D-B Scanner Power Relay\nControls power to the Material Setter ID scanner. Pin-controlled relay (Type 1, Active LOW).\nInitial state: HIGH (OFF)",
        "signal_low": "(Scanner ON)",
        "steps_low": [
            "Triggered by Pin 2 (MS ID sensor) detecting ID card",
            "Arduino sets Pin 4 LOW (scanner powers ON)",
            "Scanner boots for 2s (SCANNER_BOOT_DELAY)",
            "Arduino sends trigger to scanner via Serial1 (Pin 18 TX)",
            "Scanner scans QR and returns data via Serial1 (Pin 19 RX)",
        ],
        "signal_high": "(Scanner OFF)",
        "steps_high": [
            "Scan completed successfully \u2192 stop command sent \u2192 Pin 4 HIGH",
            "Or: ID removed mid-scan \u2192 scan cancelled \u2192 Pin 4 HIGH",
            "Or: PC sends SCANNER_RELAY_OFF command \u2192 Pin 4 HIGH",
        ],
        "key_detail": "Type 1 relay (Pin-Controlled, Active LOW = ON).\nInitial state: HIGH (OFF).\nScanner only powered on-demand when ID detected.\nAlways paired with Pin 2 (sensor).\nRetries trigger every 3s if no scan data received.",
    },
    {
        "pin": "PIN 5",
        "type": "IR Sensor 5 (MS Kitting)",
        "console": "MS_KITTING_LOAD",
        "io": "INPUT",
        "no": "YES",
        "nc": "NO",
        "pullup": "YES",
        "explanation": "MS Kitting Detection Sensor\nDetects when a kitting dunpla is placed at the Material Setter kitting scanner position",
        "signal_low": "MS_KITTING_LOAD",
        "steps_low": [
            "Arduino sends MS_KITTING_LOAD to PC",
            "Arduino turns ON Kitting Scanner power relay on Pin 6 (LOW = ON, Type 1)",
            "Arduino waits 2s boot delay for scanner to power up",
            "Arduino sends trigger to R35D-B via Serial2 (Pin 16 TX)",
            "Arduino sends MS_KIT_SCANNER_READY to PC",
            "R35D-B scans QR, sends data back via Serial2 (Pin 17 RX)",
            "Arduino sends MS_KITSCAN:<data> to PC",
            "Arduino sends stop command to scanner via Pin 16 TX",
            "Arduino turns OFF Kitting Scanner relay on Pin 6 (HIGH = OFF)",
        ],
        "signal_high": "MS_KITTING_UNLOAD",
        "steps_high": [
            "Arduino waits 500ms sustained HIGH to confirm removal",
            "Arduino sends MS_KITTING_UNLOAD to PC",
            "Arduino turns OFF Kitting Scanner relay on Pin 6 (HIGH = OFF)",
        ],
        "key_detail": "Uses edge detection (prevKittingSensorState).\n500ms sustained HIGH for unload confirmation.\nScanner is powered off on removal even if scan not complete.\n50ms buffer timeout for end-of-message detection (no CR/LF needed).",
    },
    {
        "pin": "PIN 6",
        "type": "Relay 5 (MS Kitting Scanner)",
        "console": "KIT_RELAY_ON / KIT_RELAY_OFF",
        "io": "OUTPUT",
        "no": "YES",
        "nc": "NO",
        "pullup": "NO",
        "explanation": "MS Kitting R35D-B Scanner Power Relay\nControls power to the Material Setter kitting scanner. Pin-controlled relay (Type 1, Active LOW).\nInitial state: HIGH (OFF)",
        "signal_low": "(Scanner ON)",
        "steps_low": [
            "Triggered by Pin 5 (kitting sensor) detecting dunpla",
            "Arduino sets Pin 6 LOW (scanner powers ON)",
            "Scanner boots for 2s (KITTING_SCANNER_BOOT_DELAY)",
            "Arduino sends trigger to scanner via Serial2 (Pin 16 TX)",
            "Scanner scans QR and returns data via Serial2 (Pin 17 RX)",
        ],
        "signal_high": "(Scanner OFF)",
        "steps_high": [
            "Scan completed successfully \u2192 stop command sent \u2192 Pin 6 HIGH",
            "Or: Dunpla removed (Pin 5 HIGH 500ms) \u2192 Pin 6 HIGH",
            "Or: PC sends KIT_RELAY_OFF command \u2192 Pin 6 HIGH",
        ],
        "key_detail": "Type 1 relay (Pin-Controlled, Active LOW = ON).\nInitial state: HIGH (OFF).\nScanner only powered on-demand when kitting dunpla detected.\nAlways paired with Pin 5 (sensor).",
    },
    {
        "pin": "PIN 7",
        "type": "IR Sensor 2 (Standby)",
        "console": "STANDBY_MS",
        "io": "INPUT",
        "no": "YES",
        "nc": "NO",
        "pullup": "YES",
        "explanation": "Standby Position Sensor (Sensor 2)\nDetects when a dunpla arrives at the Standby position between Material Setter and Process 1",
        "signal_low": "STANDBY_MS",
        "steps_low": [
            "Requires 2s sustained LOW (normal mode) or 3 LOW readings + 100ms (when interlock open)",
            "Arduino sends STANDBY_MS to PC",
            "PC queues RELAY2_OFF \u2192 Arduino sets Pin 3 LOW \u2192 MS interlock closes",
            "Arduino sends MS_CLOSE_INTERLOCK to PC",
            "PC queues STANDBY_RELAY_ON \u2192 Arduino sets Pin 8 HIGH \u2192 Standby interlock opens",
            "Arduino sends STANDBY_OPEN_INTERLOCK to PC",
            "Dunpla can now travel from Standby to Process 1",
        ],
        "signal_high": "(No signal name)",
        "steps_high": [
            "200ms sustained HIGH required (SENSOR2_HIGH_DEBOUNCE) to confirm removal",
            "dunplaAtStandby flag reset to false",
            "Sensor ready for next detection cycle",
        ],
        "key_detail": "Two detection modes:\n1) Normal: 2s sustained LOW (SUSTAIN_CONFIRM_MS)\n2) Fast: 100ms + 3 LOW count accumulator when interlock is open\n200ms HIGH debounce rejects relay EMI noise.\nOne-shot event \u2014 won't re-fire until sensor clears and re-triggers.\nIf P1 timer is already running, Standby interlock will NOT open (dunpla waits).",
    },
    {
        "pin": "PIN 8",
        "type": "Standby Relay (Interlock)",
        "console": "STANDBY_RELAY_ON / STANDBY_RELAY_OFF",
        "io": "OUTPUT",
        "no": "NO",
        "nc": "YES",
        "pullup": "NO",
        "explanation": "Standby Interlock Relay\nControls the gate between Standby and Process 1. PC-commanded relay (Type 2, Active HIGH).\nInitial state: LOW (closed)",
        "signal_low": "STANDBY_RELAY_OFF",
        "steps_low": [
            "PC sends STANDBY_RELAY_OFF to Arduino (when P1_DONE fires)",
            "Arduino sets Pin 8 LOW (interlock closes)",
            "Arduino sends STANDBY_CLOSE_INTERLOCK to PC",
            "Gate closes, dunpla cannot pass to Process 1",
        ],
        "signal_high": "STANDBY_RELAY_ON",
        "steps_high": [
            "PC sends STANDBY_RELAY_ON to Arduino (when STANDBY_MS fires)",
            "Arduino sets Pin 8 HIGH (interlock opens)",
            "Arduino sends STANDBY_OPEN_INTERLOCK to PC",
            "Gate opens, dunpla can pass to Process 1",
        ],
        "key_detail": "Type 2 relay (PC-Commanded, Active HIGH).\nInitial state: LOW (closed).\nOpens when STANDBY_MS fires (dunpla at Standby).\nCloses when P1_DONE fires (dunpla reached Process 1).\nState persisted in MySQL and restored on Flask restart.\nWill NOT open if P1 timer is already running.",
    },
    {
        "pin": "PIN 9",
        "type": "IR Sensor 3 (P1 ID)",
        "console": "P1_ID_LOAD",
        "io": "INPUT",
        "no": "YES",
        "nc": "NO",
        "pullup": "YES",
        "explanation": "P1 ID Detection Sensor (Sensor 3)\nDetects when an operator ID card is placed at the Process 1 scanner position",
        "signal_low": "P1_ID_LOAD",
        "steps_low": [
            "Arduino sends P1_ID_LOAD to PC",
            "Arduino turns ON P1 Scanner 3 power relay on Pin 10 (LOW = ON, Type 1)",
            "Arduino waits 2s boot delay for scanner to power up",
            "Arduino sends trigger {0x16,0x54,0x0D,0x0A} to R35D-B via Serial3 (Pin 14 TX)",
            "Arduino sends P1_SCANNER_READY to PC",
            "R35D-B scans QR, sends data back via Serial3 (Pin 15 RX)",
            "Arduino sends P1_SCAN:<data> to PC",
            "Arduino sends stop command to scanner via Pin 14 TX",
            "Arduino turns OFF Scanner 3 relay on Pin 10 (HIGH = OFF)",
            "PC receives the scanned ID \u2192 frontend auto-fills the operator ID in the \"Scan ID\" modal",
        ],
        "signal_high": "P1_ID_UNLOAD",
        "steps_high": [
            "Arduino cancels any active scan, sends stop command to scanner",
            "Arduino turns OFF Scanner 3 relay on Pin 10 (HIGH = OFF)",
            "Arduino sends P1_ID_UNLOAD to PC",
            "PC signs out the operator from Process 1 (update_time_out + clear_manpower)",
            "Frontend updates \u2014 operator ID is cleared from Process 1 display",
        ],
        "key_detail": "Pin 9's sensor and scanner relay (Pin 10) are both on the MS Arduino, and the scanner serial (Pins 14/15, Serial3) is also on the MS Arduino \u2014 unlike Pin 11 (P1 Kitting) which splits across two Arduinos.\nIf the ID is removed during a scan (before data is received), the scan is cancelled and the scanner is powered off immediately.\n500ms sustained LOW/HIGH required for load/unload.",
    },
    {
        "pin": "PIN 10",
        "type": "Relay 7 (P1 Scanner 3)",
        "console": "P1_SCANNER_RELAY_ON / P1_SCANNER_RELAY_OFF",
        "io": "OUTPUT",
        "no": "YES",
        "nc": "NO",
        "pullup": "NO",
        "explanation": "P1 ID R35D-B Scanner Power Relay (Scanner 3)\nControls power to the Process 1 ID scanner. Pin-controlled relay (Type 1, Active LOW).\nInitial state: HIGH (OFF)",
        "signal_low": "(Scanner ON)",
        "steps_low": [
            "Triggered by Pin 9 (P1 ID sensor) detecting ID card (500ms sustained LOW)",
            "Arduino sets Pin 10 LOW (scanner powers ON)",
            "Scanner boots for 2s",
            "Arduino sends trigger to scanner via Serial3 (Pin 14 TX)",
            "Scanner scans QR and returns data via Serial3 (Pin 15 RX)",
        ],
        "signal_high": "(Scanner OFF)",
        "steps_high": [
            "Scan completed successfully \u2192 stop command sent \u2192 Pin 10 HIGH",
            "Or: ID removed mid-scan (Pin 9 HIGH 500ms) \u2192 scan cancelled \u2192 Pin 10 HIGH",
            "Or: PC sends P1_SCANNER_RELAY_OFF command \u2192 Pin 10 HIGH",
        ],
        "key_detail": "Type 1 relay (Pin-Controlled, Active LOW = ON).\nInitial state: HIGH (OFF).\nScanner only powered on-demand when ID detected at Pin 9.\nAlways paired with Pin 9 (sensor).\nRetries trigger every 3s if no scan data received.",
    },
    {
        "pin": "PIN 11",
        "type": "IR Sensor (P1 Kitting)",
        "console": "P1_KITTING_LOAD",
        "io": "INPUT",
        "no": "YES",
        "nc": "NO",
        "pullup": "YES",
        "explanation": "P1 Kitting Detection Sensor\nDetects when a kitting dunpla is placed at Process 1's kitting position",
        "signal_low": "P1_KITTING_LOAD",
        "steps_low": [
            "Arduino sends P1_KITTING_LOAD to PC",
            "Arduino turns ON P1 Scanner 4 power relay on Pin 12 (LOW = ON, Type 1)",
            "Scan cycle LOCKED (p1KitScanCycleActive = true, immune to sensor glitches)",
            "Arduino waits 2s boot delay for scanner to power up",
            "Arduino sends P1_KIT_SCANNER_READY to PC",
            "PC queues P1_KIT_SCAN_TRIGGER for CT Arduino",
            "CT Arduino sends trigger to Scanner 4 via Serial1 (Pin 18 TX)",
            "R35D-B scans QR, sends data back via Serial1 (Pin 19 RX) to CT Arduino",
            "CT Arduino sends P1_KITSCAN:<data> to PC",
            "PC queues P1_KIT_SCAN_DONE for MS Arduino",
            "MS Arduino unlocks scan cycle, turns OFF relay on Pin 12 (HIGH = OFF)",
            "MS Arduino sends P1_KIT_SCAN_DONE_CONFIRM to PC",
        ],
        "signal_high": "P1_KITTING_UNLOAD",
        "steps_high": [
            "Arduino waits 500ms sustained HIGH to confirm removal",
            "Arduino sends P1_KITTING_UNLOAD to PC",
            "If scan cycle NOT locked: Arduino turns OFF relay on Pin 12 (HIGH = OFF)",
            "If scan cycle IS locked: relay stays ON until P1_KIT_SCAN_DONE or 10s timeout",
        ],
        "key_detail": "Pin 11 is on the MS Arduino, but Scanner 4's serial data (Pins 18/19, Serial1) is on the CT Arduino.\nThe scan trigger goes through PC as a relay between two Arduinos.\nRelay on Pin 12 is LOCKED during scan cycle \u2014 immune to sensor glitches.\n10s safety timeout auto-powers OFF if scan never completes.",
    },
    {
        "pin": "PIN 12",
        "type": "Relay 8 (P1 Kitting Scanner)",
        "console": "P1_KIT_RELAY_ON / P1_KIT_RELAY_OFF",
        "io": "OUTPUT",
        "no": "YES",
        "nc": "NO",
        "pullup": "NO",
        "explanation": "P1 Kitting R35D-B Scanner Power Relay (Scanner 4)\nControls power to the Process 1 kitting scanner. Pin-controlled relay (Type 1, Active LOW).\nInitial state: HIGH (OFF)",
        "signal_low": "(Scanner ON)",
        "steps_low": [
            "Triggered by Pin 11 (P1 kitting sensor) detecting dunpla",
            "Arduino sets Pin 12 LOW (scanner powers ON)",
            "Scan cycle LOCKED (p1KitScanCycleActive = true)",
            "Scanner boots for 2s",
            "Arduino sends P1_KIT_SCANNER_READY to PC",
            "PC triggers scan via CT Arduino",
        ],
        "signal_high": "(Scanner OFF)",
        "steps_high": [
            "PC sends P1_KIT_SCAN_DONE \u2192 Arduino unlocks cycle \u2192 Pin 12 HIGH",
            "Arduino sends P1_KIT_SCAN_DONE_CONFIRM to PC",
            "Or: 10s safety timeout \u2192 auto Pin 12 HIGH",
            "Arduino sends P1_KIT_SCAN_TIMEOUT to PC",
        ],
        "key_detail": "Type 1 relay (Pin-Controlled, Active LOW = ON).\nInitial state: HIGH (OFF).\nLOCKED during scan cycle \u2014 immune to sensor glitches on Pin 11.\nUnlocked ONLY by P1_KIT_SCAN_DONE from PC or 10s safety timeout.\nAlways paired with Pin 11 (sensor).\nScanner data read by CT Arduino, not MS Arduino.",
    },
    {
        "pin": "PIN 13",
        "type": "Relay 9 (P1 Interlock)",
        "console": "RELAY_P1_ON / RELAY_P1_OFF",
        "io": "OUTPUT",
        "no": "NO",
        "nc": "YES",
        "pullup": "NO",
        "explanation": "P1 Solenoid Interlock Relay\nControls the gate at Process 1. PC-commanded relay (Type 2, Active HIGH).\nInitial state: LOW (closed)",
        "signal_low": "RELAY_P1_OFF",
        "steps_low": [
            "PC sends RELAY_P1_OFF command to Arduino",
            "Arduino sets Pin 13 LOW (interlock closes)",
            "Arduino sends P1_CLOSE_INTERLOCK to PC",
            "Gate solenoid de-energizes, dunpla cannot pass",
        ],
        "signal_high": "RELAY_P1_ON",
        "steps_high": [
            "PC sends RELAY_P1_ON command to Arduino",
            "Arduino sets Pin 13 HIGH (interlock opens)",
            "Arduino sends P1_OPEN_INTERLOCK to PC",
            "Gate solenoid energizes, dunpla can pass",
        ],
        "key_detail": "Type 2 relay (PC-Commanded, Active HIGH).\nInitial state: LOW (closed).\nPC-commanded only \u2014 no sensor directly triggers this relay.\nUsed to control dunpla flow at Process 1 exit.",
    },
    {
        "pin": "PIN 14",
        "type": "TX3 (P1 Scanner 3 Trigger)",
        "console": "P1_SCAN_TRIGGER",
        "io": "TX3 (OUTPUT)",
        "no": "N/A",
        "nc": "N/A",
        "pullup": "NO",
        "explanation": "Serial3 TX Pin\nArduino sends commands to P1 ID R35D-B Scanner (Scanner 3) at 115200 baud",
        "signal_low": "Trigger Command",
        "steps_low": [
            "Arduino sends {0x16,0x54,0x0D,0x0A} (SYN + T + CR + LF) to start scanning",
            "Scanner activates and begins reading QR code",
        ],
        "signal_high": "Stop Command",
        "steps_high": [
            "Arduino sends {0x16,0x55,0x0D,0x0A} (SYN + U + CR + LF) to stop scanning",
            "Scanner deactivates and stops reading",
        ],
        "key_detail": "Serial3 TX at 115200 baud.\nUsed by MS Arduino to control P1 ID Scanner 3.\nTrigger sent after 2s boot delay when Pin 9 detects ID.\nStop sent after successful scan or when ID removed.",
    },
    {
        "pin": "PIN 15",
        "type": "RX3 (P1 Scanner 3 Data)",
        "console": "P1_SCAN:<data>",
        "io": "RX3 (INPUT)",
        "no": "N/A",
        "nc": "N/A",
        "pullup": "NO",
        "explanation": "Serial3 RX Pin\nReceives scanned QR data from P1 ID R35D-B Scanner (Scanner 3) at 115200 baud",
        "signal_low": "Receiving Data",
        "steps_low": [
            "Scanner sends scanned QR string to Arduino via Serial3 RX",
            "Arduino assembles bytes into p1ScannerBuffer",
            "On CR/LF: Arduino trims buffer and sends P1_SCAN:<data> to PC",
            "PC processes the scanned operator ID",
        ],
        "signal_high": "No Data",
        "steps_high": [
            "No data on Serial3 RX = scanner idle or not powered",
            "Arduino retries trigger every 3s if scanner is enabled but no data received",
        ],
        "key_detail": "Serial3 RX at 115200 baud.\nData forwarded as P1_SCAN:<data> to PC via Serial (USB).\nBuffer trimmed before sending.\nRetry trigger every 3s (SCAN_RETRY_MS) if no data received.",
    },
    {
        "pin": "PIN 16",
        "type": "TX2 (MS Kitting Scanner Trigger)",
        "console": "KIT_SCAN_TRIGGER",
        "io": "TX2 (OUTPUT)",
        "no": "N/A",
        "nc": "N/A",
        "pullup": "NO",
        "explanation": "Serial2 TX Pin\nArduino sends commands to MS Kitting R35D-B Scanner at 115200 baud",
        "signal_low": "Trigger Command",
        "steps_low": [
            "Arduino sends {0x16,0x54,0x0D,0x0A} (SYN + T + CR + LF) to start scanning",
            "Kitting scanner activates and begins reading QR code",
        ],
        "signal_high": "Stop Command",
        "steps_high": [
            "Arduino sends {0x16,0x55,0x0D,0x0A} (SYN + U + CR + LF) to stop scanning",
            "Kitting scanner deactivates and stops reading",
        ],
        "key_detail": "Serial2 TX at 115200 baud.\nUsed by MS Arduino to control MS Kitting Scanner.\nTrigger sent after 2s boot delay when Pin 5 detects kitting dunpla.\nStop sent after successful scan or when dunpla removed.",
    },
    {
        "pin": "PIN 17",
        "type": "RX2 (MS Kitting Scanner Data)",
        "console": "MS_KITSCAN:<data>",
        "io": "RX2 (INPUT)",
        "no": "N/A",
        "nc": "N/A",
        "pullup": "NO",
        "explanation": "Serial2 RX Pin\nReceives scanned QR data from MS Kitting R35D-B Scanner at 115200 baud",
        "signal_low": "Receiving Data",
        "steps_low": [
            "Kitting scanner sends scanned QR string to Arduino via Serial2 RX",
            "Arduino assembles bytes into kitScannerBuffer",
            "On 50ms silence (buffer timeout): Arduino trims buffer and sends MS_KITSCAN:<data> to PC",
            "PC saves kitting data to database and queues RELAY2_ON to open interlock",
        ],
        "signal_high": "No Data",
        "steps_high": [
            "No data on Serial2 RX = scanner idle or not powered",
            "Arduino retries trigger every 3s if scanner is enabled but no data received",
        ],
        "key_detail": "Serial2 RX at 115200 baud.\nData forwarded as MS_KITSCAN:<data> to PC via Serial (USB).\nUses 50ms buffer timeout for end-of-message detection (KIT_BUFFER_TIMEOUT) instead of CR/LF.\nBuffer trimmed before sending.",
    },
    {
        "pin": "PIN 18",
        "type": "TX1 (MS ID Scanner Trigger)",
        "console": "SCAN_TRIGGER",
        "io": "TX1 (OUTPUT)",
        "no": "N/A",
        "nc": "N/A",
        "pullup": "NO",
        "explanation": "Serial1 TX Pin\nArduino sends commands to MS ID R35D-B Scanner at 115200 baud",
        "signal_low": "Trigger Command",
        "steps_low": [
            "Arduino sends {0x16,0x54,0x0D,0x0A} (SYN + T + CR + LF) to start scanning",
            "ID scanner activates and begins reading QR code",
        ],
        "signal_high": "Stop Command",
        "steps_high": [
            "Arduino sends {0x16,0x55,0x0D,0x0A} (SYN + U + CR + LF) to stop scanning",
            "ID scanner deactivates and stops reading",
        ],
        "key_detail": "Serial1 TX at 115200 baud.\nUsed by MS Arduino to control MS ID Scanner.\nTrigger sent after 2s boot delay when Pin 2 detects ID.\nStop sent after successful scan or when ID removed.\nAlso used by CT Arduino for P1 Kitting Scanner 4 trigger (P1_KIT_SCAN_TRIGGER).",
    },
    {
        "pin": "PIN 19",
        "type": "RX1 (MS ID Scanner Data)",
        "console": "MS_SCAN:<data>",
        "io": "RX1 (INPUT)",
        "no": "N/A",
        "nc": "N/A",
        "pullup": "NO",
        "explanation": "Serial1 RX Pin\nReceives scanned QR data from MS ID R35D-B Scanner at 115200 baud",
        "signal_low": "Receiving Data",
        "steps_low": [
            "ID scanner sends scanned QR string to Arduino via Serial1 RX",
            "Arduino assembles bytes into scannerBuffer",
            "On CR/LF: Arduino trims buffer and sends MS_SCAN:<data> to PC",
            "PC processes the scanned operator ID",
        ],
        "signal_high": "No Data",
        "steps_high": [
            "No data on Serial1 RX = scanner idle or not powered",
            "Arduino retries trigger every 3s if scanner is enabled but no data received",
        ],
        "key_detail": "Serial1 RX at 115200 baud.\nData forwarded as MS_SCAN:<data> to PC via Serial (USB).\nBuffer trimmed before sending.\nOn CT Arduino, this same pin receives P1 Kitting Scanner 4 data (P1_KITSCAN:<data>).",
    },
    {
        "pin": "PIN 22",
        "type": "IR Sensor 6 (P1 Dunpla)",
        "console": "P1_DONE",
        "io": "INPUT",
        "no": "YES",
        "nc": "NO",
        "pullup": "YES",
        "explanation": "Process 1 Dunpla Detection Sensor (Sensor 6)\nDetects when a dunpla arrives at Process 1 from the Standby position",
        "signal_low": "P1_DONE",
        "steps_low": [
            "Requires 500ms sustained LOW (SENSOR_P2_SUSTAIN_MS)",
            "Arduino sends P1_DONE to PC",
            "PC queues STANDBY_RELAY_OFF \u2192 Arduino sets Pin 8 LOW \u2192 Standby interlock closes",
            "Arduino sends STANDBY_CLOSE_INTERLOCK to PC",
            "PC stops Process 1 server timer and saves cycle time record to database",
            "PC sets p2_dunpla_detected = True (dunpla now in P2 area)",
        ],
        "signal_high": "(No signal name)",
        "steps_high": [
            "dunplaAtP1 flag reset to false",
            "Sensor ready for next detection cycle",
        ],
        "key_detail": "One-shot event \u2014 fires once per dunpla arrival, won't re-fire until sensor clears.\n500ms sustained LOW required.\nBoundary marker between Standby and Process 1.\nStandby interlock must already be open (Pin 8 HIGH) for dunpla to reach this sensor.\nCloses the Standby gate behind the dunpla to prevent the next one entering P1.",
    },
    {
        "pin": "PIN 23",
        "type": "IR Sensor 7 (P2 ID)",
        "console": "P2_ID_LOAD",
        "io": "INPUT",
        "no": "YES",
        "nc": "NO",
        "pullup": "YES",
        "explanation": "P2 ID Detection Sensor (Sensor 7)\nDetects when an operator ID card is placed at Process 2. No scanner attached \u2014 detection only.",
        "signal_low": "P2_ID_LOAD",
        "steps_low": [
            "Requires 500ms sustained LOW",
            "Arduino sends P2_ID_LOAD to PC",
            "PC sets p2_id_loaded = True in ms_button_state",
        ],
        "signal_high": "P2_ID_UNLOAD",
        "steps_high": [
            "Requires 500ms sustained HIGH",
            "Arduino sends P2_ID_UNLOAD to PC",
            "PC signs out operator from Process 2 (update_time_out + clear_manpower)",
            "PC sets p2_id_loaded = False in ms_button_state",
        ],
        "key_detail": "No scanner attached to this sensor \u2014 it only detects presence/absence of ID card.\nUses same 500ms sustained timing as Pin 9.\nOperator sign-out happens automatically on ID removal.",
    },
    {
        "pin": "PIN 27",
        "type": "Relay (P2 Interlock)",
        "console": "RELAY_P2_ON / RELAY_P2_OFF",
        "io": "OUTPUT",
        "no": "NO",
        "nc": "YES",
        "pullup": "NO",
        "explanation": "P2 Solenoid Interlock Relay\nControls the gate at Process 2. PC-commanded relay (Type 2, Active HIGH).\nInitial state: LOW (closed)",
        "signal_low": "RELAY_P2_OFF",
        "steps_low": [
            "PC sends RELAY_P2_OFF command to Arduino",
            "Arduino sets Pin 27 LOW (interlock closes)",
            "Arduino sends P2_CLOSE_INTERLOCK to PC",
            "Gate solenoid de-energizes, dunpla cannot pass",
        ],
        "signal_high": "RELAY_P2_ON",
        "steps_high": [
            "PC sends RELAY_P2_ON command to Arduino",
            "Arduino sets Pin 27 HIGH (interlock opens)",
            "Arduino sends P2_OPEN_INTERLOCK to PC",
            "Gate solenoid energizes, dunpla can pass",
        ],
        "key_detail": "Type 2 relay (PC-Commanded, Active HIGH).\nInitial state: LOW (closed).\nPC-commanded only \u2014 no sensor directly triggers this relay.\nUsed to control dunpla flow at Process 2 exit.",
    },
    {
        "pin": "PIN 28",
        "type": "IR Sensor 8 (P2 Dunpla)",
        "console": "P2_DONE",
        "io": "INPUT",
        "no": "YES",
        "nc": "NO",
        "pullup": "YES",
        "explanation": "Process 2 Dunpla Detection Sensor (Sensor 8)\nDetects when a dunpla arrives at Process 2",
        "signal_low": "P2_DONE",
        "steps_low": [
            "Requires 500ms sustained LOW (SENSOR_P3_SUSTAIN_MS)",
            "Arduino sends P2_DONE to PC",
            "PC stops Process 2 server timer and saves cycle time record to database",
        ],
        "signal_high": "(No signal name)",
        "steps_high": [
            "dunplaAtP2 flag reset to false",
            "Sensor ready for next detection cycle",
        ],
        "key_detail": "One-shot event \u2014 fires once per dunpla arrival.\n500ms sustained LOW required (SENSOR_P3_SUSTAIN_MS).\nSignals that dunpla has completed the Process 2 transfer.",
    },
]

# ── Write pin data ──
current_row = 2

for pin_data in pins:
    steps_low = pin_data["steps_low"]
    steps_high = pin_data["steps_high"]
    num_rows = max(len(steps_low), len(steps_high))

    # Write merged columns (A-F): values in top row, merge vertically
    merged_cols = {
        1: pin_data["pin"],
        2: pin_data["type"],
        3: pin_data["console"],
        4: pin_data["io"],
        5: pin_data["no"],
        6: pin_data["nc"],
        7: pin_data["pullup"],
        8: pin_data["explanation"],
    }
    for col, value in merged_cols.items():
        c = ws.cell(row=current_row, column=col, value=value)
        c.font = data_font
        c.fill = data_fill
        c.alignment = wrap_center if col <= 7 else wrap_left
        c.border = thin_border
        # Fill remaining rows and merge
        if num_rows > 1:
            for extra_r in range(1, num_rows):
                ec = ws.cell(row=current_row + extra_r, column=col)
                ec.fill = data_fill
                ec.border = thin_border
            ws.merge_cells(
                start_row=current_row, start_column=col,
                end_row=current_row + num_rows - 1, end_column=col
            )

    # Signal When LOW (col I) - merged
    c = ws.cell(row=current_row, column=9, value=pin_data["signal_low"])
    c.font = data_font
    c.fill = low_data_fill
    c.alignment = wrap_center
    c.border = thin_border
    if num_rows > 1:
        for extra_r in range(1, num_rows):
            ec = ws.cell(row=current_row + extra_r, column=9)
            ec.fill = low_data_fill
            ec.border = thin_border
        ws.merge_cells(start_row=current_row, start_column=9,
                       end_row=current_row + num_rows - 1, end_column=9)

    # What Will Happen LOW (col J)
    for i in range(num_rows):
        c = ws.cell(row=current_row + i, column=10,
                    value=steps_low[i] if i < len(steps_low) else "")
        c.font = data_font
        c.fill = low_data_fill
        c.alignment = wrap_left
        c.border = thin_border

    # Signal When HIGH (col K) - merged
    c = ws.cell(row=current_row, column=11, value=pin_data["signal_high"])
    c.font = data_font
    c.fill = high_data_fill
    c.alignment = wrap_center
    c.border = thin_border
    if num_rows > 1:
        for extra_r in range(1, num_rows):
            ec = ws.cell(row=current_row + extra_r, column=11)
            ec.fill = high_data_fill
            ec.border = thin_border
        ws.merge_cells(start_row=current_row, start_column=11,
                       end_row=current_row + num_rows - 1, end_column=11)

    # What Will Happen HIGH (col L)
    for i in range(num_rows):
        c = ws.cell(row=current_row + i, column=12,
                    value=steps_high[i] if i < len(steps_high) else "")
        c.font = data_font
        c.fill = high_data_fill
        c.alignment = wrap_left
        c.border = thin_border

    # Key detail (col M) - merged
    c = ws.cell(row=current_row, column=13, value=pin_data["key_detail"])
    c.font = data_font
    c.fill = key_data_fill
    c.alignment = wrap_left
    c.border = thin_border
    if num_rows > 1:
        for extra_r in range(1, num_rows):
            ec = ws.cell(row=current_row + extra_r, column=13)
            ec.fill = key_data_fill
            ec.border = thin_border
        ws.merge_cells(start_row=current_row, start_column=13,
                       end_row=current_row + num_rows - 1, end_column=13)

    # Set row heights
    for i in range(num_rows):
        ws.row_dimensions[current_row + i].height = 28

    current_row += num_rows

# Save
output_path = r"c:\Users\Admin\Desktop\NEW HP 60_80 LINE\CYCLE TIME MONITORING\SAVE\NEW\4 W_ SUFFIX AND QTY  BUT W_INFO AT PY TERMINAL\3 HAVE 2 KINDS OF DATABASE\CHAT GPT\3 60-80HP-LINE-APP 4A - FIXED POLLING END POINTS\MATERIAL_SETTER_PIN_DETAILS.xlsx"
wb.save(output_path)
print(f"Excel saved to: {output_path}")
