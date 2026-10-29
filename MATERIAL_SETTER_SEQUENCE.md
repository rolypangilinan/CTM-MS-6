# MATERIAL SETTER — FULL SEQUENCE

## RELAY TYPES
- **Type 1 (Pin-Controlled Relay):** Directly controlled by Arduino pin. Active LOW = relay ON (scanner power). Pins: 4, 6, 10, 12.
- **Type 2 (PC-Commanded Relay):** PC sends command → Arduino sets pin. Used for solenoid interlocks. Pins: 3 (MS), 8 (Standby), 13 (P1), 27 (P2). HIGH = open.

---

## SEQUENCE A: Operator Places ID at Material Setter (MS ID Scanner)

| Step | Action | Pin | Direction |
|------|--------|-----|-----------|
| 1 | IR Sensor 1 detects ID (LOW) | Pin 2 | SENSOR → ARDUINO |
| 2 | Arduino sends `MS_LOAD_ID` | — | ARDUINO → PC |
| 3 | Arduino turns ON Scanner 1 relay (LOW) | Pin 4 | ARDUINO PIN (Type 1) |
| 4 | Arduino waits 2s boot delay | — | INTERNAL |
| 5 | Arduino sends trigger `{0x16,0x54,0x0D,0x0A}` to R35D-B via Serial1 | Pin 18 TX | ARDUINO → SCANNER |
| 6 | Arduino sends `MS_SCANNER_READY` | — | ARDUINO → PC |
| 7 | R35D-B scans QR, sends data back via Serial1 | Pin 19 RX | SCANNER → ARDUINO |
| 8 | Arduino sends `MS_SCAN:<data>` | — | ARDUINO → PC |
| 9 | Arduino sends stop cmd to scanner | Pin 18 TX | ARDUINO → SCANNER |
| 10 | Arduino turns OFF Scanner 1 relay (HIGH) | Pin 4 | ARDUINO PIN (Type 1) |

**IF ID IS REMOVED:**

| Step | Action | Pin | Direction |
|------|--------|-----|-----------|
| 11 | IR Sensor 1 goes HIGH (200ms sustained) | Pin 2 | SENSOR → ARDUINO |
| 12 | Arduino cancels scan, stops scanner, relay OFF | Pin 4 | ARDUINO PIN (Type 1) |
| 13 | Arduino sends `MS_UNLOAD_ID` | — | ARDUINO → PC |

---

## SEQUENCE B: Kitting Dunpla Placed at Material Setter (MS Kitting Scanner)

| Step | Action | Pin | Direction |
|------|--------|-----|-----------|
| 1 | IR Sensor 5 detects dunpla (LOW) | Pin 5 | SENSOR → ARDUINO |
| 2 | Arduino sends `MS_KITTING_LOAD` | — | ARDUINO → PC |
| 3 | Arduino turns ON Kitting Scanner relay (LOW) | Pin 6 | ARDUINO PIN (Type 1) |
| 4 | Arduino waits 2s boot delay | — | INTERNAL |
| 5 | Arduino sends trigger to Kitting R35D-B via Serial2 | Pin 16 TX | ARDUINO → SCANNER |
| 6 | Arduino sends `MS_KIT_SCANNER_READY` | — | ARDUINO → PC |
| 7 | R35D-B scans QR, sends data back via Serial2 | Pin 17 RX | SCANNER → ARDUINO |
| 8 | Arduino sends `MS_KITSCAN:<data>` | — | ARDUINO → PC |
| 9 | Arduino sends stop cmd to scanner | Pin 16 TX | ARDUINO → SCANNER |
| 10 | Arduino turns OFF Kitting Scanner relay (HIGH) | Pin 6 | ARDUINO PIN (Type 1) |

**PC PROCESSES KITTING DATA:**

