# Cloud Phone Operator

Python Operator layer for the Android Remote Control project. It wraps the existing PB Relay API with deterministic policy checks, tool execution, audit logging, optional Agno integration, and an optional FastAPI API.

## Environment

```bash
export CLOUDPHONE_RELAY_URL="https://your-domain.example/cloudphone-relay"
export CLOUDPHONE_RELAY_TOKEN="your-relay-token"
export CLOUDPHONE_DEVICE_ID="your-device-id"
```

Optional model configuration:

```bash
export CLOUDPHONE_OPERATOR_MODEL="openai:gpt-4.1"
export CLOUDPHONE_OPERATOR_BASE_URL="https://api.openai.com/v1"
export CLOUDPHONE_OPERATOR_API_KEY="your-model-key"
export CLOUDPHONE_OPERATOR_TOKEN="optional-operator-api-token"
```

## CLI

```bash
PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator devices
PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator tool observe_device
PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator run "检查设备是否可控"
PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator run "打开小红书，截图确认"
PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator run "读取当前页面"
PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator run "点击搜索"
PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator run "读取评论"
PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator log
```

## Semantic UI Tools

The Operator does not send raw `dump_ui` XML into an Agent prompt. XML is parsed internally and converted into compact semantic observations:

```bash
PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator tool ui_snapshot '{"limit":30}'
PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator tool read_screen '{"limit":30}'
PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator tool find_text '{"text":"搜索","mode":"contains","limit":5}'
PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator tool tap_text '{"text":"搜索"}'
PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator tool tap_node '{"nodeId":3}'
PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator tool read_comments '{"limit":20}'
```

Semantic tool results return `snapshotId`, `nodeId`, visible texts, compact node fields, candidate centers, and confidence scores. They do not return the original XML.

## Workflow Registry

Deterministic natural-language workflows are registered in `cloudphone_operator/workflow_registry.py` instead of being hard-coded in the Agent. Built-in workflows include:

- `device_check`
- `open_xhs`
- `read_screen`
- `tap_text`
- `read_comments`

Each workflow declares triggers, steps, risk level, and whether its steps should appear in action logs. This keeps `agent.py` small and makes new workflows testable before they are exposed to an Agent.

## Operator API

Install the optional API dependencies, then start the local API:

```bash
cd cloudphone-operator
python3 -m pip install -e ".[api]"
CLOUDPHONE_RELAY_URL="https://your-domain.example/cloudphone-relay" \
CLOUDPHONE_RELAY_TOKEN="your-relay-token" \
CLOUDPHONE_DEVICE_ID="your-device-id" \
CLOUDPHONE_OPERATOR_TOKEN="optional-operator-api-token" \
python3 -m uvicorn cloudphone_operator.api:create_app --factory --host 127.0.0.1 --port 18100
```

Web Console URL parameters:

```text
https://your-domain.example/cloudphone-console/#token=<relay-token>&operator=http://127.0.0.1:18100&operatorToken=<operator-token>
```

API endpoints:

- `GET /health`
- `GET /devices`
- `GET /actions?limit=8`
- `POST /run` with `{"message":"检查设备是否可控","deviceId":"your-device-id"}`

If `CLOUDPHONE_OPERATOR_TOKEN` is set, requests must include `x-operator-token`.

## Safety Boundaries

- No arbitrary shell.
- No arbitrary ADB command proxy.
- No arbitrary package launch.
- Write actions are routed through a fixed tool list and policy validation.
- Write actions are recorded in `.operator/action-log.jsonl`.
- Tokens, screenshot base64, and full UI XML are not written to audit logs.
