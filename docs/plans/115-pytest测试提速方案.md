> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 115 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-08-27 |
> | 对应功能/内容 | 后端 pytest 测试提速：内存库 + session 级 client + xdist 并行 + testmon + fast 分层门禁 + 全量 CI |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-27 | v1.0.0 | 初版，汇总 pytest 全链路提速方案与落地过程 |
>
> **关联文档**：[73：测试体系引入 `.env.test` 实现环境隔离](./73-测试体系引入-env-test实现环境隔离.md) · [101：后端日志细化与异常静默处理修复](./101-后端日志细化与异常静默处理修复.md)

# 115：pytest 测试提速方案

## 一、背景与目标

后端测试套件在迭代中增长到 **494 个用例**，单次全量运行在单核环境下耗时接近 **12 分钟**，导致：

- 提交门禁（`pre-commit`）卡顿，开发者每次提交都要等待数分钟；
- 本地全量回归成本高，开发者不愿跑，回归信心下降。

目标：在不降低覆盖率、不删除用例的前提下，把**提交门禁**压到秒级、把**本地/CI 全量**压到 1 分钟以内，并沉淀一套可持续的工程结构。

## 二、诊断过程

### 2.1 基线测量

直接串行运行全量（`uv run pytest`）在多核开发机预估 12 分钟级，远超可接受范围。用小批量抽样定位瓶颈：

| 抽样文件 | 用例数 | 串行耗时 | 单用例均值 |
|---------|:----:|:------:|:--------:|
| `tests/routers/test_auth.py` | 13 | 24.4s | ~1.9s |
| `tests/routers/test_diaries.py` | 11 | 20.0s | ~1.8s |
| `tests/test_debug_ai_script.py` | 5 | 0.09s | ~0.02s |

结论：慢用例集中在**依赖 DB / TestClient 的集成测试**；纯函数/模型/校验类测试本就极快。

### 2.2 瓶颈拆解（每个用例的固定开销）

1. **临时文件 SQLite 的 create/drop/unlink**：`test_engine` fixture 每用例创建临时文件库、建表、拆表、删文件，I/O 开销大。
2. **TestClient 重复触发 lifespan**：`client` fixture 为 `function` 级，每次都 `TestClient(app)` → 触发 `lifespan` → 重复执行默认角色/管理员初始化（命中 `data_test` 文件库 494 次）。
3. **单进程串行**：无并行，494 用例排队执行。

### 2.3 额外排查（重依赖顶层 import）

用 `grep` 排查 `mediapipe` / `matplotlib` / `torch` / `cv2` 顶层 import：

- `mediapipe` 在 `app/services/pose_service.py` 中**已是函数内懒加载**（仅在推理路径 import）；
- `app` 中**无任何 `matplotlib` 顶层 import**（`system.py` 仅用 `importlib.util.find_spec` 探测是否安装）；
- 因此「重依赖顶层加载拖慢 import」的假设不成立，无需改动。

## 三、优化措施

### 3.1 内存库 + StaticPool（消除每用例文件 I/O）

`tests/conftest.py` 的 `test_engine` 由临时文件库改为**内存库 + `StaticPool`**：

```python
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=engine)
```

`StaticPool` 保证单连接、规避 `:memory:` 跨线程 "no such table" 问题；每个用例仍是独立引擎，隔离性不变。代价：不再需要 `tempfile`/`os.unlink`，省去文件 I/O。

### 3.2 session 级 TestClient（lifespan 只跑一次）

原 `client` 为 `function` 级，每次创建 `TestClient(app)` 都会触发 `lifespan`。改为：

- 新增 session 级 fixture `_app_client`，整个测试会话只 `with TestClient(app)` 一次（lifespan 仅执行一次）；
- `client` 仍保持 `function` 级，仅负责**每用例设置/清理** `get_db` 等依赖 override，底层复用 `_app_client`；
- `_app_client` 显式依赖 `_init_test_database`，保证建表先于 lifespan 初始化。

效果：默认数据初始化从 494 次降为 1 次。

### 3.3 pytest-xdist 并行

新增依赖 `pytest-xdist`，全量用 `-n auto` 并行。8 核开发机上全量从 ~12min 降到 ~50s。

### 3.4 pytest-testmon（只跑受影响用例）

新增依赖 `pytest-testmon`。基于上次覆盖率缓存，仅重跑被改动代码影响的用例：

```bash
uv run pytest -n auto --testmon
```

