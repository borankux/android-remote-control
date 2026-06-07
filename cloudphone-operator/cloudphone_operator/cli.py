import argparse
import json
import sys
from typing import Any, Dict, Optional

from .agent import CloudPhoneOperator
from .audit import JsonlAuditLogger
from .config import OperatorConfig
from .executor import ToolExecutor
from .tools import CloudPhoneTools


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0

    config = OperatorConfig.from_env(require_token=False)
    audit = JsonlAuditLogger()
    executor = ToolExecutor(CloudPhoneTools(config), audit)
    operator = CloudPhoneOperator(executor, config)

    if args.command == "config":
        _print(config.safe_dict())
        return 0

    if args.command == "devices":
        result = executor.run("list_devices", {})
        _print(result.to_dict())
        return 0 if result.ok else 1

    if args.command == "tool":
        tool_args = _parse_json(args.args_json)
        result = executor.run(args.name, tool_args)
        _print(result.to_dict())
        return 0 if result.ok else 1

    if args.command == "run":
        payload = operator.run(args.message, device_id=args.device_id)
        _print(payload)
        return 0 if payload.get("ok") else 1

    if args.command == "log":
        _print({"ok": True, "actions": audit.tail(args.limit)})
        return 0

    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cloudphone-operator")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("config", help="print token-safe config")
    sub.add_parser("devices", help="list registered devices")

    tool = sub.add_parser("tool", help="run one low-level tool")
    tool.add_argument("name")
    tool.add_argument("args_json", nargs="?", default="{}")

    run = sub.add_parser("run", help="run deterministic operator workflow")
    run.add_argument("message")
    run.add_argument("--device-id", default=None)

    log = sub.add_parser("log", help="show recent write actions")
    log.add_argument("--limit", type=int, default=20)

    return parser


def _parse_json(value: str) -> Dict[str, Any]:
    try:
        payload = json.loads(value or "{}")
    except json.JSONDecodeError as error:
        raise SystemExit("invalid JSON args: %s" % error)
    if not isinstance(payload, dict):
        raise SystemExit("args_json must be a JSON object")
    return payload


def _print(payload: Any) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
