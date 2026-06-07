# Session 2026-06-07 — Project Butler Init And Skill Sync

## 本次目标

初始化 Project Butler 项目记忆栈，记录 Agno Operator 方向，并确认 `project-butler` skill 在 Codex、Claude Code、Kimi 和 Cursor 之间保持同一最新版。

## 关键操作（按时间顺序）

1. 使用 Project Butler 初始化项目管理文件：CLAUDE.md、PROJECT.md、session-handoff.md、TODO.md、STRUCTURE.md、UPDATE_LOG.md、DOCS.md、log/、.claude/、.cursor/rules/。
2. 将“Agno 只是平台操作员，不替代平台底座”的架构决策写入项目 Wiki、handoff、研究文档和候选规则池。
3. 创建 `docs/research/agno-operator-evaluation.md`，记录 Agno 适合作为 Cloud Phone Operator Agent 的评估。
4. 检查本机 `project-butler` skill 多处安装副本，发现 Claude Code、Kimi、Cursor 副本落后上游。
5. 将 Claude Code、Kimi、Cursor 的 `project-butler` 副本 fast-forward 到 `c8cc4aa`，并确认 `SKILL.md` hash 与 `.agents` 主副本一致。
6. 执行本次 wrap up：更新 handoff、PROJECT、TODO、STRUCTURE、UPDATE_LOG，并写入本日志。

## 决策与理由

- 决策：Project Butler 作为本项目默认跨会话记忆系统。
  理由：后续 Android App、Relay、Web Console、Operator Agent 会跨多个会话推进，需要稳定的 Wiki、handoff、TODO、文档索引和日志。

- 决策：多客户端 `project-butler` skill 统一到 `c8cc4aa`。
  理由：Codex、Claude Code、Kimi、Cursor 如果读取不同版本，会在初始化、收工、文档归档和 update log 行为上产生差异。

- 决策：`.superpowers/` 作为工具临时目录纳入 STRUCTURE 排除规则。
  理由：该目录由技能流程生成，不应进入业务源码整理范围。

## 产出文件

- `CLAUDE.md`
- `PROJECT.md`
- `session-handoff.md`
- `TODO.md`
- `STRUCTURE.md`
- `UPDATE_LOG.md`
- `DOCS.md`
- `.claude/candidates.md`
- `.claude/.file-snapshot.json`
- `.cursor/rules/project-system.mdc`
- `docs/prd/main.md`
- `docs/tech-design/main.md`
- `docs/design/main.md`
- `docs/research/agno-operator-evaluation.md`
- `log/session-2026-06-07-agno-operator-direction.md`
- `log/session-2026-06-07-project-butler-init-skill-sync.md`

## 未完事项 / 下次接手点

- 从 `TODO.md` 的 v0.10 主线开始：先写 Cloud Phone Operator Agent 技术设计。
- 参考 `/Users/allintech/Desktop/blacktide/ai-hr` 的 tool definitions、executor、policy engine、workflow registry 和 audit log。
- 定义 CloudPhone Toolkit 的工具 schema，包括设备状态、观察、截图、UI dump、点击、输入、等待文本和恢复流程。

## 候选 CLAUDE.md 条目（如有）

- Project Butler skill 在 Codex、Claude Code、Kimi、Cursor 中应保持同一上游版本，避免项目管理行为分叉。
