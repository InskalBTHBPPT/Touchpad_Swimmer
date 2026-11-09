"""Folder unduhan lokal, per alamat MAC board."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def normalize_mac(address: str) -> str:
    return address.replace(":", "-").upper()


def board_dir(address: str) -> Path:
    path = DATA / normalize_mac(address)
    path.mkdir(parents=True, exist_ok=True)
    return path


def bin_path(address: str, name: str) -> Path:
    file_name = name if name.endswith(".bin") else f"{name}.bin"
    return board_dir(address) / file_name
