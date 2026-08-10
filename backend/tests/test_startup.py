import subprocess
import sys
import unittest


class StartupTests(unittest.TestCase):
    def test_api_import_does_not_eagerly_load_ga_plotting_stack(self):
        command = (
            "import sys; import app.main; "
            "assert 'geneticalgorithm' not in sys.modules; "
            "assert 'matplotlib' not in sys.modules; "
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


if __name__ == "__main__":
    unittest.main()
