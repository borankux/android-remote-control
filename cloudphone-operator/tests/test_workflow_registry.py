import tempfile
import unittest
from pathlib import Path

from cloudphone_operator.audit import JsonlAuditLogger
from cloudphone_operator.config import OperatorConfig
from cloudphone_operator.executor import ToolExecutor
from cloudphone_operator.tools import CloudPhoneTools
from cloudphone_operator.workflow_registry import execute_workflow, extract_tap_text, match_workflow
from tests.test_tools import FakeRelayClient


class WorkflowRegistryTest(unittest.TestCase):
    def make_executor(self):
        config = OperatorConfig(relay_token="token", device_id="device-a")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        audit = JsonlAuditLogger(Path(tmp.name) / "action-log.jsonl")
        return ToolExecutor(CloudPhoneTools(config, FakeRelayClient()), audit)

    def test_matches_read_comments_before_generic_text_click(self):
        workflow = match_workflow("读取评论")
        self.assertEqual(workflow.name, "read_comments")

    def test_matches_tap_text_and_extracts_text(self):
        workflow = match_workflow("点击搜索按钮")
        self.assertEqual(workflow.name, "tap_text")
        self.assertEqual(extract_tap_text("点击搜索按钮"), "搜索")

    def test_executes_device_check(self):
        workflow = match_workflow("检查设备是否可控")
        payload = execute_workflow(self.make_executor(), workflow, "检查设备是否可控")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["workflow"], "device_check")
        self.assertEqual([event["tool"] for event in payload["events"]], ["list_devices", "get_device_status", "observe_device"])

    def test_executes_tap_text(self):
        workflow = match_workflow("点击搜索")
        payload = execute_workflow(self.make_executor(), workflow, "点击搜索")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["workflow"], "tap_text")
        self.assertEqual(payload["events"][0]["tool"], "tap_text")
        self.assertEqual(len(payload["actions"]), 1)


if __name__ == "__main__":
    unittest.main()
