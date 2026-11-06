#!/usr/bin/env python3
"""Kirim jam lokal laptop ke firmware Timer_RV3032 lewat USB Serial."""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime

try:
    import serial
except ImportError:
    print("Install pyserial: pip install pyserial", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Tulis waktu laptop ke RV-3032 (perintah SET ...)."
    )
    parser.add_argument(
        "port",
        nargs="?",
        default="COM12",
        help="Port USB-CDC board (default COM12, sama platformio.ini)",
    )
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    ser = serial.Serial(args.port, args.baud, timeout=2)
    try:
        time.sleep(2.0)
        ser.reset_input_buffer()

        now = datetime.now()
        frac = now.microsecond / 1_000_000.0
        if frac > 0.05:
            time.sleep(1.0 - frac)
            now = datetime.now()

        cmd = now.strftime("SET %Y-%m-%d %H:%M:%S\n")
        print(f"Port {args.port}  kirim: {cmd.strip()}")
        ser.write(cmd.encode("ascii"))
        ser.flush()

        deadline = time.time() + 3.0
        while time.time() < deadline:
            line = ser.readline().decode("ascii", errors="replace").strip()
            if line:
                print(line)
                if line.startswith("OK"):
                    return 0
        print("Tidak ada jawaban OK. Pastikan firmware Timer_RV3032 sudah jalan.", file=sys.stderr)
        return 2
    finally:
        ser.close()


if __name__ == "__main__":
    raise SystemExit(main())
