import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault("APP_API_KEY", "test-token")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app, require_key, resolve_inside


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "projects"
        self.root.mkdir()
        self.client = TestClient(app)
        self.patch = patch("app.main.PROJECT_ROOT", self.root)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_health_endpoint(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_path_inside_root(self):
        project = self.root / "Demo.eprj3"
        project.mkdir()
        self.assertEqual(resolve_inside(self.root, "Demo.eprj3"), project)

    def test_path_traversal_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            resolve_inside(self.root, "../outside")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_missing_path_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            resolve_inside(self.root, "missing")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_api_key_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            require_key("wrong")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_api_key_accepted(self):
        require_key("test-token")


if __name__ == "__main__":
    unittest.main()
