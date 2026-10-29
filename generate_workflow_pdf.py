"""
Generate System & Database Workflow PDF
Run: python generate_workflow_pdf.py
Output: System_Database_Workflow.pdf
"""
from fpdf import FPDF
import os

class WorkflowPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, '60-80HP Line  |  Cycle Time Monitoring  |  System & Database Workflow', align='C')
        self.ln(4)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

    def section_title(self, title):
        self.ln(4)
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(25, 60, 120)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(25, 60, 120)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def sub_title(self, title):
        self.ln(2)
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(50, 50, 50)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font('Helvetica', '', 9)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 4.5, text)
        self.ln(1)

    def mono_text(self, text):
        self.set_font('Courier', '', 7.5)
        self.set_text_color(30, 30, 30)
        self.set_fill_color(245, 245, 245)
        for line in text.split('\n'):
            self.cell(0, 3.8, line, new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(2)

    def table_header(self, cols, widths):
        self.set_font('Helvetica', 'B', 8)
        self.set_fill_color(25, 60, 120)
        self.set_text_color(255, 255, 255)
        for i, col in enumerate(cols):
            self.cell(widths[i], 6, col, border=1, fill=True, align='C')
        self.ln()
        self.set_text_color(30, 30, 30)

    def table_row(self, cells, widths, fill=False):
        self.set_font('Helvetica', '', 7.5)
        if fill:
            self.set_fill_color(240, 245, 255)
        else:
            self.set_fill_color(255, 255, 255)
        max_h = 5
        # Calculate row height needed
        for i, cell in enumerate(cells):
            lines = self.multi_cell(widths[i], 4, cell, split_only=True)
            needed = len(lines) * 4
            if needed > max_h:
                max_h = needed
        x_start = self.get_x()
        y_start = self.get_y()
        # Check page break
        if y_start + max_h > 280:
            self.add_page()
            y_start = self.get_y()
        for i, cell in enumerate(cells):
            self.set_xy(x_start + sum(widths[:i]), y_start)
            self.multi_cell(widths[i], 4, cell, border=1, fill=fill, align='L')
        self.set_xy(x_start, y_start + max_h)
        self.ln(0)

    def bullet(self, text, indent=10):
        self.set_font('Helvetica', '', 9)
        self.set_text_color(30, 30, 30)
        x = self.get_x()
        self.set_x(x + indent)
        self.cell(3, 4.5, chr(8226), new_x="END")
        self.multi_cell(0, 4.5, ' ' + text)


def build_pdf():
    pdf = WorkflowPDF('P', 'mm', 'A4')
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ===== TITLE PAGE =====
    pdf.ln(30)
    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(25, 60, 120)
    pdf.cell(0, 12, 'System & Database Workflow', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font('Helvetica', '', 14)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, '60-80HP Line  -  Cycle Time Monitoring', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, 'Comprehensive documentation of system architecture, signal flow,', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, 'database tables, and API endpoints.', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_draw_color(25, 60, 120)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(10)
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, 'Flask + MySQL + Arduino UNO + 9 Tablets', align='C', new_x="LMARGIN", new_y="NEXT")

    # ===== SECTION 1: SYSTEM ARCHITECTURE =====
    pdf.add_page()
    pdf.section_title('1. System Architecture Overview')

    pdf.sub_title('Hardware Layer')
    pdf.mono_text(
        "Arduino UNO #1 (Material Setter)        Arduino UNO #2 (Cycle Time)\n"
        "  Pin 4  : IR Sensor 1 (ID detection)     9 START/STOP buttons\n"
        "  Pin 5  : Relay 2 OUT (solenoid)          for Process 1-9\n"
        "  Pin 14 : IR Sensor 2 (dunpla at P1)\n"
        "\n"
        "Zebra Printer: Prints Kitting QR codes via ZPL/CPCL"
    )

    pdf.sub_title('Software Layer (Windows PC)')
    pdf.mono_text(
        "arduino_bridge_ms.py    <-- Bidirectional serial bridge (MS Arduino)\n"
        "arduino_bridge.py       <-- Read-only serial bridge (CT Arduino)\n"
        "         |                           |\n"
        "         +--- HTTP POST ---+--- HTTP POST ---+\n"
        "                           |\n"
        "              cycleTimeMoni.py (Flask :5001)\n"
        "                           |\n"
        "              database_manager.py --> MySQL (XAMPP)\n"
        "              qr_printer.py       --> Zebra Printer\n"
        "              torisql.py          --> Toritani External DB"
    )

    pdf.sub_title('Client Layer (Wi-Fi Network)')
    pdf.body_text(
        "9 Tablets (Process 1-9): QR scan, timer, PASS/NG controls.\n"
        "Material Setter Tablet/PC: Job Order, materials, kitting QR, operator IN/OUT.\n"
        "Monitoring: Cycle Graph, Line Trend pages."
    )

    # ===== SECTION 2: SIGNAL & DATA FLOW =====
    pdf.add_page()
    pdf.section_title('2. Signal & Data Flow')

    pdf.sub_title('2A. Material Setter Flow')

    steps = [
        ("Step 1: Operator Arrives",
         "IR Sensor (Pin 4) detects -> Arduino sends 'MS1LOAD' -> Bridge POSTs to /api/ms_arduino_signal\n"
         "-> Flask sets ms1_loaded=True -> Material Setter polls /api/ms_button_status (500ms)\n"
         "-> Auto-opens IN modal, focuses scan input -> Operator scans ID with handheld scanner\n"
         "-> POST /api/ms_operator_in -> saved to mtrl_set_operator table"),

        ("Step 2: Prepare Materials",
         "Operator scans Job Order -> fetches from Toritani DB\n"
         "Operator scans materials per row -> saved to MAIN_DB\n"
         "Operator scans Kitting QR code -> POST /api/complete_kitting\n"
         "-> Saves to KITTING_DB + 26 material tables + joborder_plan\n"
         "-> Flask queues 'RELAY2_ON' -> Bridge polls /api/ms_get_pending_command\n"
         "-> Bridge writes 'RELAY2_ON' to Arduino serial\n"
         "-> Arduino Pin 5 HIGH -> Relay ON -> Solenoid OPENS\n"
         "-> Arduino confirms 'MS_OPEN_INTERLOCK' -> Badge shows 'INTERLOCK OPEN' (green)"),

        ("Step 3: Dunpla Taken to Process 1",
         "IR Sensor (Pin 14) detects -> Arduino sends 'STANDBY_MS'\n"
         "-> Flask queues 'RELAY2_OFF' -> Bridge sends to Arduino\n"
         "-> Pin 5 LOW -> Relay OFF -> Solenoid CLOSES\n"
         "-> Arduino confirms 'MS_CLOSE_INTERLOCK' -> Badge shows 'INTERLOCK CLOSED' (red)"),

        ("Step 4: Operator Leaves",
         "IR Sensor (Pin 4) clears -> Arduino sends 'MS1UNLOAD'\n"
         "-> Flask sets ms1_loaded=False -> POST /api/ms_operator_out -> Operator signed out"),
    ]

    for title, desc in steps:
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(25, 60, 120)
        pdf.cell(0, 5, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 4, desc)
        pdf.ln(2)

    pdf.sub_title('2B. Cycle Time Flow')

    ct_steps = [
        ("Step 1: QR Scanned at Tablet",
         "Tablet scans QR -> POST /api/validate_kitting_qr\n"
         "-> Validates against KITTING_DB, checks sequence, checks prev process done"),
        ("Step 2: Start Timer",
         "Operator presses START -> POST /api/start_process -> Server-side timer starts, counter increments"),
        ("Step 3: Stop Timer",
         "PASS: POST /api/stop_process -> saves to process_{N} + process_records\n"
         "NG: POST /api/ng_process | LINE OUT: POST /api/lineout_process\n"
         "IN-LINE: POST /api/in_line_process | REPAIRED: POST /api/stop_repaired_process"),
        ("Step 4: Monitoring",
         "Cycle Graph: GET /api/get_cycle_graph_data -> reads process_{N} tables\n"
         "Line Trend: GET /api/get_line_trend_data -> reads process_records"),
    ]

    for title, desc in ct_steps:
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(25, 60, 120)
        pdf.cell(0, 5, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 4, desc)
        pdf.ln(2)

    # ===== SECTION 3: DATABASE TABLES =====
    pdf.add_page()
    pdf.section_title('3. Database Tables & Purpose')
    pdf.body_text('Database: cycle_time_monitoring (MySQL via XAMPP)')

    pdf.sub_title('Cycle Time Tables')
    w = [8, 40, 142]
    pdf.table_header(['#', 'Table', 'Purpose'], w)
    ct_tables = [
        ('1', 'process_records', 'Master log of all cycle time records across all processes. Stores kitting_no, elapsed_time, pass/ng, lineout/inline reasons, timestamps.'),
        ('2', 'process_1 ... process_9', 'Per-process logs - same data separated by process for faster queries. Includes operator_name, time_in, time_out, out_reasons.'),
        ('3', 'standard_times', 'Standard time config - target cycle time (minutes) and title per process (e.g., Process 1 = "EM Fastening", ST = 1.56 min).'),
        ('4', 'manpower', 'Operator assignments - current operator per process (id_no, name, employment_status, scan data, time_in). One row per process (1-9).'),
    ]
    for i, row in enumerate(ct_tables):
        pdf.table_row(list(row), w, fill=(i % 2 == 0))

    pdf.ln(4)
    pdf.sub_title('Material Setter Tables')
    ms_tables = [
        ('5', 'MAIN_DB', 'Current material state - scanned materials for active job order with remaining quantities. Unique per (job_order, row_no). Updated on each scan.'),
        ('6', 'KITTING_DB', 'Kitting history - every completed kitting creates records here. Stores kitting_no, material details, QR code data. Used by process tablets to validate QR scans.'),
        ('7', 'kitting_summary', 'Live kitting summary - mirrors current kitting state in Material Setter UI. Unique per (job_order, row_no).'),
        ('8', 'kitting_material', 'Material categories - 23 predefined categories (Frame Block, EM Block, Spacer, etc.) used as row definitions in the kitting table.'),
        ('9', 'joborder_plan', 'Kitting progress tracker - plan/result/balance counts per job order. Also stores operator info, time_in/out, change_model_reason.'),
    ]
    for i, row in enumerate(ms_tables):
        pdf.table_row(list(row), w, fill=(i % 2 == 0))

    pdf.ln(4)
    pdf.sub_title('Operator & Reason Tables')
    or_tables = [
        ('10', 'mtrl_set_operator', 'Material Setter operator - single-row table for currently signed-in MS operator (id_no, name, time_in).'),
        ('11', 'ms_operator_selection', 'Display preference - stores whether MS operator display shows "id", "name", or "all".'),
        ('12', 'bio_break', 'OUT reasons - predefined reasons for operator OUT (CR, CLINIC, GO TO OTHER LINE, EMERGENCY, SENT HOME).'),
        ('13', 'lineout_reasons', 'LINE OUT reasons - predefined reasons for line-out events (NG PRESSURE, LEAK, LW, LAV, etc.).'),
        ('14', 'in_line_reasons', 'IN-LINE reasons - predefined reasons for returning in-line after a line-out.'),
        ('15', 'repaired_actions', 'Repaired actions - predefined repair action descriptions for NG items that are fixed.'),
        ('16', 'ms_change_model_reasons', 'Change model reasons - predefined reasons (PERFORMANCE PROBLEM, LACKING MATLS, MACHINE PROBLEM).'),
    ]
    for i, row in enumerate(or_tables):
        pdf.table_row(list(row), w, fill=(i % 2 == 0))

    # ===== 26 Material Tables =====
    pdf.add_page()
    pdf.sub_title('26 Material-Specific Tables')
    pdf.body_text('Each kitting completion saves per-row detail into the corresponding material table for traceability.')
    pdf.body_text('All 26 tables share the same schema: id, kitting_no, job_order, model_code, mtrl_desc, qty_unit, scan_mtrl, lot_no, qty_kit, kitting_qr_code, date_today, timestamp')

    w2 = [8, 50, 50, 8, 50, 24]
    pdf.table_header(['#', 'Table', 'Material', '#', 'Table', 'Material'], w2)
    mat_tables = [
        ('01', '01tbl_frame_zam', 'Frame Block', '14', '14tbl_ground_wire', 'Ground Wire'),
        ('02', '02tbl_frame_lead', 'EM Block', '15', '15tbl_vcr', 'VCR'),
        ('03', '03tbl_spacer', 'Spacer', '16', '16tbl_lower_housing', 'Lower Housing'),
        ('04', '04tbl_2p', 'DF Block', '17', '17tbl_rubber_foot', 'Rubber Foot'),
        ('05', '05tbl_p3p', 'ROD Block', '18', '18tbl_power_cord', 'Powercord'),
        ('06', '06tbl_df_block', 'Casing Block', '19', '19tbl_partition_gasket', 'Part. Gasket'),
        ('07', '07tbl_rod', 'Partition Board', '20', '20tbl_upper_housing', 'Upper Housing'),
        ('08', '08tbl_casing_block', 'L-Tube', '21', '21tbl_filter_cover', 'Filter Cover'),
        ('09', '09tbl_partition_board', 'Hose Clip', '22', '22tbl_filter', 'Filter'),
        ('10', '10tbl_l_tube', 'Switch Block', '23', '23tbl_sound_absorbing', 'Sound Absorber'),
        ('11', '11tbl_hose_clip', 'Lead Bushing', '24', '24tbl_manual', 'Manual'),
        ('12', '12tbl_switch_block', 'Ground Wire', '25', '25tbl_l_hose_set', 'L-Hose Set'),
        ('13', '13tbl_lead_bushing', 'VCR', '26', '26tbl_filter_bush', 'Filter Bushing'),
    ]
    for i, row in enumerate(mat_tables):
        pdf.table_row(list(row), w2, fill=(i % 2 == 0))

    # ===== SECTION 4: API ENDPOINT MAP =====
    pdf.add_page()
    pdf.section_title('4. API Endpoint Map')

    pdf.sub_title('Pages (GET -> HTML)')
    w3 = [10, 70, 110]
    pdf.table_header(['#', 'Route', 'Page'], w3)
    pages = [
        ('1', '/', 'Main Menu'),
        ('2', '/tablet_menu', 'Tablet Main Menu'),
        ('3', '/material_setter', 'Material Setter (Desktop)'),
        ('4', '/material_setter_tablet', 'Material Setter (Tablet)'),
        ('5', '/cycle_time_home', 'Cycle Time Home'),
        ('6', '/process1 ... /process9', 'Process 1-9 Monitoring'),
        ('7', '/settings', 'Settings'),
        ('8', '/standard_time', 'Standard Time Configuration'),
        ('9', '/manpower', 'Manpower Configuration'),
        ('10', '/cycle_graph', 'Cycle Time Graph'),
        ('11', '/line_trend', 'Line Trend Graph'),
    ]
    for i, row in enumerate(pages):
        pdf.table_row(list(row), w3, fill=(i % 2 == 0))

    pdf.ln(4)
    pdf.sub_title('Arduino & Interlock APIs')
    w4 = [15, 75, 100]
    pdf.table_header(['Method', 'Endpoint', 'Purpose'], w4)
    arduino_apis = [
        ('POST', '/api/arduino_signal', 'Receive cycle time button signals from Arduino bridge'),
        ('GET', '/api/arduino_signal/<process_no>', 'Check pending Arduino signal for a process'),
        ('POST', '/api/ms_arduino_signal', 'Receive MS sensor signals (MS1LOAD, MS1UNLOAD, STANDBY_MS, interlock)'),
        ('GET', '/api/ms_button_status', 'Browser polls MS button/interlock state'),
        ('GET', '/api/ms_get_pending_command', 'Bridge polls for pending relay commands (RELAY2_ON/OFF)'),
        ('POST', '/api/ms_relay2_control', 'Manual relay control (action: on/off)'),
        ('POST', '/api/bridge_ready', 'Bridge reports ready status'),
    ]
    for i, row in enumerate(arduino_apis):
        pdf.table_row(list(row), w4, fill=(i % 2 == 0))

    pdf.ln(4)
    pdf.sub_title('Cycle Time Process APIs')
    ct_apis = [
        ('POST', '/api/start_process', 'Start timer for a process'),
        ('POST', '/api/stop_process', 'Stop timer (PASS)'),
        ('POST', '/api/ng_process', 'Stop timer (NG)'),
        ('POST', '/api/lineout_process', 'Line out with reason'),
        ('POST', '/api/in_line_process', 'Return in-line'),
        ('POST', '/api/stop_repaired_process', 'Stop repaired NG item'),
        ('GET', '/api/get_process_records/<no>', 'Get records for a process'),
        ('GET', '/api/get_process_state/<no>', 'Get counter + timer state'),
    ]
    for i, row in enumerate(ct_apis):
        pdf.table_row(list(row), w4, fill=(i % 2 == 0))

    pdf.add_page()
    pdf.sub_title('Server Timer & Counter APIs')
    timer_apis = [
        ('GET', '/api/get_server_timer/<no>', 'Get server-side timer state'),
        ('POST', '/api/start_server_timer/<no>', 'Start server timer'),
        ('POST', '/api/stop_server_timer/<no>', 'Stop server timer'),
        ('POST', '/api/clear_server_timer/<no>', 'Clear server timer'),
        ('POST', '/api/sync_counter/<no>', 'Sync browser counter with server'),
        ('GET', '/api/get_completed_count/<no>', 'DB completed count'),
        ('GET', '/api/can_start_kitting/<no>/<kn>', 'Check if kitting can start'),
        ('POST', '/api/block_counter', 'Block a counter'),
        ('POST', '/api/reset_all', 'Reset all counters and timers'),
    ]
    pdf.table_header(['Method', 'Endpoint', 'Purpose'], w4)
    for i, row in enumerate(timer_apis):
        pdf.table_row(list(row), w4, fill=(i % 2 == 0))

    pdf.ln(4)
    pdf.sub_title('Material Setter & Kitting APIs')
    ms_apis = [
        ('POST', '/api/save_main_db', 'Save materials to MAIN_DB'),
        ('GET', '/api/get_main_db', 'Get materials for a job order'),
        ('POST', '/api/clear_main_db', 'Clear MAIN_DB for a job order'),
        ('POST', '/api/complete_kitting', 'Complete kitting -> KITTING_DB + material tables + RELAY2_ON'),
        ('GET', '/api/get_kitting_db', 'Get kitting records'),
        ('POST', '/api/validate_kitting_qr', 'Validate scanned kitting QR at process tablets'),
        ('GET', '/api/get_kitting_summary', 'Get kitting summary'),
        ('GET', '/api/get_next_kitting_no', 'Get next kitting number'),
        ('POST', '/api/print_kitting_qr', 'Print kitting QR code via Zebra printer'),
    ]
    pdf.table_header(['Method', 'Endpoint', 'Purpose'], w4)
    for i, row in enumerate(ms_apis):
        pdf.table_row(list(row), w4, fill=(i % 2 == 0))

    pdf.ln(4)
    pdf.sub_title('Operator APIs')
    op_apis = [
        ('POST', '/api/ms_operator_in', 'MS operator sign in'),
        ('POST', '/api/ms_operator_out', 'MS operator sign out'),
        ('GET', '/api/get_ms_operator', 'Get current MS operator'),
        ('POST', '/api/update_manpower', 'Update process operator'),
        ('POST', '/api/operator_out', 'Process operator sign out'),
        ('GET', '/api/get_manpower', 'Get all manpower'),
        ('GET', '/api/get_manpower/<no>', 'Get operator for a process'),
    ]
    pdf.table_header(['Method', 'Endpoint', 'Purpose'], w4)
    for i, row in enumerate(op_apis):
        pdf.table_row(list(row), w4, fill=(i % 2 == 0))

    pdf.ln(4)
    pdf.sub_title('Settings & Config APIs')
    cfg_apis = [
        ('GET', '/api/get_settings', 'Get all settings'),
        ('GET', '/api/get_standard_times', 'Get standard times'),
        ('POST', '/api/save_printer_selection', 'Save printer config'),
        ('GET', '/api/get_model_codes', 'Get model codes'),
        ('POST', '/api/add_model_code', 'Add model code'),
        ('GET', '/api/get_kitting_materials', 'Get material categories'),
        ('POST', '/api/export_csv_now', 'Export data to CSV'),
    ]
    pdf.table_header(['Method', 'Endpoint', 'Purpose'], w4)
    for i, row in enumerate(cfg_apis):
        pdf.table_row(list(row), w4, fill=(i % 2 == 0))

    pdf.ln(4)
    pdf.sub_title('Monitoring APIs')
    mon_apis = [
        ('GET', '/api/get_cycle_graph_data', 'Cycle time graph data'),
        ('GET', '/api/get_line_trend_data', 'Line trend data'),
        ('GET', '/api/get_all_active_timers', 'All active timer states'),
        ('GET', '/api/server_start_time', 'Server start time (auto-reload)'),
    ]
    pdf.table_header(['Method', 'Endpoint', 'Purpose'], w4)
    for i, row in enumerate(mon_apis):
        pdf.table_row(list(row), w4, fill=(i % 2 == 0))

    # ===== SECTION 5: FILE MAP =====
    pdf.add_page()
    pdf.section_title('5. File Map')

    w5 = [60, 130]
    pdf.table_header(['File', 'Role'], w5)
    files = [
        ('cycleTimeMoni.py', 'Flask web server - all routes and API endpoints'),
        ('database_manager.py', 'MySQL database operations - all CRUD functions'),
        ('torisql.py', 'Toritani external database connector'),
        ('qr_printer.py', 'Zebra printer control (ZPL/CPCL)'),
        ('arduino_bridge.py', 'Serial bridge for Cycle Time Arduino (read-only)'),
        ('arduino_bridge_ms.py', 'Serial bridge for Material Setter Arduino (bidirectional)'),
        ('arduino_ms/arduino_ms.ino', 'Arduino UNO sketch for Material Setter (sensors + relay)'),
        ('arduino_cycle_time/', 'Arduino sketch for Cycle Time buttons'),
        ('templates/', '20 HTML templates (process1-9, material_setter, settings, etc.)'),
        ('static/', 'CSS, JS, images'),
        ('material_setter_settings.json', 'MS config (printer, row count, display options)'),
        ('model_codes_no_bushing.json', 'Model codes that skip filter bushing row'),
        ('kitting_materials.json', 'Material category definitions'),
        ('server_timer_state.json', 'Persisted timer/counter state across restarts'),
    ]
    for i, row in enumerate(files):
        pdf.table_row(list(row), w5, fill=(i % 2 == 0))

    # Output
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'System_Database_Workflow.pdf')
    pdf.output(output_path)
    print(f"PDF generated: {output_path}")

if __name__ == '__main__':
    build_pdf()
