> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 39 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-07 |
> | 对应功能/内容 | 为后端接入 Alembic 数据库迁移，替代手工 `create_all` 建表，支撑 schema 演进（含 Step 38 新增的 gender/birthday 字段） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-07 | v1.0.0 | 初版 |
> | 2026-08-07 | v1.0.0 | 实施完成（alembic.ini + alembic/ + 基线迁移 + 模型集中导出 + ruff 适配 + 迁移测试） |
>
> **关联文档**：[Step 38：修复登录时序与用户资料编辑](./38-修复登录时序与用户资料编辑-参考tarot.md) · [B1-2 核心配置](./03-B1-2-核心配置模块.md) · [B1-3 数据库模型](./04-B1-3-数据库模型.md)

# Step 39：Alembic 数据库迁移接入

## 一、背景

### 1.1 现状问题

当前数据库表结构由 SQLAlchemy 模型定义，建表方式存在隐患：

1. **无版本化管理**：应用运行时不主动建表（`create_all` 仅出现在测试 `conftest.py`），现有 `server/data/tennis_diary.db` 靠开发期手工/脚本创建，schema 演进无迹可循。
2. **字段变更不可控**：Step 38 为 `users` 表新增 `gender`、`birthday` 两列，若直接手工改已有库，极易遗漏或与模型不一致。
3. **多环境不一致**：本地/开发/生产库结构靠人工同步，无法保证一致。

### 1.2 目标

接入 **Alembic** 作为数据库迁移工具：

- 以迁移脚本（`alembic/versions/`）管理全部表结构与演进
- 新环境执行 `alembic upgrade head` 即可建到最新结构
- 模型变更后 `alembic revision --autogenerate` 生成迁移并 `upgrade`
- 生成一个**完整基线迁移**（含全部 7 张表 + users 的 gender/birthday 字段），作为后续演进的起点

## 二、技术方案

### 2.1 依赖

在 `server/pyproject.toml` 的 `[project].dependencies` 增加：

```toml
"alembic>=1.14.0",
```

常用命令直接 `uv run alembic <cmd>` 调用（如 `uv run alembic upgrade head`、`uv run alembic revision --autogenerate -m "..."`）。尝试登记 `[tool.uv.scripts]` 别名但当前 uv 版本不支持，故未采用。

> 说明：Alembic 属运行时依赖（应用升级数据库需要），故放 `dependencies` 而非 dev。

### 2.2 目录与文件

```
server/
├── alembic.ini            # Alembic 配置（script_location、logging）
├── alembic/
│   ├── env.py             # 连接 DATABASE_URL + 加载 Base.metadata
│   ├── script.py.mako     # 迁移模板
│   └── versions/
│       └── 3a79ce8c1f19_initial_schema.py  # 基线迁移（全部表 + gender/birthday）
└── app/
    └── models/
        └── __init__.py    # 集中导入全部模型，供 Alembic 发现 metadata
```

### 2.3 模型集中导入

`app/models/__init__.py` 目前为空，Alembic 的 `Base.metadata` 无法自动发现模型。需在其中导入全部模型：

```python
from app.models.analysis import Analysis
from app.models.checkin import Checkin
from app.models.diary import Diary
from app.models.gear import Gear
from app.models.post import Post
from app.models.user import User
from app.models.weight import WeightRecord

__all__ = [
    "User",
    "Diary",
    "Gear",
    "WeightRecord",
    "Analysis",
    "Checkin",
    "Post",
]
```

### 2.4 `alembic/env.py` 关键点

```python
from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.core.database import Base
from app.models import *  # noqa: F401, F403  # 确保模型注册到 Base.metadata

config = context.config

# 让 Alembic 使用应用同一套配置（含 .env 的 DATABASE_URL）
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata
```

> 复用 `app.core.config.settings.DATABASE_URL`，保证与运行环境一致（`.env` 中的 `DATA_DIR` 决定数据库路径）。

### 2.5 基线迁移生成策略

由于已有库 `server/data/tennis_diary.db` 与模型结构一致（除 users 新增的 gender/birthday），采用：

