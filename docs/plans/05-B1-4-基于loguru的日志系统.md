> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 05-B1-4 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-05 |
> | 对应功能/内容 | 基于 loguru 的日志系统 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-05 | v1.0.0 | 初版 |
>
> **关联文档**：[Tennis Diary 迁移微信小程序分析](./01-tennis-diary-迁移微信小程序分析.md) · [B1-2：核心配置模块](./03-B1-2-核心配置模块.md)

# Step B1-4：基于 loguru 的日志系统

## 一、目标

为 FastAPI 后台引入统一的日志系统，基于 **loguru** 实现控制台 + 文件双输出，支持级别过滤、按大小滚动、按时间保留，并接入启动流程与鉴权路由作为示范。

## 二、前置条件

- B1-2 完成（核心配置 `config.py` + 目录管理 `dirs.py`）

## 三、设计说明

### 3.1 技术选型

采用 **loguru**（替代标准库 `logging`），理由：

- 开箱即用的格式化、颜色、异常回溯（`backtrace`/`diagnose`）
- 文件滚动切割（`rotation`）与保留策略（`retention`）一行配置
- 线程/异步安全（`enqueue=True`）
- 统一 `logger` 单例，避免各模块重复初始化

### 3.2 双输出架构

| 输出 | 目标 | 说明 |
|---|---|---|
| 控制台 | `sys.stderr` | 便于容器 stdio 采集，`colorize=True` |
| 文件 | `{LOG_DIR}/{LOG_FILE}` | 落盘，按大小滚动 + 按时间保留 |

### 3.3 幂等初始化

`setup_logging()` 先 `logger.remove()` 清空默认 handler，再添加新 handler，保证多次调用不重复添加。模块在 import 时即调用 `setup_logging()`，确保任何模块 `from app.core.logging import logger` 拿到的都是已配置好的 logger。

## 四、详细执行步骤

### 4.1 配置项（`app/core/config.py`）

| 配置项 | 环境变量 | 默认值 | 说明 |
|---|---|---|---|
| LOG_LEVEL | LOG_LEVEL | INFO | 日志级别（DEBUG 下为 DEBUG） |
| LOG_DIR | LOG_DIR | `{DATA_DIR}/logs` | 日志目录 |
| LOG_FILE | LOG_FILE | app.log | 日志文件名 |
| LOG_ROTATION | LOG_ROTATION | 10 MB | 文件滚动切割大小 |
| LOG_RETENTION | LOG_RETENTION | 7 days | 日志保留时长 |
| LOG_FORMAT | LOG_FORMAT | 自定义格式 | 日志输出格式 |

### 4.2 目录管理（`app/core/dirs.py`）

在 `ensure_dirs()` 末尾创建 `settings.LOG_DIR` 目录（`os.makedirs(..., exist_ok=True)`）。

### 4.3 日志核心模块（`app/core/logging.py`，新增）

- `setup_logging()`：幂等初始化，控制台 + 文件双 handler
- 模块 import 时自动调用 `setup_logging()`

### 4.4 启动流程（`app/main.py`）

在 `ensure_dirs()` 之后显式调用 `setup_logging()`（幂等）。

### 4.5 路由接入示范（`app/routers/auth.py`）

- 登录成功：`logger.info(...)`
- 异常：`logger.error(...)`

### 4.6 依赖（`pyproject.toml`）

添加 `loguru>=0.7.2` 到生产依赖。

### 4.7 环境变量示例（`.env.example`）

补充 `LOG_LEVEL`/`LOG_ROTATION`/`LOG_RETENTION` 等配置示例。

## 五、TDD 测试用例（`server/tests/core/test_logging.py`）

| 编号 | 用例 | 断言 |
|---|---|---|
| 1 | test_setup_logging_adds_handlers | handler 数量 ≥ 2 |
| 2 | test_log_file_created | 日志文件存在 |
| 3 | test_level_from_config | 级别过滤生效 |
| 4 | test_rotation_config_applied | rotation 参数等于配置值 |
| 5 | test_logger_sink_to_file | 日志内容写入文件 |
| 6 | test_idempotent | 连续调用两次 handler 不翻倍 |
| 7 | test_auth_router_logs_login | mock `code_to_openid`，断言日志含关键字 |

> 测试环境注意：用 `monkeypatch.setattr(settings, "LOG_DIR", str(tmp_path))` 避免污染真实磁盘；`enqueue=True` 下必要时调用 `logger.complete()` 确保日志落盘。

## 六、产出物

| 操作 | 文件 | 说明 |
|---|---|---|
| 新增 | `server/app/core/logging.py` | 日志核心模块 |
| 修改 | `server/app/core/config.py` | 增加日志配置项 |
| 修改 | `server/app/core/dirs.py` | 创建 logs 目录 |
| 修改 | `server/app/main.py` | 启动时初始化日志 |
| 修改 | `server/app/routers/auth.py` | 接入 logger |
| 修改 | `server/pyproject.toml` | 添加 loguru 依赖 |
| 修改 | `server/.env.example` | 日志配置示例 |
| 新增 | `server/tests/core/test_logging.py` | TDD 测试 |

## 七、验收标准

- [ ] 启动后生成 `data/logs/app.log` 含启动日志
- [ ] `LOG_LEVEL`/`LOG_ROTATION`/`LOG_RETENTION` 可用环境变量调整
- [ ] 日志按大小滚动、按时间保留
- [ ] 全量 pytest 通过，`logging.py` 覆盖率 ≥ 80%
- [ ] `ruff` 无告警
- [ ] 方案文档状态更新为 ✅

## 八、提交拆分

1. `chore(server): 添加 loguru 依赖与日志配置项` — config + dirs + pyproject + .env.example
2. `feat(server): 实现 loguru 日志核心模块并接入启动流程` — logging.py + main.py
3. `test(server): 补充日志系统单元测试` — test_logging.py
4. `feat(server): 在鉴权路由接入日志` — auth.py
