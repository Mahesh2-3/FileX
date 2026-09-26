"""
FastAPI Integration Tests
"""

import unittest
from fastapi.testclient import TestClient
from pathlib import Path

from backend.main import app
from create_sample_data import generate_sample_dataset


class TestAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_dir = Path(__file__).resolve().parent.parent / "test_files"
        generate_sample_dataset(cls.test_dir)

    def test_api_workflow(self):
        # 1. Test Scan
        scan_res = self.client.post("/api/scan", json={
            "path": str(self.test_dir),
            "recursive": False
        })
        self.assertEqual(scan_res.status_code, 200)
        data = scan_res.json()
        self.assertTrue(data["success"])
        self.assertGreaterEqual(data["total_files"], 8)

        # 2. Test Analyze with natural language instruction
        analyze_res = self.client.post("/api/analyze", json={
            "files": data["files"],
            "custom_instructions": "Organize all my college materials and separate them by subject",
            "api_provider": "offline"
        })
        self.assertEqual(analyze_res.status_code, 200)
        ana_data = analyze_res.json()
        self.assertTrue(ana_data["success"])
        ops = ana_data["proposed_operations"]
        self.assertGreaterEqual(len(ops), 5)

        # Check college subject suggestion
        os_op = next((o for o in ops if "doc123" in o["original_name"]), None)
        self.assertIsNotNone(os_op)
        self.assertIn("College", os_op["target_folder"])

        # 3. Test Preview
        first_file = data["files"][0]["full_path"]
        prev_res = self.client.get(f"/api/preview?path={first_file}")
        self.assertEqual(prev_res.status_code, 200)
        prev_data = prev_res.json()
        self.assertIn("metadata", prev_data)

        # 4. Test History
        hist_res = self.client.get("/api/history")
        self.assertEqual(hist_res.status_code, 200)
        self.assertTrue(hist_res.json()["success"])

    def test_streaming_analyze(self):
        # 1. Scan directory
        scan_res = self.client.post("/api/scan", json={
            "path": str(self.test_dir),
            "recursive": False
        })
        self.assertEqual(scan_res.status_code, 200)
        data = scan_res.json()

        # 2. Test Stream endpoint
        stream_res = self.client.post("/api/analyze/stream", json={
            "files": data["files"][:3],
            "api_provider": "offline"
        })
        self.assertEqual(stream_res.status_code, 200)
        self.assertIn("text/event-stream", stream_res.headers.get("content-type", ""))
        self.assertIn("data: ", stream_res.text)
        self.assertIn('"type": "progress"', stream_res.text)


if __name__ == "__main__":
    unittest.main()

