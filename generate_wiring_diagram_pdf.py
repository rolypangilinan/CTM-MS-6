"""Generate SERIAL_SELECTOR_WIRING_DIAGRAM.pdf — Visual wiring diagram with colored wire routes."""
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, white, gray, HexColor

OUTPUT = r"c:\Users\Admin\Desktop\NEW HP 60_80 LINE\CYCLE TIME MONITORING\SAVE\NEW\4 W_ SUFFIX AND QTY  BUT W_INFO AT PY TERMINAL\3 HAVE 2 KINDS OF DATABASE\CHAT GPT\3 60-80HP-LINE-APP 4A - FIXED POLLING END POINTS\SERIAL_SELECTOR_WIRING_DIAGRAM.pdf"

# Colors
BLUE = HexColor("#0066CC")
RED = HexColor("#CC0000")
GREEN = HexColor("#008800")
ORANGE = HexColor("#DD6600")
PURPLE = HexColor("#7030A0")
TEAL = HexColor("#008080")
BROWN = HexColor("#996633")
DARK_BLUE = HexColor("#003399")
PINK = HexColor("#CC3399")
DARK_GREEN = HexColor("#006600")
YELLOW_BG = HexColor("#FFFFDD")
BLUE_BG = HexColor("#E0ECF8")
GREEN_BG = HexColor("#E8F5E8")
GRAY_BG = HexColor("#F0F0F0")
IC_BG = HexColor("#E8E8E8")
SCANNER_BG = HexColor("#FFF8DD")
SERIAL_BG = HexColor("#DDECFF")

c = canvas.Canvas(OUTPUT, pagesize=landscape(A3))
W, H = landscape(A3)

# ── Helpers ──
def wire(x1, y1, x2, y2, color=black, w=1.0):
    c.setStrokeColor(color)
    c.setLineWidth(w)
    c.line(x1, y1, x2, y2)

def wire_h_v(x1, y1, x2, y2, color=black, w=1.0):
    """Horizontal then vertical wire."""
    c.setStrokeColor(color)
    c.setLineWidth(w)
    c.line(x1, y1, x2, y1)
    c.line(x2, y1, x2, y2)

def wire_v_h(x1, y1, x2, y2, color=black, w=1.0):
    """Vertical then horizontal wire."""
    c.setStrokeColor(color)
    c.setLineWidth(w)
    c.line(x1, y1, x1, y2)
    c.line(x1, y2, x2, y2)

def wire_hvh(x1, y1, mx, x2, y2, color=black, w=1.0):
    """H-V-H: horizontal to mx, vertical, horizontal to x2."""
    c.setStrokeColor(color)
    c.setLineWidth(w)
    c.line(x1, y1, mx, y1)
    c.line(mx, y1, mx, y2)
    c.line(mx, y2, x2, y2)

def dot(x, y, r=2.5, color=black):
    c.setFillColor(color)
    c.circle(x, y, r, fill=1, stroke=0)

def arrow_right(x, y, size=5, color=black):
    c.setFillColor(color)
    c.setStrokeColor(color)
    p = c.beginPath()
    p.moveTo(x, y)
    p.lineTo(x - size, y + size/2)
    p.lineTo(x - size, y - size/2)
    p.close()
    c.drawPath(p, fill=1)

def arrow_left(x, y, size=5, color=black):
    c.setFillColor(color)
    c.setStrokeColor(color)
    p = c.beginPath()
    p.moveTo(x, y)
    p.lineTo(x + size, y + size/2)
    p.lineTo(x + size, y - size/2)
    p.close()
    c.drawPath(p, fill=1)

def label(x, y, text, size=7, color=black, bold=False, anchor="left"):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    if anchor == "center":
        c.drawCentredString(x, y, text)
    elif anchor == "right":
        c.drawRightString(x, y, text)
    else:
        c.drawString(x, y, text)

def box(x, y, w, h, fill=IC_BG, stroke=black, lw=1.5, radius=3):
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(lw)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)

def pin_dot(x, y, color=black):
    c.setFillColor(color)
    c.circle(x, y, 2.5, fill=1, stroke=0)

def gnd_symbol(x, y):
    c.setStrokeColor(black)
    c.setLineWidth(1)
    c.line(x, y, x, y - 6)
    c.line(x - 6, y - 6, x + 6, y - 6)
    c.line(x - 4, y - 9, x + 4, y - 9)
    c.line(x - 2, y - 12, x + 2, y - 12)
    label(x - 6, y - 22, "GND", 6, black, True, "left")

def vcc_symbol(x, y):
    c.setStrokeColor(RED)
    c.setLineWidth(1)
    c.line(x, y, x, y + 8)
    c.setFillColor(RED)
    c.circle(x, y + 8, 2, fill=1)
    label(x, y + 12, "+5V", 6, RED, True, "center")


# ════════════════════════════════════════════════════════════
#  PAGE 1: MAIN WIRING DIAGRAM — SIGNAL FLOW
# ════════════════════════════════════════════════════════════
c.setFont("Helvetica-Bold", 16)
c.setFillColor(DARK_BLUE)
c.drawCentredString(W/2, H - 25, "SERIAL PORT SELECTOR — WIRING DIAGRAM")
c.setFont("Helvetica", 8)
c.setFillColor(black)
c.drawCentredString(W/2, H - 38, "2 Switches (SW0, SW1) select 1 of 4 serial ports  |  ICs: 74LS04 + 3x74LS08 + 74LS32  |  All connections shown with colored wires")

