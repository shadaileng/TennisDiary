---
name: git-commit
description: >
  Git commit conventions for the Tennis Diary project (miniapp + server + admin).
  Use when creating any Git commit. Defines Conventional Commits message
  format with scope, CHANGELOG update workflow, and atomic commit principle.
---

## 提交格式

```
<type>(<scope>): <中文简短描述>

<body>（可选，多行中文详细说明）

BREAKING CHANGE: <不兼容变更说明>（仅在必要时）
```

**scope 可选值**：`miniapp` / `server` / `admin` / `docs` / `plans` / `workspace`

示例：
```bash
git commit -m "fix(miniapp): 上传视频前检查文件是否存在，修复模拟器临时文件失效报错"
git commit -m "fix(server): 修复骨架视频只含1帧的bug（ffmpeg concat静态图片缺陷）"
git commit -m "docs(plans): 新增 84-骨架视频多帧修复方案文档"
```

## type 类型及语义化版本影响

| type | 用途 | 版本影响 |
|------|------|---------|
| `feat` | 新功能 | **MINOR**（次版本号 +1，修订号归零） |
| `fix` | Bug 修复 | **PATCH**（修订号 +1） |
| `feat!` / `fix!` / `BREAKING CHANGE` | 破坏性变更 | **MAJOR**（主版本号 +1） |
| `docs` / `style` / `refactor` / `perf` / `test` / `chore` / `ci` | 其他 | 不触发版本变更 |

## 规则要求

1. **自动推断 type**：新增功能/接口 → `feat`，修复错误/异常 → `fix`，文档/注释 → `docs`，重构 → `refactor`，依赖/配置 → `chore`
2. **描述使用中文**，简洁明了，不超过 50 字
3. **有破坏性变更时必须标注** `BREAKING CHANGE:` 或在 type 后加 `!`
4. **禁止** `git add .` 或 `git add -A` 全量暂存，必须指定具体文件

## 自动提交行为

- 每次代码编写完成后自动 `git add <具体文件>` + `git commit`，**不推送远程**
- 提交消息严格遵循上述格式

## 版本管理说明

本项目为 monorepo，各子项目独立版本管理：

| 子项目 | 版本文件 | 变更触发 |
|--------|---------|---------|
| 根项目（CHANGELOG） | `CHANGELOG.md` | `feat`/`fix` 必须更新 |
| miniapp | `miniapp/package.json` | `feat` → MINOR，`fix` → PATCH |
| server | `server/pyproject.toml` | `feat` → MINOR，`fix` → PATCH |
| admin | `admin/package.json` | `feat` → MINOR，`fix` → PATCH |

**版本 bump 操作流程**（仅在涉及子项目代码变更时执行）：

```bash
# 1. 先提交代码
git add <具体文件> && git commit -m "<type>(<scope>): <描述>"

# 2. 若需要 bump 版本（feat/fix）
npm version <major|minor|patch> --no-git-tag-version  # 在对应子项目目录执行

# 3. 将版本号变更 amend 到同一提交
git add <版本文件> && git commit --amend --no-edit
```

> **注意**：仅更新 `CHANGELOG.md` / `docs/plans/` 等文档类提交不需要 bump 任何版本号。

## 原子提交原则

> **一个提交只做一件事，一件事完整地放在一个提交里。**

## `--amend` 使用规范

| ✅ 允许 | ❌ 禁止 |
|---------|---------|
| 版本号 bump 合并到同一提交 | 修改已推送的提交（确认无协作者时除外） |
| 漏提交同一逻辑的文件 | 跨任务、跨功能的不同改动合并压缩 |
| 修正提交消息中的笔误 | 用 amend 掩盖错误、频繁 "fix typo" |
| CHANGELOG 更新 amend 到相关提交 | 频繁 amend 历史提交（超过最近 3 个） |

## 禁止的提交模式

```bash
git commit -m "wip"                    # ❌ 无意义消息
git commit -m "tmp save"               # ❌ 无意义消息
git commit -m "fix"                    # ❌ 缺少 scope 和描述
git add . && git commit -m "feat: 大版本更新"  # ❌ 全量暂存 + 海量文件
```

