import dataclasses
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _camel_duration(payload: Dict[str, Any], duration_ms: int) -> Dict[str, Any]:
    output = dict(payload)
    output["durationMs"] = duration_ms
    output.pop("duration_ms", None)
    return output


@dataclass
class CommandResult:
    id: str
    device_id: str
    name: str
    status: str
    error: Optional[str] = None
    result: Any = None
    duration_ms: int = 0

    @classmethod
    def from_command(cls, command: Dict[str, Any], duration_ms: int = 0) -> "CommandResult":
        return cls(
            id=str(command.get("id") or ""),
            device_id=str(command.get("deviceId") or command.get("device_id") or ""),
            name=str(command.get("name") or ""),
            status=str(command.get("status") or ""),
            error=command.get("error"),
            result=command.get("result"),
            duration_ms=duration_ms,
        )

    def to_dict(self) -> dict:
        return _camel_duration(dataclasses.asdict(self), self.duration_ms)


@dataclass
class ToolResult:
    ok: bool
    error: Optional[str] = None
    duration_ms: int = 0
    summary: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(cls, summary: str, data: Optional[Dict[str, Any]] = None, duration_ms: int = 0) -> "ToolResult":
        return cls(ok=True, error=None, duration_ms=duration_ms, summary=summary, data=data or {})

    @classmethod
    def failure(cls, error: str, summary: Optional[str] = None, data: Optional[Dict[str, Any]] = None, duration_ms: int = 0) -> "ToolResult":
        return cls(ok=False, error=error, duration_ms=duration_ms, summary=summary or error, data=data or {})

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "error": self.error,
            "durationMs": self.duration_ms,
            "summary": self.summary,
            "data": self.data,
        }


@dataclass
class ActionLogEntry:
    time: str
    tool: str
    device_id: str
    args_summary: Dict[str, Any]
    ok: bool
    error: Optional[str]
    duration_ms: int
    summary: str

    def to_dict(self) -> dict:
        return {
            "time": self.time,
            "tool": self.tool,
            "deviceId": self.device_id,
            "argsSummary": self.args_summary,
            "ok": self.ok,
            "error": self.error,
            "durationMs": self.duration_ms,
            "summary": self.summary,
        }


@dataclass
class Observation:
    device_id: str
    online: bool
    root_available: Optional[bool] = None
    foreground: Optional[str] = None
    screenshot: Dict[str, Any] = field(default_factory=dict)
    ui_snippets: List[str] = field(default_factory=list)
    ui_char_count: int = 0

    def to_dict(self) -> dict:
        return {
            "deviceId": self.device_id,
            "online": self.online,
            "rootAvailable": self.root_available,
            "foreground": self.foreground,
            "screenshot": self.screenshot,
            "uiSnippets": self.ui_snippets,
            "uiCharCount": self.ui_char_count,
        }
