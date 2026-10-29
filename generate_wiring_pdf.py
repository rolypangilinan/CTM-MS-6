"""Generate SERIAL_SELECTOR_WIRING.pdf — Logic circuit wiring diagram."""
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import (
    black, white, red, blue, green, orange, gray, darkgreen,
    Color, HexColor
)

OUTPUT = r"c:\Users\Admin\Desktop\NEW HP 60_80 LINE\CYCLE TIME MONITORING\SAVE\NEW\4 W_ SUFFIX AND QTY  BUT W_INFO AT PY TERMINAL\3 HAVE 2 KINDS OF DATABASE\CHAT GPT\3 60-80HP-LINE-APP 4A - FIXED POLLING END POINTS\SERIAL_SELECTOR_WIRING.pdf"

purple = HexColor("#7030A0")
brown = HexColor("#996633")
dark_blue = HexColor("#003399")
dark_red = HexColor("#CC0000")
teal = HexColor("#008080")
dark_orange = HexColor("#CC6600")

c = canvas.Canvas(OUTPUT, pagesize=landscape(A3))
W, H = landscape(A3)

# ── Helper functions ──
def draw_ic_box(x, y, w, h, label, sublabel, pin_left, pin_right, fill_color=HexColor("#E8E8E8")):
    """Draw an IC chip box with pins labeled on left and right."""
    c.setFillColor(fill_color)
    c.setStrokeColor(black)
    c.setLineWidth(1.5)
    c.roundRect(x, y, w, h, 3, fill=1, stroke=1)
    # IC label
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(x + w/2, y + h - 14, label)
    c.setFont("Helvetica", 7)
    c.drawCentredString(x + w/2, y + h - 23, sublabel)
    # Pin labels
    c.setFont("Helvetica", 6.5)
    n_left = len(pin_left)
    n_right = len(pin_right)
    pin_area_top = y + h - 30
    pin_area_bot = y + 5
    # Left pins (top to bottom)
    for i, (pin_num, pin_name) in enumerate(pin_left):
        py = pin_area_top - i * ((pin_area_top - pin_area_bot) / max(n_left - 1, 1))
        # pin dot
        c.setFillColor(black)
        c.circle(x, py, 2, fill=1)
        # pin number
        c.setFillColor(gray)
        c.drawRightString(x - 4, py - 3, str(pin_num))
        # pin name inside
        c.setFillColor(black)
        c.drawString(x + 4, py - 3, pin_name)
    # Right pins (top to bottom)
    for i, (pin_num, pin_name) in enumerate(pin_right):
        py = pin_area_top - i * ((pin_area_top - pin_area_bot) / max(n_right - 1, 1))
        c.setFillColor(black)
        c.circle(x + w, py, 2, fill=1)
        c.setFillColor(gray)
        c.drawString(x + w + 4, py - 3, str(pin_num))
        c.setFillColor(black)
        c.drawRightString(x + w - 4, py - 3, pin_name)
    return pin_area_top, pin_area_bot

def draw_wire(x1, y1, x2, y2, color=black, width=0.8):
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(x1, y1, x2, y2)

def draw_wire_L(x1, y1, x2, y2, color=black, width=0.8, mid_x=None, mid_y=None):
    """Draw an L-shaped or Z-shaped wire."""
    c.setStrokeColor(color)
    c.setLineWidth(width)
    if mid_x is not None:
        c.line(x1, y1, mid_x, y1)
        c.line(mid_x, y1, mid_x, y2)
        c.line(mid_x, y2, x2, y2)
    elif mid_y is not None:
        c.line(x1, y1, x1, mid_y)
        c.line(x1, mid_y, x2, mid_y)
        c.line(x2, mid_y, x2, y2)
    else:
        c.line(x1, y1, x2, y1)
        c.line(x2, y1, x2, y2)

def draw_dot(x, y, r=2.5):
    c.setFillColor(black)
    c.circle(x, y, r, fill=1, stroke=0)

def draw_label(x, y, text, size=7, color=black, bold=False):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.drawString(x, y, text)

def draw_label_center(x, y, text, size=7, color=black, bold=False):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.drawCentredString(x, y, text)

def draw_switch(x, y, label):
    """Draw a toggle switch symbol."""
    c.setStrokeColor(black)
    c.setLineWidth(1)
    # Base
    c.circle(x, y, 3, fill=0, stroke=1)
    c.circle(x + 25, y, 3, fill=0, stroke=1)
    # Arm
    c.setLineWidth(1.5)
    c.line(x + 3, y, x + 22, y + 8)
    # Label
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x + 12, y - 12, label)
    # Connection points
    return x, y, x + 25, y

