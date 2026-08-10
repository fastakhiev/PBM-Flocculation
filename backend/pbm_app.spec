#!/usr/bin/env python3
# PyInstaller spec for a one-directory distribution with fast startup.
# Build on Windows to produce a Windows .exe.

from pathlib import Path

project_root = Path(SPECPATH).resolve().parents[0]
frontend_dist = project_root / "pbm_model_interface" / "dist"

datas = []
if frontend_dist.exists():
    datas.append((str(frontend_dist), "pbm_model_interface/dist"))

a = Analysis(
    ["standalone.py"],
    pathex=[str(Path(SPECPATH).resolve())],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["pyinstaller_runtime_hook.py"],
    excludes=["cefpython3", "gi", "IPython", "kivy", "PyQt5", "qtpy"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name="PBM-Flocculation",
    console=False,
    exclude_binaries=True,
    disable_windowed_traceback=False,
)

bundle = COLLECT(
    exe,
    a.binaries,
    a.datas,
    a.zipfiles,
    name="PBM-Flocculation",
)
