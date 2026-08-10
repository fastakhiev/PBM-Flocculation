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


def _close_boot_splash() -> None:
    try:
        import pyi_splash

        pyi_splash.close()
    except ImportError:
        pass


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

    logging.info("Starting PBM Flocculation at %s", url)
    threading.Thread(target=_run_server, args=(host, port, server_failed), daemon=True).start()
    server_ready = _wait_for_server(health_url, server_failed)

    if os.getenv("PBM_SMOKE_TEST", "").lower() in {"1", "true", "yes"}:
        _close_boot_splash()
        if not server_ready:
            raise RuntimeError(f"Embedded server smoke test failed; see {log_path}")
        logging.info("Embedded server smoke test passed")
        return

    window_options = {
        "title": "PBM Flocculation",
        "width": 1280,
        "height": 820,
        "min_size": (1024, 700),
    }
    if server_ready:
        webview.create_window(url=url, **window_options)
    else:
        logging.error("Server did not become ready at %s", url)
        error_html = (
            "<h2>PBM Flocculation could not start</h2>"
            "<p>The embedded server failed to launch.</p>"
            f"<p>Diagnostic log: <code>{log_path}</code></p>"
        )
        webview.create_window(html=error_html, **window_options)
    webview.start(
        _close_boot_splash,
        debug=os.getenv("WEBVIEW_DEBUG", "").lower() in {"1", "true", "yes"},
    )


if __name__ == "__main__":
    main()
