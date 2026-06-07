import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .schemas import ActionLogEntry, ToolResult, now_iso


DEFAULT_AUDIT_PATH = Path(__file__).resolve().parents[1] / ".operator" / "action-log.jsonl"
SENSITIVE_KEY_PARTS = ("token", "api_key", "apikey", "base64", "xml")


def sanitize(value: Any, key: str = "") -> Any:
    lowered = key.lower()
    if any(part in lowered for part in SENSITIVE_KEY_PARTS):
        return "[redacted]"
    if isinstance(value, dict):
        return {str(k): sanitize(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(item, key) for item in value]
    if isinstance(value, str) and len(value) > 800:
        return value[:797] + "..."
    return value


class JsonlAuditLogger:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else DEFAULT_AUDIT_PATH

    def log(self, tool: str, device_id: str, args: Dict[str, Any], result: ToolResult) -> None:
        entry = ActionLogEntry(
            time=now_iso(),
            tool=tool,
            device_id=device_id,
            args_summary=sanitize(args or {}),
            ok=result.ok,
            error=result.error,
            duration_ms=result.duration_ms,
            summary=result.summary,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

    def tail(self, limit: int = 20) -> List[dict]:
        if not self.path.exists():
            return []
        lines = _tail_lines(self.path, max(1, limit))
        output = []
        for line in lines:
            try:
                output.append(json.loads(line))
            except json.JSONDecodeError:
                output.append({"malformed": line})
        return output


def _tail_lines(path: Path, limit: int) -> Iterable[str]:
    with path.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()
    return [line.rstrip("\n") for line in lines[-limit:]]
