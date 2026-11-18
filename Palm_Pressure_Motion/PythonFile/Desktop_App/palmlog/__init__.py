"""PalmLog laptop — companion untuk FW Log_Session_Bin (PLG1 v4)."""

from pathlib import Path

__version__ = (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip()