def draw_resistor(x, y, label, horizontal=True):
    """Draw a resistor symbol."""
    c.setStrokeColor(black)
    c.setLineWidth(1)
    if horizontal:
        c.line(x, y, x + 5, y)
        c.rect(x + 5, y - 3, 15, 6, fill=0)
        c.line(x + 20, y, x + 25, y)
        c.setFont("Helvetica", 6)
        c.setFillColor(black)
        c.drawCentredString(x + 12, y - 10, label)
    return x, y, x + 25, y

def draw_capacitor(x, y, label):
    c.setStrokeColor(black)
    c.setLineWidth(1)
    c.line(x, y, x, y - 5)
    c.line(x - 4, y - 5, x + 4, y - 5)
    c.line(x - 4, y - 8, x + 4, y - 8)
    c.line(x, y - 8, x, y - 13)
    c.setFont("Helvetica", 5)
    c.setFillColor(black)
    c.drawString(x + 5, y - 8, label)

def draw_gnd(x, y):
    c.setStrokeColor(black)
    c.setLineWidth(1)
    c.line(x, y, x, y - 5)
    c.line(x - 5, y - 5, x + 5, y - 5)
    c.line(x - 3, y - 8, x + 3, y - 8)
    c.line(x - 1, y - 11, x + 1, y - 11)

def draw_vcc(x, y):
    c.setStrokeColor(red)
    c.setLineWidth(1)
    c.line(x, y, x, y + 8)
    c.setFillColor(red)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(x, y + 10, "+5V")

def draw_scanner_box(x, y, w, h):
    c.setFillColor(HexColor("#FFFFCC"))
    c.setStrokeColor(dark_orange)
    c.setLineWidth(2)
    c.roundRect(x, y, w, h, 5, fill=1, stroke=1)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(x + w/2, y + h - 18, "R35D-B SCANNER")
    c.setFont("Helvetica", 8)
    c.drawCentredString(x + w/2, y + h - 30, "(Device Under Test)")
    # Pins
    pin_y = y + 15
    c.setFont("Helvetica-Bold", 8)
    for i, (name, clr) in enumerate([("TX", blue), ("RX", green), ("GND", black)]):
        px = x + 25 + i * 45
        c.setFillColor(clr)
        c.drawCentredString(px, pin_y, name)
        c.circle(px, pin_y + 10, 3, fill=1)

def draw_serial_port(x, y, label1, label2, tx_pin, rx_pin):
    """Draw a serial port box."""
    c.setFillColor(HexColor("#CCE5FF"))
    c.setStrokeColor(dark_blue)
    c.setLineWidth(1.5)
    c.roundRect(x, y, 105, 55, 4, fill=1, stroke=1)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x + 52, y + 42, label1)
    c.setFont("Helvetica", 7)
    c.drawCentredString(x + 52, y + 32, label2)
    # TX pin
    c.setFillColor(blue)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x + 5, y + 17, f"TX (Pin {tx_pin})")
    c.circle(x, y + 19, 2.5, fill=1)
    # RX pin
    c.setFillColor(green)
    c.drawString(x + 5, y + 7, f"RX (Pin {rx_pin})")
    c.circle(x, y + 9, 2.5, fill=1)
    # GND
    c.setFillColor(black)
    c.drawString(x + 65, y + 7, "GND")
    c.circle(x + 62, y + 9, 2.5, fill=1)


# ════════════════════════════════════════════════════════════
#  PAGE 1: BLOCK DIAGRAM
# ════════════════════════════════════════════════════════════
c.setFont("Helvetica-Bold", 18)
c.setFillColor(dark_blue)
c.drawCentredString(W/2, H - 30, "SERIAL PORT SELECTOR — WIRING DIAGRAM")
c.setFont("Helvetica", 10)
c.setFillColor(black)
c.drawCentredString(W/2, H - 45, "4-to-1 MUX using 74LS08 (AND), 74LS32 (OR), 74LS04 (INV)  |  2 Switches select 1 of 4 serial ports")

# ── Scanner (top-left) ──
draw_scanner_box(30, H - 130, 150, 70)
scanner_tx_x, scanner_tx_y = 55, H - 105
scanner_rx_x, scanner_rx_y = 100, H - 105
scanner_gnd_x, scanner_gnd_y = 145, H - 105

