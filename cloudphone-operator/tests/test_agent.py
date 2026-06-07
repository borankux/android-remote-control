import unittest
import tempfile
from pathlib import Path

from cloudphone_operator.agent import CloudPhoneOperator, create_agno_agent
from cloudphone_operator.audit import JsonlAuditLogger
from cloudphone_operator.config import OperatorConfig
from cloudphone_operator.executor import ToolExecutor
from cloudphone_operator.tools import CloudPhoneTools
from tests.test_tools import FakeRelayClient


class AgentTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def make_operator(self):
        config = OperatorConfig(relay_token="token", device_id="device-a")
        logger = JsonlAuditLogger(Path(self.tmp.name) / "action-log.jsonl")
        executor = ToolExecutor(CloudPhoneTools(config, FakeRelayClient()), logger)
        return CloudPhoneOperator(executor, config), executor

    def test_help_requires_no_relay_action(self):
        operator, _ = self.make_operator()
        payload = operator.run("帮助")
        self.assertTrue(payload["ok"])
        self.assertIn("列出设备", payload["capabilities"])

    def test_check_workflow(self):
        operator, _ = self.make_operator()
        payload = operator.run("检查设备是否可控")
        self.assertTrue(payload["ok"])
        self.assertEqual([event["tool"] for event in payload["events"]], ["list_devices", "get_device_status", "observe_device"])

    def test_xhs_workflow(self):
        operator, _ = self.make_operator()
        payload = operator.run("打开小红书，截图确认")
        self.assertTrue(payload["ok"])
        self.assertIn("launch_xhs", [event["tool"] for event in payload["events"]])

    def test_read_screen_workflow(self):
        operator, _ = self.make_operator()
        payload = operator.run("读取当前页面")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["events"][0]["tool"], "read_screen")
        self.assertIn("visibleTexts", payload["events"][0]["data"])

    def test_read_comments_workflow(self):
        operator, _ = self.make_operator()
        payload = operator.run("读取评论")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["events"][0]["tool"], "read_comments")
        self.assertIn("comments", payload["events"][0]["data"])

    def test_tap_text_workflow(self):
        operator, _ = self.make_operator()
        payload = operator.run("点击搜索")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["events"][0]["tool"], "tap_text")

    def test_agno_factory_without_model_is_clear(self):
        config = OperatorConfig(relay_token="token", device_id="device-a")
        logger = JsonlAuditLogger(Path(self.tmp.name) / "action-log.jsonl")
        executor = ToolExecutor(CloudPhoneTools(config, FakeRelayClient()), logger)
        agent, error = create_agno_agent(executor, config)
        self.assertIsNone(agent)
        self.assertEqual(error, "model_not_configured")


if __name__ == "__main__":
    unittest.main()
