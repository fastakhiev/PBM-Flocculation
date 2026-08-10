import os
import tempfile
import unittest
from pathlib import Path


_TEST_DIRECTORY = tempfile.TemporaryDirectory()
os.environ["SQLITE_PATH"] = str(Path(_TEST_DIRECTORY.name) / "api.sqlite3")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.jobs import create_job  # noqa: E402


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)

    def test_openapi_identifies_release(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["info"]["title"], "PBM Flocculation")
        self.assertIn("/api/optimization_report", response.json()["paths"])

    def test_saved_result_has_downloadable_audit_report(self):
        job = create_job()
        job.status = "completed"
        job.result = {
            "success": True,
            "g": 312.0,
            "do": 100.0,
            "cpamm": "E2",
            "dosage": 6,
            "amax": 0.8,
            "B": 49.2,
            "gama": 0.43,
            "gof": 98.2,
            "optimization_time": 1.2,
            "moments": [1, 1.0439, 1.3993, 2.4084, 5.3226],
            "algorithm": {"name": "Differential Evolution Algorithm (DEA)"},
            "provenance": {
                "software_version": "test",
                "protocol_version": "EQMOM-PCC-2STAGE-1.0",
                "experimental_sha256": "a" * 64,
                "moments_sha256": "b" * 64,
                "runtime": {"python": "test"},
            },
        }
        saved = self.client.post("/api/save_optimization_results", json={"task_id": job.id})
        self.assertEqual(saved.status_code, 200)

        report = self.client.get("/api/optimization_report")
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.json()["provenance"]["protocol_version"], "EQMOM-PCC-2STAGE-1.0")
        self.assertEqual(report.json()["provenance"]["runtime"]["python"], "test")
        self.client.delete("/api/delete_optimization_data")

    def test_simulation_requires_saved_optimization(self):
        response = self.client.post(
            "/api/start_simulation",
            files={"file": ("experiment.csv", b"invalid", "text/csv")},
        )
        self.assertEqual(response.status_code, 409)

    def test_upload_rejects_non_csv_extension(self):
        form_values = ["312", "100", "BHMW", "Differential Evolution Algorithm (DEA)", "14"]
        multipart = [("data", (None, value)) for value in form_values]
        multipart.extend(
            [
                ("file_exp", ("experiment.txt", b"invalid", "text/plain")),
                ("file_init", ("moments.csv", b"value\n1\n2\n3\n4\n5", "text/csv")),
            ]
        )
        response = self.client.post("/api/start_optimize", files=multipart)
        self.assertEqual(response.status_code, 422)
        self.assertIn(".csv", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