# ── Component positions ──
# Scanner
scn_x, scn_y, scn_w, scn_h = 20, H - 110, 130, 55
# Switches
sw_x, sw_y = 25, H - 200
# IC1 (74LS04 Inverter)
ic1_x, ic1_y, ic1_w, ic1_h = 195, H - 215, 85, 75
# IC2 (74LS08 Enable Generator)
ic2_x, ic2_y, ic2_w, ic2_h = 340, H - 230, 95, 105
# IC3 (74LS08 TX Gate)
ic3_x, ic3_y, ic3_w, ic3_h = 510, H - 150, 100, 100
# IC4 (74LS08 RX Gate)
ic4_x, ic4_y, ic4_w, ic4_h = 510, H - 300, 100, 100
# IC5 (74LS32 OR Tree)
ic5_x, ic5_y, ic5_w, ic5_h = 700, H - 300, 95, 100
# Serial ports
sp_x = 870
sp_y_base = H - 80

# ── Draw Scanner ──
box(scn_x, scn_y, scn_w, scn_h, SCANNER_BG, ORANGE, 2)
label(scn_x + scn_w/2, scn_y + scn_h - 14, "R35D-B SCANNER", 9, black, True, "center")
label(scn_x + scn_w/2, scn_y + scn_h - 26, "(Device Under Test)", 7, gray, False, "center")
# Scanner pins on bottom
scn_tx_x, scn_tx_y = scn_x + 25, scn_y
scn_rx_x, scn_rx_y = scn_x + 65, scn_y
scn_gnd_x, scn_gnd_y = scn_x + 105, scn_y
pin_dot(scn_tx_x, scn_tx_y, BLUE)
pin_dot(scn_rx_x, scn_rx_y, GREEN)
pin_dot(scn_gnd_x, scn_gnd_y, black)
label(scn_tx_x, scn_y + 5, "TX", 7, BLUE, True, "center")
label(scn_rx_x, scn_y + 5, "RX", 7, GREEN, True, "center")
label(scn_gnd_x, scn_y + 5, "GND", 7, black, True, "center")

# ── Draw Switches ──
for i, (name, clr) in enumerate([("SW0", BLUE), ("SW1", RED)]):
    sy = sw_y - i * 40
    # Switch box
    box(sw_x, sy - 10, 75, 22, HexColor("#FFF0DD"), ORANGE, 1)
    label(sw_x + 5, sy - 5, name, 9, clr, True)
    # VCC side
    vcc_symbol(sw_x + 85, sy)
    wire(sw_x + 75, sy, sw_x + 85, sy, RED, 0.8)
    # Pull-down resistor
    c.setStrokeColor(black)
    c.setLineWidth(0.8)
    c.rect(sw_x + 15, sy - 22, 20, 8, fill=0)
    wire(sw_x + 25, sy - 10, sw_x + 25, sy - 22, black, 0.8)
    label(sw_x + 37, sy - 20, "10k\u03A9", 5, gray)
    gnd_symbol(sw_x + 25, sy - 30)
    # Signal output dot
    pin_dot(sw_x + 75, sy, clr)

# SW0 output point
sw0_out_x, sw0_out_y = sw_x + 75, sw_y
# SW1 output point
sw1_out_x, sw1_out_y = sw_x + 75, sw_y - 40

# ── Draw IC1: 74LS04 ──
box(ic1_x, ic1_y, ic1_w, ic1_h, HexColor("#E8F5E8"), DARK_GREEN, 1.5)
label(ic1_x + ic1_w/2, ic1_y + ic1_h - 12, "74LS04", 9, black, True, "center")
label(ic1_x + ic1_w/2, ic1_y + ic1_h - 22, "IC1 - Inverter", 7, DARK_GREEN, False, "center")
# Pins
ic1_pins_l = [("1", "1A", BLUE), ("3", "2A", RED)]
ic1_pins_r = [("2", "1Y", BLUE), ("4", "2Y", RED)]
for i, (pn, nm, clr) in enumerate(ic1_pins_l):
    py = ic1_y + ic1_h - 38 - i * 22
    pin_dot(ic1_x, py, clr)
    label(ic1_x + 4, py - 3, f"p{pn} {nm}", 6, clr)
for i, (pn, nm, clr) in enumerate(ic1_pins_r):
    py = ic1_y + ic1_h - 38 - i * 22
    pin_dot(ic1_x + ic1_w, py, clr)
    label(ic1_x + ic1_w - 4, py - 3, f"{nm} p{pn}", 6, clr, False, "right")
# Power labels
label(ic1_x + 2, ic1_y + 3, "p14=VCC p7=GND", 5, gray)
# IC1 pin positions
ic1_p1_y = ic1_y + ic1_h - 38       # pin 1 (SW0 in)
ic1_p3_y = ic1_y + ic1_h - 60       # pin 3 (SW1 in)
ic1_p2_y = ic1_p1_y                  # pin 2 (SW0' out)
ic1_p4_y = ic1_p3_y                  # pin 4 (SW1' out)

# ── Draw IC2: 74LS08 Enable Gen ──
box(ic2_x, ic2_y, ic2_w, ic2_h, HexColor("#F5E8E8"), RED, 1.5)
label(ic2_x + ic2_w/2, ic2_y + ic2_h - 12, "74LS08", 9, black, True, "center")
label(ic2_x + ic2_w/2, ic2_y + ic2_h - 22, "IC2 - Enable Gen", 7, RED, False, "center")
# Left pins
ic2_left = [
    ("1", "SW1'", PURPLE), ("2", "SW0'", TEAL),
    ("4", "SW1'", PURPLE), ("5", "SW0", BLUE),
    ("9", "SW1", RED), ("10", "SW0'", TEAL),
    ("12", "SW1", RED), ("13", "SW0", BLUE),
]
ic2_right = [
    ("3", "EN0", HexColor("#CC0000")),
    ("6", "EN1", HexColor("#0066CC")),
    ("8", "EN2", HexColor("#008800")),
    ("11", "EN3", HexColor("#DD6600")),
]
ic2_pin_ys = {}
for i, (pn, nm, clr) in enumerate(ic2_left):
    py = ic2_y + ic2_h - 32 - i * 10
    pin_dot(ic2_x, py, clr)
    label(ic2_x + 4, py - 3, f"p{pn} {nm}", 5, clr)
    ic2_pin_ys[f"L{pn}"] = py
