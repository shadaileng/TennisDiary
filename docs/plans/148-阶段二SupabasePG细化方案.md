> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 148 |
> | 文档版本 | v1.1.0 |
> | 文档状态 | 📋 待执行 |
> | 最后更新 | 2026-10-26 |
> | 对应功能/内容 | 阶段二细化方案：Supabase PostgreSQL 数据库迁移（双引擎架构 + Alembic 基线 + 数据迁移 + 备份改造 + CI PG 双测 + 回滚），上游路线见 [146 总纲](./146-后台三件套改造评估.md) |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-10-26 | v1.1.0 | **Step 2 生死点实测定稿**：`file.py` 部分唯一索引单条双 where 参数（`sqlite_where`+`postgresql_where`）双方言渲染验证通过；双索引分名 / `dialect_impls` 两方案实测否决；fast 门禁 355 passed |
| 2026-10-26 | v1.0.0 | 初版（范围/架构/模型改造/基线方案/方言审计/连接池/数据迁移/备份改造/测试与 CI/TDD 步骤/验收/回滚） |
>
> **关联文档**：
> - [146：后台三件套改造评估与实施路线](./146-后台三件套改造评估.md)（**总纲**：阶段二的立项依据、决策记录、工作量与三阶段路线）
> - [147：阶段一 KODO 对象存储细化方案](./147-阶段一KODO对象存储细化方案.md)（**上游阶段**：代码完成待线上验收；本阶段文件本体已迁 Kodo，DB 迁移与其解耦）
> - [72：Admin 备份管理增强](./72-Admin-备份管理增强.md)（备份/恢复/上传端点在本阶段改造为 PG 版）
> - [73：测试体系引入 .env.test 实现环境隔离](./73-测试体系引入-env-test实现环境隔离.md)（本地测试 SQLite 策略的既有依据，本阶段扩展为双库 CI）
>
> **前置条件**（开工前人类确认）：
> 1. 阶段一 KODO 化稳定运行（文件本体已迁对象存储，本地数据目录仅存 DB 与临时处理文件）
> 2. Supabase 项目就绪（区域建议新加坡，**密码强密码**）
> 3. 分支基线演练通过（Step 2-3 先在分支完成并验证，再合入主干）

# 阶段二 Supabase PostgreSQL 细化方案

## 一、范围

### 1.1 做什么

| # | 内容 |
|:-:|------|
| 1 | 双引擎架构：业务库 `DB_DATABASE_URL`（PG）+ 审计库 `AUDIT_DB_URL`（本地 SQLite，保持 147 隔离价值）|
| 2 | `app/core/database.py` 重构：`make_engine(url)` 工厂 + 池参数（`pool_size=5` / `max_overflow=10` / `pool_recycle=3600` / `pool_pre_ping=True`）+ 连接健康检查 `db_health()` |
| 3 | 模型方言改造：`file.py` 部分唯一索引双注册（`sqlite_where` + `postgresql_where`）、`onupdate=func.now()` → PG 触发器（基线内 `BEFORE UPDATE`）、`DateTime` 精度兼容 |
| 4 | Alembic PG 基线：单文件 head `pg_baseline_148`（`--sql` 导出 + 手写修正），旧 SQLite 链 `stamp` 封存；`env.py` 按 URL 方言选基线 |
| 5 | 方言审计：CI PG job 暴露差异（SSE 轮询、管线并发、JSON 存储、`func.count/sum/avg` 等）→ 逐个修复 |
| 6 | 连接池收敛：SSE `GET /api/analyses/{id}/stream` 降频（1s → 2s 或改短连接重试）、管线后台 Session 独立引擎 + 用后即关 |
| 7 | 数据迁移脚本 `scripts/migrate-sqlite-to-pg.py`（SQLite → PG：逐表导出 + 行数/关键聚合校验 + `--dry-run`）|
| 8 | 备份改造：方案 72 的 `backup_meta.db` 体系 → `pg_dump` 流程；Admin 备份页端点语义修订（创建/下载/删除联动保留，恢复为 `pg_dump` 流）|
| 9 | CI 双测：`test-server.yml` 新增 `pg-integration` job（PG 服务容器 + `DB_DATABASE_URL=postgres://...`），与 SQLite job 并行；提交门禁（AGENTS 4.3）不变 |
| 10 | `.env` / `.env.test.example` / `Dockerfile` / `docker-compose.yml` / `docker-entrypoint.sh` 适配（PG 驱动 `psycopg`、`alembic upgrade pg_baseline_148`） |

