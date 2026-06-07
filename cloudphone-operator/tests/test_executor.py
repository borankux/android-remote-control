import tempfile
import unittest
from pathlib import Path

from cloudphone_operator.audit import JsonlAuditLogger
from cloudphone_operator.config import OperatorConfig
from cloudphone_operator.executor import ToolExecutor
from cloudphone_operator.tools import CloudPhoneTools
from tests.test_tools import FakeRelayClient


class ExecutorTest(unittest.TestCase):
    def test_rejects_policy_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = OperatorConfig(relay_token="token", device_id="device-a")
            logger = JsonlAuditLogger(Path(tmp) / "action-log.jsonl")
            executor = ToolExecutor(CloudPhoneTools(config, FakeRelayClient()), logger)
            result = executor.run("input_text", {"text": "hello && id"})
            self.assertFalse(result.ok)
            self.assertEqual(result.error, "unsafe_text")

    def test_audits_write_actions_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "action-log.jsonl"
            config = OperatorConfig(relay_token="token", device_id="device-a")
            executor = ToolExecutor(CloudPhoneTools(config, FakeRelayClient()), JsonlAuditLogger(path))
            read = executor.run("list_devices", {})
            write = executor.run("tap", {"x": 1, "y": 2})
            self.assertTrue(read.ok)
            self.assertTrue(write.ok)
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            self.assertIn('"tool": "tap"', lines[0])


if __name__ == "__main__":
    unittest.main()
