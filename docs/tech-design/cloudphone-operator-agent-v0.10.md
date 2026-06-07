# Cloud Phone Operator Agent v0.10 技术设计

> 最后更新：2026-06-07
> 状态：已确认设计，待实施计划
> 范围：新增独立 Python Operator 层；不改 Android App，不改 Relay 协议，不先做 Web Console 面板。

## 背景

当前项目已经具备 Android App、PB Relay、Web Console、Root API、MJPEG 预览、ADB Bridge 和本地 CLI helper。下一版目标不是重做平台，而是在确定性平台层上方增加一个 Agno 操作员，让自然语言可以安全地调用现有设备控制能力。

核心边界：

- Relay、Android App、命令队列、状态、鉴权、MJPEG、ADB Bridge 仍由平台层负责。
- Agno 只作为 Cloud Phone Operator Agent，负责理解意图、选择工具、执行 workflow、解释结果。
- 不开放任意 shell，不绕过 Relay 白名单命令。

## 目标

v0.10 第一版要跑通一个最小闭环：

```text
用户自然语言
  -> Cloud Phone Operator Agent
  -> CloudPhone Toolkit
  -> Policy + Executor + Audit
  -> 现有 PB Relay API
  -> Android App / 云手机
```

验收口径：

- 能列出在线设备。
- 能检查默认设备是否可控。
- 能通过自然语言打开小红书。
- 能截图、dump UI，并返回可读摘要。
- 每个动作都有 action log。
- token 缺失、设备离线、命令失败、超时都有明确错误。

## 非目标

- 不实现新的 Android Root 命令。
- 不修改现有 Relay API 路径或协议。
- 不实现 Web Console Operator 面板。
- 不做小红书业务自动化策略。
- 不保存截图历史、不录像、不做高帧率视频传输。
- 不提供任意 shell、任意包名启动、任意 ADB 命令代理。

## 方案选择

采用方案 B：Python Operator API + CLI。

理由：

- 比纯 CLI 更接近后续控制台接入形态。
- 比直接做 Web Console 面板风险低。
- 可以先用 CLI 验收自然语言到工具调用的闭环。
- Python 适合接 Agno，同时不影响现有 Node Relay 和 React Console。

## 目录结构

新增：

```text
cloudphone-operator/
  pyproject.toml
  README.md
  cloudphone_operator/
    __init__.py
    __main__.py
    agent.py
    api.py
    audit.py
    cli.py
    config.py
    executor.py
    policy.py
    relay_client.py
    schemas.py
    tools.py
  tests/
    test_config.py
    test_policy.py
    test_relay_client.py
    test_tools.py
    test_executor.py
```

## 模块职责

### config.py

读取运行配置：

- `CLOUDPHONE_RELAY_URL`
- `CLOUDPHONE_RELAY_TOKEN`
- `CLOUDPHONE_DEVICE_ID`
- `CLOUDPHONE_OPERATOR_MODEL`
- `CLOUDPHONE_OPERATOR_BASE_URL`
- `CLOUDPHONE_OPERATOR_API_KEY`

配置对象不在日志中输出 token 原文。

### relay_client.py

封装现有 Relay HTTP API：

- `GET /devices`
- `POST /commands`
- `GET /commands/{id}`

职责：

- 设置 `x-relay-token`。
- 创建命令。
- 轮询命令结果。
- 统一处理 401、404、设备离线、超时和 JSON 解析失败。

### schemas.py

定义内部结构：

- `DeviceSummary`
- `CommandRequest`
- `CommandResult`
- `ToolResult`
- `ActionLogEntry`
- `Observation`

所有工具返回统一结构：

```json
{
  "ok": true,
  "error": null,
  "durationMs": 123,
  "summary": "已打开小红书",
  "data": {}
}
```

失败时：

```json
{
  "ok": false,
  "error": "device_not_online",
  "durationMs": 120,
  "summary": "设备不在线",
  "data": {}
}
```

### policy.py

确定性安全策略：

- 只允许调用预定义工具。
- 只允许 Relay 白名单命令。
- `input_text` 限长 200 字符。
- 坐标必须在 Relay 现有范围内。
- 不接受 shell 文本、ADB shell 文本或任意命令字符串。
- 写动作必须进入 audit。
- 失败结果必须保留 Relay 原始 `error`。

第一版写动作：

- `tap`
- `swipe`
- `input_text`
- `back`
- `home`
- `launch_xhs`
- `wait_for_text`

查询动作：

- `list_devices`
- `get_device_status`
- `observe_device`
- `screencap`
- `dump_ui`

### executor.py

统一工具执行入口，参考 `ai-hr` 的 `tools/executor.py` 模式。

职责：

- 执行前调用 policy。
- 执行工具函数。
- 捕获异常并转为标准 `ToolResult`。
- 为结果生成短摘要。
- 对写动作调用 audit。

### audit.py

第一版用本地 JSONL 文件，避免引入数据库：

默认路径：

```text
cloudphone-operator/.operator/action-log.jsonl
```

每条记录包含：

- time
- tool
- deviceId
- argsSummary
- ok
- error
- durationMs
- summary

token、截图 base64、完整 UI XML 不写入日志。

### tools.py

封装 CloudPhone Toolkit。

第一版工具：

```text
list_devices
get_device_status
observe_device
screencap
dump_ui
tap
swipe
input_text
back
home
launch_xhs
wait_for_text
```

