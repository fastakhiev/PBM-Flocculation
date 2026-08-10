import os
import sys


os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")

_DLL_DIRECTORY_HANDLES = []
if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
    bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    dll_directories = (
        bundle_dir,
        os.path.dirname(sys.executable),
        os.path.join(bundle_dir, "DLLs"),
        os.path.join(bundle_dir, "Library", "bin"),
    )
    existing_path = os.environ.get("PATH", "")
    for directory in dll_directories:
        if not os.path.isdir(directory):
            continue
        if directory not in existing_path.split(os.pathsep):
            os.environ["PATH"] = directory + os.pathsep + existing_path
            existing_path = os.environ["PATH"]
        try:
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(directory))
        except OSError:
            pass

for stream_name in ("stdout", "stderr"):
    stream = getattr(sys, stream_name, None)
    if stream is None:
        stream = open(os.devnull, "w", encoding="utf-8")
        setattr(sys, stream_name, stream)
    elif hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")
