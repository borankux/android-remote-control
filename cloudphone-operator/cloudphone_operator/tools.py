import html
import re
import time
from typing import Any, Dict, List, Optional

from .config import OperatorConfig
from .relay_client import RelayClient
from .schemas import Observation, ToolResult
from .ui_parser import comment_candidates, find_nodes, get_node, parse_ui_xml, read_texts


TEXT_ATTR_PATTERN = re.compile(r'\btext="([^"]+)"')


class CloudPhoneTools:
    def __init__(self, config: OperatorConfig, client: Optional[RelayClient] = None):
        self.config = config
        self.client = client or RelayClient(config)

    def run(self, name: str, args: Optional[Dict[str, Any]] = None) -> ToolResult:
        args = args or {}
        method = getattr(self, name, None)
        if not method:
            return ToolResult.failure("tool_not_found", "工具不存在: %s" % name)
        return method(args)

    def list_devices(self, args: Dict[str, Any]) -> ToolResult:
        started = time.monotonic()
        devices = self.client.list_devices()
        duration_ms = _elapsed_ms(started)
        online_count = sum(1 for device in devices if device.get("online"))
        return ToolResult.success(
            "找到 %s 台设备，%s 台在线" % (len(devices), online_count),
            {"devices": devices, "count": len(devices), "onlineCount": online_count},
            duration_ms=duration_ms,
        )

    def get_device_status(self, args: Dict[str, Any]) -> ToolResult:
        started = time.monotonic()
        device_id = self._device_id(args)
        devices = self.client.list_devices()
        device = _find_device(devices, device_id)
        duration_ms = _elapsed_ms(started)
        if not device:
            return ToolResult.failure(
                "device_not_found",
                "设备未注册或不可见: %s" % device_id,
                {"deviceId": device_id, "devices": devices},
                duration_ms=duration_ms,
            )
        summary = "%s，%s" % (
            "Relay 在线" if device.get("online") else "Relay 离线",
            _device_label(device),
        )
        return ToolResult.success(summary, {"device": _summarize_device(device)}, duration_ms=duration_ms)

    def observe_device(self, args: Dict[str, Any]) -> ToolResult:
        started = time.monotonic()
        device_id = self._device_id(args)
        status = self.get_device_status({"deviceId": device_id})
        if not status.ok:
            return status

        snapshot_result = self._send("snapshot", {}, "已读取设备状态快照", device_id=device_id, timeout_ms=10000)
        include_screenshot = args.get("includeScreenshot", True)
        include_ui = args.get("includeUi", True)
        screenshot_summary: Dict[str, Any] = {}
        ui_snippets: List[str] = []
        ui_char_count = 0

        if include_screenshot:
            screen = self._send(
                "screencap",
                {
                    "format": args.get("format", "jpeg"),
                    "maxWidth": int(args.get("maxWidth", 540)),
                    "quality": int(args.get("quality", 65)),
                },
                "已截取设备画面",
                device_id=device_id,
                timeout_ms=30000,
            )
            screen_data = screen.data.get("result") if isinstance(screen.data.get("result"), dict) else screen.data
            screenshot_summary = {
                "ok": screen.ok,
                "error": screen.error,
                "mimeType": screen_data.get("mimeType") if isinstance(screen_data, dict) else None,
                "byteCount": screen_data.get("byteCount") if isinstance(screen_data, dict) else None,
                "format": screen_data.get("format") if isinstance(screen_data, dict) else None,
            }

        if include_ui:
            ui = self._send("dump_ui", {}, "已读取 UI 树", device_id=device_id, timeout_ms=30000)
            ui_data = ui.data.get("result") if isinstance(ui.data.get("result"), dict) else ui.data
            xml = ""
            if isinstance(ui_data, dict):
                xml = str(ui_data.get("xml") or "")
                ui_char_count = int(ui_data.get("charCount") or len(xml))
            ui_snippets = extract_ui_snippets(xml)

        snapshot_data = snapshot_result.data.get("result") if isinstance(snapshot_result.data.get("result"), dict) else snapshot_result.data
        foreground = None
        root_available = None
        if isinstance(snapshot_data, dict):
            foreground = snapshot_data.get("foreground") or snapshot_data.get("foregroundPackage") or snapshot_data.get("topActivity")
            root_available = snapshot_data.get("rootAvailable")

        observation = Observation(
            device_id=device_id,
            online=True,
            root_available=root_available,
            foreground=foreground,
            screenshot=screenshot_summary,
            ui_snippets=ui_snippets,
            ui_char_count=ui_char_count,
        )
        duration_ms = _elapsed_ms(started)
        return ToolResult.success(
            "观察完成：截图 %s，UI 文本 %s 条" % (
                "可用" if screenshot_summary.get("ok", False) else "不可用",
                len(ui_snippets),
            ),
            {
                "observation": observation.to_dict(),
                "status": status.data,
                "snapshot": snapshot_data if isinstance(snapshot_data, dict) else {},
            },
            duration_ms=duration_ms,
        )

    def screencap(self, args: Dict[str, Any]) -> ToolResult:
        params = {
            "format": args.get("format", "jpeg"),
            "maxWidth": int(args.get("maxWidth", 540)),
            "quality": int(args.get("quality", 65)),
        }
        return self._send("screencap", params, "已截取设备画面", device_id=self._device_id(args), timeout_ms=30000)

    def dump_ui(self, args: Dict[str, Any]) -> ToolResult:
        return self._send("dump_ui", {}, "已读取 UI 树", device_id=self._device_id(args), timeout_ms=30000)

    def ui_snapshot(self, args: Dict[str, Any]) -> ToolResult:
        parsed = self._parsed_ui(args)
        if not parsed["ok"]:
            return parsed["result"]
        snapshot = parsed["snapshot"]
        limit = int(args.get("limit", 50))
        compact = snapshot.compact(node_limit=limit, text_limit=min(limit, 50))
        return ToolResult.success(
            "UI 快照完成：%s 个节点，%s 条文本" % (compact["nodeCount"], len(compact["visibleTexts"])),
            {"ui": compact},
            duration_ms=parsed["durationMs"],
        )

    def read_screen(self, args: Dict[str, Any]) -> ToolResult:
        parsed = self._parsed_ui(args)
        if not parsed["ok"]:
            return parsed["result"]
        snapshot = parsed["snapshot"]
        limit = int(args.get("limit", 30))
        texts = read_texts(snapshot.nodes, limit=limit)
        compact = snapshot.compact(node_limit=min(limit, 50), text_limit=limit)
        return ToolResult.success(
            "当前页面读取完成：%s 条可见文本" % len(texts),
            {"snapshotId": snapshot.snapshot_id, "visibleTexts": texts, "nodes": compact["nodes"]},
            duration_ms=parsed["durationMs"],
        )

    def read_ui_texts(self, args: Dict[str, Any]) -> ToolResult:
        return self.read_screen(args)

    def find_text(self, args: Dict[str, Any]) -> ToolResult:
        parsed = self._parsed_ui(args)
        if not parsed["ok"]:
            return parsed["result"]
        text = str(args.get("text") or "")
        mode = str(args.get("mode") or "contains")
        limit = int(args.get("limit", 10))
        matches = find_nodes(parsed["snapshot"].nodes, text, mode=mode, limit=limit)
        return ToolResult.success(
            "找到 %s 个匹配「%s」的节点" % (len(matches), text),
            {
                "snapshotId": parsed["snapshot"].snapshot_id,
                "query": text,
                "mode": mode,
                "matches": [node.compact() for node in matches],
            },
            duration_ms=parsed["durationMs"],
        )

    def read_comments(self, args: Dict[str, Any]) -> ToolResult:
        parsed = self._parsed_ui(args)
        if not parsed["ok"]:
            return parsed["result"]
        limit = int(args.get("limit", 20))
        comments = comment_candidates(parsed["snapshot"].nodes, limit=limit)
        return ToolResult.success(
            "读取到 %s 条疑似评论" % len(comments),
            {"snapshotId": parsed["snapshot"].snapshot_id, "comments": comments},
            duration_ms=parsed["durationMs"],
        )

    def tap(self, args: Dict[str, Any]) -> ToolResult:
        return self._send("tap", {"x": int(args["x"]), "y": int(args["y"])}, "已点击 (%s,%s)" % (args["x"], args["y"]), device_id=self._device_id(args))

    def tap_text(self, args: Dict[str, Any]) -> ToolResult:
        parsed = self._parsed_ui(args)
        if not parsed["ok"]:
            return parsed["result"]
        text = str(args.get("text") or "")
        mode = str(args.get("mode") or "contains")
        matches = find_nodes(parsed["snapshot"].nodes, text, mode=mode, limit=1)
        if not matches:
            return ToolResult.failure(
                "text_not_found",
                "未找到可点击文本：%s" % text,
                {"snapshotId": parsed["snapshot"].snapshot_id, "query": text, "matches": []},
                duration_ms=parsed["durationMs"],
            )
        node = matches[0]
        if not node.center:
            return ToolResult.failure(
                "node_without_bounds",
                "匹配节点没有 bounds，无法点击",
                {"snapshotId": parsed["snapshot"].snapshot_id, "node": node.compact()},
                duration_ms=parsed["durationMs"],
            )
        x, y = node.center
        tapped = self._send("tap", {"x": x, "y": y}, "已点击文本：%s" % text, device_id=self._device_id(args))
        tapped.data["snapshotId"] = parsed["snapshot"].snapshot_id
        tapped.data["node"] = node.compact()
        return tapped

    def tap_node(self, args: Dict[str, Any]) -> ToolResult:
        parsed = self._parsed_ui(args)
        if not parsed["ok"]:
            return parsed["result"]
        node_id = int(args.get("nodeId"))
        node = get_node(parsed["snapshot"].nodes, node_id)
        if not node:
            return ToolResult.failure(
                "node_not_found",
                "未找到节点：%s" % node_id,
                {"snapshotId": parsed["snapshot"].snapshot_id, "nodeId": node_id},
                duration_ms=parsed["durationMs"],
            )
        if not node.center:
            return ToolResult.failure(
                "node_without_bounds",
                "节点没有 bounds，无法点击",
                {"snapshotId": parsed["snapshot"].snapshot_id, "node": node.compact()},
                duration_ms=parsed["durationMs"],
            )
        x, y = node.center
        tapped = self._send("tap", {"x": x, "y": y}, "已点击节点：%s" % node_id, device_id=self._device_id(args))
        tapped.data["snapshotId"] = parsed["snapshot"].snapshot_id
        tapped.data["node"] = node.compact()
        return tapped

    def swipe(self, args: Dict[str, Any]) -> ToolResult:
        params = {
            "x1": int(args["x1"]),
            "y1": int(args["y1"]),
            "x2": int(args["x2"]),
            "y2": int(args["y2"]),
            "durationMs": int(args.get("durationMs", 300)),
        }
        return self._send("swipe", params, "已滑动", device_id=self._device_id(args))

    def input_text(self, args: Dict[str, Any]) -> ToolResult:
        text = str(args.get("text") or "")
        return self._send("input_text", {"text": text}, "已输入文本：%s" % _short(text, 24), device_id=self._device_id(args))

    def back(self, args: Dict[str, Any]) -> ToolResult:
        return self._send("back", {}, "已返回", device_id=self._device_id(args))

    def home(self, args: Dict[str, Any]) -> ToolResult:
        return self._send("home", {}, "已回到桌面", device_id=self._device_id(args))

    def launch_xhs(self, args: Dict[str, Any]) -> ToolResult:
        return self._send("launch_xhs", {}, "已请求启动小红书", device_id=self._device_id(args), timeout_ms=15000)

    def wait_for_text(self, args: Dict[str, Any]) -> ToolResult:
        params = {
            "text": str(args.get("text") or ""),
            "timeoutMs": int(args.get("timeoutMs", 5000)),
            "intervalMs": int(args.get("intervalMs", 500)),
        }
        return self._send("wait_for_text", params, "已等待文本：%s" % _short(params["text"], 24), device_id=self._device_id(args), timeout_ms=params["timeoutMs"] + 5000)

    def _send(self, relay_name: str, params: Dict[str, Any], summary: str, device_id: Optional[str] = None, timeout_ms: int = 30000) -> ToolResult:
        started = time.monotonic()
        command = self.client.send_command(device_id or self.config.device_id, relay_name, params, timeout_ms=timeout_ms)
        duration_ms = _elapsed_ms(started)
        return command_to_tool_result(command, summary, duration_ms)

    def _parsed_ui(self, args: Dict[str, Any]) -> Dict[str, Any]:
        started = time.monotonic()
        ui = self._send("dump_ui", {}, "已读取 UI 树", device_id=self._device_id(args), timeout_ms=30000)
        duration_ms = _elapsed_ms(started)
        if not ui.ok:
            return {"ok": False, "result": ui, "durationMs": duration_ms}
        ui_data = ui.data.get("result") if isinstance(ui.data.get("result"), dict) else ui.data
        xml = str(ui_data.get("xml") or "") if isinstance(ui_data, dict) else ""
        snapshot = parse_ui_xml(xml)
        return {"ok": True, "snapshot": snapshot, "durationMs": duration_ms}

    def _device_id(self, args: Dict[str, Any]) -> str:
        return str(args.get("deviceId") or self.config.device_id)