`observe_device` 是组合工具：

1. `list_devices`
2. `snapshot`
3. `screencap`，默认 `jpeg + maxWidth=540 + quality=65`
4. `dump_ui`
5. 生成 `Observation` 摘要

`Observation` 不把完整截图直接塞进 prompt，只提供：

- device online/root/app summary
- foreground/focus
- screen/display summary
- screenshot mime/byteCount
- UI text snippets
- UI XML charCount

### agent.py

定义 Agno Operator Agent。

职责：

- 使用 Agno Agent。
- 注册 CloudPhone Toolkit 工具。
- 使用明确 instructions：
  - 必须先观察再行动。
  - 每次动作后必须验证。
  - 不允许声称成功，除非工具返回成功。
  - 不允许任意 shell。
  - 命令失败时必须返回 error/status。

如果当前环境缺少模型配置，CLI 应能以 deterministic workflow 模式运行基础命令，而不是直接崩溃。

### api.py

提供后续 Web Console 可接入的 HTTP API。

第一版建议使用 FastAPI：

- `GET /health`
- `GET /devices`
- `GET /actions`
- `POST /run`

`POST /run`：

```json
{
  "message": "检查设备并打开小红书，截图确认",
  "deviceId": "optional-device-id"
}
```

返回：

```json
{
  "ok": true,
  "summary": "...",
  "events": [],
  "actions": []
}
```

### cli.py / __main__.py

CLI 入口：

```bash
python -m cloudphone_operator devices
python -m cloudphone_operator run "检查设备是否可控"
python -m cloudphone_operator run "打开小红书，截图确认"
python -m cloudphone_operator tool observe_device
python -m cloudphone_operator log
```

## 工具协议

### list_devices

输入：无
输出：设备列表摘要。

### get_device_status

输入：

```json
{"deviceId":"optional"}
```

输出：在线状态、Root、App 版本、最后心跳、设备型号。

### observe_device

输入：

```json
{"deviceId":"optional","includeScreenshot":true,"includeUi":true}
```

输出：状态、截图摘要、UI 摘要。

### screencap

输入：

```json
{"deviceId":"optional","format":"jpeg","maxWidth":540,"quality":65}
```

输出：mimeType、byteCount、可选输出文件路径或 base64。

### dump_ui

输入：

```json
{"deviceId":"optional"}
```

输出：charCount、文本片段、原始 XML 可选返回。

### launch_xhs

输入：

```json
{"deviceId":"optional"}
```

输出：Relay command result 摘要。

### tap / swipe / input_text / back / home / wait_for_text

直接映射现有 Relay 命令，并通过 policy 做参数约束。

## 工作流

### 检查设备是否可控

```text
list_devices
-> get_device_status
-> observe_device
-> summary
```

成功摘要应说明：

- 设备是否在线
- Root 是否可用
- 最近心跳
- 当前前台状态是否可读
- 截图/UI dump 是否成功

### 打开小红书并截图确认

```text
get_device_status
-> launch_xhs
-> wait_for_text("搜索") 或 observe_device
-> screencap
-> dump_ui
-> summary
```

如果 `wait_for_text("搜索")` 失败，不直接判失败；继续 `observe_device`，根据 focus、UI text snippets 和截图摘要说明当前状态。

## 错误处理

| 场景 | 行为 |
|------|------|
| token 缺失 | CLI/API 返回 `missing_relay_token` |
| Relay 401 | 返回 `unauthorized`，不打印 token |
| 设备离线 | 返回 `device_not_online` |
| 命令超时 | 返回 `command_timeout` |
| Relay 返回 failed | 保留 Relay `error` |
| JSON 解析失败 | 返回 `invalid_relay_response` |
| Agno/model 缺失 | 基础 workflow 可运行，LLM run 明确提示模型配置缺失 |

## 测试计划

单元测试：

- `config` 正确读取环境变量，并隐藏 token。
- `policy` 拒绝未知工具、过长文本、越界坐标、shell-like 输入。
- `relay_client` 能 mock 创建命令、轮询成功、轮询失败、超时、401。
- `tools` 能把 Relay result 归一化为 `ToolResult`。
- `audit` 不写入 token、base64、完整 XML。

集成测试（需要 Relay 在线）：

```bash
python -m cloudphone_operator devices
python -m cloudphone_operator tool observe_device
python -m cloudphone_operator run "检查设备是否可控"
python -m cloudphone_operator run "打开小红书，截图确认"
```

## 验收标准

- CLI 能列出设备。
- CLI 能执行 `observe_device` 并返回状态摘要。
- 自然语言 run 能调用工具完成检查设备和打开小红书。
- 每个写动作进入 JSONL action log。
- 失败结果不被吞掉，不伪造成成功。
- 不需要修改 Android App 或 Relay 即可运行。

## 后续版本

v0.11：

- Web Console 增加 Operator 面板。
- Relay 增加持久 action log API 或 Operator 同步日志。
- `dump_ui` 增强为 XML + 简化 JSON。

v0.12：

- 增加 `tap_text`、`tap_node`、`find_text`、`read_comments` 等 UI 语义工具。
- 引入可配置 workflow registry。

v1.0：

- 多设备 fleet operator。
- 任务编排、人工确认、失败恢复 SOP。
- AgentOS session/storage/tracing 正式接入。
