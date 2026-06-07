# 技术设计总览

> 最后更新：2026-06-07

## 概述

系统分为确定性平台层和 Agent 操作员层。

```text
Web Console / Local Agent / API Client
          |
      Agno Operator Agent
          |
  CloudPhone Toolkit / Workflow Tools
          |
 Deterministic Platform API
          |
 PB Relay + Android App + ADB Bridge
          |
      Cloud Phones
```

## 边界

- 平台层负责设备注册、鉴权、命令队列、状态、审计、MJPEG、ADB Bridge。
- Agno 层负责理解自然语言、选择工具、执行 workflow、总结结果和恢复建议。
- Agent 不直接调用任意 shell，不绕过平台白名单。
