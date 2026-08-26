import subprocess
import sys
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import Mock, patch

import standalone


class StartupTests(unittest.TestCase):
    def test_desktop_title_identifies_the_release_and_protocol(self):
        self.assertEqual(standalone.APP_VERSION, "1.0.0-rc2")
        self.assertEqual(standalone.PROTOCOL_VERSION, "EQMOM-PCC-2STAGE-1.7")

    def test_api_import_does_not_eagerly_load_numerical_stack(self):
        command = (
            "import sys; import app.main; "
            "assert 'numpy' not in sys.modules; "
            "assert 'pandas' not in sys.modules; "
            "assert 'scipy' not in sys.modules"
        )
        result = subprocess.run(
            [sys.executable, "-c", command],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_loading_window_switches_to_application_when_server_is_ready(self):
        window = Mock()
        window.events.shown.wait.return_value = True

        with patch.object(standalone, "_wait_for_server", return_value=True):
            standalone._load_application_window(
                window,
                "http://127.0.0.1:8000/",
                "http://127.0.0.1:8000/openapi.json",
                Event(),
                Path("pbm-app.log"),
            )

        window.load_url.assert_called_once_with("http://127.0.0.1:8000/")
        window.load_html.assert_not_called()

    def test_loading_window_shows_diagnostics_when_server_fails(self):
        window = Mock()
        window.events.shown.wait.return_value = True

        with patch.object(standalone, "_wait_for_server", return_value=False), self.assertLogs(level="ERROR"):
            standalone._load_application_window(
                window,
                "http://127.0.0.1:8000/",
                "http://127.0.0.1:8000/openapi.json",
                Event(),
                Path("pbm-app.log"),
            )

        window.load_url.assert_not_called()
        self.assertIn("pbm-app.log", window.load_html.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
