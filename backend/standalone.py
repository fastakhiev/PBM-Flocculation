import os
import logging
import socket
import sys
import tempfile
import threading
import time
from contextlib import suppress
from pathlib import Path
from urllib.request import urlopen

import uvicorn
import webview

from app.protocol import PROTOCOL_VERSION
from app.version import APP_NAME, APP_VERSION


_LOADING_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PBM Flocculation</title>
  <style>
    * { box-sizing: border-box; }
    html, body { width: 100%; height: 100%; margin: 0; }
    body {
      display: grid;
      place-items: center;
      color: #2f3740;
      background: #f0f2f5;
      font-family: "Segoe UI", Arial, sans-serif;
    }
    main { text-align: center; }
    h1 { margin: 0 0 20px; font-size: 24px; font-weight: 600; letter-spacing: 0; }
    .spinner {
      width: 42px;
      height: 42px;
      margin: 0 auto 18px;
      border: 4px solid #d9dee3;
      border-top-color: #42b983;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    p { margin: 0; color: #66707a; font-size: 14px; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <main role="status" aria-live="polite">
    <h1>PBM Flocculation</h1>
    <div class="spinner" aria-hidden="true"></div>
    <p>Starting application...</p>
  </main>
</body>
</html>"""


def _log_path() -> Path:
    if sys.platform == "win32" and os.getenv("LOCALAPPDATA"):
        base_dir = Path(os.environ["LOCALAPPDATA"])
    elif sys.platform == "win32":
        base_dir = Path(tempfile.gettempdir())
    else:
        base_dir = Path.home()
    try:
        log_dir = base_dir / "PBM-Flocculation"
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        log_dir = Path(tempfile.gettempdir())
    return log_dir / "pbm-app.log"


def _available_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]


def _wait_for_server(url: str, server_failed: threading.Event, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server_failed.is_set():
            return False
        with suppress(Exception):
            with urlopen(url, timeout=0.5):
                return True
        time.sleep(0.2)
    return False


def _run_server(host: str, port: int, server_failed: threading.Event) -> None:
    try:
        # A direct import is required so PyInstaller includes the complete app package.
        from app.main import app

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=os.getenv("LOG_LEVEL", "warning"),
            access_log=False,
            log_config=None,
        )
        logging.error("Embedded server stopped before the application window closed")
        server_failed.set()
    except Exception:
        logging.exception("Embedded server failed to start")
        server_failed.set()


def _load_application_window(
    window,
    url: str,
    health_url: str,
    server_failed: threading.Event,
    log_path: Path,
) -> None:
    window.events.shown.wait(10)
    if _wait_for_server(health_url, server_failed):
        window.load_url(url)
        return

    logging.error("Server did not become ready at %s", url)
    error_html = (
        "<h2>PBM Flocculation could not start</h2>"
        "<p>The embedded server failed to launch.</p>"
        f"<p>Diagnostic log: <code>{log_path}</code></p>"
    )
    window.load_html(error_html)


def main() -> None:
    log_path = _log_path()
    logging_options = {
        "level": logging.INFO,
        "format": "%(asctime)s %(levelname)s %(message)s",
        "force": True,
    }
    try:
        logging.basicConfig(filename=log_path, **logging_options)
    except OSError:
        log_path = Path(tempfile.gettempdir()) / f"pbm-app-{os.getpid()}.log"
        logging.basicConfig(filename=log_path, **logging_options)

    # The desktop API is intentionally loopback-only; it has no remote-user
    # authentication and must not be exposed on the LAN.
    host = "127.0.0.1"
    port = int(os.environ["PORT"]) if "PORT" in os.environ else _available_port(host)
    url = f"http://{host}:{port}/"
    health_url = f"{url}openapi.json"
    server_failed = threading.Event()

    logging.info(
        "Starting %s %s with protocol %s at %s",
        APP_NAME,
        APP_VERSION,
        PROTOCOL_VERSION,
        url,
    )
    threading.Thread(target=_run_server, args=(host, port, server_failed), daemon=True).start()

    if os.getenv("PBM_SMOKE_TEST", "").lower() in {"1", "true", "yes"}:
        if not _wait_for_server(health_url, server_failed):
            raise RuntimeError(f"Embedded server smoke test failed; see {log_path}")
        logging.info("Embedded server smoke test passed")
        return

    window_options = {
        "title": f"{APP_NAME} {APP_VERSION} | {PROTOCOL_VERSION}",
        "width": 1280,
        "height": 820,
        "min_size": (1024, 700),
    }
    window = webview.create_window(html=_LOADING_HTML, **window_options)
    webview.start(
        _load_application_window,
        args=(window, url, health_url, server_failed, log_path),
        debug=os.getenv("WEBVIEW_DEBUG", "").lower() in {"1", "true", "yes"},
    )


if __name__ == "__main__":
    main()
