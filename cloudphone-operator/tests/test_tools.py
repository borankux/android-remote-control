import unittest

from cloudphone_operator.config import OperatorConfig
from cloudphone_operator.tools import CloudPhoneTools, extract_ui_snippets


class FakeRelayClient:
    def __init__(self):
        self.commands = []

    def list_devices(self):
        return [
            {
                "deviceId": "device-a",
                "online": True,
                "lastSeenAt": "2026-06-07T00:00:00Z",
                "hello": {
                    "appVersion": "0.8.2",
                    "report": {
                        "system": {"model": "23049RAD8C", "androidVersion": "12", "sdkInt": 31},
                        "root": {"available": True},
                    },
                },
            }
        ]

    def send_command(self, device_id, name, params, timeout_ms=30000):
        self.commands.append((device_id, name, params, timeout_ms))
        if name == "snapshot":
            result = {"ok": True, "foreground": "com.xingin.xhs", "rootAvailable": True}
        elif name == "screencap":
            result = {"ok": True, "format": "jpeg", "mimeType": "image/jpeg", "byteCount": 1234, "base64": "abc"}
        elif name == "dump_ui":
            result = {
                "ok": True,
                "xml": (
                    '<hierarchy>'
                    '<node text="搜索" class="android.widget.TextView" bounds="[20,30][200,90]" clickable="true" enabled="true"/>'
                    '<node text="首页" class="android.widget.TextView" bounds="[10,100][80,160]" clickable="true" enabled="true"/>'
                    '<node text="这条笔记真的很有用" class="android.widget.TextView" bounds="[40,900][680,960]" clickable="false" enabled="true"/>'
                    '</hierarchy>'
                ),
                "charCount": 260,
            }
        else:
            result = {"ok": True}
        return {"id": "cmd-1", "deviceId": device_id, "name": name, "status": "completed", "result": result}


class ToolsTest(unittest.TestCase):
    def make_tools(self):
        config = OperatorConfig(relay_token="token", device_id="device-a")
        fake = FakeRelayClient()
        return CloudPhoneTools(config, fake), fake

    def test_get_device_status(self):
        tools, _ = self.make_tools()
        result = tools.get_device_status({})
        self.assertTrue(result.ok)
        self.assertEqual(result.data["device"]["model"], "23049RAD8C")

    def test_observe_device_summarizes_screenshot_and_ui(self):
        tools, fake = self.make_tools()
        result = tools.observe_device({})
        self.assertTrue(result.ok)
        observation = result.data["observation"]
        self.assertEqual(observation["foreground"], "com.xingin.xhs")
        self.assertEqual(observation["screenshot"]["byteCount"], 1234)
        self.assertIn("搜索", observation["uiSnippets"])
        self.assertEqual(fake.commands[0][1], "snapshot")

    def test_tap_uses_config_device_id(self):
        tools, fake = self.make_tools()
        result = tools.tap({"x": 10, "y": 20})
        self.assertTrue(result.ok)
        self.assertEqual(fake.commands[-1][0], "device-a")
        self.assertEqual(fake.commands[-1][1], "tap")

    def test_extract_ui_snippets_deduplicates(self):
        snippets = extract_ui_snippets('<node text="搜索"/><node text="搜索"/><node text="评论"/>')
        self.assertEqual(snippets, ["搜索", "评论"])

    def test_ui_snapshot_is_compact_and_omits_xml(self):
        tools, _ = self.make_tools()
        result = tools.ui_snapshot({"limit": 10})
        self.assertTrue(result.ok)
        self.assertIn("visibleTexts", result.data["ui"])
        self.assertIn("搜索", result.data["ui"]["visibleTexts"])
        self.assertNotIn("<hierarchy", str(result.to_dict()))

    def test_find_text_returns_node_handles(self):
        tools, _ = self.make_tools()
        result = tools.find_text({"text": "搜索"})
        self.assertTrue(result.ok)
        self.assertEqual(result.data["matches"][0]["text"], "搜索")
        self.assertEqual(result.data["matches"][0]["center"], [110, 60])

    def test_tap_text_clicks_node_center(self):
        tools, fake = self.make_tools()
        result = tools.tap_text({"text": "搜索"})
        self.assertTrue(result.ok)
        self.assertEqual(fake.commands[-1][1], "tap")
        self.assertEqual(fake.commands[-1][2], {"x": 110, "y": 60})
        self.assertEqual(result.data["node"]["text"], "搜索")

    def test_tap_node_clicks_current_node_id(self):
        tools, fake = self.make_tools()
        result = tools.tap_node({"nodeId": 1})
        self.assertTrue(result.ok)
        self.assertEqual(fake.commands[-1][1], "tap")
        self.assertEqual(fake.commands[-1][2], {"x": 45, "y": 130})

    def test_read_comments_returns_candidates(self):
        tools, _ = self.make_tools()
        result = tools.read_comments({})
        self.assertTrue(result.ok)
        self.assertEqual(result.data["comments"][0]["text"], "这条笔记真的很有用")


if __name__ == "__main__":
    unittest.main()
