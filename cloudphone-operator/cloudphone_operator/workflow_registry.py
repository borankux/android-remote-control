from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .executor import ToolExecutor


ArgsBuilder = Callable[[str], Dict[str, object]]
Trigger = Callable[[str], bool]


@dataclass(frozen=True)
class WorkflowStep:
    tool: str
    args: Dict[str, object] = field(default_factory=dict)
    include_in_actions: bool = False
    args_builder: Optional[ArgsBuilder] = None

    def build_args(self, message: str, device_id: Optional[str] = None) -> Dict[str, object]:
        payload = dict(self.args_builder(message) if self.args_builder else self.args)
        if device_id:
            payload["deviceId"] = device_id
        return payload


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    description: str
    triggers: List[Trigger]
    steps: List[WorkflowStep]
    success_summary: str
    failure_summary: str
    risk_level: str = "low"
    requires_confirmation: bool = False

    def matches(self, message: str) -> bool:
        normalized = normalize_message(message)
        return any(trigger(normalized) for trigger in self.triggers)


def normalize_message(message: str) -> str:
    return (message or "").strip().lower()


def match_workflow(message: str) -> Optional[WorkflowDefinition]:
    for workflow in WORKFLOWS:
        if workflow.matches(message):
            return workflow
    return None


def execute_workflow(
    executor: ToolExecutor,
    workflow: WorkflowDefinition,
    message: str,
    device_id: Optional[str] = None,
) -> dict:
    events = []
    actions = []
    for step in workflow.steps:
        result = executor.run(step.tool, step.build_args(message, device_id=device_id))
        event = event_from_result(step.tool, result)
        events.append(event)
        if step.include_in_actions:
            actions.append(event)

    ok = all(event["ok"] for event in events)
    return {
        "ok": ok,
        "summary": workflow.success_summary if ok else workflow.failure_summary,
        "workflow": workflow.name,
        "events": events,
        "actions": actions,
    }


def event_from_result(name: str, result) -> dict:
    payload = result.to_dict()
    return {
        "tool": name,
        "ok": payload["ok"],
        "error": payload["error"],
        "durationMs": payload["durationMs"],
        "summary": payload["summary"],
        "data": payload["data"],
    }


def workflow_capabilities() -> List[str]:
    return [
        "列出设备",
        "检查设备是否可控",
        "打开小红书并截图确认",
        "观察设备状态、截图摘要和 UI 文本",
        "读取当前页面文本",
        "点击包含指定文本的节点",
        "读取当前页面疑似评论",
    ]


def _contains_any(*needles: str) -> Trigger:
    return lambda message: any(needle in message for needle in needles)


def _tap_text_args(message: str) -> Dict[str, object]:
    text = extract_tap_text(message)
    return {"text": text}


def extract_tap_text(message: str) -> str:
    text = (message or "").strip()
    if text.startswith("点击"):
        text = text[2:].strip()
    for suffix in ("按钮", "节点", "文本"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    return text[:80]


def _wants_tap_text(message: str) -> bool:
    return message.startswith("点击") and len(extract_tap_text(message)) > 0


WORKFLOWS: List[WorkflowDefinition] = [
    WorkflowDefinition(
        name="read_comments",
        description="读取当前页面疑似评论",
        triggers=[_contains_any("评论", "read comments")],
        steps=[WorkflowStep("read_comments")],
        success_summary="已读取当前页面疑似评论",
        failure_summary="读取评论失败",
    ),
    WorkflowDefinition(
        name="tap_text",
        description="点击包含指定文本的节点",
        triggers=[_wants_tap_text],
        steps=[WorkflowStep("tap_text", args_builder=_tap_text_args, include_in_actions=True)],
        success_summary="已按文本点击",
        failure_summary="按文本点击失败",
        risk_level="medium",
    ),
    WorkflowDefinition(
        name="read_screen",
        description="读取当前页面文本",
        triggers=[_contains_any("读取当前页面", "页面文本", "读页面", "read screen")],
        steps=[WorkflowStep("read_screen")],
        success_summary="已读取当前页面文本",
        failure_summary="读取当前页面失败",
    ),
    WorkflowDefinition(
        name="open_xhs",
        description="打开小红书并观察画面",
        triggers=[_contains_any("小红书", "xhs", "xingin")],
        steps=[
            WorkflowStep("get_device_status"),
            WorkflowStep("launch_xhs", include_in_actions=True),
            WorkflowStep("observe_device"),
        ],
        success_summary="已执行打开小红书并观察画面",
        failure_summary="打开小红书流程未完全成功",
        risk_level="medium",
    ),
    WorkflowDefinition(
        name="device_check",
        description="检查设备是否可控",
        triggers=[_contains_any("检查", "可控", "状态", "observe")],
        steps=[
            WorkflowStep("list_devices"),
            WorkflowStep("get_device_status"),
            WorkflowStep("observe_device", include_in_actions=True),
        ],
        success_summary="设备可控性检查完成",
        failure_summary="设备可控性检查未完全通过",
    ),
]