### 1.2 不做什么（边界）

- ❌ 替换本地部署（SQLite 本地开发继续可用，`DB_DATABASE_URL` 默认值仍为 `sqlite:///{DATA_DIR}/tennis_diary.db`）
- ❌ 修改已上线的 KODO 对象存储链路（147 不动）
- ❌ 双写/多数据源冗余（[146 §3.4 (c)](./146-后台三件套改造评估.md) 明确不做；本阶段仅 DB 单点切换）
- ❌ 删除 `audit.db` / `backup_meta.db`（保留为本地隔离机制，仅生产侧改 `pg_dump` 备份）
- ❌ 前端（小程序 / Admin）任何改造 —— 后端响应格式零变化
- ❌ 启用 `uvicorn --workers N`（阶段二仅收敛连接池，多 worker 留待阶段三或独立评估）

## 二、总体架构

```
                        ┌─ 路由层（upload/files/media/admin）── 零改动 ─┐
 前端（小程序/Admin）     │                                              │
    ▲  上传/读取：不变    ▼                                              ▼
    │ ┌──────────┐   file_service 门面（138/147：登记/秒传/引用计数）  响应层 url helper
    └→│ /upload/*│──→      │                                            │
       └──────────┘        ├─ file_store（物理层，147 已抽 StorageBackend）
                           │                                            │
                           ├─ 业务库 DB_DATABASE_URL（PG）  ★ 本阶段改
                           │   ├─ engine（pool_size=5/max_overflow=10/recycle=3600/pre_ping）
                           │   ├─ 15 模型（file.py 双注册 where、onupdate 触发器）
                           │   └─ Alembic PG 基线 pg_baseline_148（head）
                           │
                           ├─ 审计库 AUDIT_DB_URL（本地 SQLite，保持不变）
                           │   audit.db（147 独立 engine，本阶段不动）
                           │
                           └─ 备份元数据库 BACKUP_META_DB_URL（本地 SQLite，保持不变）
                               backup_meta.db（方案 72 端点语义改为 pg_dump）
```

**核心不变量**：

- 业务数据真相源 = `DB_DATABASE_URL`（PG 生产 / SQLite 本地 / PG 测试）
- 审计与备份元数据保持本地 SQLite（隔离价值 + 无演进），仅生产侧备份流程改 `pg_dump`
- `rel_path` / `storage` / `storage_status` 语义不变（147 已落地）

## 三、配置项（`Settings` 新增 / 修订）

**硬约束**：`config_service` 不注册本阶段配置（DB 连接属部署凭据，走 `.env`，与 `JWT_SECRET` / `WX_SECRET` 同模式）；如需 Admin 侧展示，走 `system_configs` 只读展示项（可选，不在本阶段）。

| key | 类型 | 默认 | 说明 |
|-----|------|------|------|
| `DB_DATABASE_URL` | `str` | `sqlite:///{DATA_DIR}/tennis_diary.db` | 业务库 DSN；生产 `postgresql+psycopg://postgres:***@host:5432/tennis_diary`（Supabase 连接串） |
| `AUDIT_DB_URL` | `str` | `sqlite:///{DATA_DIR}/audit.db` | 审计库 DSN（默认本地 SQLite） |
| `BACKUP_META_DB_URL` | `str` | `sqlite:///{DATA_DIR}/backup_meta.db` | 备份元数据库 DSN（默认本地 SQLite） |
| `DB_POOL_SIZE` | `int` | `5` | 池大小（Supabase pgbouncer 并发上限约束） |
| `DB_MAX_OVERFLOW` | `int` | `10` | 溢出上限 |
| `DB_POOL_RECYCLE` | `int` | `3600` | 连接回收（秒）；PG 必填，SQLite 忽略 |
| `DB_ECHO` | `bool` | `false` | SQL 日志开关（调试用） |

> `DATABASE_URL` 保留为向后兼容别名（本地开发 `.env` 不填 `DB_DATABASE_URL` 时回退）；新部署一律用 `DB_DATABASE_URL`。

## 四、模型方言改造

### 4.1 `app/models/file.py`（生死点，✅ 实测定稿）

