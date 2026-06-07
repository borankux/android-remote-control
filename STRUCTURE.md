# Android Remote Control / 云机远程控制 — 文件管理结构

> 最后更新：2026-06-07

## 项目类型

Android + Node.js + React + Python CLI/API 的多端远程控制系统，包含移动端 App、Relay 后端、Web 控制台、Operator Agent、本地工具、项目文档和会话日志。

## 排除规则

以下目录/文件不参与整理：

- .git/
- .gradle/
- node_modules/
- __pycache__/
- .venv/
- dist/
- build/
- vendor/
- .superpowers/
- .claude/
- docs/
- log/
- log/summaries/
- log/archive/
- app/build/
- cloudphone-console/dist/
- cloudphone-console/node_modules/
- cloudphone-relay/node_modules/
- cloudphone-operator/.operator/
- cloudphone-operator/.pytest_cache/

## 目录规则

| 路径 | 用途 | 匹配条件 | 命名规范 | 优先级 |
|------|------|----------|----------|--------|
| app/ | Android App 源码、资源、测试 | Kotlin、XML、AndroidManifest、Gradle Android 模块文件 | 遵循 Android/Kotlin 现有规范 | 1 |
| cloudphone-relay/ | Node Relay 服务 | server.js、Relay package.json、WebSocket/HTTP 服务代码 | kebab-case / camelCase | 2 |
| cloudphone-console/ | React/Vite Web 控制台 | JSX、CSS、前端 package.json、控制台组件 | kebab-case / PascalCase 组件 | 3 |
| cloudphone-operator/ | Python Operator Agent | Python package、unittest、pyproject.toml、可选 FastAPI/Agno 接入 | snake_case 模块，kebab-case 项目目录 | 4 |
| tools/ | 本地 CLI helper | `.mjs`、本地 API client、ADB bridge client | kebab-case | 5 |
| gradle/ | Gradle wrapper 与构建支持 | Gradle wrapper jar/properties | Gradle 默认规范 | 6 |
| docs/ | 文档仓库 | PRD、技术设计、设计文档、调研、实验记录 | 英文目录名，中文标题可用 | 7 |
| log/ | Project Butler 会话日志 | `session-YYYY-MM-DD-{slug}.md` | kebab-case slug | 8 |
| .claude/ | Project Butler 候选规则和快照 | candidates.md、.file-snapshot.json | 固定文件名 | 9 |
| 根目录 | 项目说明和管理文件 | README、PROJECT、TODO、STRUCTURE、UPDATE_LOG、DOCS、Gradle 根配置 | 固定文件名 | 10 |

## 待分类

以下文件尚未归类（下次整理时处理）：

- （暂无）

## 整理历史

| 日期 | 操作 | 文件数 |
|------|------|--------|
| 2026-06-07 | 初始化结构 | 0 |
| 2026-06-07 | 收工增量检查：补充 .superpowers/ 排除规则 | 1 |