| Step | Action | Pin | Direction |
|------|--------|-----|-----------|
| 11 | PC (Flask) receives `MS_KITSCAN:<data>`, saves to DB | — | PC INTERNAL |
| 12 | PC queues `RELAY2_ON` command | — | PC → ARDUINO (queued) |
| 13 | Arduino receives `RELAY2_ON`, sets Pin 3 HIGH | Pin 3 | PC → ARDUINO → RELAY (Type 2) |
| 14 | MS solenoid interlock OPENS (dunpla can pass) | Pin 3 | SOLENOID OPENS |
| 15 | Arduino sends `MS_OPEN_INTERLOCK` | — | ARDUINO → PC |

**DUNPLA REMOVED FROM KITTING SENSOR:**

| Step | Action | Pin | Direction |
|------|--------|-----|-----------|
| 16 | IR Sensor 5 goes HIGH (500ms sustained) | Pin 5 | SENSOR → ARDUINO |
| 17 | Arduino sends `MS_KITTING_UNLOAD` | — | ARDUINO → PC |
| 18 | Arduino powers OFF kitting scanner relay | Pin 6 | ARDUINO PIN (Type 1) |

---

## SEQUENCE C: Dunpla Reaches Standby Position

| Step | Action | Pin | Direction |
|------|--------|-----|-----------|
| 1 | IR Sensor 2 detects dunpla (LOW, 2s sustained) | Pin 7 | SENSOR → ARDUINO |
| 2 | Arduino sends `STANDBY_MS` | — | ARDUINO → PC |
| 3 | PC queues `RELAY2_OFF` (close MS interlock) | — | PC → ARDUINO (queued) |
| 4 | Arduino receives `RELAY2_OFF`, sets Pin 3 LOW | Pin 3 | PC → ARDUINO → RELAY (Type 2) |
| 5 | MS solenoid interlock CLOSES | Pin 3 | SOLENOID CLOSES |
| 6 | Arduino sends `MS_CLOSE_INTERLOCK` | — | ARDUINO → PC |
| 7 | PC queues `STANDBY_RELAY_ON` | — | PC → ARDUINO (queued) |
| 8 | Arduino receives cmd, sets Pin 8 HIGH | Pin 8 | PC → ARDUINO → RELAY (Type 2) |
| 9 | Standby interlock OPENS (dunpla can go to P1) | Pin 8 | SOLENOID OPENS |
| 10 | Arduino sends `STANDBY_OPEN_INTERLOCK` | — | ARDUINO → PC |

---

## SEQUENCE D: Dunpla Reaches Process 1

| Step | Action | Pin | Direction |
|------|--------|-----|-----------|
| 1 | IR Sensor 6 detects dunpla (LOW, 500ms sustained) | Pin 22 | SENSOR → ARDUINO |
| 2 | Arduino sends `P1_DONE` | — | ARDUINO → PC |
| 3 | PC queues `STANDBY_RELAY_OFF` | — | PC → ARDUINO (queued) |
| 4 | Arduino receives cmd, sets Pin 8 LOW | Pin 8 | PC → ARDUINO → RELAY (Type 2) |
| 5 | Standby interlock CLOSES | Pin 8 | SOLENOID CLOSES |
| 6 | Arduino sends `STANDBY_CLOSE_INTERLOCK` | — | ARDUINO → PC |

---

## SEQUENCE E: Operator Places ID at Process 1 (P1 ID Scanner 3)

| Step | Action | Pin | Direction |
|------|--------|-----|-----------|
| 1 | IR Sensor 3 detects ID (LOW, 500ms sustained) | Pin 9 | SENSOR → ARDUINO |
| 2 | Arduino sends `P1_ID_LOAD` | — | ARDUINO → PC |
| 3 | Arduino turns ON P1 Scanner 3 relay (LOW) | Pin 10 | ARDUINO PIN (Type 1) |
| 4 | Arduino waits 2s boot delay | — | INTERNAL |
| 5 | Arduino sends trigger to P1 R35D-B via Serial3 | Pin 14 TX | ARDUINO → SCANNER |
| 6 | Arduino sends `P1_SCANNER_READY` | — | ARDUINO → PC |
| 7 | R35D-B scans QR, sends data back via Serial3 | Pin 15 RX | SCANNER → ARDUINO |
| 8 | Arduino sends `P1_SCAN:<data>` | — | ARDUINO → PC |
| 9 | Arduino sends stop cmd to scanner | Pin 14 TX | ARDUINO → SCANNER |
| 10 | Arduino turns OFF P1 Scanner 3 relay (HIGH) | Pin 10 | ARDUINO PIN (Type 1) |

