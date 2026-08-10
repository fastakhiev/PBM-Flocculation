import os
import sys


os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")

for stream_name in ("stdout", "stderr"):
    stream = getattr(sys, stream_name, None)
    if stream is None:
        stream = open(os.devnull, "w", encoding="utf-8")
        setattr(sys, stream_name, stream)
    elif hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")
