import re
from typing import Any, Dict


READ_TOOLS = {
    "list_devices",
    "get_device_status",
    "observe_device",
    "screencap",
    "dump_ui",
    "ui_snapshot",
    "read_screen",
    "find_text",
    "read_ui_texts",
    "read_comments",
}

WRITE_TOOLS = {
    "tap",
    "tap_text",
    "tap_node",
    "swipe",
    "input_text",
    "back",
    "home",
    "launch_xhs",
    "wait_for_text",
}

ALLOWED_TOOLS = READ_TOOLS | WRITE_TOOLS
SCREENSHOT_FORMATS = {"png", "jpg", "jpeg", "webp"}
SHELL_LIKE_PATTERN = re.compile(r"(\n|\r|`|\$\(|&&|\|\||\b(?:su|sh|bash|adb)\b\s|-c\s|;)")


class PolicyViolation(ValueError):
    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.code = code


def is_write_tool(name: str) -> bool:
    return name in WRITE_TOOLS


def validate_tool(name: str, args: Dict[str, Any]) -> None:
    args = args or {}
    if name not in ALLOWED_TOOLS:
        raise PolicyViolation("tool_not_allowed", "tool is not allowed: %s" % name)
    if name == "screencap":
        _validate_screencap(args)
    elif name in ("find_text", "tap_text"):
        _validate_text_query(args)
    elif name == "tap_node":
        _int_arg(args, "nodeId", 0, 5000)
    elif name in ("ui_snapshot", "read_screen", "read_ui_texts", "read_comments"):
        _int_arg(args, "limit", 1, 100, default=30)
    elif name == "tap":
        _int_arg(args, "x", 0, 4096)
        _int_arg(args, "y", 0, 4096)
    elif name == "swipe":
        for key in ("x1", "y1", "x2", "y2"):
            _int_arg(args, key, 0, 4096)
        _int_arg(args, "durationMs", 50, 5000, default=300)
    elif name == "input_text":
        text = str(args.get("text") or "")
        if len(text) > 200:
            raise PolicyViolation("text_too_long", "input_text is limited to 200 characters")
        _reject_shell_like(text)
    elif name == "wait_for_text":
        text = str(args.get("text") or "")
        if not text or len(text) > 80:
            raise PolicyViolation("invalid_text", "wait_for_text requires 1-80 characters")
        _reject_shell_like(text)


def _validate_screencap(args: Dict[str, Any]) -> None:
    fmt = str(args.get("format") or "jpeg").lower()
    if fmt not in SCREENSHOT_FORMATS:
        raise PolicyViolation("invalid_screenshot_format", "unsupported screenshot format")
    _int_arg(args, "maxWidth", 0, 1440, default=540)
    _int_arg(args, "quality", 10, 100, default=65)


def _validate_text_query(args: Dict[str, Any]) -> None:
    text = str(args.get("text") or "")
    if not text or len(text) > 80:
        raise PolicyViolation("invalid_text", "text query requires 1-80 characters")
    _reject_shell_like(text)
    mode = str(args.get("mode") or "contains")
    if mode not in ("contains", "exact"):
        raise PolicyViolation("invalid_match_mode", "match mode must be contains or exact")
    _int_arg(args, "limit", 1, 20, default=10)


def _int_arg(args: Dict[str, Any], name: str, min_value: int, max_value: int, default: Any = None) -> int:
    raw = args.get(name, default)
    if raw is None:
        raise PolicyViolation("missing_%s" % name, "%s is required" % name)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise PolicyViolation("invalid_%s" % name, "%s must be an integer" % name)
    if value < min_value or value > max_value:
        raise PolicyViolation("%s_out_of_range" % name, "%s is out of range" % name)
    return value


def _reject_shell_like(text: str) -> None:
    if SHELL_LIKE_PATTERN.search(text):
        raise PolicyViolation("unsafe_text", "shell-like text is not allowed")
