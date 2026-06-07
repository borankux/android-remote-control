# Android Remote Control / 云机远程控制 项目指令

> 本文件由 Claude Code 自动加载，定义项目协作规则。

## 项目概况
- **产品：** 面向自有 Android 真机、云手机和测试设备的远程控制运行时，包含 Kotlin Android App、Node Relay、React 控制台、Root API、MJPEG 预览、ADB Bridge 和 Agent 操作员接入。
- **当前阶段：** v0.10 规划中：Cloud Phone Operator Agent
- **GitHub：** borankux/android-remote-control

## Language / 语言
- **Language:** zh

## 项目管理系统

本项目使用 6 组件管理系统。

- **Log Compaction Threshold:** 10（每积累 10 个日志文件压缩为 1 个 summary）

### 触发词

| Intent | AI Action |
|--------|-----------|
| End session / wrap up — any expression of "we're done for now" (end session, 结束会话, 收工, wrap up, done for today, etc.) | Write log + update handoff + sync Wiki + check TODO + collect constitution candidates + file reorganization + document archiving + evaluate update log + version bump + output summary in configured language |
| Review constitution — any expression of "check/update rules" (review claude, 更新宪法, check rules, etc.) | Show .claude/candidates.md for confirmation one by one |
| Sync wiki — any expression of "update project overview" (sync wiki, 同步项目, refresh overview, etc.) | Force rescan and update PROJECT.md |
| Check status — any expression of "what's the current state" (status, 项目现状, where are we, etc.) | Read PROJECT.md + session-handoff.md summary aloud |
| Organize files — any expression of "clean up files" (organize files, 整理文件, clean up, sort files, etc.) | Scan project files, organize per STRUCTURE.md rules |
| Change language — any expression of "switch language" (切换语言, change language, switch to English, 换成中文, etc.) | Execute Language Change Protocol |
| Continue — any expression of "pick up where we left off" (接着上次, continue, 上次做到哪了, etc.) | Read last session log + session-handoff.md + PROJECT.md to recover context |
| Continue full context — any expression of "full project review" (全面回顾, full context, 项目全景, etc.) | Full project trajectory recovery across all sessions |

### 文件职责

| File | Who writes | When |
|------|-----------|------|
| CLAUDE.md | 人工确认 | review claude 时 |
| PROJECT.md | AI 自动 | end session + 文件结构变化时 |
| session-handoff.md | AI 自动 | end session 时 |
| TODO.md | AI + 人 | 随时 |
| log/session-*.md | AI | end session 时 |
| .claude/candidates.md | AI 自动 | 过程中识别到稳定规则时 |
| STRUCTURE.md | AI 自动 | end session + 文件结构变化时 |
| .claude/.file-snapshot.json | AI 自动 | end session 时 |
| UPDATE_LOG.md | AI 自动 | end session + 重大更新时 |
| DOCS.md | AI 自动 | end session + 文档归档时 |

### Session Start Protocol

At session start:

1. Read `PROJECT.md` for project overview and `session-handoff.md` for current progress / next steps. Check the Language setting in CLAUDE.md to determine output language.
2. **Read logs (bounded):**
   - Find the highest level with summaries in `log/summaries/` and read all summaries at that level.
   - Read all unarchived raw logs in `log/` excluding `summaries/` and `archive/`.
   - Total files read: at most 2 x (threshold - 1), regardless of project age.
   - If `log/` does not exist yet, skip this step.

### Session End Protocol

当用户说 "end session" / "结束会话" / "收工" 时，按顺序执行：

1. **写会话日志** -> `log/session-YYYY-MM-DD-{主题slug}.md`
2. **Log Compaction** -> 检查未归档 raw logs 数量，若 >= threshold 则执行压缩。
3. **更新 session-handoff.md** -> 刷新当前进度和下一步。
4. **更新 PROJECT.md** -> 如有结构或模块状态变化，同步更新。
5. **更新 TODO.md** -> 标记本次已完成的任务。
6. **收集宪法候选** -> 识别规则、偏好、边界，追加到 `.claude/candidates.md`。
7. **整理文件结构（增量模式）** -> 只处理新增/变更文件，按 STRUCTURE.md 规则归类。
7.5. **文档归档** -> 扫描本次会话产出的文档，归档到 docs/ 并更新 DOCS.md。
8. **评估并写入 Update Log** -> 如包含重大更新，判断版本递增级别并写入 UPDATE_LOG.md。
9. **Output summary** -> 使用配置语言输出简短总结。

### Session Log 格式

写入 `log/` 的每条日志遵循以下格式：

```markdown
# Session YYYY-MM-DD — {topic}

## 本次目标
## 关键操作（按时间顺序）
## 决策与理由
## 产出文件
## 未完事项 / 下次接手点
## 候选 CLAUDE.md 条目（如有）
```

### 宪法候选识别规则

AI 在工作过程中，遇到以下情况时自动追加条目到 `.claude/candidates.md`：
- 用户明确说"以后都这么做" / "这是规则" / "不要再..."
- 同一类决策在多次会话中连续出现
- 涉及命名规范、文件分层、协作流程的决定
- 涉及技术栈选择、架构约束的决定

**绝对不要直接修改 CLAUDE.md。** 所有候选条目必须经用户 review 后才写入。

### TODO 格式

TODO.md 中每条任务必须包含三要素：

```markdown
- [ ] {任务描述}
  负责人：{name}｜截止：{date}｜依赖：{prerequisite}
```

完成的任务勾选保留，不删除。

## Coding Guidelines

### 1. Think Before Coding

实现前先明确假设、约束和成功标准。若存在多个解释，先指出差异；如果更简单的路径足够，优先选择简单路径。

### 2. Simplicity First

只做当前目标需要的功能。不为未来猜测做抽象，不增加未请求的配置或功能。

### 3. Surgical Changes

只改和任务直接相关的文件。不要顺手重构无关代码，不要回滚用户或其他流程产生的改动。

### 4. Goal-Driven Execution

多步骤任务要写清计划和验证方式。完成前用实际命令或可观察结果验证。

## 项目特定规则

- Agno 只作为 Cloud Phone Operator Agent，不替代 Relay、命令队列、设备状态、鉴权、审计、截图流、ADB Bridge 等确定性平台层。
- 平台层必须保持固定命令白名单，不提供任意 shell 入口。
- Agent 只能通过标准工具调用平台能力，关键动作必须产生可读操作日志和结构化结果。
- 小红书等业务自动化应放在业务 Agent 或 workflow 层，不直接污染底层设备控制协议。