首次/大改会跑全量以重建 `.testmondata` 缓存；之后小改动只跑个位数用例（实测工作区有缓存时 6s 完成）。`.testmondata` 已加入 `server/.gitignore`。

> 注意：在**每次提交都重建、且单核的沙箱门禁**中，缓存不持久，`--testmon` 会退化成全量，对门禁无效（见 3.5 / 第四节）。

### 3.5 fast 分层 + 提交门禁只跑轻量子集

行业做法是「pre-commit 跑快子集、CI 跑全量」。本仓库落地为：

1. 为 5 个纯函数/模型/校验类模块打 `pytestmark = pytest.mark.fast`（共 45 用例，不依赖 DB 与 TestClient）：
   - `tests/core/test_config_env.py`
   - `tests/core/test_dirs.py`
   - `tests/models/test_models_registry.py`
   - `tests/schemas/test_schemas.py`
   - `tests/test_debug_ai_script.py`
2. 在 `pyproject.toml` 的 `[tool.pytest.ini_options]` 注册 `fast` marker（消除未知标记警告）。
3. **真正的提交门禁** `.githooks/pre-commit`（项目设了 `core.hooksPath=.githooks`）的 pytest 步骤改为：

   ```bash
   uv run pytest -q -n auto -m fast
   ```

   仅跑 45 个轻量用例，秒级完成。

> ⚠️ 排查教训：此前误改 `scripts/verify.sh`，但提交门禁实际由 `.githooks/pre-commit` 驱动，`verify.sh` 只是独立脚本，门禁从不调用。改对位置后才生效。

### 3.6 全量并行移交 CI

新增 `.github/workflows/test-server.yml`：在 `push`/`pull_request` 到 `dev`/`master` 且改动 `server/**` 时，自动 `uv sync` + `ruff` + `uv run pytest -n auto` 跑全量（约 50s），承接门禁放行后的全量回归。

## 四、关键发现与坑

1. **门禁位置**：提交门禁是 `.githooks/pre-commit`（非 `verify.sh`、非 `AGENTS.md` 文本）。任何想影响门禁的改动必须改这个 hook 文件。
2. **沙箱约束**：门禁运行环境为**单核 + 工作区不持久**，因此 `-n auto` 只能起 1 个 worker、`--testmon` 无缓存可复用 → 二者都无法加速门禁；只有「减少门禁实际运行的用例数」（`-m fast`）才有效。
3. **重依赖已懒加载**：`mediapipe` 函数内 import、`app` 无 `matplotlib` 顶层 import，无需额外优化。

## 五、成果对比

| 场景 | 优化前 | 优化后 | 提速 |
|------|------|------|:----:|
| 单核串行全量（门禁原路径） | ~12 min | ~119s（内存库+session client 后仍约 2min，受单核地板限制） | ~6x |
| 多核并行全量（`-n auto`） | ~12 min | ~50s | ~14x |
| 本地受影响用例（`--testmon`，有缓存） | ~12 min | ~6s | 量级提升 |
| **提交门禁（`.githooks/pre-commit -m fast`）** | ~119s | ~7s | **~17x** |

> 单核全量的 ~2min 已是 ~0.24s/用例的地板（494 用例），无法仅靠代码继续下压；进一步提速需平台侧给门禁多核/持久工作区，或继续减少全量用例规模（不推荐）。

## 六、使用方式速查

```bash
# 提交门禁（自动，仅 fast 子集，秒级）：.githooks/pre-commit

# 本地全量并行（推荐日常）
cd server && uv run pytest -n auto

# 本地只跑受影响用例（需先有一次全量建缓存）
cd server && uv run pytest -n auto --testmon

# 本地只跑快子集（等价于门禁）
cd server && uv run pytest -m fast

# CI 全量（push/PR 自动触发 .github/workflows/test-server.yml）
```

## 七、后续可优化方向（未实施）

1. **门禁环境多核化**：若平台支持为提交门禁分配多核 + 持久工作目录，`-n auto` 与 `--testmon` 即可在门禁生效，无需 `-m fast` 子集。
2. **`httpx.ASGITransport` 直连**：绕过 `TestClient` 的 lifespan/端口开销，进一步压低每用例固定成本（已有 session 级 client 缓解，收益有限）。
3. **按成本自动分层**：用 pytest 插件按 fixture 依赖自动识别「免 DB」用例并打标，减少手工维护 `fast` 列表的成本。