# ── Switches (left side) ──
sw0_x, sw0_y = 50, H - 185
sw1_x, sw1_y = 50, H - 225
draw_switch(sw0_x, sw0_y, "SW0")
draw_switch(sw1_x, sw1_y, "SW1")
# Pull-down resistors
draw_resistor(sw0_x - 30, sw0_y, "10k\u03A9")
draw_gnd(sw0_x - 30, sw0_y - 15)
draw_wire(sw0_x - 30, sw0_y, sw0_x, sw0_y, black)
draw_resistor(sw1_x - 30, sw1_y, "10k\u03A9")
draw_gnd(sw1_x - 30, sw1_y - 15)
draw_wire(sw1_x - 30, sw1_y, sw1_x, sw1_y, black)
# VCC to switch other end
draw_vcc(sw0_x + 25, sw0_y)
draw_vcc(sw1_x + 25, sw1_y)
# Labels
draw_label(sw0_x + 30, sw0_y - 3, "→ SW0 signal", 7, blue)
draw_label(sw1_x + 30, sw1_y - 3, "→ SW1 signal", 7, red)

# ── IC1: 74LS04 Inverter ──
ic1_x, ic1_y = 200, H - 240
ic1_w, ic1_h = 90, 70
draw_ic_box(ic1_x, ic1_y, ic1_w, ic1_h, "74LS04", "Hex Inverter",
    [(1, "1A=SW0"), (3, "2A=SW1")],
    [(2, "1Y=SW0'"), (4, "2Y=SW1'")],
    HexColor("#E8F0E8"))
draw_label(ic1_x + ic1_w + 5, ic1_y + ic1_h - 5, "IC1", 8, teal, True)
# Power
draw_label(ic1_x + 2, ic1_y - 10, "Pin14=VCC, Pin7=GND", 6, gray)

# ── IC2: 74LS08 Enable Generator ──
ic2_x, ic2_y = 370, H - 260
ic2_w, ic2_h = 110, 110
draw_ic_box(ic2_x, ic2_y, ic2_w, ic2_h, "74LS08 (IC2)", "Enable Generator",
    [(1, "SW1'"), (2, "SW0'"), (4, "SW1'"), (5, "SW0"), (9, "SW1"), (10, "SW0'"), (12, "SW1"), (13, "SW0")],
    [(3, "EN0 (00)"), (6, "EN1 (01)"), (8, "EN2 (10)"), (11, "EN3 (11)")],
    HexColor("#F0E8E8"))
draw_label(ic2_x + ic2_w + 5, ic2_y + ic2_h - 5, "IC2", 8, teal, True)
draw_label(ic2_x + 2, ic2_y - 10, "Pin14=VCC, Pin7=GND", 6, gray)

# ── IC3: 74LS08 TX Gate (Scanner→Arduino) ──
ic3_x, ic3_y = 560, H - 170
ic3_w, ic3_h = 120, 100
draw_ic_box(ic3_x, ic3_y, ic3_w, ic3_h, "74LS08 (IC3)", "TX Gate: Scanner\u2192Arduino",
    [(1, "Scanner_TX"), (2, "EN0"), (4, "Scanner_TX"), (5, "EN1"), (9, "Scanner_TX"), (10, "EN2"), (12, "Scanner_TX"), (13, "EN3")],
    [(3, "\u2192Ser1 COM3 RX"), (6, "\u2192Ser2 COM3 RX"), (8, "\u2192Ser3 COM3 RX"), (11, "\u2192Ser1 COM2 RX")],
    HexColor("#E8E8F0"))
draw_label(ic3_x + ic3_w + 5, ic3_y + ic3_h - 5, "IC3", 8, teal, True)
draw_label(ic3_x + 2, ic3_y - 10, "Pin14=VCC, Pin7=GND", 6, gray)

# ── IC4: 74LS08 RX Gate (Arduino→Scanner) ──
ic4_x, ic4_y = 560, H - 310
ic4_w, ic4_h = 120, 100
draw_ic_box(ic4_x, ic4_y, ic4_w, ic4_h, "74LS08 (IC4)", "RX Gate: Arduino\u2192Scanner",
    [(1, "Ser1 COM3 TX"), (2, "EN0"), (4, "Ser2 COM3 TX"), (5, "EN1"), (9, "Ser3 COM3 TX"), (10, "EN2"), (12, "Ser1 COM2 TX"), (13, "EN3")],
    [(3, "G0_RX"), (6, "G1_RX"), (8, "G2_RX"), (11, "G3_RX")],
    HexColor("#F0F0E0"))
