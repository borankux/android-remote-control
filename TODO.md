# Android Remote Control / 云机远程控制 — TODO

> 每条任务必须包含：负责人 / 截止时间 / 依赖项
> 完成的任务勾选保留（不删除），作为执行历史

## v0.10 Cloud Phone Operator Agent

- [x] 初始化 Project Butler 项目管理栈
  负责人：Codex｜截止：2026-06-07｜依赖：当前项目结构

- [x] 同步 project-butler skill 到 Claude Code / Kimi / Cursor / Codex 主副本
  负责人：Codex｜截止：2026-06-07｜依赖：GitHub 上游 `JamesShi96/project-butler`

- [x] 编写 Cloud Phone Operator Agent 技术设计
  负责人：Codex｜截止：2026-06-08｜依赖：当前 Relay API 和控制台能力清单

- [x] 定义 CloudPhone Toolkit 工具清单与参数/返回协议
  负责人：Codex｜截止：2026-06-08｜依赖：技术设计确认

- [x] 评估并迁移 ai-hr 的工具执行模式
  负责人：Codex｜截止：2026-06-09｜依赖：读取 `/Users/allintech/Desktop/blacktide/ai-hr`

- [x] 实现 Agno Operator 最小闭环
  负责人：Codex｜截止：2026-06-10｜依赖：CloudPhone Toolkit 工具协议

- [x] 实现 Operator 本地 JSONL action log
  负责人：Codex｜截止：2026-06-07｜依赖：ToolExecutor 和 policy

- [ ] 使用真实 Relay 环境变量验证 Operator CLI
  负责人：Codex｜截止：2026-06-08｜依赖：在线设备、`CLOUDPHONE_RELAY_URL`、`CLOUDPHONE_RELAY_TOKEN`、`CLOUDPHONE_DEVICE_ID`

- [x] 在 Web Console 增加 Operator 面板
  负责人：Codex｜截止：2026-06-11｜依赖：Operator API 可用

- [ ] 真实联调 Web Console Operator 面板
  负责人：Codex｜截止：2026-06-08｜依赖：Operator API 进程、Relay token、在线云手机

## 平台可靠性

- [ ] 标准化命令状态：queued / running / success / failed / timeout
  负责人：Codex｜截止：2026-06-09｜依赖：Relay command model

- [ ] 为每个写操作落 action log
  负责人：Codex｜截止：2026-06-09｜依赖：Relay / Operator 统一事件结构

- [x] 增强 dump_ui 使用方式：内部 XML parser + compact semantic snapshot
  负责人：Codex｜截止：2026-06-10｜依赖：Python Operator Toolkit

- [x] 增加 Agent 友好动作：tap_text / tap_node / observe_device
  负责人：Codex｜截止：2026-06-10｜依赖：UI JSON 节点模型

- [x] 增加 Agent 友好读取：ui_snapshot / read_screen / find_text / read_comments
  负责人：Codex｜截止：2026-06-07｜依赖：Python UI parser

- [x] 引入 Workflow Registry，替代 agent.py 硬编码流程分支
  负责人：Codex｜截止：2026-06-07｜依赖：v0.12 semantic tools

- [ ] 真实联调 UI 语义工具
  负责人：Codex｜截止：2026-06-08｜依赖：在线云手机、Relay token、小红书页面
