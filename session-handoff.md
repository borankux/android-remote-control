# Session Handoff — Android Remote Control / 云机远程控制

> 最后更新：2026-06-07 v0.6

## 项目目标

把自有 Android 真机、云手机和测试设备变成可被远程观察、远程控制、远程恢复、并可由 Agent 安全调用的移动设备运行时。

## 核心产出文件

| 文件 | 状态 | 版本 | 说明 |
|------|------|------|------|
| app/ | 已实现 | v0.8.x | Android 诊断与 Relay 客户端 |
| cloudphone-relay/ | 已实现 | v0.8.x | Relay、Root API 命令、MJPEG、ADB tunnel |
| cloudphone-console/ | 已实现 | v0.11.x | Web 控制台、设备详情、动作日志、Agent 提示词、Operator 面板 |
| cloudphone-operator/ | 已实现 | v0.13.0 | Python Operator Agent、Workflow Registry、Toolkit、compact UI semantic tools、policy、executor、audit、CLI、可选 API/Agno |
| tools/ | 已实现 | v0.8.x | 本地 API helper 与 ADB bridge helper |
| PROJECT.md | 已创建 | v0.1 | 项目 Wiki |
| STRUCTURE.md | 已创建 | v0.1 | 文件管理规则 |

## 当前进度

- 已完成 Android App、Relay、Web Console、Root API、MJPEG 预览、ADB Bridge、Agent 提示词复制等基础控制平面。
- 已创建公开 GitHub 仓库 `borankux/android-remote-control`，README 包含 SEO keywords、GitHub topics 和脱敏截图。
- 产品方向已从“云机体检”升级为“Android Remote Runtime / Cloud Phone Control Plane”。
- 最新架构边界已确定：Agno 只作为平台操作员，不替代平台层。
- 已初始化 Project Butler 管理栈，并完成 Claude Code / Kimi / Cursor / Codex 相关 `project-butler` skill 同步。
- 已实现 v0.10 Cloud Phone Operator Python 包：本地 deterministic workflow 可执行，核心单测和 CLI smoke 已通过。
- 已实现 v0.11 Web Console Operator 面板：详情页可通过 URL 配置 Operator API，运行自然语言 workflow，并合并 Operator events/action log。
- 已实现 v0.12 compact UI semantic tools：内部解析 `dump_ui` XML，但只向 Agent 暴露 `snapshotId/nodeId`、可见文本、节点中心点和疑似评论。
- 已实现 v0.13 Workflow Registry：确定性自然语言流程从 `agent.py` 抽成可注册、可测试的工作流定义。

## 关键设计决策

| # | 决策 | 理由 | 日期 |
|---|------|------|------|
| 1 | 采用 Project Butler 6 组件管理系统 | 便于跨会话维护项目状态、日志、TODO、文档和规则候选 | 2026-06-07 |
| 2 | 平台层保持确定性，Agent 层只做操作员 | Relay、命令队列、鉴权、审计、截图流和 ADB bridge 必须可靠、可测试、可恢复 | 2026-06-07 |
| 3 | Agno 用作 Cloud Phone Operator Agent | Agno 适合自然语言理解、工具选择、workflow 编排和人类可读总结 | 2026-06-07 |
| 4 | 第一版 Operator Agent 做通用机器管理，不做小红书业务自动化 | 先建立稳定控制闭环，再让业务 Agent 调用通用能力 | 2026-06-07 |
| 5 | Project Butler skill 在多客户端保持同一上游版本 | 避免 Codex、Claude Code、Kimi、Cursor 对项目管理流程理解不一致 | 2026-06-07 |
| 6 | Operator 先做可测试的确定性 workflow，再接 Agno 模型 | 没有模型或 token 时也能验证能力边界；真实控制只通过 Relay 白名单工具 | 2026-06-07 |

## 迭代历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.1 | 2026-06-07 | 项目管理系统初始化，记录 Agno Operator 方向 |
| v0.2 | 2026-06-07 | Project Butler 收工记录与多客户端 skill 同步 |
| v0.3 | 2026-06-07 | 实现 Cloud Phone Operator Agent v0.10 MVP |
| v0.4 | 2026-06-07 | 实现 Web Console Operator 面板 v0.11 MVP |
| v0.5 | 2026-06-07 | 实现 compact UI semantic tools v0.12 MVP |
| v0.6 | 2026-06-07 | 实现 Workflow Registry v0.13 质量重构 |

## 下一步

- [ ] 配置真实 `CLOUDPHONE_RELAY_URL` / `CLOUDPHONE_RELAY_TOKEN` / `CLOUDPHONE_DEVICE_ID` 后运行联调：
  `PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator devices`
- [ ] 运行：
  `PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator run "检查设备是否可控"`
- [ ] 运行：
  `PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator run "打开小红书，截图确认"`
- [ ] 启动 Operator API 并用控制台 URL 联调：
  `#token=<relay-token>&operator=http://127.0.0.1:18100&operatorToken=<operator-token>`
- [ ] 在控制台详情页执行“检查设备”和“打开小红书”，确认 Operator events 合并到动作日志。
- [ ] 用真实设备验证：
  `PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator run "读取当前页面"`
- [ ] 用真实设备验证：
  `PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator run "点击搜索"`
- [ ] 用真实设备验证：
  `PYTHONPATH=cloudphone-operator python3 -m cloudphone_operator run "读取评论"`