draw_label(ic4_x + ic4_w + 5, ic4_y + ic4_h - 5, "IC4", 8, teal, True)
draw_label(ic4_x + 2, ic4_y - 10, "Pin14=VCC, Pin7=GND", 6, gray)

# ── IC5: 74LS32 OR Tree ──
ic5_x, ic5_y = 780, H - 310
ic5_w, ic5_h = 110, 100
draw_ic_box(ic5_x, ic5_y, ic5_w, ic5_h, "74LS32 (IC5)", "OR Tree \u2192 Scanner RX",
    [(1, "G0_RX"), (2, "G1_RX"), (4, "G2_RX"), (5, "G3_RX"), (9, "OR1"), (10, "OR2")],
    [(3, "OR1"), (6, "OR2"), (8, "Scanner_RX")],
    HexColor("#F0E0F0"))
draw_label(ic5_x + ic5_w + 5, ic5_y + ic5_h - 5, "IC5", 8, teal, True)
draw_label(ic5_x + 2, ic5_y - 10, "Pin14=VCC, Pin7=GND", 6, gray)

# ── Serial Port Boxes (right side) ──
sp_x = 810
sp_y_start = H - 120
sp_gap = 62
serial_ports = [
    ("Serial1 COM3", "MS Arduino Pin 18/19", 18, 19),
    ("Serial2 COM3", "MS Arduino Pin 16/17", 16, 17),
    ("Serial3 COM3", "MS Arduino Pin 14/15", 14, 15),
    ("Serial1 COM2", "CT Arduino Pin 18/19", 18, 19),
]
for i, (l1, l2, tx, rx) in enumerate(serial_ports):
    draw_serial_port(sp_x, sp_y_start - i * sp_gap, l1, l2, tx, rx)

# ── Connection lines from IC3 outputs to serial port RX pins ──
colors_sp = [dark_red, blue, darkgreen, purple]
for i in range(4):
    sp_rx_y = sp_y_start - i * sp_gap + 9
    # draw arrow from right side
    draw_wire(sp_x - 5, sp_rx_y, sp_x, sp_rx_y, colors_sp[i], 1.2)
    draw_label(sp_x - 80, sp_rx_y - 3, f"from IC3 pin {[3,6,8,11][i]}", 6, colors_sp[i])

# ── Connection lines from serial port TX pins to IC4 inputs ──
for i in range(4):
    sp_tx_y = sp_y_start - i * sp_gap + 19
    draw_label(sp_x - 80, sp_tx_y - 3, f"to IC4 pin {[1,4,9,12][i]}", 6, colors_sp[i])

# ── Scanner_RX from IC5 ──
draw_label(ic5_x + ic5_w + 5, ic5_y + 55, "\u2192 Scanner RX", 8, green, True)

# ── Legend ──
legend_x = 30
legend_y = 80
c.setFont("Helvetica-Bold", 10)
c.setFillColor(black)
c.drawString(legend_x, legend_y + 55, "LEGEND")
c.setFont("Helvetica", 7)
items = [
    ("SW0=0, SW1=0 \u2192 Serial1 COM3 (MS Arduino, Pin 18 TX / Pin 19 RX)", black),
    ("SW0=1, SW1=0 \u2192 Serial2 COM3 (MS Arduino, Pin 16 TX / Pin 17 RX)", black),
    ("SW0=0, SW1=1 \u2192 Serial3 COM3 (MS Arduino, Pin 14 TX / Pin 15 RX)", black),
    ("SW0=1, SW1=1 \u2192 Serial1 COM2 (CT Arduino, Pin 18 TX / Pin 19 RX)", black),
]
for i, (txt, clr) in enumerate(items):
    c.setFillColor(clr)
    c.drawString(legend_x, legend_y + 40 - i * 12, txt)