for i, (pn, nm, clr) in enumerate(ic2_right):
    py = ic2_y + ic2_h - 35 - i * 20
    pin_dot(ic2_x + ic2_w, py, clr)
    label(ic2_x + ic2_w - 4, py - 3, f"{nm} p{pn}", 5, clr, False, "right")
    ic2_pin_ys[f"R{pn}"] = py
label(ic2_x + 2, ic2_y + 3, "p14=VCC p7=GND", 5, gray)

# ── Draw IC3: 74LS08 TX Gate ──
box(ic3_x, ic3_y, ic3_w, ic3_h, HexColor("#E8E8F5"), BLUE, 1.5)
label(ic3_x + ic3_w/2, ic3_y + ic3_h - 12, "74LS08", 9, black, True, "center")
label(ic3_x + ic3_w/2, ic3_y + ic3_h - 22, "IC3 - TX Gate", 7, BLUE, False, "center")
label(ic3_x + ic3_w/2, ic3_y + ic3_h - 31, "Scanner\u2192Arduino", 6, gray, False, "center")
ic3_left = [
    ("1", "ScnTX", BLUE), ("2", "EN0", HexColor("#CC0000")),
    ("4", "ScnTX", BLUE), ("5", "EN1", HexColor("#0066CC")),
    ("9", "ScnTX", BLUE), ("10", "EN2", HexColor("#008800")),
    ("12", "ScnTX", BLUE), ("13", "EN3", HexColor("#DD6600")),
]
ic3_right = [
    ("3", "\u2192S1 RX", HexColor("#CC0000")),
    ("6", "\u2192S2 RX", HexColor("#0066CC")),
    ("8", "\u2192S3 RX", HexColor("#008800")),
    ("11", "\u2192COM2 RX", HexColor("#DD6600")),
]
ic3_pin_ys = {}
for i, (pn, nm, clr) in enumerate(ic3_left):
    py = ic3_y + ic3_h - 38 - i * 8
    pin_dot(ic3_x, py, clr)
    label(ic3_x + 4, py - 3, f"p{pn} {nm}", 5, clr)
    ic3_pin_ys[f"L{pn}"] = py
for i, (pn, nm, clr) in enumerate(ic3_right):
    py = ic3_y + ic3_h - 42 - i * 16
    pin_dot(ic3_x + ic3_w, py, clr)
    label(ic3_x + ic3_w - 4, py - 3, f"{nm} p{pn}", 5, clr, False, "right")
    ic3_pin_ys[f"R{pn}"] = py

label(ic3_x + 2, ic3_y + 3, "p14=VCC p7=GND", 5, gray)

# ── Draw IC4: 74LS08 RX Gate ──
box(ic4_x, ic4_y, ic4_w, ic4_h, HexColor("#F5F5E0"), BROWN, 1.5)
label(ic4_x + ic4_w/2, ic4_y + ic4_h - 12, "74LS08", 9, black, True, "center")
label(ic4_x + ic4_w/2, ic4_y + ic4_h - 22, "IC4 - RX Gate", 7, BROWN, False, "center")
label(ic4_x + ic4_w/2, ic4_y + ic4_h - 31, "Arduino\u2192Scanner", 6, gray, False, "center")
ic4_left = [
    ("1", "S1TX", HexColor("#CC0000")), ("2", "EN0", HexColor("#CC0000")),
    ("4", "S2TX", HexColor("#0066CC")), ("5", "EN1", HexColor("#0066CC")),
    ("9", "S3TX", HexColor("#008800")), ("10", "EN2", HexColor("#008800")),
    ("12", "C2TX", HexColor("#DD6600")), ("13", "EN3", HexColor("#DD6600")),
]
ic4_right = [
    ("3", "G0", HexColor("#CC0000")),
    ("6", "G1", HexColor("#0066CC")),
    ("8", "G2", HexColor("#008800")),
    ("11", "G3", HexColor("#DD6600")),
]
ic4_pin_ys = {}
for i, (pn, nm, clr) in enumerate(ic4_left):
    py = ic4_y + ic4_h - 38 - i * 8
    pin_dot(ic4_x, py, clr)
    label(ic4_x + 4, py - 3, f"p{pn} {nm}", 5, clr)
    ic4_pin_ys[f"L{pn}"] = py
for i, (pn, nm, clr) in enumerate(ic4_right):
    py = ic4_y + ic4_h - 42 - i * 16
    pin_dot(ic4_x + ic4_w, py, clr)
    label(ic4_x + ic4_w - 4, py - 3, f"{nm} p{pn}", 5, clr, False, "right")
    ic4_pin_ys[f"R{pn}"] = py
label(ic4_x + 2, ic4_y + 3, "p14=VCC p7=GND", 5, gray)

