# Agno Operator 评估记录

> 最后更新：2026-06-07

## 结论

Agno 适合作为 Cloud Phone Operator Agent，不适合替代平台底座。

平台底座必须继续由确定性服务承担：Android App、PB Relay、命令队列、鉴权、状态机、审计日志、MJPEG、ADB Bridge。Agno 位于上层，作为会理解自然语言的操作员，通过固定工具调用平台能力。

## 依据

- Agno 的 Agent 是围绕模型和工具调用的控制循环，适合理解用户意图并调用外部系统。
- Agno 的 Tool 模型适合封装 `list_devices`、`get_device_status`、`screencap`、`dump_ui`、`tap`、`wait_for_text` 等固定工具。
- Agno 的 Workflow / AgentOS 方向适合后续做会话、状态、监控、human-in-the-loop 和平台操作记录。
- 参考 `ai-hr` 项目时，最值得迁移的不是具体 HR 业务，而是工具定义、执行器、policy engine、workflow registry 和 audit log 模式。

## 推荐架构

```text
用户自然语言
  ↓
Agno Operator Agent
  ↓
CloudPhone Toolkit
  ↓
Relay API / Console API
  ↓
Android App / 云手机
```

## v0.10 最小闭环

用户输入：

> 检查这台云手机能不能控制，然后打开小红书，截图给我看。

系统执行：

1. 找到在线设备。
2. 查询 Relay / Root / ADB 状态。
3. 调用 `launch_xhs`。
4. 等待前台变成小红书。
5. 截图。
6. dump UI。
7. 返回人类可读总结。
8. 写入动作日志。

## 风险边界

- 不开放任意 shell。
- 不让 LLM 决定底层安全边界。
- 截图和 MJPEG 不直接进入 LLM 主循环，应先抽象为状态摘要、UI JSON 或截图引用。
- 所有写操作必须有结构化结果和动作日志。