# Selection table
tbl_x = 400
tbl_y = legend_y
c.setFont("Helvetica-Bold", 9)
c.setFillColor(black)
c.drawString(tbl_x, tbl_y + 55, "SELECTION TABLE")
c.setFont("Helvetica-Bold", 7)
c.setFillColor(white)
c.setStrokeColor(black)
c.setLineWidth(1)
# Header
c.setFillColor(dark_blue)
c.rect(tbl_x, tbl_y + 38, 40, 14, fill=1)
c.rect(tbl_x + 40, tbl_y + 38, 40, 14, fill=1)
c.rect(tbl_x + 80, tbl_y + 38, 60, 14, fill=1)
c.rect(tbl_x + 140, tbl_y + 38, 60, 14, fill=1)
c.rect(tbl_x + 200, tbl_y + 38, 100, 14, fill=1)
c.setFillColor(white)
c.drawCentredString(tbl_x + 20, tbl_y + 42, "SW1")
c.drawCentredString(tbl_x + 60, tbl_y + 42, "SW0")
c.drawCentredString(tbl_x + 110, tbl_y + 42, "EN Active")
c.drawCentredString(tbl_x + 170, tbl_y + 42, "Port")
c.drawCentredString(tbl_x + 250, tbl_y + 42, "Connection")
# Rows
rows = [
    ("0", "0", "EN0", "Serial1 COM3", "MS Arduino Pin 18/19"),
    ("0", "1", "EN1", "Serial2 COM3", "MS Arduino Pin 16/17"),
    ("1", "0", "EN2", "Serial3 COM3", "MS Arduino Pin 14/15"),
    ("1", "1", "EN3", "Serial1 COM2", "CT Arduino Pin 18/19"),
]
c.setFont("Helvetica", 7)
for i, (s1, s0, en, port, conn) in enumerate(rows):
    ry = tbl_y + 24 - i * 14
    c.setFillColor(HexColor("#F0F0F0") if i % 2 == 0 else white)
    c.rect(tbl_x, ry, 40, 14, fill=1)
    c.rect(tbl_x + 40, ry, 40, 14, fill=1)
    c.rect(tbl_x + 80, ry, 60, 14, fill=1)
    c.rect(tbl_x + 140, ry, 60, 14, fill=1)
    c.rect(tbl_x + 200, ry, 100, 14, fill=1)
    c.setFillColor(black)
    c.drawCentredString(tbl_x + 20, ry + 4, s1)
    c.drawCentredString(tbl_x + 60, ry + 4, s0)
    c.drawCentredString(tbl_x + 110, ry + 4, en)
    c.drawCentredString(tbl_x + 170, ry + 4, port)
    c.drawCentredString(tbl_x + 250, ry + 4, conn)

# ── BOM ──
bom_x = 750
bom_y = legend_y
c.setFont("Helvetica-Bold", 9)
c.setFillColor(black)
c.drawString(bom_x, bom_y + 55, "BILL OF MATERIALS")
c.setFont("Helvetica", 7)
bom_items = [
    "1x 74LS04 (Hex Inverter) — IC1",
    "3x 74LS08 (Quad 2-input AND) — IC2, IC3, IC4",
    "1x 74LS32 (Quad 2-input OR) — IC5",
    "2x Toggle Switch (SPST)",
    "2x 10k\u03A9 Resistor (pull-down)",
    "5x 0.1\u00B5F Ceramic Capacitor (bypass)",
    "1x R35D-B QR Scanner",
]
for i, item in enumerate(bom_items):
    c.drawString(bom_x, bom_y + 40 - i * 10, item)

# ── Notes ──
notes_x = 30
notes_y = 30
c.setFont("Helvetica-Bold", 8)
c.setFillColor(dark_red)
c.drawString(notes_x, notes_y + 15, "IMPORTANT NOTES:")
c.setFont("Helvetica", 7)
c.setFillColor(black)
notes = [
    "1. All ICs: VCC (Pin 14) = +5V, GND (Pin 7) = Ground.  Place 0.1\u00B5F bypass cap between VCC and GND on each IC.",
    "2. Switches: SPST toggle. One side to +5V, other side to signal line. 10k\u03A9 pull-down to GND on signal side.",
    "3. All GNDs must be connected together: Scanner GND + Arduino GND + IC GND = common ground.",
    "4. 74LS series is 5V TTL. R35D-B scanner must be 5V TTL compatible. For 3.3V logic, add level shifters.",
]
for i, note in enumerate(notes):
    c.drawString(notes_x, notes_y + 3 - i * 9, note)


# ════════════════════════════════════════════════════════════
#  PAGE 2: DETAILED PIN-TO-PIN WIRING TABLE
# ════════════════════════════════════════════════════════════
c.showPage()
c.setFont("Helvetica-Bold", 16)
c.setFillColor(dark_blue)
c.drawCentredString(W/2, H - 30, "DETAILED PIN-TO-PIN WIRING LIST")
c.setFont("Helvetica", 9)
c.setFillColor(black)
c.drawCentredString(W/2, H - 45, "Every wire connection listed: FROM \u2192 TO")

