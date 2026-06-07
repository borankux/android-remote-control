# Android Remote Control / 云机远程控制 — 项目 Wiki

> 最后同步：2026-06-07（自动）

## 一句话定义

面向自有 Android 真机、云手机和测试设备的远程控制运行时，包含 Kotlin Android App、Node Relay、React 控制台、Root API、MJPEG 预览、ADB Bridge 和 Agent 操作员接入。

## 当前阶段

v0.13 首个实现已完成：Python Operator 已新增 Workflow Registry，把确定性自然语言流程从 `agent.py` 抽成可注册、可测试的工作流；当前重点是真实云手机联调语义工具和控制台 Operator 面板。

## 模块/章节地图

| 模块 | 状态 | 备注 |
|------|------|------|
| Android App (`app/`) | 已实现基础能力 | Kotlin + XML/View；设备诊断、Relay 连接、Root 白名单命令、截图、UI dump、ADB tunnel。 |
| PB Relay (`cloudphone-relay/`) | 已实现基础能力 | Node.js HTTP/WebSocket；设备注册、命令队列、MJPEG 流、ADB Bridge。 |
| Web Console (`cloudphone-console/`) | 已实现基础能力 | React/Vite；设备列表、详情页、MJPEG 预览、动作日志、Agent 提示词复制、Operator 面板。 |
| CLI Tools (`tools/`) | 已实现基础能力 | 本地 Root API client 和 ADB bridge client。 |
| Public Repo | 已发布 | GitHub: `borankux/android-remote-control`，包含 README、SEO topics、截图和脱敏源码。 |
| Operator Agent (`cloudphone-operator/`) | MVP 已实现 | Python 3.9；Workflow Registry、CloudPhone Toolkit、compact UI semantic tools、policy、executor、JSONL audit、CLI、可选 Agno/FastAPI。 |
| Project Butler | 已初始化 | 已创建项目 Wiki、handoff、TODO、日志、文档索引、结构规则和候选规则池。 |

## 文件结构

> 详细目录规则见 STRUCTURE.md

```text
.
├── CLAUDE.md                   ← 项目宪法（人工确认）
├── PROJECT.md                  ← 本文件（AI 自动同步）
├── STRUCTURE.md                ← 文件管理规则（AI 自动维护）
├── session-handoff.md          ← 接手指引（AI 自动）
├── TODO.md                     ← 执行清单
├── UPDATE_LOG.md               ← 更新日志（重大更新时写入）
├── DOCS.md                     ← 文档索引（AI 自动归档）
├── README.md                   ← 公开项目说明
├── app/                        ← Android App
├── cloudphone-relay/           ← Relay 服务
├── cloudphone-console/         ← Web 控制台
├── cloudphone-operator/        ← Python Operator Agent
├── tools/                      ← 本地 CLI / ADB bridge 工具
├── docs/                       ← 文档仓库
├── log/                        ← 会话日志
└── .claude/
    ├── candidates.md           ← 宪法候选池
    └── .file-snapshot.json     ← 文件整理快照
```

## 关键文件索引

| 文件 | 说明 |
|------|------|
| CLAUDE.md | 项目宪法，定义规则和边界 |
| PROJECT.md | 本文件，项目百科全貌 |
| session-handoff.md | 跨会话接手指引 |
| TODO.md | 执行任务清单 |
| .claude/candidates.md | 待确认的宪法候选条目 |
| STRUCTURE.md | 文件管理规则，定义目录组织和匹配条件 |
| UPDATE_LOG.md | 更新日志，记录重大更新 |
| DOCS.md | 文档索引，记录所有文档的元数据和层级关系 |
| app/src/main/java/com/allin/cloudphone/inspector/relay/RelayService.kt | Android Relay/Root API/ADB tunnel 核心 |
| cloudphone-relay/server.js | Relay 服务核心 |
| cloudphone-console/src/main.jsx | 控制台主入口和 Agent 提示词生成 |
| cloudphone-operator/cloudphone_operator/agent.py | Operator workflow 与可选 Agno Agent 工厂 |
| cloudphone-operator/cloudphone_operator/workflow_registry.py | 确定性自然语言工作流注册表和执行器 |
| cloudphone-operator/cloudphone_operator/tools.py | CloudPhone Toolkit，映射现有 Relay 白名单命令 |
| cloudphone-operator/cloudphone_operator/ui_parser.py | uiautomator XML 内部解析器，输出 compact semantic snapshot |
| cloudphone-operator/cloudphone_operator/executor.py | Policy + Tool + Audit 统一执行入口 |
| cloudphone-operator/cloudphone_operator/cli.py | Python Operator CLI |
| tools/cloudphone-api-client.mjs | 本地 Root API helper |
| tools/adb-bridge-client.mjs | 本地 ADB bridge helper |

## 当前进度快照

| 模块 | 状态 | 备注 |
|------|------|------|
| 设备接入 | 可用 | 云手机可通过 App 主动连接 Relay。 |
| Root API | 可用 | 已有固定白名单命令，不做任意 shell。 |
| 远程画面 | 可用但可优化 | MJPEG 基于 repeated screencap，适合观察和短时操作。 |
| ADB Bridge | 可用性待继续验证 | 依赖云手机 adbd tcp 和 Root 权限。 |
| 控制台 | 可用 | 详情页已可配置 Operator API；后续需要转为多设备 fleet dashboard。 |
| Agno Operator | MVP 已实现 | 可在无模型配置下运行 registry workflow；支持页面读取、文本点击、疑似评论提取；有 Agno/模型配置时可扩展为 Agent。 |
| 项目记忆栈 | 可用 | `project-butler` 已在 Claude Code、Kimi、Cursor 和 Codex 主副本同步到同一 commit。 |

## 相关链接

- GitHub: https://github.com/borankux/android-remote-control
