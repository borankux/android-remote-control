import unittest

from cloudphone_operator.ui_parser import comment_candidates, find_nodes, get_node, parse_bounds, parse_ui_xml


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="" class="android.widget.FrameLayout" bounds="[0,0][720,1280]" clickable="false" enabled="true">
    <node index="1" text="搜索" content-desc="" resource-id="com.xingin.xhs:id/search" class="android.widget.TextView" package="com.xingin.xhs" bounds="[20,30][200,90]" clickable="true" enabled="true" />
    <node index="2" text="这条笔记真的很有用" class="android.widget.TextView" bounds="[40,900][680,960]" clickable="false" enabled="true" />
    <node index="3" text="点赞" class="android.widget.TextView" bounds="[500,1000][620,1060]" clickable="true" enabled="true" />
  </node>
</hierarchy>
"""


class UiParserTest(unittest.TestCase):
    def test_parse_bounds(self):
        bounds = parse_bounds("[12,34][56,78]")
        self.assertEqual(bounds.to_list(), [12, 34, 56, 78])
        self.assertEqual(bounds.center, (34, 56))
        self.assertIsNone(parse_bounds("bad"))

    def test_parse_ui_xml_compact_snapshot(self):
        snapshot = parse_ui_xml(SAMPLE_XML)
        compact = snapshot.compact()
        self.assertEqual(compact["nodeCount"], 4)
        self.assertIn("搜索", compact["visibleTexts"])
        self.assertIn("nodes", compact)
        self.assertNotIn("xml", str(compact).lower())

    def test_find_nodes_prioritizes_clickable(self):
        snapshot = parse_ui_xml(SAMPLE_XML)
        matches = find_nodes(snapshot.nodes, "搜索")
        self.assertEqual(matches[0].text_value, "搜索")
        self.assertTrue(matches[0].clickable)

    def test_get_node(self):
        snapshot = parse_ui_xml(SAMPLE_XML)
        node = get_node(snapshot.nodes, 1)
        self.assertEqual(node.text_value, "搜索")
        self.assertIsNone(get_node(snapshot.nodes, 99))

    def test_comment_candidates_filters_controls(self):
        snapshot = parse_ui_xml(SAMPLE_XML)
        comments = comment_candidates(snapshot.nodes)
        self.assertEqual(comments[0]["text"], "这条笔记真的很有用")
        self.assertNotIn("点赞", [item["text"] for item in comments])


if __name__ == "__main__":
    unittest.main()
