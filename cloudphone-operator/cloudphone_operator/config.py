import os
from dataclasses import dataclass
from typing import Mapping, Optional


DEFAULT_RELAY_URL = "https://relay.example.com/cloudphone-relay"
DEFAULT_DEVICE_ID = "demo-device-id"


class ConfigError(Exception):
    """Configuration is missing or invalid."""

    def __init__(self, code: str, message: Optional[str] = None):
        super().__init__(message or code)
        self.code = code


def _clean_url(value: Optional[str]) -> str:
    url = (value or DEFAULT_RELAY_URL).strip()
    return url.rstrip("/")


def _redact(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    if len(value) <= 8:
        return "***"
    return "%s...%s" % (value[:4], value[-4:])


@dataclass(frozen=True)
class OperatorConfig:
    relay_url: str = DEFAULT_RELAY_URL
    relay_token: str = ""
    device_id: str = DEFAULT_DEVICE_ID
    operator_model: Optional[str] = None
    operator_base_url: Optional[str] = None
    operator_api_key: Optional[str] = None
    operator_access_token: Optional[str] = None

    @classmethod
    def from_env(
        cls,
        environ: Optional[Mapping[str, str]] = None,
        require_token: bool = True,
    ) -> "OperatorConfig":
        env = environ or os.environ
        config = cls(
            relay_url=_clean_url(env.get("CLOUDPHONE_RELAY_URL")),
            relay_token=(env.get("CLOUDPHONE_RELAY_TOKEN") or "").strip(),
            device_id=(env.get("CLOUDPHONE_DEVICE_ID") or DEFAULT_DEVICE_ID).strip()
            or DEFAULT_DEVICE_ID,
            operator_model=(env.get("CLOUDPHONE_OPERATOR_MODEL") or "").strip() or None,
            operator_base_url=(env.get("CLOUDPHONE_OPERATOR_BASE_URL") or "").strip() or None,
            operator_api_key=(env.get("CLOUDPHONE_OPERATOR_API_KEY") or "").strip() or None,
            operator_access_token=(env.get("CLOUDPHONE_OPERATOR_TOKEN") or "").strip() or None,
        )
        if require_token and not config.relay_token:
            raise ConfigError("missing_relay_token", "CLOUDPHONE_RELAY_TOKEN is required")
        return config

    def safe_dict(self) -> dict:
        return {
            "relayUrl": self.relay_url,
            "relayToken": _redact(self.relay_token),
            "deviceId": self.device_id,
            "operatorModel": self.operator_model,
            "operatorBaseUrl": self.operator_base_url,
            "operatorApiKey": _redact(self.operator_api_key),
            "operatorAccessToken": _redact(self.operator_access_token),
        }

    def require_token(self) -> None:
        if not self.relay_token:
            raise ConfigError("missing_relay_token", "CLOUDPHONE_RELAY_TOKEN is required")
