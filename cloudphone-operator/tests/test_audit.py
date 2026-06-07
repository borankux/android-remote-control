import tempfile
import unittest
from pathlib import Path

from cloudphone_operator.audit import JsonlAuditLogger, sanitize
from cloudphone_operator.schemas import ToolResult


class AuditTest(unittest.TestCase):
    def test_sanitize_redacts_sensitive_fields(self):
        payload = sanitize({"token": "secret", "base64": "image", "xml": "<node />", "ok": True})
        self.assertEqual(payload["token"], "[redacted]")
        self.assertEqual(payload["base64"], "[redacted]")
        self.assertEqual(payload["xml"], "[redacted]")
        self.assertTrue(payload["ok"])

    def test_log_does_not_write_sensitive_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "action-log.jsonl"
            logger = JsonlAuditLogger(path)
            logger.log(
                "tap",
                "device-a",
                {"x": 1, "token": "secret", "base64": "image", "xml": "<node />"},
                ToolResult.success("ok"),
            )
            text = path.read_text(encoding="utf-8")
            self.assertIn('"tool": "tap"', text)
            self.assertNotIn("secret", text)
            self.assertNotIn("<node", text)
            self.assertNotIn("image", text)
            self.assertEqual(len(logger.tail(1)), 1)


if __name__ == "__main__":
    unittest.main()