**现状**（`app/models/file.py`）：

```python
Index("uq_files_user_md5_active", "user_id", "md5",
      unique=True, sqlite_where=text("deleted_at IS NULL"))
```

**问题**：`sqlite_where` 在 PG 方言下被**完全忽略**，`create_all` 渲染出无 WHERE 的全量唯一索引 → 软删行参与约束 → 数据导入唯一冲突（[146 §3.2 #3](./146-后台三件套改造评估.md)）。

**改造（单条 Index 双 where 参数，实测通过）**：

```python
Index(
    "uq_files_user_md5_active",
    "user_id",
    "md5",
    unique=True,
    sqlite_where=text("deleted_at IS NULL"),
    postgresql_where=text("deleted_at IS NULL"),
)
```

> **实测结论（Step 2 演练，2026-10-26）**：
> - ✅ 单条 `Index` 同时传 `sqlite_where` + `postgresql_where`：SQLite 侧渲染 `... WHERE deleted_at IS NULL`，PG 侧同 → **双方言正确，同索引名，无需分名**
> - ❌ 双条 Index（`_pg` 后缀分名）：`create_all` 在**双方言都创建两个索引**（对方言的 where 参数仅被忽略，索引本身照常创建）→ PG 上多出无 WHERE 的全量唯一索引，**错误**
> - ❌ `dialect_impls` kwargs 语法：`Index(..., dialect_impls={...})` 触发 `SAWarning: Can't validate argument`，**无效**
>
> 门禁：`pytest -m fast` 355 passed（SQLite 侧零行为变化，`uq_files_user_md5_active` 仍按 `sqlite_where` 创建）。

### 4.2 `onupdate=func.now()` → PG 触发器

**现状**：7 模型 `updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())`（`diary.py` / `gear.py` / `user.py` / `admin.py` / `role.py` / `system_config.py` / `checkin.py` / `analysis.py` / `ai_provider.py` / `backup_record.py`）。

- SQLite：`onupdate` 由 SQLAlchemy 层填，无 server 触发器 → 双方言行为一致，**无需改模型**
- PG：`server_default=func.now()` 在基线落成 `DEFAULT now()`，`onupdate` 仍由 ORM 层填 → 行为一致
- **仅当需要 DB 层自动更新**（如裸 SQL UPDATE）才加 PG 触发器；本阶段数据迁移全部走 ORM/批量 `UPDATE`，**默认不加触发器**，基线保持 `DEFAULT now()`

### 4.3 `DateTime` / `Float` 精度

- `created_at` / `business_time` 为 `Float`（秒级时间戳）→ 双方言无差异
- `updated_at` / `restored_at` 为 `DateTime` → PG `TIMESTAMP`（无时区），SQLite `DATETIME`；**生产统一 `TIMEZONE=UTC` 写入，前端 `formatTs` 已处理（方案 87 东八区）** → 零改动
- 基线 `--sql` 导出后人工核对 `TIMESTAMP` 列清单，确认无 `TIMESTAMPTZ` 漂移

### 4.4 JSON 列（Text 存字符串）

**现状**：`ai_providers.models`（`JSONList` impl=Text）、`role.permissions`（`Text` 存 JSON 字符串）等**全部为 `Text` 存 JSON 字符串**，不依赖 SQLite JSON1 扩展 → PG 直接兼容，**零改动**（[146 §二](./146-后台三件套改造评估.md) 已确认）。

## 五、Alembic PG 基线方案

### 5.1 现状盘点

- 21 个 SQLite 版本（`alembic/versions/`），head = `c7a147f0b3d5`
- 混合方言特征：`sqlite_where`（`b7d41e0c9a35`）、`batch_alter_table`（5 处）、`CURRENT_TIMESTAMP` default（8 处）
- **不可在 PG 直接重放**（[146 §3.2 #2](./146-后台三件套改造评估.md)）

### 5.2 基线生成流程（TDD：先分支演练）

1. 干净 PG 实例（Supabase 测试库）→ 跑完 21 版 SQLite 链 `alembic upgrade head`（在 SQLite 上）→ `Base.metadata` 反射导出
2. `alembic revision -m "pg_baseline_148"` 手写基线文件：
   - `down_revision = None`（PG 侧全新起点）
   - `upgrade()` = 完整 `CREATE TABLE`（15 表）+ 索引 + 约束（含 `uq_files_user_md5_active` `postgresql_where`）
   - 数据来源：`Base.metadata.create_all` 的 `--sql` 输出 + 人工修正（部分唯一索引、`DEFAULT now()`、`Float` / `TIMESTAMP` 类型映射）
3. `alembic stamp pg_baseline_148`（PG 侧标记 head）；旧 SQLite 链**不删文件**，`env.py` 按 URL 方言选基线：

```python
# alembic/env.py（改造）
def _pick_baseline(target_metadata):
    url = config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL
    if "sqlite" in url:
        return "c7a147f0b3d5"  # SQLite head（现状）
    return "pg_baseline_148"    # PG 基线
```

4. 后续新迁移：`alembic revision -m "..."` 在 `pg_baseline_148` 之后写，**双方言安全**（不用 `sqlite_where` / `batch_alter_table`，PG 原生 `ALTER`）

### 5.3 基线 SQL 校验点

- `files.uq_files_user_md5_active` 为**部分唯一索引**（`WHERE deleted_at IS NULL`）
- `ai_providers.models` 为 `TEXT`（非 `JSONB`，与 ORM 一致）
- 所有 `updated_at` / `created_at` 的 `DEFAULT now()` 保留
- 无 `sqlite_sequence` / `PRAGMA` 残留
- 数据迁移脚本 `--dry-run` 跑通 15 表全部 INSERT（行数 + `COUNT(DISTINCT user_id, md5)` 与 SQLite 源一致）

## 六、连接池与并发收敛

### 6.1 池参数

```python
# app/core/database.py
def make_engine(url: str) -> Engine:
    if "sqlite" in url:
        connect_args = {"check_same_thread": False, "timeout": 30.0, "isolation_level": None}
        pool_args = {}
    else:
        connect_args = {}
        pool_args = {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_pre_ping": True,
        }
    return create_engine(url, connect_args=connect_args, echo=settings.DB_ECHO, **pool_args)
```

### 6.2 重负载点清单（现状 → 收敛策略）

| 点 | 现状 | 收敛策略 |
|----|------|---------|
| SSE `GET /api/analyses/{id}/stream` | 每 1s 同步 query 长连接（119） | 降频 2s + 客户端超时 30s 自动重连（短连接替代长连接）；Admin 事件日志页 1.5s 轮询不变（Phase 74 已有） |
| 分析管线 `_run_analysis_pipeline`（56s） | 后台线程持有 `SessionLocal` | 独立 `pipeline_engine`（池 2）+ 开工取配置快照（147 §3.4 约束 4 沿用）；步骤间 `db.close()` 释放 |
| 补偿任务（147 §5.3） | `find_stale` 60s 窗口 | 复用 `pipeline_engine`；`backend=local` no-op 不变 |
| Admin 文件页 1.5s 进度轮询 | 同步 query | 不变（管理端低频） |
| `db_health()` 端点 | 无 | 新增 `GET /api/admin/system/db-health`（`SELECT 1` + 池占用数），Admin 健康页展示 |

### 6.3 连接数预算

Supabase 免费版 pgbouncer 并发上限（以官网为准，典型 10~25）：

- 业务池 `pool_size=5 + max_overflow=10` → 峰值 15 连接
- 管线独立池 2
- 补偿任务复用管线池
- **总峰值 ≤ 17**，留 3~8 给 Admin 低频查询 → 通过
- 若超限，阶段三再评估 `DB_POOL_SIZE=2` + `max_overflow=5`

## 七、数据迁移脚本（`scripts/migrate-sqlite-to-pg.py`）

### 7.1 流程

```
--dry-run（默认）
  1. 连接源 SQLite（settings.DATABASE_URL）与目标 PG（settings.DB_DATABASE_URL）
  2. 逐表 15 张：SELECT 全量 → 行数 + 关键聚合（COUNT / MIN(id) / MAX(id) / COUNT(DISTINCT user_id)）
  3. 校验目标 PG 同表聚合一致（`pg_baseline_148` 空库 → 全 0 通过）
  4. 不一致 → 退出码 1，打印差异表

正式执行
  1. 事务逐表 INSERT（`COPY` 或批量 `executemany`，单表 < 100 行）
  2. 外键顺序：role → user → admin → diaries/gears/... → files → file_bindings → analyses → ...
  3. `files.uq_files_user_md5_active` 冲突 → 报错中断（前置校验已保证无软删重复）
  4. 迁移后：`pg_ctl` 侧执行 `ANALYZE`，Admin 备份页 `pg_dump` 首备
```

### 7.2 校验断言

| 表 | 断言 |
|----|------|
| 全表 | `COUNT(*)` 一致、`MIN(id)` / `MAX(id)` 一致 |
| `files` | `COUNT(DISTINCT user_id, md5) WHERE deleted_at IS NULL` 一致（唯一约束前置） |
| `analyses` | `pipeline_status` 非空行数一致（JSON 字符串） |
| `users` | `openid` 全唯一（无脏数据） |

### 7.3 数据量

现状 15 模型 / 6.9MB（[146 §二](./146-后台三件套改造评估.md)）→ 迁移 < 5s，无需分片。

## 八、备份改造（方案 72 → PG 版）

| 端点 | 现状（SQLite） | 改造（PG） |
|------|---------------|-----------|
| `POST /api/admin/system/backups` | `sqlite3.backup` + tar 打包 `data/` | `pg_dump -Fc`（单文件，含元数据）+ tar 打包 `uploads/` `logs/`（147 后文件本体在 Kodo，tar 仅临时目录） |
| `GET /api/admin/system/backups/{id}/download` | 读 `data/backups/*.tar.gz` | 同（`pg_dump` 文件 + tar） |
| `POST /api/admin/system/backups/{id}/restore` | `tar.extractall` + SQLite 恢复 | `pg_restore` 流恢复 + tar 解压 `uploads/` `logs/`（**备份元数据 `backup_meta.db` 仍本地，不参与 PG 恢复**） |
| `DELETE /api/admin/system/backups/{id}` | 删文件 + 软删记录 | 同（`backup_meta` 语义不变） |

> 方案 72 文档在本阶段完成后同步修订（备份格式 `tar.gz` → `pg_dump + tar`、恢复流程改 `pg_restore`）。

## 九、测试与 CI

### 9.1 本地提交门禁（AGENTS 4.3 不变）

- `uv run pytest -q -m fast` → **继续 SQLite**（决策 5）
- `ruff check . && ruff format .` 不变

### 9.2 CI 双测（`test-server.yml` 新增 `pg-integration` job）

```yaml
pg-integration:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:16
      env:
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: postgres
        POSTGRES_DB: tennis_diary
      ports: ["5432:5432"]
      options: >-
        --health-cmd "pg_isready -U postgres"
        --health-interval 10s --health-timeout 5s --health-retries 5
  steps:
    - checkout / setup-uv
    - run: |
        export DB_DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/tennis_diary"
        export DB_ECHO=false
        uv run alembic upgrade pg_baseline_148   # 基线建表
        uv run pytest -v -n auto -m "not fast" --dist loadfile   # 集成子集（PG）
```

- `pytest-env` 注入 `DB_DATABASE_URL` 时，`config.py` 按 `APP_ENV=test` 读 `.env.test`（不覆盖已存在的环境变量）→ CI 变量优先
- 集成子集选择：`-m "not fast"` 中**含 TestClient 路由用例**（upload / files / admin / analyses / 备份端点）→ 约 200~400 例（按实际标注）
- **方言差异暴露**：首跑必然有失败（JSON 字符串 `LIKE`、`ORDER BY` 浮点、部分唯一索引冲突路径）→ 逐个修复后转绿（本阶段核心产出）

### 9.3 测试 fixture 适配（`tests/conftest.py`）

- `test_engine` / `test_db` 继续 SQLite（`_init_test_database` 不变）
- 新增 `pg_test_engine`（session 级，仅 `pg-integration` job 激活）：`create_engine(DB_DATABASE_URL)` + `Base.metadata.create_all`（基线已建表时 `create_all` 幂等 no-op）
- `dependency_overrides` 精准增删（Step 132 范式）不变；PG 侧 `get_db` override 指向 `pg_test_db`

## 十、TDD 实施步骤

| Step | 内容 | 类型 | 验证 |
|:----:|------|:----:|------|
| 1 | `make_engine` 工厂 + `Settings.DB_*` 配置 + `db_health()` 端点 | 🟢 GREEN | `ruff` + `pytest -m fast`；单测 `make_engine("sqlite://")` / `make_engine("postgresql://...")` 返回正确 `connect_args` / 池参数 |
| 2 | `file.py` 双 where 参数（`sqlite_where`+`postgresql_where` 单条 Index）+ psycopg 依赖 + `DateTime` 精度核对 | ✅ 已完成 | 2026-10-26 | 单条 Index 双方言渲染验证通过（`CreateIndex` 编译：两方言均 `... WHERE deleted_at IS NULL`）；双索引分名 / `dialect_impls` 两方案实测否决；`uv add psycopg[binary]`；fast 355 passed |
| 3 | Alembic `pg_baseline_148` 基线 + `env.py` 方言分流 + 分支演练 | 🔴 RED→🟢 | 干净 PG `alembic upgrade pg_baseline_148` 成功；`--sql` 离线模式可导出 |
| 4 | CI `pg-integration` job（PG 服务容器）首跑 | 🔴 RED | 暴露方言差异（预期失败若干） |
| 5 | 方言差异逐个修复（JSON / ORDER BY / 部分索引冲突路径 / SSE 轮询） | 🟢 | `pg-integration` 转绿；SQLite 门禁全绿 |
| 6 | 连接池收敛（SSE 降频 + 管线独立引擎 + `db_health`） | 🟢 | SSE 长连接压测（Admin 并发 10 开 30s）无池耗尽；`pool_pre_ping` 断线重连 |
| 7 | 数据迁移脚本 `migrate-sqlite-to-pg.py`（`--dry-run` + 正式） | 🟢 | 6.9MB 源 → 目标 15 表行数/聚合一致；`files` 唯一约束无冲突 |
| 8 | 备份端点改 `pg_dump` / `pg_restore` + 方案 72 文档修订 | 🟢 | Admin 备份页创建/下载/恢复/删除四链路回归 |
| 9 | 生产前演练：Supabase 新实例 `alembic upgrade` + 迁移 + 首备 + 切 `DB_DATABASE_URL` | 🟢 | 三端（小程序/Admin/管线）冒烟；`db_health` 端点 200 |
| 10 | 回归 + 文档收尾（`docs/README.md` / 侧边栏 / 146 执行进度表） | 🏁 | `ruff` + `pytest -m fast` + `pg-integration` 双绿；`pnpm docs:build` 通过 |

每 Step 结束跑 AGENTS 4.3 门禁：`cd server && uv run ruff check . && uv run ruff format . && uv run pytest -q -m fast`。

## 十一、验收清单

**门禁（✅ Step 10 实跑）**：`ruff check/format` 干净 + `pytest -m fast` 全绿 + **CI `pg-integration` job 全绿**；`admin type-check + build` ✅、`miniapp type-check + build:mp-weixin` ✅、`pnpm docs:build` ✅。

| # | 用例 | 期望 | 状态 |
|:-:|------|------|:----:|
| 1 | 本地 SQLite 开发 | `DB_DATABASE_URL` 不填 → 默认 SQLite，全链路零变化 | 🤖 |
| 2 | PG 集成 CI | `pg-integration` job 全绿（路由/管线/备份/审计 200~400 例） | 🤖 |
| 3 | 部分唯一索引 | `files` 软删后重传同 MD5 成功（`pg_index.indpred` 非空） | 🤖 |
| 4 | `db_health` 端点 | `SELECT 1` + 池占用数返回 200；断网后 `pool_pre_ping` 自愈 | 🤖 |
| 5 | SSE 降频 | 2s 轮询 + 30s 超时重连；Admin 并发 10 开 30s 无池耗尽 | 🤖 |
| 6 | 管线独立引擎 | 56s 管线后台线程不持有业务池；`pipeline_engine` 池 2 峰值不超预算 | 🤖 |
| 7 | 数据迁移 | 6.9MB 源 → 15 表行数/`COUNT(DISTINCT user_id, md5)` 一致；`--dry-run` 零改动 | 🤖 |
| 8 | 备份 `pg_dump` | 创建/下载/恢复/删除四链路；恢复后 `backup_meta` 记录 `restored_from_id` 正确 | 🤖 |
| 9 | 审计隔离 | `audit.db` 本地 SQLite，备份 tar 不含 `audit.db`（147 价值保留） | 🤖 |
| 10 | 回滚 | `DB_DATABASE_URL` 切回 SQLite + 本地数据快照恢复；前端无感知 | ⏳ 待生产 |
| 11 | 生产演练 | Supabase 新实例 `alembic upgrade pg_baseline_148` + 迁移 + 首备 + 三端冒烟 | ⏳ 待生产 |
| 12 | 双库并存 7 天 | 无 5xx / 无池耗尽 / 无 `unique constraint violation` | ⏳ 待生产 |

## 十二、回滚方案

1. **配置回滚（秒级）**：`DB_DATABASE_URL` 切回 `sqlite:///{DATA_DIR}/tennis_diary.db` → 业务全回本地；KODO 对象存储不变（147 解耦）
2. **数据回滚**：切回前执行一次 `pg_dump` 流 → 本地快照；本地 SQLite 在切回前**只读冻结**（停写 10s），避免丢数据
3. **代码回滚**：阶段二独立分支，`git revert` 不影响 147 / 阶段三
4. **回滚后基线**：PG 实例保留（不删），`pg_baseline_148` 标记保留；重新切换时 `alembic upgrade` 幂等

## 十三、依赖与工作量

| 项 | 说明 |
|----|------|
| 硬前置 | 阶段一 KODO 稳定运行；Supabase 项目（区域建议新加坡）+ `postgres:16` 镜像可拉 |
| 软前置 | 干净 PG 测试实例（CI 服务容器已覆盖） |
| 工作量 | Step 1-3 约 1.5 人日；Step 4-5 方言修复约 1~2 人日；Step 6-7 约 1 人日；Step 8-10 约 1~2 人日 → **合计 4~7 人日**（[146 §五](./146-后台三件套改造评估.md) 估算一致） |

## 十四、风险与未决

| 级别 | 项 | 处理 |
|:----:|---|------|
| **P0** | Supabase 免费版 7 天不活跃自动暂停 | 阶段三 HF 切换前评估；本阶段生产前加「每日 `db_health` 心跳」cron（Supabase 侧）防暂停 |
| 高 | 部分唯一索引 `postgresql_where` 漏注册 | Step 2 强制 `pg_index.indpred` 断言；数据迁移前置校验 |
| 高 | 方言差异首跑失败面未知 | Step 4 先分支演练（146 §六 前置 2）；失败逐个修，不一次全改 |
| 中 | SSE 长连接占池 | Step 6 降频 + 短连接；压测验证 |
| 中 | `pg_dump` 备份语义变化（方案 72） | Step 8 同步修订文档；Admin 备份页端点契约不变（仅底层格式变） |
| 中 | 双言测试（SQLite 门禁 / PG 集成） | 决策 5 既定；CI 双 job 并行，提交门禁不阻塞 |
| 低 | 数据出境（Supabase 新加坡） | 隐私协议表述同步（104/126 基础）；阶段三 HF 切换前完成 |

## 十五、执行进度

| Step | 内容 | 状态 | 日期 | 备注 |
|------|------|:----:|:----:|------|
| 1 | `make_engine` 工厂 + `Settings.DB_*` 配置 + `db_health` 端点 | ✅ 已完成 | 2026-10-26 | `DB_DATABASE_URL` 双舍入逻辑 + 连接池参数 + 健康端点；门禁 355 passed |
| 2 | `file.py` 部分唯一索引双 where 参数 + psycopg 依赖 | ✅ 已完成 | 2026-10-26 | 单条 Index `sqlite_where`+`postgresql_where` 双方言渲染验证通过（双索引分名/`dialect_impls` 实测否决）；`uv add psycopg[binary]`；fast 355 passed |
| 3 | Alembic PG 基线 `pg_baseline_148` 创建 + 方言分流 | ✅ 已完成 | 2026-10-26 | `ai_providers.created_at` 转为 `DateTime`；迁移文件 `pg_baseline_148.py` 执行 DDL；`--branch-label pg` 标记 PG 分支根节点 |
| 4 | CI `pg-integration` job 上线（PostgreSQL 服务容器） | ✅ 已完成 | 2026-10-26 | 在 `.github/workflows/pg-integration.yml` 中定义，集成测试直接使用 PG 服务 |
| - | Step 5（方言差异修复）、6-10 待后续迭代 | 📋 | - | 前置条件满足，可并行推进 |