# Table header
th_y = H - 75
th_x = 40
col_w = [30, 180, 30, 180, 200]
headers_p2 = ["#", "FROM", "", "TO", "PURPOSE"]
c.setFillColor(dark_blue)
cx = th_x
for i, w in enumerate(col_w):
    c.rect(cx, th_y, w, 18, fill=1)
    cx += w
c.setFillColor(white)
c.setFont("Helvetica-Bold", 8)
cx = th_x
for i, (h, w) in enumerate(zip(headers_p2, col_w)):
    c.drawCentredString(cx + w/2, th_y + 5, h)
    cx += w

# Wiring data
wires = [
    # Switches & Inverter
    ("1", "SW0 (switch output)", "\u2192", "IC1 74LS04 Pin 1 (1A)", "SW0 signal to inverter input"),
    ("2", "SW1 (switch output)", "\u2192", "IC1 74LS04 Pin 3 (2A)", "SW1 signal to inverter input"),
    ("3", "IC1 74LS04 Pin 2 (1Y=SW0')", "\u2192", "IC2 74LS08 Pin 2, Pin 10", "SW0 inverted to EN0 and EN2 generator"),
    ("4", "IC1 74LS04 Pin 4 (2Y=SW1')", "\u2192", "IC2 74LS08 Pin 1, Pin 4", "SW1 inverted to EN0 and EN1 generator"),
    # SW direct to IC2
    ("5", "SW0 (direct)", "\u2192", "IC2 74LS08 Pin 5, Pin 13", "SW0 direct to EN1 and EN3 generator"),
    ("6", "SW1 (direct)", "\u2192", "IC2 74LS08 Pin 9, Pin 12", "SW1 direct to EN2 and EN3 generator"),
    # EN lines from IC2 to IC3 and IC4
    ("7", "IC2 Pin 3 (EN0)", "\u2192", "IC3 Pin 2, IC4 Pin 2", "EN0 enables Serial1 COM3 gates"),
    ("8", "IC2 Pin 6 (EN1)", "\u2192", "IC3 Pin 5, IC4 Pin 5", "EN1 enables Serial2 COM3 gates"),
    ("9", "IC2 Pin 8 (EN2)", "\u2192", "IC3 Pin 10, IC4 Pin 10", "EN2 enables Serial3 COM3 gates"),
    ("10", "IC2 Pin 11 (EN3)", "\u2192", "IC3 Pin 13, IC4 Pin 13", "EN3 enables Serial1 COM2 gates"),
    # Scanner TX to IC3
    ("11", "R35D-B Scanner TX", "\u2192", "IC3 Pin 1, 4, 9, 12", "Scanner TX to all 4 AND gate inputs"),
    # IC3 outputs to Arduino RX pins
    ("12", "IC3 Pin 3 (gate out)", "\u2192", "Serial1 COM3 RX (MS Arduino Pin 19)", "Scanner data to Serial1 COM3"),
    ("13", "IC3 Pin 6 (gate out)", "\u2192", "Serial2 COM3 RX (MS Arduino Pin 17)", "Scanner data to Serial2 COM3"),
    ("14", "IC3 Pin 8 (gate out)", "\u2192", "Serial3 COM3 RX (MS Arduino Pin 15)", "Scanner data to Serial3 COM3"),
    ("15", "IC3 Pin 11 (gate out)", "\u2192", "Serial1 COM2 RX (CT Arduino Pin 19)", "Scanner data to Serial1 COM2"),
    # Arduino TX pins to IC4
    ("16", "Serial1 COM3 TX (MS Arduino Pin 18)", "\u2192", "IC4 Pin 1", "Arduino trigger cmd to gate"),
    ("17", "Serial2 COM3 TX (MS Arduino Pin 16)", "\u2192", "IC4 Pin 4", "Arduino trigger cmd to gate"),
    ("18", "Serial3 COM3 TX (MS Arduino Pin 14)", "\u2192", "IC4 Pin 9", "Arduino trigger cmd to gate"),
    ("19", "Serial1 COM2 TX (CT Arduino Pin 18)", "\u2192", "IC4 Pin 12", "Arduino trigger cmd to gate"),
    # IC4 outputs to IC5 OR tree
    ("20", "IC4 Pin 3 (G0_RX)", "\u2192", "IC5 74LS32 Pin 1", "OR tree input 1"),
    ("21", "IC4 Pin 6 (G1_RX)", "\u2192", "IC5 74LS32 Pin 2", "OR tree input 2"),
    ("22", "IC4 Pin 8 (G2_RX)", "\u2192", "IC5 74LS32 Pin 4", "OR tree input 3"),
    ("23", "IC4 Pin 11 (G3_RX)", "\u2192", "IC5 74LS32 Pin 5", "OR tree input 4"),
    # IC5 internal
    ("24", "IC5 Pin 3 (OR1)", "\u2192", "IC5 Pin 9", "First OR output to final OR input A"),
    ("25", "IC5 Pin 6 (OR2)", "\u2192", "IC5 Pin 10", "Second OR output to final OR input B"),
    # IC5 output to scanner
    ("26", "IC5 Pin 8 (final OR out)", "\u2192", "R35D-B Scanner RX", "Combined Arduino TX to scanner"),
    # Power
    ("27", "+5V VCC", "\u2192", "IC1-IC5 Pin 14", "Power all ICs"),
    ("28", "GND", "\u2192", "IC1-IC5 Pin 7", "Ground all ICs"),
    ("29", "GND", "\u2192", "R35D-B Scanner GND", "Common ground with scanner"),
    ("30", "GND", "\u2192", "Arduino GND (COM3 + COM2)", "Common ground with both Arduinos"),
]

