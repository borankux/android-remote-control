import time
from typing import Any, Dict, Optional

from .audit import JsonlAuditLogger
from .policy import PolicyViolation, is_write_tool, validate_tool
from .relay_client import RelayError
from .schemas import ToolResult
from .tools import CloudPhoneTools


class ToolExecutor:
    def __init__(
        self,
        toolkit: CloudPhoneTools,
        audit_logger: Optional[JsonlAuditLogger] = None,
    ):
        self.toolkit = toolkit
        self.audit_logger = audit_logger or JsonlAuditLogger()

    def run(self, name: str, args: Optional[Dict[str, Any]] = None) -> ToolResult:
        args = args or {}
        started = time.monotonic()
        try:
            validate_tool(name, args)
            result = self.toolkit.run(name, args)
        except PolicyViolation as error:
            result = ToolResult.failure(error.code, str(error), duration_ms=_elapsed_ms(started))
        except RelayError as error:
            result = ToolResult.failure(error.code, str(error), {"detail": error.detail}, duration_ms=_elapsed_ms(started))
        except Exception as error:
            result = ToolResult.failure("tool_exception", str(error), duration_ms=_elapsed_ms(started))

        if is_write_tool(name):
            self.audit_logger.log(name, str(args.get("deviceId") or self.toolkit.config.device_id), args, result)
        return result


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
