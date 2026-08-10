#!/usr/bin/env python3
# PyInstaller spec for a one-directory distribution with fast startup.
# Build on Windows to produce a Windows .exe.

from pathlib import Path
import sys

project_root = Path(SPECPATH).resolve().parents[0]
frontend_dist = project_root / "pbm_model_interface" / "dist"

datas = []
if frontend_dist.exists():
    datas.append((str(frontend_dist), "pbm_model_interface/dist"))

runtime_binaries = []
if sys.platform == "win32":
    python_roots = {
        Path(sys.base_prefix).resolve(),
        Path(sys.prefix).resolve(),
        Path(sys.executable).resolve().parent,
    }
    runtime_dlls = set()
    for root in python_roots:
        for directory in (root, root / "DLLs", root / "Library" / "bin"):
            for pattern in ("libffi*.dll", "ffi-*.dll"):
                runtime_dlls.update(directory.glob(pattern))

    if not runtime_dlls:
        raise SystemExit(
            "The build Python installation does not contain the libffi DLL required by _ctypes. "
            "Install 64-bit CPython from python.org and run the build again."
        )
    runtime_binaries.extend((str(dll), ".") for dll in sorted(runtime_dlls))

a = Analysis(
    ["standalone.py"],
    pathex=[str(Path(SPECPATH).resolve())],
    binaries=runtime_binaries,
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