c.setFont("Helvetica", 7)
row_h = 16
for i, (num, frm, arrow, to, purpose) in enumerate(wires):
    ry = th_y - 18 - i * row_h
    if ry < 40:  # page break if needed
        c.showPage()
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(dark_blue)
        c.drawCentredString(W/2, H - 30, "DETAILED PIN-TO-PIN WIRING LIST (continued)")
        th_y = H - 55
        ry = th_y - 18 - 0 * row_h
        # re-draw header
        c.setFillColor(dark_blue)
        cx = th_x
        for j, w in enumerate(col_w):
            c.rect(cx, th_y, w, 18, fill=1)
            cx += w
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 8)
        cx = th_x
        for j, (h, w) in enumerate(zip(headers_p2, col_w)):
            c.drawCentredString(cx + w/2, th_y + 5, h)
            cx += w
        c.setFont("Helvetica", 7)

    # Alternate row shading
    c.setFillColor(HexColor("#F5F5F5") if i % 2 == 0 else white)
    cx = th_x
    for j, w in enumerate(col_w):
        c.rect(cx, ry, w, row_h, fill=1, stroke=1)
        cx += w
    c.setFillColor(black)
    vals = [num, frm, arrow, to, purpose]
    cx = th_x
    for j, (v, w) in enumerate(zip(vals, col_w)):
        if j == 0 or j == 2:
            c.drawCentredString(cx + w/2, ry + 4, v)
        else:
            c.drawString(cx + 3, ry + 4, v)
        cx += w


# ════════════════════════════════════════════════════════════
#  PAGE 3: PHYSICAL IC PINOUT REFERENCE
# ════════════════════════════════════════════════════════════
c.showPage()
c.setFont("Helvetica-Bold", 16)
c.setFillColor(dark_blue)
c.drawCentredString(W/2, H - 30, "IC PINOUT REFERENCE")

def draw_dip14(x, y, ic_name, ic_desc, pin_names_left, pin_names_right):
    """Draw a DIP-14 IC package with pin names."""
    w, h = 120, 160
    c.setFillColor(HexColor("#333333"))
    c.setStrokeColor(black)
    c.setLineWidth(2)
    c.roundRect(x, y, w, h, 3, fill=1, stroke=1)
    # Notch
    c.setFillColor(HexColor("#555555"))
    c.circle(x + w/2, y + h, 5, fill=1)
    # IC name
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(x + w/2, y + h/2 + 10, ic_name)
    c.setFont("Helvetica", 7)
    c.drawCentredString(x + w/2, y + h/2 - 2, ic_desc)
    # Left pins (1-7, top to bottom)
    pin_spacing = (h - 20) / 6
    c.setFont("Helvetica-Bold", 8)
    for i in range(7):
        py = y + h - 15 - i * pin_spacing
        # Pin pad
        c.setFillColor(HexColor("#CCCCCC"))
        c.rect(x - 20, py - 5, 20, 10, fill=1, stroke=1)
        # Pin number
        c.setFillColor(black)
        c.drawCentredString(x - 10, py - 3, str(i + 1))
        # Pin name
        c.setFillColor(dark_blue)
        c.setFont("Helvetica", 7)
        c.drawRightString(x - 24, py - 3, pin_names_left[i])
    # Right pins (14-8, top to bottom)
    for i in range(7):
        py = y + h - 15 - i * pin_spacing
        c.setFillColor(HexColor("#CCCCCC"))
        c.rect(x + w, py - 5, 20, 10, fill=1, stroke=1)
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x + w + 10, py - 3, str(14 - i))
        c.setFillColor(dark_blue)
        c.setFont("Helvetica", 7)
        c.drawString(x + w + 24, py - 3, pin_names_right[i])

