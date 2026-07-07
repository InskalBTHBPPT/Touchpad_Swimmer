# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — Swimmer Force Motion Monitoring v2.4.0 (onefile, Windows)

from PyInstaller.utils.hooks import collect_all

block_cipher = None

pyside6_datas, pyside6_binaries, pyside6_hidden = collect_all("PySide6")
cv2_datas, cv2_binaries, cv2_hidden = collect_all("cv2")

_EXCLUDES = [
    "torch",
    "torchvision",
    "torchaudio",
    "tensorflow",
    "tensorboard",
    "matplotlib",
    "pandas",
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
    ["Swimmer_Force_Motion_Monitoring_v2.4.0.py"],
    pathex=[],
    binaries=pyside6_binaries + cv2_binaries,
    datas=[
        ("UserManual_Force_Motion_v2.4.0-e.pdf", "."),
        ("../Changelog.md", "."),
        ("image/logo_brin.png", "image"),
        ("image/logo_unnes.png", "image"),
    ] + pyside6_datas + cv2_datas,
    hiddenimports=pyside6_hidden + cv2_hidden + [
        "pyqtgraph",
        "numpy",
        "serial",
        "serial.tools",
        "serial.tools.list_ports",
        "scipy",
        "scipy.signal",
        "scipy.special",
        "scipy.special._ufuncs_cxx",
        "pygrabber",
        "pygrabber.dshow_graph",
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
    name="Swimmer_Force_Motion_Monitoring_v2.4.0",
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