def command_to_tool_result(command: Dict[str, Any], summary: str, duration_ms: int) -> ToolResult:
    status = command.get("status")
    if status == "offline":
        return ToolResult.failure("device_not_online", "设备不在线", {"command": command}, duration_ms)
    if status != "completed":
        return ToolResult.failure(command.get("error") or str(status or "command_failed"), "命令失败", {"command": command}, duration_ms)

    result = command.get("result")
    if isinstance(result, dict) and result.get("ok") is False:
        return ToolResult.failure(str(result.get("error") or "command_failed"), "命令返回失败", {"command": command, "result": result}, duration_ms)
    return ToolResult.success(summary, {"command": command, "result": result or {}}, duration_ms)


def extract_ui_snippets(xml: str, limit: int = 12) -> List[str]:
    snippets = []
    seen = set()
    for match in TEXT_ATTR_PATTERN.finditer(xml or ""):
        text = html.unescape(match.group(1)).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        snippets.append(_short(text, 80))
        if len(snippets) >= limit:
            break
    return snippets


def _find_device(devices: List[Dict[str, Any]], device_id: str) -> Optional[Dict[str, Any]]:
    for device in devices:
        if str(device.get("deviceId")) == device_id:
            return device
    if device_id == "demo-device-id" and devices:
        return devices[0]
    return None


def _summarize_device(device: Dict[str, Any]) -> Dict[str, Any]:
    hello = device.get("hello") or {}
    report = hello.get("report") or {}
    system = report.get("system") or {}
    root = report.get("root") or {}
    return {
        "deviceId": device.get("deviceId"),
        "online": device.get("online"),
        "lastSeenAt": device.get("lastSeenAt"),
        "remoteAddress": device.get("remoteAddress"),
        "appVersion": hello.get("appVersion") or report.get("appVersion"),
        "model": system.get("model") or hello.get("model"),
        "manufacturer": system.get("manufacturer"),
        "androidVersion": system.get("androidVersion") or hello.get("androidVersion"),
        "sdkInt": system.get("sdkInt") or hello.get("sdkInt"),
        "rootAvailable": root.get("available") if isinstance(root, dict) else None,
    }


def _device_label(device: Dict[str, Any]) -> str:
    summary = _summarize_device(device)
    parts = [str(summary.get("model") or summary.get("deviceId") or "unknown")]
    if summary.get("androidVersion"):
        parts.append("Android %s" % summary["androidVersion"])
    if summary.get("sdkInt"):
        parts.append("SDK %s" % summary["sdkInt"])
    return " / ".join(parts)


def _short(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