# ── Draw IC5: 74LS32 OR Tree ──
box(ic5_x, ic5_y, ic5_w, ic5_h, HexColor("#F0E0F0"), PURPLE, 1.5)
label(ic5_x + ic5_w/2, ic5_y + ic5_h - 12, "74LS32", 9, black, True, "center")
label(ic5_x + ic5_w/2, ic5_y + ic5_h - 22, "IC5 - OR Tree", 7, PURPLE, False, "center")
label(ic5_x + ic5_w/2, ic5_y + ic5_h - 31, "\u2192Scanner RX", 6, gray, False, "center")
ic5_left = [
    ("1", "G0", HexColor("#CC0000")), ("2", "G1", HexColor("#0066CC")),
    ("4", "G2", HexColor("#008800")), ("5", "G3", HexColor("#DD6600")),
    ("9", "OR1", PURPLE), ("10", "OR2", PURPLE),
]
ic5_right = [
    ("3", "OR1", PURPLE),
    ("6", "OR2", PURPLE),
    ("8", "OUT", GREEN),
]
ic5_pin_ys = {}
for i, (pn, nm, clr) in enumerate(ic5_left):
    py = ic5_y + ic5_h - 38 - i * 11
    pin_dot(ic5_x, py, clr)
    label(ic5_x + 4, py - 3, f"p{pn} {nm}", 5, clr)
    ic5_pin_ys[f"L{pn}"] = py
for i, (pn, nm, clr) in enumerate(ic5_right):
    py = ic5_y + ic5_h - 40 - i * 20
    pin_dot(ic5_x + ic5_w, py, clr)
    label(ic5_x + ic5_w - 4, py - 3, f"{nm} p{pn}", 5, clr, False, "right")
    ic5_pin_ys[f"R{pn}"] = py
label(ic5_x + 2, ic5_y + 3, "p14=VCC p7=GND", 5, gray)

# ── Draw Serial Ports ──
sp_h, sp_gap = 48, 55
serial_ports = [
    ("Serial1 COM3", "MS Arduino", "Pin 18 TX", "Pin 19 RX", HexColor("#CC0000")),
    ("Serial2 COM3", "MS Arduino", "Pin 16 TX", "Pin 17 RX", HexColor("#0066CC")),
    ("Serial3 COM3", "MS Arduino", "Pin 14 TX", "Pin 15 RX", HexColor("#008800")),
    ("Serial1 COM2", "CT Arduino", "Pin 18 TX", "Pin 19 RX", HexColor("#DD6600")),
]
sp_pin_ys = {}
for i, (name, board, tx, rx, clr) in enumerate(serial_ports):
    sy = sp_y_base - i * sp_gap
    box(sp_x, sy, 115, sp_h, SERIAL_BG, clr, 1.5)
    label(sp_x + 57, sy + sp_h - 12, name, 8, clr, True, "center")
    label(sp_x + 57, sy + sp_h - 22, board, 7, gray, False, "center")
    # TX pin (output from Arduino)
    tx_y = sy + 18
    pin_dot(sp_x, tx_y, clr)
    label(sp_x + 5, tx_y - 3, tx, 6, clr, True)
    # RX pin (input to Arduino)
    rx_y = sy + 8
    pin_dot(sp_x, rx_y, clr)
    label(sp_x + 5, rx_y - 3, rx, 6, clr)
    # GND
    label(sp_x + 80, sy + 5, "GND", 6, black)
    sp_pin_ys[f"TX{i}"] = tx_y
    sp_pin_ys[f"RX{i}"] = rx_y

# ════════════════════════════════════════════════════════════
#  DRAW WIRES
# ════════════════════════════════════════════════════════════

# ── 1. SW0 → IC1 pin 1 ──
wire(sw0_out_x, sw0_out_y, ic1_x, ic1_p1_y, BLUE, 1.2)
label(sw0_out_x + 20, sw0_out_y + 3, "SW0", 6, BLUE, True)

# ── 2. SW1 → IC1 pin 3 ──
wire(sw1_out_x, sw1_out_y, ic1_x, ic1_p3_y, RED, 1.2)
label(sw1_out_x + 20, sw1_out_y + 3, "SW1", 6, RED, True)

# ── 3. IC1 pin 2 (SW0') → IC2 pin 2, pin 10 ──
sw0_inv_x = ic1_x + ic1_w
sw0_inv_y = ic1_p2_y
# bus line for SW0'
bus_sw0i_x = ic1_x + ic1_w + 20
wire(sw0_inv_x, sw0_inv_y, bus_sw0i_x, sw0_inv_y, TEAL, 1.2)
wire(bus_sw0i_x, ic2_pin_ys["L2"], ic2_x, ic2_pin_ys["L2"], TEAL, 1.0)
wire(bus_sw0i_x, ic2_pin_ys["L10"], ic2_x, ic2_pin_ys["L10"], TEAL, 1.0)
wire(bus_sw0i_x, ic2_pin_ys["L2"], bus_sw0i_x, ic2_pin_ys["L10"], TEAL, 1.0)
dot(bus_sw0i_x, ic2_pin_ys["L2"], 2, TEAL)
dot(bus_sw0i_x, ic2_pin_ys["L10"], 2, TEAL)
label(bus_sw0i_x + 2, sw0_inv_y + 3, "SW0'", 5, TEAL, True)

# ── 4. IC1 pin 4 (SW1') → IC2 pin 1, pin 4 ──
sw1_inv_x = ic1_x + ic1_w
sw1_inv_y = ic1_p4_y
bus_sw1i_x = ic1_x + ic1_w + 12
wire(sw1_inv_x, sw1_inv_y, bus_sw1i_x, sw1_inv_y, PURPLE, 1.2)
wire(bus_sw1i_x, ic2_pin_ys["L1"], ic2_x, ic2_pin_ys["L1"], PURPLE, 1.0)
wire(bus_sw1i_x, ic2_pin_ys["L4"], ic2_x, ic2_pin_ys["L4"], PURPLE, 1.0)
wire(bus_sw1i_x, ic2_pin_ys["L1"], bus_sw1i_x, ic2_pin_ys["L4"], PURPLE, 1.0)
dot(bus_sw1i_x, ic2_pin_ys["L1"], 2, PURPLE)
dot(bus_sw1i_x, ic2_pin_ys["L4"], 2, PURPLE)
label(bus_sw1i_x - 8, sw1_inv_y - 8, "SW1'", 5, PURPLE, True)