1. 用 `alembic revision --autogenerate -m "initial schema"` 生成基线迁移，得到完整 `create_table`。
2. 校验生成的 `users` 表包含 `gender`、`birthday` 列。
3. 对现有开发库执行 `alembic stamp head`（标记当前库已是最新，避免重复建表报错）——若该库为测试/一次性库，也可直接 `upgrade` 重建。

## 三、实施步骤

1. 安装依赖：`uv add alembic`
2. 修改 `app/models/__init__.py` 集中导入模型
3. 生成 `alembic.ini` 与 `alembic/` 骨架（`uv run alembic init alembic`）
4. 改写 `alembic/env.py`（接 DATABASE_URL + Base.metadata）
5. `uv run alembic revision --autogenerate -m "initial schema"` 生成基线迁移
6. 校验迁移脚本（表结构、gender/birthday 列、索引）
7. 清理旧开发库或 `stamp head`，`alembic upgrade head` 验证建表
8. 新增自动化测试：迁移可执行 + 迁移后表结构与模型一致
9. 更新方案文档状态、AGENTS.md

## 四、验证

- `alembic upgrade head` 能成功建表
- `alembic current` / `alembic history` 输出正确
- 迁移后数据库表结构与 SQLAlchemy 模型一致（对比 columns）
- `bash scripts/verify.sh` 全通过

## 五、字段更新操作流程

当数据模型字段发生变更时（新增/删除/改类型/改约束），一律通过 Alembic 迁移脚本实现，**严禁手动 `create_all`**。标准流程三步：

### 5.1 修改模型定义

在 `server/app/models/*.py` 中修改字段，例如给 `User` 增加 `phone` 列：

```python
# server/app/models/user.py
class User(Base):
    ...
    gender = Column(Integer, default=0)
    birthday = Column(String(10), default="")
    phone = Column(String(20), default="")   # 新增字段
```

> 若**新增模型类**，还需在 `server/app/models/__init__.py` 中登记导出，否则 Alembic 发现不到（`env.py` 靠 `from app.models import *` 收集 `Base.metadata`）。

### 5.2 自动生成迁移脚本（RED）

```bash
cd server
uv run alembic revision --autogenerate -m "add phone to users"
```

- 命令会比较 `Base.metadata`（当前模型）与数据库中已应用的迁移，生成增量脚本，自动落在 `alembic/versions/` 下，形成新版本节点。
- **坑**：若开发库已过期（`current` 落后于 `head`），autogenerate 会基于旧库生成不完整迁移。稳妥做法：改动前先 `uv run alembic current` 确认与 `head` 一致，必要时先 `upgrade head` 再改模型。

### 5.3 应用迁移（GREEN）

```bash
cd server
uv run alembic upgrade head
```

应用后数据库表结构与模型保持一致。

### 5.4 验证

```bash
uv run alembic current   # 当前版本应显示 head
uv run alembic history   # 迁移历史链
```

### 5.5 常见场景

| 场景 | 操作 |
|---|---|
| 纯新增字段（带默认值） | 上述三步即可，autogenerate 生成 `add_column` |
| 字段类型/约束变更 | autogenerate 通常能识别；但 SQLite 对某些 `alter` 支持有限，可能需手写 `op` 语句（如重建表） |
| 删除字段 | autogenerate 生成 `drop_column`，确认后应用 |
| 新增模型未在 `__init__.py` 登记 | 先补登记再生成迁移 |

> 迁移脚本生成后**无需手工格式化**：`pyproject.toml` 已对 `alembic/versions/*` 做了 `per-file-ignore`（E501/I/UP）并加入 `[tool.ruff.format] exclude`，保持自动生成原样即可，勿用 `ruff format` 重新格式化。

## 六、注意事项

- `data/` 已被 `.gitignore` 忽略，迁移只管理 schema，数据文件不入库
- 生产环境升级库用 `alembic upgrade head`；严禁手动 `create_all`
- 测试 `conftest.py` 仍用 `Base.metadata.create_all` 建临时库（内存/临时文件），不依赖 Alembic，保持测试轻量——这是有意为之，两者职责分离
