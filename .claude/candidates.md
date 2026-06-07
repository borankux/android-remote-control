# CLAUDE.md 候选条目

> 以下条目由 AI 自动收集，等待人工 review。
> 触发 review：对 AI 说 "review claude" 或 "更新宪法"

## 待确认（待 review）

- [ ] Agno 在本项目中只作为 Cloud Phone Operator Agent，不作为平台底座；平台层仍由 Relay、Android App、命令队列、状态机、审计和控制台承担。
  来源：2026-06-07 架构讨论

- [ ] 任何 Agent 控制能力都必须通过固定白名单工具调用，不提供任意 shell，不绕过 Root API 命令边界。
  来源：2026-06-07 安全边界讨论

- [ ] 业务自动化（例如小红书操作）应构建在通用设备控制工具之上，不直接污染底层 Relay/Root API 协议。
  来源：2026-06-07 产品方向讨论

- [ ] 所有写操作和设备动作必须产生人类可读日志与结构化结果，便于控制台展示、回放排错和 Agent 验证。
  来源：2026-06-07 Operator Agent 规划

- [ ] Project Butler skill 在 Codex、Claude Code、Kimi、Cursor 中应保持同一上游版本，避免项目管理行为分叉。
  来源：2026-06-07 skill 同步检查

## 已驳回

（暂无）

## 已采纳（已写入 CLAUDE.md）

（暂无）