# ── 5. SW0 direct → IC2 pin 5, pin 13 ──
bus_sw0d_x = ic2_x - 12
# Bring SW0 down
wire_hvh(sw0_out_x, sw0_out_y, sw0_out_x + 30, bus_sw0d_x, ic2_pin_ys["L5"], BLUE, 0.8)
wire(bus_sw0d_x, ic2_pin_ys["L5"], ic2_x, ic2_pin_ys["L5"], BLUE, 0.8)
wire(bus_sw0d_x, ic2_pin_ys["L13"], ic2_x, ic2_pin_ys["L13"], BLUE, 0.8)
wire(bus_sw0d_x, ic2_pin_ys["L5"], bus_sw0d_x, ic2_pin_ys["L13"], BLUE, 0.8)
dot(bus_sw0d_x, ic2_pin_ys["L5"], 2, BLUE)
dot(bus_sw0d_x, ic2_pin_ys["L13"], 2, BLUE)

# ── 6. SW1 direct → IC2 pin 9, pin 12 ──
bus_sw1d_x = ic2_x - 6
wire_hvh(sw1_out_x, sw1_out_y, sw1_out_x + 36, bus_sw1d_x, ic2_pin_ys["L9"], RED, 0.8)
wire(bus_sw1d_x, ic2_pin_ys["L9"], ic2_x, ic2_pin_ys["L9"], RED, 0.8)
wire(bus_sw1d_x, ic2_pin_ys["L12"], ic2_x, ic2_pin_ys["L12"], RED, 0.8)
wire(bus_sw1d_x, ic2_pin_ys["L9"], bus_sw1d_x, ic2_pin_ys["L12"], RED, 0.8)
dot(bus_sw1d_x, ic2_pin_ys["L9"], 2, RED)
dot(bus_sw1d_x, ic2_pin_ys["L12"], 2, RED)

# ── 7. EN0-EN3 from IC2 → IC3 and IC4 ──
en_colors = [HexColor("#CC0000"), HexColor("#0066CC"), HexColor("#008800"), HexColor("#DD6600")]
en_rpins = ["R3", "R6", "R8", "R11"]
ic3_en_lpins = ["L2", "L5", "L10", "L13"]
ic4_en_lpins = ["L2", "L5", "L10", "L13"]

for i in range(4):
    clr = en_colors[i]
    en_out_x = ic2_x + ic2_w
    en_out_y = ic2_pin_ys[en_rpins[i]]
    bus_en_x = ic2_x + ic2_w + 8 + i * 6
    # EN line out
    wire(en_out_x, en_out_y, bus_en_x, en_out_y, clr, 1.0)
    # vertical bus down to IC3 and IC4
    ic3_target_y = ic3_pin_ys[ic3_en_lpins[i]]
    ic4_target_y = ic4_pin_ys[ic4_en_lpins[i]]
    min_y = min(ic3_target_y, ic4_target_y)
    max_y = max(ic3_target_y, ic4_target_y, en_out_y)
    wire(bus_en_x, en_out_y, bus_en_x, min_y, clr, 0.8)
    # horizontal to IC3
    wire(bus_en_x, ic3_target_y, ic3_x, ic3_target_y, clr, 0.8)
    dot(bus_en_x, ic3_target_y, 2, clr)
    # horizontal to IC4
    wire(bus_en_x, ic4_target_y, ic4_x, ic4_target_y, clr, 0.8)
    dot(bus_en_x, ic4_target_y, 2, clr)
    # Label
    label(bus_en_x + 1, en_out_y + 3, f"EN{i}", 5, clr, True)

# ── 8. Scanner TX → IC3 (all 4 inputs) ──
# Scanner TX goes down from scanner to a bus, then to IC3 left pins
scn_tx_bus_y = scn_tx_y - 15
wire(scn_tx_x, scn_tx_y, scn_tx_x, scn_tx_bus_y, BLUE, 1.5)
scn_tx_bus_x = ic3_x - 15
wire(scn_tx_x, scn_tx_bus_y, scn_tx_bus_x, scn_tx_bus_y, BLUE, 1.2)
# vertical bus alongside IC3
ic3_tx_pins = ["L1", "L4", "L9", "L12"]
wire(scn_tx_bus_x, scn_tx_bus_y, scn_tx_bus_x, ic3_pin_ys["L12"], BLUE, 1.0)
for pn in ic3_tx_pins:
    wire(scn_tx_bus_x, ic3_pin_ys[pn], ic3_x, ic3_pin_ys[pn], BLUE, 0.8)
    dot(scn_tx_bus_x, ic3_pin_ys[pn], 2, BLUE)
label(scn_tx_bus_x - 3, scn_tx_bus_y + 4, "Scanner TX", 6, BLUE, True, "right")

# ── 9. IC3 outputs → Serial port RX pins ──
ic3_out_pins = ["R3", "R6", "R8", "R11"]
for i in range(4):
    clr = en_colors[i]
    out_x = ic3_x + ic3_w
    out_y = ic3_pin_ys[ic3_out_pins[i]]
    target_y = sp_pin_ys[f"RX{i}"]
    mid_x = out_x + 15 + i * 8
    wire(out_x, out_y, mid_x, out_y, clr, 1.0)
    wire(mid_x, out_y, mid_x, target_y, clr, 0.8)
    wire(mid_x, target_y, sp_x, target_y, clr, 0.8)
    arrow_right(sp_x, target_y, 4, clr)
    dot(mid_x, out_y, 2, clr)

