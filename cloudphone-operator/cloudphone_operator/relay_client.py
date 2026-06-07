import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Optional, Tuple

from .config import ConfigError, OperatorConfig


Transport = Callable[[str, str, Dict[str, str], Optional[str], float], Tuple[int, str]]


class RelayError(Exception):
    """Relay request or command failed."""

    def __init__(self, code: str, message: Optional[str] = None, status: Optional[int] = None, detail: Any = None):
        super().__init__(message or code)
        self.code = code
        self.status = status
        self.detail = detail


class RelayClient:
    def __init__(
        self,
        config: OperatorConfig,
        timeout_seconds: float = 10.0,
        transport: Optional[Transport] = None,
        sleeper: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self.config = config
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self.sleeper = sleeper
        self.monotonic = monotonic

    def list_devices(self) -> list:
        payload = self._request_json("GET", "/devices")
        return payload.get("devices") or []

    def create_command(self, device_id: str, name: str, params: Optional[Dict[str, Any]] = None) -> dict:
        payload = self._request_json(
            "POST",
            "/commands",
            {"deviceId": device_id, "name": name, "params": params or {}},
        )
        return payload.get("command") or {}

    def get_command(self, command_id: str) -> dict:
        payload = self._request_json("GET", "/commands/%s" % urllib.parse.quote(command_id))
        return payload.get("command") or {}

    def wait_command(
        self,
        command_id: str,
        timeout_ms: int = 30000,
        poll_interval_ms: int = 500,
    ) -> dict:
        deadline = self.monotonic() + (timeout_ms / 1000.0)
        while self.monotonic() < deadline:
            command = self.get_command(command_id)
            status = command.get("status")
            if status in ("completed", "failed", "offline"):
                return command
            self.sleeper(poll_interval_ms / 1000.0)
        raise RelayError("command_timeout", "command timed out")

    def send_command(
        self,
        device_id: str,
        name: str,
        params: Optional[Dict[str, Any]] = None,
        timeout_ms: int = 30000,
    ) -> dict:
        created = self.create_command(device_id, name, params or {})
        if created.get("status") in ("completed", "failed", "offline"):
            return created
        return self.wait_command(str(created.get("id") or ""), timeout_ms=timeout_ms)

    def _request_json(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> dict:
        if not self.config.relay_token:
            raise RelayError("missing_relay_token", "CLOUDPHONE_RELAY_TOKEN is required")

        body_text = json.dumps(body).encode("utf-8").decode("utf-8") if body is not None else None
        headers = {
            "x-relay-token": self.config.relay_token,
            "content-type": "application/json",
        }
        if self.transport:
            status, text = self.transport(method, path, headers, body_text, self.timeout_seconds)
        else:
            status, text = self._urllib_request(method, path, headers, body_text)

        if status == 401:
            raise RelayError("unauthorized", "relay token is invalid", status=status)

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            raise RelayError("invalid_relay_response", "Relay returned invalid JSON", status=status, detail=text[:300])

        if status == 404:
            raise RelayError(payload.get("error") or "not_found", "Relay resource not found", status=status, detail=payload)

        if status >= 400 or payload.get("ok") is False:
            raise RelayError(payload.get("error") or "relay_error", status=status, detail=payload)

        return payload

    def _urllib_request(self, method: str, path: str, headers: Dict[str, str], body_text: Optional[str]) -> Tuple[int, str]:
        url = "%s%s" % (self.config.relay_url, path)
        data = body_text.encode("utf-8") if body_text is not None else None
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as error:
            reason = getattr(error, "reason", error)
            if isinstance(reason, TimeoutError):
                raise RelayError("relay_timeout", "Relay request timed out")
            raise RelayError("relay_unreachable", str(reason))
        except TimeoutError:
            raise RelayError("relay_timeout", "Relay request timed out")


def config_error_to_relay_error(error: ConfigError) -> RelayError:
    return RelayError(error.code, str(error))