## 文档同步更新

每次 `feat`/`fix` 提交后，**必须**更新 `CHANGELOG.md`，并 amend 到同一提交。

### CHANGELOG.md

| commit type | 是否更新 | CHANGELOG 归类 |
|-------------|:---:|------|
| `feat` | **必须** | `### Added` |
| `fix` | **必须** | `### Fixed` |
| `BREAKING CHANGE` / `feat!` / `fix!` | **必须** | `### Changed`（标注 **BREAKING**） |
| `refactor` / `perf` | 建议 | 按实际变更归类 |
| `docs` / `style` / `test` / `chore` / `ci` | 跳过 | — |

格式遵循 Keep a Changelog，版本号格式：`## [x.y.z] - YYYY-MM-DD`

**CHANGELOG 排序规则（必须遵循）：**

1. **版本之间按倒序排列**：最新版本在最上方，旧版本依次往下
2. **版本内章节按固定顺序排列**：

| 序号 | 章节 | 说明 |
|:---:|------|------|
| 1 | `### Added` | 新增功能 |
| 2 | `### Changed` | 已有功能的变更 |
| 3 | `### Deprecated` | 即将废弃的功能 |
| 4 | `### Removed` | 已移除的功能 |
| 5 | `### Fixed` | Bug 修复 |
| 6 | `### Security` | 安全修复 |

3. **同章节内条目按时间倒序排列**：最新提交在最上方，最早在最下方
4. 未使用的章节直接跳过，不保留空标题
5. CHANGELOG 条目格式：`- <范围> <简述>（<plan编号>）：详细说明`

### README.md / AGENTS.md

- 功能特性/API/部署/环境变量有变更 → **必须**更新 README.md
- 项目结构/API 契约/编码规范有变更 → **必须**更新 AGENTS.md
- 方案进度表有变更 → **必须**更新 AGENTS.md 的项目进度表

### 操作流程

1. 执行 `git add <具体文件>` + `git commit -m "<type>(<scope>): <描述>"`
2. 若涉及子项目代码变更 → bump 版本号（见上文版本管理说明）
3. 若为 `feat`/`fix` → 更新 `CHANGELOG.md`（新增 `## [x.y.z]` 块）
4. 若涉及 API/部署/环境变量/项目结构 → 同步更新 `README.md` / `AGENTS.md`
5. 执行 `git add <文档文件>` + `git commit --amend --no-edit`（将所有变更合并到同一提交）

## 提交前自检

- [ ] 本次提交是否只围绕一个目的？
- [ ] 是否遗漏了相关的文件？
- [ ] 是否有调试代码（`console.log`、临时注释）混入？
- [ ] 提交消息是否符合 `<type>(<scope>): <中文描述>` 格式？
- [ ] 是否使用了具体文件名（而非 `git add .`）？
- [ ] 是否需要更新 CHANGELOG.md？（feat/fix 必须）
- [ ] 是否需要 bump 子项目版本号？（feat/fix 且涉及该子项目代码时）
- [ ] 是否需要更新 README.md / AGENTS.md？（API/部署/结构有变更时）

## 示例

```bash
# 好 ✅
git commit -m "fix(miniapp): 上传视频前检查文件是否存在，修复模拟器临时文件失效报错"
git commit -m "fix(server): 修复骨架视频只含1帧的bug（ffmpeg concat静态图片缺陷）"
git commit -m "docs(plans): 新增 84-骨架视频多帧修复方案文档"

# 不好 ❌
git commit -m "update code"
git commit -m "fix"
git commit -m "wip"
git add . && git commit -m "feat: 修复一堆问题"
```

## 本地历史清理（rebase）

```bash
git rebase -i HEAD~3
# pick 第一个，其余改为 squash / fixup
```

适用于开发过程中产生多个 "wip" 提交需要压缩、提交顺序混乱需要重排等场景。
