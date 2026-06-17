# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — Swimmer Force Motion Monitoring v1.0.08 (onefile, Windows)

from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Hanya PySide6 perlu collect_all penuh (plugin Qt).
pyside6_datas, pyside6_binaries, pyside6_hidden = collect_all("PySide6")

_EXCLUDES = [
    "torch",
    "torchvision",
    "torchaudio",
    "tensorflow",
    "tensorboard",
    "scipy",
    "matplotlib",
    "pandas",
    "cv2",
    "IPython",
    "jupyter",
    "notebook",
    "sklearn",
    "sympy",
    "pytest",
    "OpenGL",
    "pyqtgraph.opengl",
    "tkinter",
]

a = Analysis(
    ["Swimmer_Force_Motion_Monitoring_v1_0_08.py"],
    pathex=[],
    binaries=pyside6_binaries,
    datas=[
        ("UserManual_Force_Motion_v1.0.08-e.pdf", "."),
        ("UserManual_Force_Motion_v1.0.08-e.md", "."),
    ] + pyside6_datas,
    hiddenimports=pyside6_hidden + [
        "pyqtgraph",
        "numpy",
        "serial",
        "serial.tools",
        "serial.tools.list_ports",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_EXCLUDES,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Swimmer_Force_Motion_Monitoring_v1.0.08",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
