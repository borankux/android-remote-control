from typing import Any, Dict, List, Optional, Tuple

from .config import OperatorConfig
from .executor import ToolExecutor
from .workflow_registry import execute_workflow, match_workflow, workflow_capabilities


class CloudPhoneOperator:
    """Deterministic operator workflows with optional Agno integration outside the hot path."""

    def __init__(self, executor: ToolExecutor, config: Optional[OperatorConfig] = None):
        self.executor = executor
        self.config = config or executor.toolkit.config

    def run(self, message: str, device_id: Optional[str] = None) -> dict:
        message = (message or "").strip()
        normalized = message.lower()
        if _looks_like_help(normalized):
            return self._capabilities()
        workflow = match_workflow(message)
        if workflow:
            return execute_workflow(self.executor, workflow, message, device_id=device_id)
        return self._capabilities(prefix="我可以执行设备检查、打开小红书、截图观察和读取 UI。")

    def _capabilities(self, prefix: str = "Cloud Phone Operator 已就绪。") -> dict:
        return {
            "ok": True,
            "summary": prefix,
            "events": [],
            "actions": [],
            "capabilities": workflow_capabilities(),
        }


def create_agno_agent(executor: ToolExecutor, config: Optional[OperatorConfig] = None) -> Tuple[Any, Optional[str]]:
    cfg = config or executor.toolkit.config
    if not cfg.operator_model:
        return None, "model_not_configured"
    try:
        from agno.agent import Agent  # type: ignore
    except Exception:
        return None, "agno_not_installed"

    def list_devices() -> dict:
        return executor.run("list_devices", {}).to_dict()

    def observe_device() -> dict:
        return executor.run("observe_device", {}).to_dict()

    def launch_xhs() -> dict:
        return executor.run("launch_xhs", {}).to_dict()

    agent = Agent(
        name="Cloud Phone Operator",
        instructions=[
            "你是 Cloud Phone Operator，只能通过注册工具控制设备。",
            "必须先观察再行动，每次动作后必须验证。",
            "禁止任意 shell、任意 ADB 命令和任意包名启动。",
            "工具失败时必须说明 error，不得伪造成功。",
        ],
        tools=[list_devices, observe_device, launch_xhs],
    )
    return agent, None


def _looks_like_help(message: str) -> bool:
    return not message or "帮助" in message or "help" in message or "能做什么" in message