**IF ID IS REMOVED:**

| Step | Action | Pin | Direction |
|------|--------|-----|-----------|
| 11 | IR Sensor 3 goes HIGH (500ms sustained) | Pin 9 | SENSOR → ARDUINO |
| 12 | Arduino cancels scan, stops scanner, relay OFF | Pin 10 | ARDUINO PIN (Type 1) |
| 13 | Arduino sends `P1_ID_UNLOAD` | — | ARDUINO → PC |

---

## SEQUENCE F: P1 Kitting Dunpla Placed (P1 Kitting Scanner 4)

**NOTE:** Sensor & relay on **MS Arduino**. Scanner serial data on **CT Arduino** (Serial1).

| Step | Action | Pin | Direction |
|------|--------|-----|-----------|
| 1 | IR Sensor detects dunpla (LOW) | Pin 11 | SENSOR → MS ARDUINO |
| 2 | MS Arduino sends `P1_KITTING_LOAD` | — | MS ARDUINO → PC |
| 3 | MS Arduino turns ON Scanner 4 relay (LOW). Scan cycle LOCKED. | Pin 12 | MS ARDUINO PIN (Type 1) |
| 4 | MS Arduino waits 2s boot delay | — | INTERNAL |
| 5 | MS Arduino sends `P1_KIT_SCANNER_READY` | — | MS ARDUINO → PC |
| 6 | PC queues `P1_KIT_SCAN_TRIGGER` for CT Arduino | — | PC → CT ARDUINO (queued) |
| 7 | CT Arduino sends trigger to Scanner 4 via Serial1 | Pin 18 TX | CT ARDUINO → SCANNER |
| 8 | R35D-B scans QR, sends data back via Serial1 | Pin 19 RX | SCANNER → CT ARDUINO |
| 9 | CT Arduino sends `P1_KITSCAN:<data>` | — | CT ARDUINO → PC |
| 10 | PC receives data, queues `P1_KIT_SCAN_DONE` for MS Arduino | — | PC → MS ARDUINO (queued) |
| 11 | MS Arduino receives `P1_KIT_SCAN_DONE`, ends scan cycle | — | PC → MS ARDUINO |
| 12 | MS Arduino turns OFF Scanner 4 relay (HIGH) | Pin 12 | MS ARDUINO PIN (Type 1) |
| 13 | MS Arduino sends `P1_KIT_SCAN_DONE_CONFIRM` | — | MS ARDUINO → PC |

**SAFETY TIMEOUT (if scan never completes, 10s):**

| Step | Action | Pin | Direction |
|------|--------|-----|-----------|
| T | MS Arduino auto-powers OFF relay after 10s | Pin 12 | MS ARDUINO PIN (Type 1) |
| T+1 | MS Arduino sends `P1_KIT_SCAN_TIMEOUT` | — | MS ARDUINO → PC |

---

## SEQUENCE G: P2 ID Detection

| Step | Action | Pin | Direction |
|------|--------|-----|-----------|
| 1 | IR Sensor 7 detects ID (LOW, 500ms sustained) | Pin 23 | SENSOR → ARDUINO |
| 2 | Arduino sends `P2_ID_LOAD` | — | ARDUINO → PC |
| 3 | (removal) IR Sensor 7 goes HIGH (500ms) | Pin 23 | SENSOR → ARDUINO |
| 4 | Arduino sends `P2_ID_UNLOAD` | — | ARDUINO → PC |

---

## SEQUENCE H: Dunpla Reaches Process 2

