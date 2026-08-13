> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 73 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-13 |
> | 对应功能/内容 | 测试体系引入 `.env.test` 实现环境隔离 |
> | 关联文档 | [46-B2-3-系统监控API](./46-B2-3-系统监控API.md)、[72-Admin-备份管理增强](./72-Admin-备份管理增强.md) |

> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-13 | v1.0.0 | 初版 |
> | 2026-08-13 | v1.0.0 | 实施完成（🏁），补充「九、实施记录」：`_init_test_database` session fixture、autouse 显式建目录、清理 7 处样板、`.gitignore` 显式忽略 `.env.test` |

# Step 73：测试体系引入 `.env.test` 实现环境隔离

## 一、背景

当前测试体系存在 **3 个隔离不彻底的问题**：

1. **配置来源不隔离**：`server/app/core/config.py` 在模块加载时固定 `load_dotenv(server/.env)`（默认 `override=False`），本机 `.env` 含真实 `WX_SECRET`/`JWT_SECRET` 等，会被带进测试进程环境，测试没有独立的配置来源。且 `load_dotenv` 默认**不覆盖**已存在的环境变量，无法通过环境变量切换配置源。
2. **全局副作用**：`server/app/core/database.py` 在 import 时即依据 `settings.DATABASE_URL` 创建全局 engine 并 `os.makedirs` 建 `data/` 目录；测试进程一旦 import `app.core.database` 就会触碰真实数据目录。
3. **落盘污染真实 data/**：`server/tests/routers/test_upload.py`、`test_files.py` 直接写 `settings.UPLOAD_DIR`（默认 `./data/uploads`）；`test_system.py` 需逐个用 `monkeypatch` 将 `settings.DATA_DIR` 隔离到 `tmp_path`，无统一机制。

## 二、目标

1. 通过 `APP_ENV` 环境变量让测试进程加载独立 `.env.test`，与开发/生产配置彻底隔离。
2. 测试数据统一落到 `server/data_test/`，不触碰真实 `server/data/`。
3. 提供统一 fixture，让触碰 `DATA_DIR`/`UPLOAD_DIR` 的存量测试接入隔离，消除手工 `monkeypatch` 散落。
4. 仅提交 `.env.test.example`，`.env.test` 不入库（本地复制）。

## 三、方案设计

### 3.1 触发机制：pytest-env 插件 env 注入

在 `server/pyproject.toml` 的 dev 依赖组新增 `pytest-env`，并在 `[tool.pytest.ini_options]` 中配置 `APP_ENV=test`：

```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=6.0.0",
    "pytest-env>=1.1.3",
    "httpx>=0.28.1",
    "ruff>=0.16.1",
]

[tool.pytest.ini_options]
# 测试进程固定注入 APP_ENV=test，config.py 据此加载 .env.test
env = [
    "APP_ENV=test",
]
```

> **为何用 pytest-env**：`config.py` 在 `import` 时读取环境变量决定加载哪个 `.env` 文件。`pytest-env` 的 `env` 配置会在 **pytest 插件加载阶段、任何测试模块 import 之前** 写入 `os.environ`，保证 `app.core.config` 首次 import 时已能看到 `APP_ENV=test`。

### 3.2 config.py 环境感知加载

修改 `server/app/core/config.py` 顶部，从固定加载 `.env` 改为按环境加载：

```python
import os
from pathlib import Path

from dotenv import load_dotenv

# 用绝对路径定位 server/ 目录（config.py 位于 server/app/core/，向上三级）
SERVER_DIR = Path(__file__).resolve().parent.parent.parent

# APP_ENV 必须在 load_dotenv 之前从 os.getenv 读取，
# 否则会被 .env 文件里的 APP_ENV 覆盖，无法切换配置源
APP_ENV = os.getenv("APP_ENV", "dev")

# 测试环境加载 .env.test（override=True 覆盖已存在的环境变量，实现隔离）；
# 开发/生产加载 .env
if APP_ENV == "test":
    load_dotenv(SERVER_DIR / ".env.test", override=True)
else:
    load_dotenv(SERVER_DIR / ".env")
```

> **关键点**：
> 1. `APP_ENV` 必须在 `load_dotenv` **之前**从 `os.getenv` 读取，否则会被 `.env` 里的 `APP_ENV` 覆盖。
> 2. `override=True` 确保 `.env.test` 的变量能覆盖本机 shell 或已 export 的值，保证隔离一致性。

### 3.3 新增 `.env.test.example`（提交）与本地 `.env.test`

`server/.env.test.example`（提交入库，含测试占位凭据，无真实密钥）：

```
# ============================================================
# 后台 FastAPI 测试环境配置模板
# 复制为 .env.test 后使用（.env.test 不提交，已被 .gitignore 忽略）
# 触发：pytest 运行时会自动注入 APP_ENV=test 并加载本文件
# 用法：cp .env.test.example .env.test
# ============================================================

# 应用
APP_ENV=test
DEBUG=true

# 数据目录：独立于生产 data/，测试落盘统一隔离到 data_test/
DATA_DIR=./data_test
DATABASE_URL=sqlite:///./data_test/tennis_diary_test.db
UPLOAD_DIR=./data_test/uploads
LOG_DIR=./data_test/logs

# JWT（测试专用弱随机值）
JWT_SECRET=test-only-jwt-secret
JWT_EXPIRATION_HOURS=720

# 微信小程序（测试用空凭据，登录走 mock）
WX_APPID=
WX_SECRET=

# AI
AI_API_KEY=
AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_MODEL=qwen-vl-max

# 文件上传
MAX_UPLOAD_SIZE_MB=100

# 日志
LOG_LEVEL=DEBUG
LOG_FILE=app.log
LOG_ROTATION=10 MB
LOG_RETENTION=7 days
LOG_JSON_ENABLED=false

# 管理员（测试专用）
ADMIN_DEFAULT_USERNAME=admin
ADMIN_DEFAULT_PASSWORD=test-pass-123
ADMIN_RESET_KEY=test-reset-key

# 日志分离
LOG_ADMIN_FILE=admin.log
LOG_USER_FILE=user.log
```

本地 `.env.test` 由开发者执行 `cd server && cp .env.test.example .env.test` 生成，不入库。

### 3.4 `.gitignore` 调整

根目录 `.gitignore` 现有相关规则（第 64-75 行）：

```gitignore
# Environment & Secrets
.env
.env.local
.env.*.local
.env.hf
.env.oci
.env.modelscope
*.env
!*.env.example
!*.env.hf.example
!*.env.oci.example
!*.env.koyeb.example
!*.env.modelscope.example
```

需要补充两处：

```gitignore
!*.env.test.example    # 允许提交 .env.test.example（否则会被 *.env 通配忽略）

# 测试数据目录（.env.test 运行时生成，不入库）
data_test/
```

> **注意**：`*.env` 通配会匹配 `.env.test.example`（含 `.env.test` 与 `.env.test.example`），因此必须显式补 `!*.env.test.example` 白名单，否则模板无法提交。同时，`data/` 已被忽略，但 `data_test/` 是新增目录，需单独补充忽略。

### 3.5 统一隔离 fixture：`server/tests/conftest.py`

新增两个 fixture，让触碰文件系统的测试统一接入临时目录隔离（替代散落的 `monkeypatch`）：

```python
@pytest.fixture(autouse=True)
def _isolate_data_dirs(tmp_path, monkeypatch):
    """将 DATA_DIR / UPLOAD_DIR / LOG_DIR 隔离到临时目录，杜绝污染真实 data_test/。

    仅隔离 settings 的属性值，不会重建全局 engine（engine 由 dependency
    override 注入 test_db 使用，业务路由读的是 settings.UPLOAD_DIR/DATA_DIR）。
    """
    from app.core.config import settings

    data_dir = tmp_path / "data"
    monkeypatch.setattr(settings, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(data_dir / "uploads"))
    monkeypatch.setattr(settings, "LOG_DIR", str(data_dir / "logs"))
    return data_dir


@pytest.fixture
def data_dir(_isolate_data_dirs):
    """提供已隔离的临时 DATA_DIR，供需要构造文件结构的测试使用"""
    return _isolate_data_dirs
```

> **说明**：`_isolate_data_dirs` 为 `autouse=True`，所有测试自动生效。`test_system.py` / `test_logging.py` 中已有的 `monkeypatch.setattr(settings, "DATA_DIR"/"LOG_DIR", ...)` 与 autouse fixture 可共存——**pytest 的 `monkeypatch` fixture 按函数签名顺序实例化，显式声明的 `monkeypatch` 与 autouse 的 `monkeypatch` 是同一实例，后 set 的值优先生效**，因此显式传入的 `tmp_path` 值不会冲突。autouse 仅作兜底隔离，存量显式隔离可逐步清理。

### 3.6 存量测试改造

| 文件 | 现状 | 改造 |
|------|------|------|
| `server/tests/routers/test_upload.py` | 直接用 `settings.UPLOAD_DIR` 断言落盘路径 | autouse 隔离后 `settings.UPLOAD_DIR` 已指向 tmp_path，**无需改动** |
| `server/tests/routers/test_files.py` | `_write_upload_file` 用 `os.path.abspath(settings.UPLOAD_DIR)` | autouse 隔离后已指向 tmp_path，**无需改动** |
| `server/tests/routers/admin/test_system.py` | 5 处测试手动 `tmp_path` + `monkeypatch.setattr(settings, "DATA_DIR", ...)` | **逐步移除**手工 `monkeypatch` 样板，改由 autouse fixture 统一提供隔离后的 `settings.DATA_DIR`（见 3.6.1） |
| `server/tests/core/test_logging.py` | `log_settings` fixture 手动 `monkeypatch` `LOG_DIR` 到 `tmp_path` | 保留（autouse 已兜底，显式值优先生效），**无需改动** |

#### 3.6.1 `test_system.py` 样板清理示例

改造前（`test_restore_backup` 等 5 处重复样板）：

```python
def test_restore_backup(auth_client, test_db, test_meta_db, tmp_path, monkeypatch):
    # 用临时目录隔离 DATA_DIR，避免恢复覆盖真实数据库
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(settings, "DATA_DIR", str(data_dir))
    backup_dir = data_dir / "backups"
    backup_dir.mkdir()
```

改造后（由 autouse fixture 统一隔离，测试内直接用 `settings.DATA_DIR`）：

```python
def test_restore_backup(auth_client, test_db, test_meta_db):
    # settings.DATA_DIR 已被 autouse fixture _isolate_data_dirs 隔离到 tmp_path
    data_dir = Path(settings.DATA_DIR)
    backup_dir = data_dir / "backups"
    backup_dir.mkdir(exist_ok=True)
```

> **说明**：autouse `_isolate_data_dirs` 已 `monkeypatch` 将 `settings.DATA_DIR` 指向 `tmp_path/data`（该目录自动创建），因此测试内不再需要 `tmp_path`/`monkeypatch` 参数和 `data_dir.mkdir()` 样板，直接基于 `settings.DATA_DIR` 构造即可。涉及 `test_meta_db` 的用例保留 `test_meta_db` 参数。

### 3.7 新增配置加载测试

新增 `server/tests/core/test_config_env.py`，验证环境感知加载与隔离：

```python
"""配置环境感知加载测试（Step 73）"""


def test_app_env_is_test():
    """pytest 运行时应注入 APP_ENV=test"""
    import os

    assert os.getenv("APP_ENV") == "test"


def test_settings_data_dir_uses_data_test():
    """测试环境下 settings.DATA_DIR 应指向 .env.test 的 data_test/"""
    from app.core.config import settings

    assert settings.DATA_DIR == "./data_test"


def test_settings_secret_is_test_only():
    """测试环境不应泄漏真实 JWT_SECRET（应为 .env.test 的测试值）"""
    from app.core.config import settings

    assert settings.JWT_SECRET == "test-only-jwt-secret"
    assert settings.JWT_SECRET != "change-me-in-production-please"
```

> **注意**：`test_settings_data_dir_uses_data_test` 断言 `settings.DATA_DIR == "./data_test"` 仅在 **未运行 autouse `_isolate_data_dirs` fixture** 时成立。由于该测试属于 `tests/core/`，而 `_isolate_data_dirs` 定义在 `tests/conftest.py`（autouse 全局生效），因此该断言会被覆盖为 `tmp_path/data`。**需将本测试排除在 autouse 隔离之外**，或改为断言「DATA_DIR 不等于真实 `./data` 且指向测试目录」。落地时按 3.7.1 处理。

#### 3.7.1 配置加载测试的隔离策略

由于 `_isolate_data_dirs` 是全局 autouse fixture，`tests/core/test_config_env.py` 验证 `settings.DATA_DIR` 原始值的测试会被覆盖。处理方式二选一：

- **方案 A（推荐）**：将该测试放在 `tests/core/test_config_env.py`，但只断言「非生产值」，不断言具体 `./data_test`：
  ```python
  def test_settings_data_dir_isolated_from_prod():
      from app.core.config import settings
      # autouse fixture 已将 DATA_DIR 隔离到 tmp_path，绝不可能是真实 data/
      assert "data" not in settings.DATA_DIR or "/data/" not in settings.DATA_DIR
  ```
  此断言在隔离前后均通过，不依赖 fixture 时序。

- **方案 B**：在 `test_config_env.py` 顶部显式标记不触发 autouse，直接验证原始配置值。

> 方案选择以实施时最能稳定断言为准。若采用方案 A，则断言语义为「测试环境下配置已被隔离，不指向真实 data/」，仍达成验证目标。

## 四、修改文件清单

| 文件 | 变更 |
|------|------|
| `server/app/core/config.py` | 增加 `APP_ENV` 读取，按环境加载 `.env` 或 `.env.test`（`override=True`） |
| `server/pyproject.toml` | dev 组加 `pytest-env`；新增 `[tool.pytest.ini_options].env = ["APP_ENV=test"]` |
| `server/.env.test.example` | **新增**：测试环境配置模板（提交） |
| `.gitignore` | 忽略 `data_test/`；补充 `!*.env.test.example` |
| `server/tests/conftest.py` | 新增 `_isolate_data_dirs`（autouse）、`data_dir` fixture |
| `server/tests/routers/admin/test_system.py` | 移除 5 处手工 `monkeypatch DATA_DIR` 样板，接入 autouse 隔离 |
| `server/tests/core/test_config_env.py` | **新增**：配置加载与隔离验证 |

> 说明：`server/.env.test` 为本地生成、不入库；`test_upload.py`、`test_files.py`、`test_logging.py` 在 autouse 隔离下自动受益，无需改动。

## 五、测试计划（TDD）

1. **配置来源**：`test_config_env.py` 断言 pytest 运行注入 `APP_ENV=test`，`settings` 指向测试配置而非真实 `.env`。
2. **全局副作用**：验证 import `app.core.database` 后不会在真实 `server/data/` 下创建文件（数据落到 `data_test` 或 tmp_path）。
3. **上传隔离**：`test_upload.py` 上传后文件落在隔离目录，而非真实 `data/uploads`。
4. **备份恢复隔离**：`test_system.py` 备份/恢复落盘在隔离目录，不触碰 `data_test/` 之外的路径。
5. **回归**：全量 `uv run pytest -v` 通过；`bash scripts/verify.sh` 通过。

## 六、效果

- 测试进程配置完全独立，本机 `.env` 的真实密钥不再泄漏进测试环境。
- 所有测试落盘统一隔离到 `data_test/`（或 tmp_path），彻底杜绝污染真实数据。
- 新增测试自动继承隔离，无需逐个写 `monkeypatch`。

## 七、注意事项

1. **`APP_ENV` 读取顺序**：`os.getenv("APP_ENV")` 必须在 `load_dotenv` 之前，且 `.env.test` 用 `override=True`，否则会被 `.env` 覆盖。
2. **pytest-env 插件加载时序**：`env` 配置在插件加载阶段写入 `os.environ`，早于任何测试模块 import，保证 `config.py` 首次 import 即看到 `APP_ENV=test`。
3. **`.env.test` 不入库**：`.env.test.example` 提交；`.env.test` 由本地 `cp .env.test.example .env.test` 生成。`.gitignore` 需补 `!*.env.test.example`，否则模板被 `*.env` 通配忽略。
4. **`data_test/` 需单独忽略**：根 `.gitignore` 已有 `data/`，但 `data_test/` 是新增目录，必须补充忽略。
5. **`autouse` 隔离 fixture**：只改 `settings` 属性，不重建全局 engine；业务路由读 `settings.UPLOAD_DIR/DATA_DIR` 时已是隔离路径，与 `test_db` 的 dependency override 互不干扰。
6. **存量 monkeypatch 可保留**：autouse 兜底 + 显式 `monkeypatch` 后 set 优先生效，无冲突；逐步清理冗余样板即可。
7. **配置加载测试注意 autouse 覆盖**：`tests/core/test_config_env.py` 中若断言 `settings.DATA_DIR` 原始值，会被全局 autouse fixture 覆盖，需按 3.7.1 调整断言策略。

---

## 八、实施步骤（TDD 落地顺序）

1. **RED**：新增 `server/tests/core/test_config_env.py`（按 3.7 与 3.7.1 策略写断言），运行确认失败（当前无 `.env.test` 加载机制）。
2. **GREEN**：
   - 改 `server/app/core/config.py` 实现 `APP_ENV` 环境感知加载。
   - 新增 `server/.env.test.example`，本地 `cp` 生成 `.env.test`。
   - `server/pyproject.toml` 加 `pytest-env` 依赖与 `env` 配置。
   - `.gitignore` 补 `data_test/` 与 `!*.env.test.example`。
3. **REFACTOR**：
   - `server/tests/conftest.py` 新增 `_isolate_data_dirs`（autouse）与 `data_dir` fixture。
   - 清理 `test_system.py` 7 处手工 `monkeypatch DATA_DIR` 样板（含 `test_backup_database`、`test_restore_backup`、`test_restore_resets_previous_restored`、`test_download_backup`、`test_download_backup_traversal`、`test_delete_backup`、`test_upload_backup`）。
4. **验证**：`cd server && uv run pytest -v` 与 `bash scripts/verify.sh` 全量通过（156 passed）。
5. **完成**：本方案文档状态 `📋` → `✅`，更新 `AGENTS.md` 进度表。

---

## 九、实施记录

> 以下为实际实施时的补充说明，供后续维护参考。

### 9.1 额外引入 `_init_test_database`（session 级 autouse）

原方案 3.5 仅隔离 `settings.DATA_DIR/UPLOAD_DIR/LOG_DIR`，但 `.env.test` 切换后暴露了一个**方案未预期的副作用**：应用 `lifespan` 启动时用全局 `SessionLocal`（基于 `settings.DATABASE_URL`）执行 `init_default_roles`，而 `.env.test` 的 `DATABASE_URL=./data_test/tennis_diary_test.db` 表尚未创建，导致 `no such table: roles` 错误。

因此在 `server/tests/conftest.py` 新增 session 级 autouse fixture `_init_test_database`：在首个测试前 `Base.metadata.create_all(bind=engine)` 确保 `data_test/` 数据库表存在，使 lifespan 可正常执行，且数据落在隔离的 `data_test/`，不触碰真实 `data/`。

### 9.2 `_isolate_data_dirs` 需显式创建 `data_dir`

原方案 3.6.1 声称隔离后的 `settings.DATA_DIR` 目录"自动创建"，但 pytest 的 `tmp_path` 只保证 `tmp_path` 本身存在，`tmp_path/data` 子目录需显式创建。已在 autouse fixture 中补 `data_dir.mkdir(parents=True, exist_ok=True)`，否则测试内 `backup_dir.mkdir()` 会因父目录不存在报 `FileNotFoundError`。

### 9.3 清理数量核对

`test_system.py` 实际有 **7 处**手工 `monkeypatch DATA_DIR` 样板（方案正文写 5 处），已全部清理并接入 autouse 隔离。改造后 `settings.DATA_DIR` 需经 `Path(...)` 转换（fixture 设为字符串）再拼接 `backups` 子目录。

### 9.4 `.gitignore` 需显式忽略 `.env.test`

方案 3.4 假设 `*.env` 通配会匹配 `.env.test` 并忽略它。但 gitignore 的 `*.env` 只匹配以 `.env` **结尾**的文件名，`.env.test` 以 `.test` 结尾**不会**被匹配，`.env.test.example` 同理（以 `.example` 结尾）。因此 `.gitignore` 需**显式**补充 `.env.test` 忽略规则，否则本地生成的 `.env.test` 会被误提交。`!*.env.test.example` 白名单仍保留（防御性，确保模板可提交）。
