# 更新日志

> 记录项目的重大更新（AI 在 end session 时自动判断是否写入）。

<!-- version-style: semantic -->

## v0.6.0 (2026-06-07)

### Minor: Workflow Registry v0.13 质量重构

- 新增 `workflow_registry.py`，将 `device_check`、`open_xhs`、`read_screen`、`tap_text`、`read_comments` 等确定性流程声明为可测试 workflow。
- `agent.py` 改为匹配并执行 registry workflow，减少硬编码分支，保持原有 response shape。
- 新增 registry 单测，确保 workflow 匹配顺序、动态参数提取和 action log 标记可验证。
- 保持 Android App、Relay、Web Console、policy 和工具协议不变。

---

## v0.5.0 (2026-06-07)

### Minor: Compact UI Semantic Tools v0.12 MVP

- 新增 `ui_parser.py`，将 `dump_ui` XML 内部解析为 compact semantic snapshot，只暴露 `snapshotId/nodeId`、可见文本、节点中心点和疑似评论。
- Operator Toolkit 新增 `ui_snapshot`、`read_screen`、`find_text`、`tap_text`、`tap_node`、`read_comments`，不把原始 XML 交给 Agent。
- Deterministic workflow 支持“读取当前页面”“点击搜索/点击某文本”“读取评论”。
- 单测扩展到 45 个，覆盖 parser、policy、semantic tools 和 workflow。

---

## v0.4.0 (2026-06-07)

### Minor: Web Console Operator 面板 v0.11 MVP

- Web Console 详情页新增 Operator 面板，支持配置 Python Operator API、运行自然语言 workflow、刷新 Operator action log。
- Operator workflow 返回的 events/actions 会合并进控制台现有动作日志，保留人类可读状态、耗时和摘要。
- Python Operator API 新增可选 `CLOUDPHONE_OPERATOR_TOKEN` 鉴权和 CORS 支持，便于从静态控制台安全调用。
- 补充 Operator API 启动方式和控制台 URL 参数文档。

---

## v0.3.0 (2026-06-07)

### Minor: Cloud Phone Operator Agent v0.10 MVP

- 新增 `cloudphone-operator/` Python 包，包含 CloudPhone Toolkit、policy、executor、JSONL audit、CLI、可选 Agno/FastAPI 接入。
- 支持无模型配置的 deterministic workflow：检查设备是否可控、打开小红书并观察、能力摘要。
- 补充 29 个 unittest，验证配置脱敏、Relay 错误归一化、policy 拒绝危险输入、audit 脱敏、工具映射和 CLI 行为。
- 更新 Project Butler 文档索引、TODO、handoff 和结构规则，下一步进入真实 Relay 联调与 Web Console Operator 面板。

---

## v0.2.0 (2026-06-07)

### Minor: Project Butler 管理栈与多客户端 skill 同步

- 初始化项目记忆系统并记录 Cloud Phone Operator Agent 的产品与架构方向。
- 将 Project Butler 同步到 Claude Code、Kimi、Cursor 和 Codex 使用的同一上游版本。
- 补充收工日志、handoff、TODO、文档索引和结构排除规则，方便下次继续 v0.10 设计。

---

## v0.1.0 (2026-06-07)

### Minor: 项目管理系统初始化

- 初始化 Project Butler 管理栈：CLAUDE.md、PROJECT.md、session-handoff.md、TODO.md、STRUCTURE.md、UPDATE_LOG.md、DOCS.md、log/、.claude/。
- 记录当前产品方向：Android Remote Control 从云机体检升级为可被 Agent 调用的 Android Remote Runtime。
- 明确 v0.10 主线：Cloud Phone Operator Agent，Agno 作为平台操作员，不替代确定性平台层。

---