# ── 10. Serial port TX pins → IC4 inputs ──
ic4_tx_pins = ["L1", "L4", "L9", "L12"]
for i in range(4):
    clr = en_colors[i]
    tx_y = sp_pin_ys[f"TX{i}"]
    target_y = ic4_pin_ys[ic4_tx_pins[i]]
    mid_x = sp_x - 35 - i * 8
    wire(sp_x, tx_y, mid_x, tx_y, clr, 0.8)
    wire(mid_x, tx_y, mid_x, target_y, clr, 0.7)
    wire(mid_x, target_y, ic4_x + ic4_w + 70, target_y, clr, 0.7)
    # route around to left side of IC4
    route_x = ic4_x - 35 - i * 6
    wire_hvh(ic4_x + ic4_w + 70, target_y, ic4_x + ic4_w + 70, route_x, ic4_pin_ys[ic4_tx_pins[i]], clr, 0.7)
    wire(route_x, ic4_pin_ys[ic4_tx_pins[i]], ic4_x, ic4_pin_ys[ic4_tx_pins[i]], clr, 0.7)
    dot(route_x, ic4_pin_ys[ic4_tx_pins[i]], 2, clr)

# ── 11. IC4 outputs → IC5 inputs ──
ic4_out_pins = ["R3", "R6", "R8", "R11"]
ic5_in_pins = ["L1", "L2", "L4", "L5"]
for i in range(4):
    clr = en_colors[i]
    out_x = ic4_x + ic4_w
    out_y = ic4_pin_ys[ic4_out_pins[i]]
    in_y = ic5_pin_ys[ic5_in_pins[i]]
    mid_x = out_x + 10 + i * 6
    wire(out_x, out_y, mid_x, out_y, clr, 1.0)
    wire(mid_x, out_y, mid_x, in_y, clr, 0.8)
    wire(mid_x, in_y, ic5_x, in_y, clr, 0.8)
    dot(mid_x, out_y, 2, clr)

# ── 12. IC5 internal: pin3→pin9, pin6→pin10 ──
or1_out_y = ic5_pin_ys["R3"]
or2_out_y = ic5_pin_ys["R6"]
or1_in_y = ic5_pin_ys["L9"]
or2_in_y = ic5_pin_ys["L10"]
# OR1 feedback
mid_or1 = ic5_x + ic5_w + 10
wire(ic5_x + ic5_w, or1_out_y, mid_or1, or1_out_y, PURPLE, 1.0)
wire(mid_or1, or1_out_y, mid_or1, or1_in_y, PURPLE, 0.8)
wire(mid_or1, or1_in_y, ic5_x + ic5_w + 15, or1_in_y, PURPLE, 0.8)
# route back to left
wire_hvh(ic5_x + ic5_w + 15, or1_in_y, ic5_x + ic5_w + 15, ic5_x - 10, or1_in_y, PURPLE, 0.8)
wire(ic5_x - 10, or1_in_y, ic5_x, or1_in_y, PURPLE, 0.8)
label(mid_or1 + 2, or1_out_y + 3, "OR1", 5, PURPLE, True)
# OR2 feedback
mid_or2 = ic5_x + ic5_w + 18
wire(ic5_x + ic5_w, or2_out_y, mid_or2, or2_out_y, PURPLE, 1.0)
wire(mid_or2, or2_out_y, mid_or2, or2_in_y, PURPLE, 0.8)
wire(mid_or2, or2_in_y, ic5_x + ic5_w + 22, or2_in_y, PURPLE, 0.8)
wire_hvh(ic5_x + ic5_w + 22, or2_in_y, ic5_x + ic5_w + 22, ic5_x - 5, or2_in_y, PURPLE, 0.8)
wire(ic5_x - 5, or2_in_y, ic5_x, or2_in_y, PURPLE, 0.8)
label(mid_or2 + 2, or2_out_y - 8, "OR2", 5, PURPLE, True)

# ── 13. IC5 pin 8 → Scanner RX ──
final_out_y = ic5_pin_ys["R8"]
wire(ic5_x + ic5_w, final_out_y, ic5_x + ic5_w + 30, final_out_y, GREEN, 1.5)
# Route up to scanner RX
route_scn_rx_x = ic5_x + ic5_w + 30
wire(route_scn_rx_x, final_out_y, route_scn_rx_x, scn_rx_y - 25, GREEN, 1.2)
wire(route_scn_rx_x, scn_rx_y - 25, scn_rx_x, scn_rx_y - 25, GREEN, 1.2)
wire(scn_rx_x, scn_rx_y - 25, scn_rx_x, scn_rx_y, GREEN, 1.2)
arrow_left(scn_rx_x - 3, scn_rx_y, 4, GREEN)
label(route_scn_rx_x + 3, final_out_y + 3, "\u2192 Scanner RX", 7, GREEN, True)

# ── 14. Scanner GND line ──
wire(scn_gnd_x, scn_gnd_y, scn_gnd_x, scn_gnd_y - 20, black, 1.0)
gnd_symbol(scn_gnd_x, scn_gnd_y - 20)
label(scn_gnd_x + 8, scn_gnd_y - 25, "Common GND with all Arduinos & ICs", 6, gray)

# ════════════════════════════════════════════════════════════
#  LEGEND & NOTES
# ════════════════════════════════════════════════════════════
legend_y = 50
box(15, legend_y - 15, W - 30, 55, HexColor("#FAFAFA"), black, 0.5)
label(25, legend_y + 32, "WIRE COLOR LEGEND:", 8, black, True)
legend_items = [
    ("Scanner TX", BLUE), ("Scanner RX (from OR tree)", GREEN),
    ("SW0 / SW0 direct", BLUE), ("SW1 / SW1 direct", RED),
    ("SW0' (inverted)", TEAL), ("SW1' (inverted)", PURPLE),
    ("EN0 / Serial1 COM3", en_colors[0]), ("EN1 / Serial2 COM3", en_colors[1]),
    ("EN2 / Serial3 COM3", en_colors[2]), ("EN3 / Serial1 COM2", en_colors[3]),
]
for i, (txt, clr) in enumerate(legend_items):
    col = i % 5
    row = i // 5
    lx = 25 + col * 195
    ly = legend_y + 18 - row * 14
    wire(lx, ly + 3, lx + 20, ly + 3, clr, 2)
    label(lx + 23, ly, txt, 6, clr)

