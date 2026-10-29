KITTING SCANNER FIX
===================

1. arduino_ms/arduino_ms.ino
   - Uses the proven Serial2 kitting scanner logic.
   - Does not flush valid Serial2 QR bytes before they are parsed.
   - Kitting scanner boot delay is 2 seconds.
   - Expected Arduino output: KITSCAN:<QR DATA>

2. arduino_bridge_ms.py
   - Explicitly detects KITSCAN:<QR DATA> and posts it to Flask.
   - Adds a console line: KITSCAN detected from Arduino: ...

3. cycleTimeMoni.py
   - A valid kitting scan is no longer erased on KITTING_UNLOAD.
   - Scan data is cleared at the next KITTING_LOAD instead.
   - This prevents a race with the browser's 500 ms polling interval.

IMPORTANT TEST QR
-----------------
The scanner must scan the same QR currently shown/printed by the Material Setter page.
If the UI currently expects:
  260826 0001 3J73802302 0001
then scanning:
  260826 0001 3J00733952 0000
is a mismatch. The existing web logic intentionally clears mismatched QR values.
