import unittest

from cloudphone_operator.policy import PolicyViolation, validate_tool


class PolicyTest(unittest.TestCase):
    def test_allows_basic_read_tool(self):
        validate_tool("list_devices", {})

    def test_rejects_unknown_tool(self):
        with self.assertRaises(PolicyViolation) as ctx:
            validate_tool("shell", {"cmd": "id"})
        self.assertEqual(ctx.exception.code, "tool_not_allowed")

    def test_rejects_overlong_input_text(self):
        with self.assertRaises(PolicyViolation) as ctx:
            validate_tool("input_text", {"text": "a" * 201})
        self.assertEqual(ctx.exception.code, "text_too_long")

    def test_rejects_shell_like_input(self):
        with self.assertRaises(PolicyViolation) as ctx:
            validate_tool("input_text", {"text": "hello && id"})
        self.assertEqual(ctx.exception.code, "unsafe_text")

    def test_rejects_bad_coordinates(self):
        with self.assertRaises(PolicyViolation) as ctx:
            validate_tool("tap", {"x": -1, "y": 10})
        self.assertEqual(ctx.exception.code, "x_out_of_range")

    def test_rejects_bad_screenshot_format(self):
        with self.assertRaises(PolicyViolation) as ctx:
            validate_tool("screencap", {"format": "bmp"})
        self.assertEqual(ctx.exception.code, "invalid_screenshot_format")

    def test_allows_semantic_read_tools(self):
        validate_tool("ui_snapshot", {"limit": 20})
        validate_tool("read_screen", {"limit": 20})
        validate_tool("read_comments", {"limit": 20})

    def test_rejects_bad_text_query(self):
        with self.assertRaises(PolicyViolation) as ctx:
            validate_tool("find_text", {"text": "hello && id"})
        self.assertEqual(ctx.exception.code, "unsafe_text")

    def test_rejects_bad_tap_node(self):
        with self.assertRaises(PolicyViolation) as ctx:
            validate_tool("tap_node", {"nodeId": -1})
        self.assertEqual(ctx.exception.code, "nodeId_out_of_range")


if __name__ == "__main__":
    unittest.main()
