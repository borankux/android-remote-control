# Session 2026-06-07 — Agno Operator Direction

## 本次目标

评估 Android Remote Control 下一阶段是否应引入 Agno，并明确 Agno 在平台中的位置。

## 关键操作（按时间顺序）

1. 回顾当前项目状态：Android App、Relay、Web Console、Root API、MJPEG、ADB Bridge 和 Agent 提示词已形成基础控制平面。
2. 讨论产品大方向：从“云机体检”升级为 Android Remote Runtime / Cloud Phone Control Plane。
3. 评估 Agno：Agno 适合做平台上方的自然语言操作员，不适合替代平台层。
4. 对照 `ai-hr` 项目：参考其 tool definitions、executor、policy engine、workflow registry、audit log 模式。
5. 收敛 v0.10 方向：Cloud Phone Operator Agent。

## 决策与理由

- 决策：Agno 只作为 Cloud Phone Operator Agent。
  理由：设备注册、命令队列、Relay、ADB、鉴权、截图流和审计必须保持确定性、可测试、可恢复。

- 决策：Operator 第一版只做通用机器管理，不做小红书业务自动化。
  理由：先建立稳定观察、控制、验证、恢复闭环，再让业务 Agent 复用这些通用能力。

- 决策：平台工具必须固定白名单。
  理由：降低 Root 和远程控制风险，避免任意 shell 和不可审计行为。

## 产出文件

- `CLAUDE.md`
- `PROJECT.md`
- `session-handoff.md`
- `TODO.md`
- `.claude/candidates.md`
- `STRUCTURE.md`
- `UPDATE_LOG.md`
- `DOCS.md`
- `docs/prd/main.md`
- `docs/tech-design/main.md`
- `docs/design/main.md`
- `docs/research/agno-operator-evaluation.md`

## 未完事项 / 下次接手点

- 编写 v0.10 Cloud Phone Operator Agent 技术设计。
- 定义 CloudPhone Toolkit 工具 schema。
- 迁移/借鉴 `ai-hr` 的工具执行、policy、workflow 和 audit 结构。
- 实现最小闭环：检查设备、打开小红书、截图、dump UI、总结结果。

## 候选 CLAUDE.md 条目（如有）

- Agno 只作为平台操作员，不替代平台底座。
- Agent 控制能力必须通过固定白名单工具调用，不提供任意 shell。
- 业务自动化构建在通用设备控制工具之上。
- 所有写操作和设备动作必须产生人类可读日志与结构化结果。
