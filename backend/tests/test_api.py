import importlib.util
import unittest

HAVE_WEB = all(importlib.util.find_spec(m) for m in ("fastapi", "httpx", "multipart"))


@unittest.skipUnless(HAVE_WEB, "fastapi/httpx/python-multipart not installed")
class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from app.config import load_settings
        from app.main import create_app
        from tests.helpers import make_pipeline
        import tempfile, dataclasses, pathlib
        tmp = pathlib.Path(tempfile.mkdtemp())
        cls.settings = dataclasses.replace(load_settings(), feedback_path=tmp / "fb.jsonl",
                                           overrides_path=tmp / "ov.json")
        cls.pipe, _, _ = make_pipeline()
        cls.client = TestClient(create_app(cls.settings, pipeline=cls.pipe))
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def test_health(self):
        r = self.client.get("/health").json()
        self.assertEqual(r["status"], "ok")
        self.assertTrue(r["models_ready"])

    def test_translate_ok_shape(self):
        r = self.client.post("/api/v1/translate", json={"text": "Naanu ivattu college ge baralla"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.json()) >= {"original_text", "detected_languages", "normalized_text",
                                           "translated_text", "warnings"}, True)

    def test_invalid_requests(self):
        self.assertEqual(self.client.post("/api/v1/translate", json={}).status_code, 422)
        self.assertEqual(self.client.post("/api/v1/translate", json={"text": "   "}).status_code, 422)
        self.assertEqual(self.client.post("/api/v1/translate", json={"text": 5}).status_code, 422)
        self.assertEqual(self.client.post("/api/v1/translate", content="not json").status_code, 422)
        self.assertEqual(self.client.post("/api/v1/translate",
                                          json={"text": "a" * (self.settings.max_text_chars + 1)}).status_code, 413)

    def test_feedback_and_override(self):
        r = self.client.post("/api/v1/feedback", json={"original_text": "a", "corrected_translation": "b"})
        self.assertEqual(r.status_code, 201)
        r = self.client.post("/api/v1/tokens/override", json={"word": "bus", "label": "english"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.post("/api/v1/tokens/override",
                                          json={"word": "bus", "label": "nonsense"}).status_code, 422)

    def test_dataset_validate_endpoint(self):
        with open("../datasets/sample/synthetic_demo.csv", "rb") as fh:
            r = self.client.post("/api/v1/datasets/validate", files={"file": ("d.csv", fh, "text/csv")})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["rows"], 20)
        r = self.client.post("/api/v1/datasets/validate", files={"file": ("d.txt", b"x", "text/plain")})
        self.assertEqual(r.status_code, 415)

    def test_cors_blocks_foreign_origin(self):
        r = self.client.get("/health", headers={"Origin": "https://evil.example"})
        self.assertNotIn("access-control-allow-origin", r.headers)


@unittest.skipUnless(HAVE_WEB, "fastapi not installed")
class ModelLoadFailureTests(unittest.TestCase):
    def test_503_and_health_report_when_models_fail(self):
        import time
        from unittest import mock
        from fastapi.testclient import TestClient
        from app.main import create_app
        from app.nlp.base import ModelLoadError
        with mock.patch("app.main.build_default_pipeline", side_effect=ModelLoadError("nope")):
            with TestClient(create_app()) as c:
                for _ in range(50):
                    if c.get("/health").json()["models"]["translator"] == "error":
                        break
                    time.sleep(0.1)
                h = c.get("/health").json()
                self.assertFalse(h["models_ready"])
                self.assertEqual(h["models"]["translator"], "error")
                self.assertEqual(c.post("/api/v1/translate", json={"text": "naanu"}).status_code, 503)
                self.assertNotIn("/home", str(h))


if __name__ == "__main__":
    unittest.main()