# 74LS04
draw_dip14(60, H - 250, "74LS04", "Hex Inverter",
    ["1A (SW0)", "1Y (SW0')", "2A (SW1)", "2Y (SW1')", "3A (n/c)", "3Y (n/c)", "GND"],
    ["VCC (+5V)", "6A (n/c)", "6Y (n/c)", "5A (n/c)", "5Y (n/c)", "4A (n/c)", "4Y (n/c)"])

# 74LS08 (IC2)
draw_dip14(340, H - 250, "74LS08", "AND (IC2-Enable)",
    ["1A (SW1')", "1B (SW0')", "1Y (EN0)", "2A (SW1')", "2B (SW0)", "2Y (EN1)", "GND"],
    ["VCC (+5V)", "4B (SW0)", "4A (SW1)", "4Y (EN3)", "3B (SW0')", "3A (SW1)", "3Y (EN2)"])

# 74LS08 (IC3)
draw_dip14(620, H - 250, "74LS08", "AND (IC3-TX Gate)",
    ["1A (Scn TX)", "1B (EN0)", "1Y (\u2192S1RX)", "2A (Scn TX)", "2B (EN1)", "2Y (\u2192S2RX)", "GND"],
    ["VCC (+5V)", "4B (EN3)", "4A (Scn TX)", "4Y (\u2192COM2RX)", "3B (EN2)", "3A (Scn TX)", "3Y (\u2192S3RX)"])

# 74LS08 (IC4)
draw_dip14(120, H - 490, "74LS08", "AND (IC4-RX Gate)",
    ["1A (S1 TX)", "1B (EN0)", "1Y (G0)", "2A (S2 TX)", "2B (EN1)", "2Y (G1)", "GND"],
    ["VCC (+5V)", "4B (EN3)", "4A (COM2TX)", "4Y (G3)", "3B (EN2)", "3A (S3 TX)", "3Y (G2)"])

# 74LS32 (IC5)
draw_dip14(440, H - 490, "74LS32", "OR (IC5-Tree)",
    ["1A (G0)", "1B (G1)", "1Y (OR1)", "2A (G2)", "2B (G3)", "2Y (OR2)", "GND"],
    ["VCC (+5V)", "4B (n/c)", "4A (n/c)", "4Y (n/c)", "3B (OR2)", "3A (OR1)", "3Y (Scn RX)"])

# Scanner pinout
scn_x, scn_y = 700, H - 490
c.setFillColor(HexColor("#FFFFCC"))
c.setStrokeColor(dark_orange)
c.setLineWidth(2)
c.roundRect(scn_x, scn_y, 180, 160, 5, fill=1, stroke=1)
c.setFillColor(black)
c.setFont("Helvetica-Bold", 12)
c.drawCentredString(scn_x + 90, scn_y + 135, "R35D-B SCANNER")
c.setFont("Helvetica", 9)
c.drawCentredString(scn_x + 90, scn_y + 118, "QR Code Reader")
c.setFont("Helvetica-Bold", 9)
pin_info = [
    ("TX (Yellow wire)", "Scanner transmits scanned data", blue),
    ("RX (Green wire)", "Scanner receives trigger/stop cmds", green),
    ("GND (Black wire)", "Common ground", black),
    ("VCC (Red wire)", "Power +5V (from relay)", red),
]
for i, (name, desc, clr) in enumerate(pin_info):
    py = scn_y + 90 - i * 25
    c.setFillColor(clr)
    c.circle(scn_x + 15, py + 3, 4, fill=1)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(scn_x + 25, py, name)
    c.setFont("Helvetica", 7)
    c.setFillColor(black)
    c.drawString(scn_x + 25, py - 10, desc)

# Save
c.save()
print(f"PDF saved to: {OUTPUT}")
