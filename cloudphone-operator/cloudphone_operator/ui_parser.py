import hashlib
import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


BOUNDS_PATTERN = re.compile(r"^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$")
COMMENT_MIN_LEN = 2
DEFAULT_NODE_LIMIT = 50


@dataclass
class Bounds:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def center(self) -> Tuple[int, int]:
        return (int((self.left + self.right) / 2), int((self.top + self.bottom) / 2))

    def to_list(self) -> List[int]:
        return [self.left, self.top, self.right, self.bottom]


@dataclass
class UiNode:
    node_id: int
    text: str
    content_description: str
    class_name: str
    resource_id: str
    package_name: str
    bounds: Optional[Bounds]
    clickable: bool
    enabled: bool

    @property
    def text_value(self) -> str:
        return (self.text or self.content_description or "").strip()

    @property
    def center(self) -> Optional[Tuple[int, int]]:
        return self.bounds.center if self.bounds else None

    def matches_text(self, query: str, mode: str = "contains") -> bool:
        haystack = self.text_value
        if mode == "exact":
            return haystack == query
        return query in haystack

    def compact(self) -> Dict[str, object]:
        center = self.center
        return {
            "nodeId": self.node_id,
            "text": self.text,
            "contentDescription": self.content_description,
            "className": self.class_name,
            "resourceId": self.resource_id,
            "bounds": self.bounds.to_list() if self.bounds else None,
            "center": list(center) if center else None,
            "clickable": self.clickable,
            "enabled": self.enabled,
        }


@dataclass
class UiSnapshot:
    snapshot_id: str
    nodes: List[UiNode]

    def visible_texts(self, limit: int = 30) -> List[str]:
        return read_texts(self.nodes, limit=limit)

    def compact(self, node_limit: int = DEFAULT_NODE_LIMIT, text_limit: int = 30) -> Dict[str, object]:
        actionable = [node for node in self.nodes if node.text_value and (node.clickable or node.center)]
        return {
            "snapshotId": self.snapshot_id,
            "nodeCount": len(self.nodes),
            "visibleTexts": self.visible_texts(limit=text_limit),
            "nodes": [node.compact() for node in actionable[:node_limit]],
        }


def parse_ui_xml(xml: str) -> UiSnapshot:
    xml = xml or ""
    snapshot_id = hashlib.sha1(xml.encode("utf-8", errors="ignore")).hexdigest()[:12]
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return UiSnapshot(snapshot_id=snapshot_id, nodes=[])

    nodes: List[UiNode] = []
    for element in root.iter():
        if element.tag != "node":
            continue
        node = UiNode(
            node_id=len(nodes),
            text=_attr(element, "text"),
            content_description=_attr(element, "content-desc"),
            class_name=_attr(element, "class"),
            resource_id=_attr(element, "resource-id"),
            package_name=_attr(element, "package"),
            bounds=parse_bounds(_attr(element, "bounds")),
            clickable=_bool_attr(element, "clickable"),
            enabled=_bool_attr(element, "enabled", default=True),
        )
        nodes.append(node)
    return UiSnapshot(snapshot_id=snapshot_id, nodes=nodes)


def parse_bounds(value: str) -> Optional[Bounds]:
    match = BOUNDS_PATTERN.match(value or "")
    if not match:
        return None
    left, top, right, bottom = [int(part) for part in match.groups()]
    if right < left or bottom < top:
        return None
    return Bounds(left=left, top=top, right=right, bottom=bottom)


def find_nodes(nodes: List[UiNode], query: str, mode: str = "contains", limit: int = 10) -> List[UiNode]:
    query = (query or "").strip()
    if not query:
        return []
    exact_first = sorted(
        [node for node in nodes if node.matches_text(query, mode=mode)],
        key=lambda node: (not node.clickable, node.node_id),
    )
    return exact_first[: max(1, limit)]


def get_node(nodes: List[UiNode], node_id: int) -> Optional[UiNode]:
    for node in nodes:
        if node.node_id == node_id:
            return node
    return None


def read_texts(nodes: List[UiNode], limit: int = 30) -> List[str]:
    output: List[str] = []
    seen = set()
    for node in nodes:
        value = node.text_value
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value[:120])
        if len(output) >= limit:
            break
    return output


def comment_candidates(nodes: List[UiNode], limit: int = 20) -> List[Dict[str, object]]:
    candidates = []
    seen = set()
    for node in nodes:
        value = node.text_value
        if not _looks_like_comment(value) or value in seen:
            continue
        seen.add(value)
        candidates.append({
            "nodeId": node.node_id,
            "text": value[:180],
            "center": list(node.center) if node.center else None,
            "confidence": _comment_confidence(value),
        })
        if len(candidates) >= limit:
            break
    return candidates


def _looks_like_comment(value: str) -> bool:
    text = (value or "").strip()
    if len(text) < COMMENT_MIN_LEN:
        return False
    if text in {"关注", "点赞", "评论", "分享", "收藏", "搜索", "首页", "消息", "我"}:
        return False
    if re.fullmatch(r"\d+[万wW]?", text):
        return False
    return any(ch.isalpha() or "\u4e00" <= ch <= "\u9fff" for ch in text)


def _comment_confidence(value: str) -> float:
    length = len(value)
    if length >= 12:
        return 0.82
    if length >= 5:
        return 0.66
    return 0.45


def _attr(element: ET.Element, name: str) -> str:
    return html.unescape(element.attrib.get(name, "") or "").strip()


def _bool_attr(element: ET.Element, name: str, default: bool = False) -> bool:
    value = element.attrib.get(name)
    if value is None:
        return default
    return str(value).lower() == "true"