| Step | Action | Pin | Direction |
|------|--------|-----|-----------|
| 1 | IR Sensor 8 detects dunpla (LOW, 500ms sustained) | Pin 28 | SENSOR → ARDUINO |
| 2 | Arduino sends `P2_DONE` | — | ARDUINO → PC |

---

## SEQUENCE I: P1 Interlock (PC-Commanded)

| Action | Pin | Direction |
|--------|-----|-----------|
| PC queues `RELAY_P1_ON` | — | PC → ARDUINO |
| Arduino sets Pin 13 HIGH | Pin 13 | PC → ARDUINO → RELAY (Type 2) |
| Arduino sends `P1_OPEN_INTERLOCK` | — | ARDUINO → PC |
| PC queues `RELAY_P1_OFF` | — | PC → ARDUINO |
| Arduino sets Pin 13 LOW | Pin 13 | PC → ARDUINO → RELAY (Type 2) |
| Arduino sends `P1_CLOSE_INTERLOCK` | — | ARDUINO → PC |

---

## SEQUENCE J: P2 Interlock (PC-Commanded)

| Action | Pin | Direction |
|--------|-----|-----------|
| PC queues `RELAY_P2_ON` | — | PC → ARDUINO |
| Arduino sets Pin 27 HIGH | Pin 27 | PC → ARDUINO → RELAY (Type 2) |
| Arduino sends `P2_OPEN_INTERLOCK` | — | ARDUINO → PC |
| PC queues `RELAY_P2_OFF` | — | PC → ARDUINO |
| Arduino sets Pin 27 LOW | Pin 27 | PC → ARDUINO → RELAY (Type 2) |
| Arduino sends `P2_CLOSE_INTERLOCK` | — | ARDUINO → PC |

---

## PIN SUMMARY TABLE

| Pin | Type | Function | Relay Type |
|-----|------|----------|------------|
| **2** | INPUT | IR Sensor 1 — MS ID detection | — |
| **3** | OUTPUT | Relay 2 — MS solenoid interlock | **Type 2** (PC-Commanded, HIGH=open) |
| **4** | OUTPUT | Relay 4 — MS ID scanner power | **Type 1** (Pin-Controlled, LOW=on) |
| **5** | INPUT | IR Sensor 5 — MS kitting detection | — |
| **6** | OUTPUT | Relay 5 — MS kitting scanner power | **Type 1** (Pin-Controlled, LOW=on) |
| **7** | INPUT | IR Sensor 2 — dunpla at Standby | — |
| **8** | OUTPUT | Standby Relay — Standby interlock | **Type 2** (PC-Commanded, HIGH=open) |
| **9** | INPUT | IR Sensor 3 — P1 ID detection | — |
| **10** | OUTPUT | Relay 7 — P1 Scanner 3 power | **Type 1** (Pin-Controlled, LOW=on) |
| **11** | INPUT | IR Sensor — P1 kitting detection | — |
| **12** | OUTPUT | Relay 8 — P1 Scanner 4 power | **Type 1** (Pin-Controlled, LOW=on) |
| **13** | OUTPUT | Relay 9 — P1 solenoid interlock | **Type 2** (PC-Commanded, HIGH=open) |
| **14** | TX3 | P1 Scanner 3 trigger (Serial3 TX) | — |
| **15** | RX3 | P1 Scanner 3 data (Serial3 RX) | — |
| **16** | TX2 | MS Kitting Scanner trigger (Serial2 TX) | — |
| **17** | RX2 | MS Kitting Scanner data (Serial2 RX) | — |
| **18** | TX1 | MS ID Scanner trigger (Serial1 TX) | — |
| **19** | RX1 | MS ID Scanner data (Serial1 RX) | — |
| **22** | INPUT | IR Sensor 6 — dunpla at Process 1 | — |
| **23** | INPUT | IR Sensor 7 — P2 ID detection | — |
| **27** | OUTPUT | Relay — P2 solenoid interlock | **Type 2** (PC-Commanded, HIGH=open) |
| **28** | INPUT | IR Sensor 8 — dunpla at Process 2 | — |
