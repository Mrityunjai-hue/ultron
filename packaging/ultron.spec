# -*- mode: python ; coding: utf-8 -*-
"""
ULTRON — PyInstaller Standalone Windows Binary Specification
─────────────────────────────────────────────────────────────────────────────
Compiles ULTRON into a sovereign, standalone Windows binary package
including CPython runtime, all native C-extensions (win32, PortAudio, numpy),
and package resources.
─────────────────────────────────────────────────────────────────────────────
"""
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

repo_root = Path(SPECPATH).resolve().parent if 'SPECPATH' in globals() else Path.cwd().resolve()

hidden_imports = [
    "google.genai",
    "google.genai.types",
    "sounddevice",
    "_sounddevice_data",
    "numpy",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "win32gui",
    "win32con",
    "win32api",
    "win32process",
    "win32event",
    "winerror",
    "winreg",
    "psutil",
    "requests",
    "websockets",
    "pydantic",
    "ultron",
    "ultron.core",
    "ultron.core.paths",
    "ultron.core.config",
    "ultron.core.credentials",
    "ultron.core.logging_sanitizer",
    "ultron.core.single_instance",
    "ultron.core.startup",
    "ultron.core.lifecycle",
    "ultron.core.runtime",
    "ultron.presence",
    "ultron.presence.manager",
    "ultron.presence.window",
    "ultron.presence.renderer",
    "ultron.presence.animation",
    "ultron.presence.hit_testing",
    "ultron.realtime",
    "ultron.realtime.gemini_live",
    "ultron.realtime.audio_stream",
    "ultron.tasks",
    "ultron.tasks.executor",
    "ultron.tasks.persistence",
    "ultron.tasks.journal",
    "ultron.tasks.evidence",
    "ultron.tasks.goal",
    "ultron.tasks.goal_planner",
    "ultron.tasks.verifier",
    "ultron.tasks.recovery",
    "ultron.tasks.replanner",
    "ultron.tools",
    "ultron.tools.registry",
    "ultron.tools.executor",
    "ultron.tools.safety",
    "ultron.tools.confirmation",
    "ultron.apps",
    "ultron.apps.chrome",
    "ultron.diagnostics",
    "ultron.diagnostics.system",
]

datas = [
    (str(repo_root / "ultron" / "__version__.py"), "ultron"),
]

a = Analysis(
    [str(repo_root / "ultron" / "main.py")],
    pathex=[str(repo_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "torch", "notebook", "jupyter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ultron",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ultron",
)
