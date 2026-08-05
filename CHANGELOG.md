# Changelog

本项目的所有显著变更均记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.11.0] - 2026-08-05

### Added

- 实现体重记录接口（`/api/weights`）：列表 / 添加 / 删除，强制用户归属校验

## [1.10.0] - 2026-08-05

### Added

- 实现装备 CRUD 接口（`/api/gears`）：列表 / 添加 / 详情 / 编辑 / 删除，强制用户归属校验

## [1.9.0] - 2026-08-05

### Added

- 实现日记 CRUD 接口（`/api/diaries`）：列表 / 创建 / 详情 / 编辑 / 删除，强制用户归属校验（B1 数据层首块）

## [1.8.0] - 2026-08-05

### Added

- 鉴权路由接入日志：登录成功 / 无效 code / code2session 异常均有日志输出

## [1.7.0] - 2026-08-05

### Added

- 后台新增基于 loguru 的统一日志系统（`app/core/logging.py`）：控制台 + 文件双输出，支持级别过滤、按大小滚动、按时间保留

## [1.6.0] - 2026-08-05

### Added

- 实现微信登录鉴权接口（`POST /api/auth/login`）：接收 `wx.login` code，换取 openid，自动创建用户并签发 JWT；新增 `GET /api/auth/me` 获取当前用户

## [1.5.0] - 2026-08-05

### Added

- 完善 Pydantic Schemas 并添加验证测试

## [1.4.0] - 2026-08-05

### Added

- 启动时自动创建运行时数据目录（`ensure_dirs`）

## [1.3.0] - 2026-08-05

### Added

- 统一 `data` 目录管理运行时数据（数据库 + 上传文件），新增 `.env.example` 配置模板

### Fixed

- 数据目录管理统一为 `data/`，避免数据库与上传文件分散

## [1.2.0] - 2026-08-05

### Added

- 引入 TDD 测试框架（pytest + httpx TestClient），补充 auth 与 models 单元测试

## [1.1.0] - 2026-08-05

### Added

- FastAPI 项目初始化：包含 ORM 模型（Diary / Gear / Weight / Analysis / Checkin / Post / User）、核心配置、uv 依赖管理

## [1.0.0] - 2026-08-05

### Added

- 初始化项目基础设施（gitignore / pnpm 工作区 / VitePress 文档站点配置）

---

**docs / test / chore 类型提交**（不触发版本变更，随所属功能版本记录）：

- `docs: 新增 B1-4 基于 loguru 的日志系统方案`
- `test(server): 补充日志系统单元测试`
- `docs(plans): 新增 Phase B1 后台执行方案文档及侧边栏配置`
- `docs: 添加 VitePress 文档站点与 Tennis Diary 迁移分析方案`
- `docs: 新增 README.md 和 AGENTS.md 项目文档`
