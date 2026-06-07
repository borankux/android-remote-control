from typing import Optional
import hmac

from .agent import CloudPhoneOperator
from .audit import JsonlAuditLogger
from .config import OperatorConfig
from .executor import ToolExecutor
from .tools import CloudPhoneTools


def create_app(
    config: Optional[OperatorConfig] = None,
    executor: Optional[ToolExecutor] = None,
):
    try:
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.middleware.cors import CORSMiddleware
        from pydantic import BaseModel
    except Exception as error:
        raise RuntimeError("fastapi_not_installed") from error

    cfg = config or OperatorConfig.from_env(require_token=False)
    toolkit = CloudPhoneTools(cfg)
    runner = executor or ToolExecutor(toolkit)
    operator = CloudPhoneOperator(runner, cfg)
    audit = runner.audit_logger
    app = FastAPI(title="Cloud Phone Operator", version="0.10.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["content-type", "x-operator-token"],
    )

    class RunRequest(BaseModel):
        message: str
        deviceId: Optional[str] = None

    def authorize(request: Request) -> None:
        expected = cfg.operator_access_token
        if not expected:
            return
        provided = request.headers.get("x-operator-token") or request.query_params.get("operatorToken") or ""
        if not provided or not hmac.compare_digest(str(provided), str(expected)):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/health")
    def health(request: Request):
        authorize(request)
        return {"ok": True, "service": "cloudphone-operator", "config": cfg.safe_dict()}

    @app.get("/devices")
    def devices(request: Request):
        authorize(request)
        return runner.run("list_devices", {}).to_dict()

    @app.get("/actions")
    def actions(request: Request, limit: int = 20):
        authorize(request)
        return {"ok": True, "actions": audit.tail(limit)}

    @app.post("/run")
    def run(payload: RunRequest, request: Request):
        authorize(request)
        return operator.run(payload.message, device_id=payload.deviceId)

    return app