label(25, legend_y - 8, "NOTE: All IC VCC=Pin14 (+5V), GND=Pin7. Add 0.1\u00B5F bypass cap on each IC. All GNDs connected together.", 7, gray)

# ════════════════════════════════════════════════════════════
#  PAGE 2: CLEAN PIN-TO-PIN CONNECTION TABLE
# ════════════════════════════════════════════════════════════
c.showPage()
c.setFont("Helvetica-Bold", 16)
c.setFillColor(DARK_BLUE)
c.drawCentredString(W/2, H - 25, "PIN-TO-PIN CONNECTION TABLE")
c.setFont("Helvetica", 8)
c.setFillColor(black)
c.drawCentredString(W/2, H - 38, "Every physical wire listed: FROM \u2192 TO  |  Use this as your wiring checklist")

# Table
th_x, th_y = 30, H - 65
col_w = [25, 45, 55, 195, 55, 195, 10]
headers = ["#", "Wire\nColor", "FROM\nComponent", "FROM Pin", "TO\nComponent", "TO Pin", ""]
# Header
c.setFillColor(DARK_BLUE)
cx = th_x
for w in col_w:
    c.rect(cx, th_y, w, 22, fill=1, stroke=1)
    cx += w
c.setFillColor(white)
c.setFont("Helvetica-Bold", 7)
cx = th_x
for h_text, w in zip(headers, col_w):
    c.drawCentredString(cx + w/2, th_y + 7, h_text)
    cx += w

connections = [
    ("1", "Blue", "SW0 Switch", "Output terminal", "IC1 74LS04", "Pin 1 (1A input)"),
    ("2", "Red", "SW1 Switch", "Output terminal", "IC1 74LS04", "Pin 3 (2A input)"),
    ("3", "Teal", "IC1 74LS04", "Pin 2 (1Y = SW0')", "IC2 74LS08", "Pin 2 (1B) + Pin 10 (3B)"),
    ("4", "Purple", "IC1 74LS04", "Pin 4 (2Y = SW1')", "IC2 74LS08", "Pin 1 (1A) + Pin 4 (2A)"),
    ("5", "Blue", "SW0 Switch", "Output terminal (direct)", "IC2 74LS08", "Pin 5 (2B) + Pin 13 (4B)"),
    ("6", "Red", "SW1 Switch", "Output terminal (direct)", "IC2 74LS08", "Pin 9 (3A) + Pin 12 (4A)"),
    ("7", "DkRed", "IC2 74LS08", "Pin 3 (EN0 output)", "IC3 Pin 2 + IC4 Pin 2", "(1B on both)"),
    ("8", "Blue", "IC2 74LS08", "Pin 6 (EN1 output)", "IC3 Pin 5 + IC4 Pin 5", "(2B on both)"),
    ("9", "Green", "IC2 74LS08", "Pin 8 (EN2 output)", "IC3 Pin 10 + IC4 Pin 10", "(3B on both)"),
    ("10", "Orange", "IC2 74LS08", "Pin 11 (EN3 output)", "IC3 Pin 13 + IC4 Pin 13", "(4B on both)"),
    ("11", "Blue", "R35D-B Scanner", "TX wire (Yellow)", "IC3 74LS08", "Pin 1 + 4 + 9 + 12 (all A inputs)"),
    ("12", "DkRed", "IC3 74LS08", "Pin 3 (1Y output)", "MS Arduino COM3", "Pin 19 (Serial1 RX)"),
    ("13", "Blue", "IC3 74LS08", "Pin 6 (2Y output)", "MS Arduino COM3", "Pin 17 (Serial2 RX)"),
    ("14", "Green", "IC3 74LS08", "Pin 8 (3Y output)", "MS Arduino COM3", "Pin 15 (Serial3 RX)"),
    ("15", "Orange", "IC3 74LS08", "Pin 11 (4Y output)", "CT Arduino COM2", "Pin 19 (Serial1 RX)"),
    ("16", "DkRed", "MS Arduino COM3", "Pin 18 (Serial1 TX)", "IC4 74LS08", "Pin 1 (1A input)"),
    ("17", "Blue", "MS Arduino COM3", "Pin 16 (Serial2 TX)", "IC4 74LS08", "Pin 4 (2A input)"),
    ("18", "Green", "MS Arduino COM3", "Pin 14 (Serial3 TX)", "IC4 74LS08", "Pin 9 (3A input)"),
    ("19", "Orange", "CT Arduino COM2", "Pin 18 (Serial1 TX)", "IC4 74LS08", "Pin 12 (4A input)"),
    ("20", "DkRed", "IC4 74LS08", "Pin 3 (1Y = G0_RX)", "IC5 74LS32", "Pin 1 (1A input)"),
    ("21", "Blue", "IC4 74LS08", "Pin 6 (2Y = G1_RX)", "IC5 74LS32", "Pin 2 (1B input)"),
    ("22", "Green", "IC4 74LS08", "Pin 8 (3Y = G2_RX)", "IC5 74LS32", "Pin 4 (2A input)"),
    ("23", "Orange", "IC4 74LS08", "Pin 11 (4Y = G3_RX)", "IC5 74LS32", "Pin 5 (2B input)"),
    ("24", "Purple", "IC5 74LS32", "Pin 3 (1Y = OR1)", "IC5 74LS32", "Pin 9 (3A input)"),
    ("25", "Purple", "IC5 74LS32", "Pin 6 (2Y = OR2)", "IC5 74LS32", "Pin 10 (3B input)"),
    ("26", "Green", "IC5 74LS32", "Pin 8 (3Y = final output)", "R35D-B Scanner", "RX wire (Green)"),
    ("27", "Red", "+5V Power Rail", "VCC", "IC1-IC5", "Pin 14 on each IC"),
    ("28", "Black", "GND Rail", "Ground", "IC1-IC5", "Pin 7 on each IC"),
    ("29", "Black", "GND Rail", "Ground", "R35D-B Scanner", "GND wire (Black)"),
    ("30", "Black", "GND Rail", "Ground", "Both Arduinos", "GND pin"),
    ("31", "Red", "+5V Power Rail", "VCC", "SW0 Switch", "One terminal (other to signal+10k\u03A9 pulldown)"),
    ("32", "Red", "+5V Power Rail", "VCC", "SW1 Switch", "One terminal (other to signal+10k\u03A9 pulldown)"),
]

row_h = 15
c.setFont("Helvetica", 6.5)
for idx, (num, clr_name, from_comp, from_pin, to_comp, to_pin) in enumerate(connections):
    ry = th_y - 22 - idx * row_h
    if ry < 30:
        c.showPage()
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(DARK_BLUE)
        c.drawCentredString(W/2, H - 25, "PIN-TO-PIN CONNECTION TABLE (continued)")
        th_y = H - 50
        ry = th_y - 22
        # redraw header
        c.setFillColor(DARK_BLUE)
        cx = th_x
        for w in col_w:
            c.rect(cx, th_y, w, 22, fill=1, stroke=1)
            cx += w
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 7)
        cx = th_x
        for h_text, w in zip(headers, col_w):
            c.drawCentredString(cx + w/2, th_y + 7, h_text)
            cx += w
        c.setFont("Helvetica", 6.5)
    # Alternate shading
    c.setFillColor(HexColor("#F5F5F5") if idx % 2 == 0 else white)
    cx = th_x
    for w in col_w:
        c.rect(cx, ry, w, row_h, fill=1, stroke=1)
        cx += w
    # Color indicator
    color_map = {
        "Blue": BLUE, "Red": RED, "Green": GREEN, "Orange": ORANGE,
        "Purple": PURPLE, "Teal": TEAL, "DkRed": HexColor("#CC0000"),
        "Black": black, "Brown": BROWN
    }
    wire_clr = color_map.get(clr_name, black)
    c.setFillColor(wire_clr)
    c.rect(th_x + 25 + 5, ry + 3, 35, row_h - 6, fill=1, stroke=0)
    c.setFillColor(white if clr_name in ("Blue", "Red", "Green", "Purple", "DkRed", "Black", "Brown") else black)
    c.setFont("Helvetica", 5)
    c.drawCentredString(th_x + 25 + 22, ry + 5, clr_name)
    # Data
    c.setFillColor(black)
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(th_x + 12, ry + 4, num)
    c.drawString(th_x + 25 + 45 + 3, ry + 4, from_comp)
    c.drawString(th_x + 25 + 45 + 55 + 3, ry + 4, from_pin)
    c.drawString(th_x + 25 + 45 + 55 + 195 + 3, ry + 4, to_comp)
    c.drawString(th_x + 25 + 45 + 55 + 195 + 55 + 3, ry + 4, to_pin)

# ── Selection truth table at bottom ──
ry_bottom = ry - 30
c.setFont("Helvetica-Bold", 10)
c.setFillColor(DARK_BLUE)
c.drawString(th_x, ry_bottom, "SWITCH SELECTION TABLE:")
ry_bottom -= 5

tbl_headers = ["SW1", "SW0", "EN Active", "Selected Port", "Arduino", "TX Pin", "RX Pin"]
tbl_widths = [35, 35, 55, 80, 80, 55, 55]
# Header
c.setFillColor(DARK_BLUE)
cx = th_x
for w in tbl_widths:
    c.rect(cx, ry_bottom - 15, w, 15, fill=1, stroke=1)
    cx += w
c.setFillColor(white)
c.setFont("Helvetica-Bold", 7)
cx = th_x
for h_text, w in zip(tbl_headers, tbl_widths):
    c.drawCentredString(cx + w/2, ry_bottom - 11, h_text)
    cx += w

tbl_rows = [
    ("0 (OFF)", "0 (OFF)", "EN0", "Serial1 COM3", "MS Arduino", "Pin 18", "Pin 19"),
    ("0 (OFF)", "1 (ON)", "EN1", "Serial2 COM3", "MS Arduino", "Pin 16", "Pin 17"),
    ("1 (ON)", "0 (OFF)", "EN2", "Serial3 COM3", "MS Arduino", "Pin 14", "Pin 15"),
    ("1 (ON)", "1 (ON)", "EN3", "Serial1 COM2", "CT Arduino", "Pin 18", "Pin 19"),
]
c.setFont("Helvetica", 7)
for i, row in enumerate(tbl_rows):
    ry_r = ry_bottom - 30 - i * 14
    c.setFillColor(HexColor("#F0F0F0") if i % 2 == 0 else white)
    cx = th_x
    for w in tbl_widths:
        c.rect(cx, ry_r, w, 14, fill=1, stroke=1)
        cx += w
    c.setFillColor(black)
    cx = th_x
    for val, w in zip(row, tbl_widths):
        c.drawCentredString(cx + w/2, ry_r + 4, val)
        cx += w

c.save()
print(f"PDF saved to: {OUTPUT}")
