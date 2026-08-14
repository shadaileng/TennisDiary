> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 78 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-14 |
> | 对应功能/内容 | 通用动态配置系统 + Admin 系统配置页（AI 为首个可动态配置分类） |
> | 关联文档 | [03-B1-2-核心配置模块](./03-B1-2-核心配置模块.md)、[75-1-AI评分代理接口](./75-1-AI评分代理接口.md)、[75-B2-Admin同步AI网关功能](./75-B2-Admin同步AI网关功能.md) |

> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-14 | v1.0.0 | 初版 |

# Step 78：动态配置系统与 Admin 配置页

## 一、背景

当前后端全部配置（含 AI 三件套 `AI_API_KEY` / `AI_BASE_URL` / `AI_MODEL`）均为**进程启动时**从环境变量/`.env` 读取（`server/app/core/config.py`），运行期修改只能改 `.env` 后重启服务。这带来两个问题：

1. **AI 配置无法在线调整**：Key 过期更换、切换模型、更换 OpenAI 兼容供应商都要登录服务器改环境变量并重启，运维成本高。
2. **配置状态不可见**：Admin 端只能通过 `ai-status` 看到 AI 三项的只读探测结果，没有统一的配置总览与变更入口。

本次引入**通用动态配置框架**：配置注册表（代码声明，覆盖全部配置项并按分类组织）+ 数据库覆盖表，**生效值 = DB 覆盖 > 环境变量默认值**，请求时实时解析、无需重启。首个接入动态配置的分类为 **AI 服务**，其余配置项在配置页**分类只读展示**（状态可查），后续可逐步放开。

## 二、目标

1. **配置注册表**：声明式覆盖 `Settings` 全部配置项，按「应用基础 / 认证与安全 / 微信小程序 / AI 服务 / 数据与存储 / 姿态模型 / 日志」分类组织。
2. **DB 覆盖表** `system_configs`：只存覆盖值（`key` / `value` / `updated_by` / `updated_at`），环境变量始终作为默认值兜底。
3. **实时生效**：可动态配置的项（AI 三件套）运行时读取全部走配置服务，改完即生效，**无需重启**。
4. **Admin 配置页**：分类卡片展示全部配置项；可编辑项带输入/校验/保存/恢复默认；每项展示「来源状态」（默认/自定义/内置）；支持测试 AI 连接与全部恢复默认。
5. **权限**：新增 `system:config` 权限，配置接口走 `require_permission`，前端菜单按权限隐藏。

## 三、方案设计

### 3.1 核心语义

```
生效值 = DB 覆盖值（system_configs）> 环境变量默认值（settings.*，启动时读入）
```

- DB 覆盖是**可选**的：没有覆盖行时，该项即环境变量默认值（`source=env`）。
- 配置定义（分类、标签、类型、是否可编辑、env 映射）在**代码注册表**中，不落库，避免配置表冗余与定义漂移。
- 默认值**运行时**从 `settings` 解析（`getattr(settings, env_key)`），兼容测试 `monkeypatch` 与代码热改。

### 3.2 配置注册表 `app/core/config_registry.py`（新增）

```python
@dataclass(frozen=True)
class ConfigItemDef:
    key: str            # 唯一键，如 "ai.api_key"
    category: str       # 分类 key，如 "ai"
    label: str          # 显示名
    description: str    # 说明
    value_type: str     # str | secret | url | bool | int | select
    env_key: str        # 关联环境变量（读取 settings 属性）
    editable: bool      # 是否可动态配置（可编辑）
    options: list[str] | None = None  # select 选项

    @property
    def default(self) -> str:  # 运行时解析环境变量默认值
        return str(getattr(settings, self.env_key, "") or "")
```

分类元数据 `CONFIG_CATEGORIES`：`{key, label, description}`。

**可编辑项（接入运行时）**：

| key | 类型 | env | 默认 |
|---|---|---|---|
| `ai.api_key` | secret | AI_API_KEY | `.env` 配置 |
| `ai.base_url` | url | AI_BASE_URL | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `ai.model` | str | AI_MODEL | `qwen-vl-max` |

**只读展示项**：其余全部 `Settings` 项（含 `ai.timeout=120s`、`ai.temperature=0.3` 内置常量，`source=builtin`）。

### 3.3 数据库模型 `app/models/system_config.py`（新增）

```python
class SystemConfig(Base):
    __tablename__ = "system_configs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)          # 覆盖值
    updated_by = Column(Integer, nullable=True)  # 管理员 id
    created_at = Column(Float, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

- 登记到 `app/models/__init__.py`。
- Alembic 迁移 `add_system_configs_table`（autogenerate，禁止 `create_all`）。

### 3.4 配置服务 `app/services/config_service.py`（新增）

| 函数 | 说明 |
|---|---|
| `get_config_value(db, key) -> str` | 生效值：DB 覆盖 > 注册表 env 默认 |
| `get_ai_config(db) -> AIConfig` | 组装 AI 三件套（dataclass `AIConfig(api_key, base_url, model)`） |
| `list_config_items(db) -> list[dict]` | 合并覆盖值，输出 source / 掩码 / updated_at / updated_by |
| `set_config_value(db, key, value, admin_id) -> dict` | 校验 editable 与类型后 upsert；值等于 env 默认时**删行归一化**；secret 空值/掩码值=保持不变 |
| `delete_config_value(db, key) -> None` | 删除覆盖行（恢复默认） |
| `reset_all(db) -> None` | 清空全部覆盖行 |
| `_mask_secret(value) -> str` | 掩码 `sk-****last4`（与 system.py `_mask_api_key` 同规则，抽离复用） |

类型校验：`url`（`http(s)://` 前缀）、`bool`（true/false/1/0）、`int`（可解析）、`select`（值必须在 options 内）。

### 3.5 管理端 API `app/routers/admin/config.py`（新增）

前缀 `/api/admin/config`，tag `admin-config`，全部接口 `require_permission("system:config")`：

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 全量配置（分类 + items + 来源状态 + summary） |
| PUT | `/{key}` | 设置覆盖值（`{value}`），返回更新后 item |
| DELETE | `/{key}` | 恢复默认 |
| POST | `/reset` | 全部恢复默认 |

GET `/` 响应结构：

```json
{
  "summary": {
    "total": 20, "editable": 3, "overridden": 1,
    "categories": [{"key": "ai", "label": "AI 服务", "item_count": 5, "overridden": 1}]
  },
  "items": [
    {
      "key": "ai.api_key", "category": "ai", "label": "API Key", "description": "...",
      "value_type": "secret", "editable": true,
      "value": "sk-****abcd", "has_value": true, "default_value": "sk-****abcd",
      "source": "db", "options": null, "updated_at": null, "updated_by": null
    }
  ]
}
```

- secret 项 `value`/`default_value` 均为掩码，明文永不回传。
- `source`：`db`（有覆盖）/ `env`（默认）/ `builtin`（代码内置只读常量）。
- 未知 key → 404；不可编辑项 → 403。

### 3.6 运行时接线（替换 `settings.AI_*` 直读）

| 文件 | 改动 |
|---|---|
| `app/services/ai_service.py` | `chat_vision` / `analyze_swing` 增加 `ai_config: AIConfig` 参数，不再直读 `settings.AI_*` |
| `app/routers/ai.py` | `analyze` 增加 `db: Session = Depends(get_db)`，用 `get_ai_config` 判断降级并传入 |
| `app/routers/admin/system.py` | `ai-status` / `ai-connect` 增加 `db` 依赖，改用生效值；掩码逻辑复用 config_service |

### 3.7 权限

`app/core/permissions.py` 新增 `"system:config": "系统配置管理"`。超级管理员天然放行；普通/只读管理员默认不含，可在角色页勾选。

### 3.8 Admin 前端

| 文件 | 改动 |
|---|---|
| `src/api/config.ts` | 类型 + `getConfigs / updateConfig / resetConfig / resetAllConfigs` |
| `src/views/system/config.vue` | 新增：AI 状态概览卡（复用 `ai-status`）+ 分类卡片（项：label/描述/来源徽标/输入框/保存/恢复默认）+ 测试连接 + 全部恢复默认 |
| `src/router/routes.ts` | `system` 组新增 `config` 子路由，`permission: 'system:config'` |

前端交互细节：

- secret 输入框 `type=password`，已配置时 placeholder「已设置，留空则不修改」；提交空值=保持不变。
- 每项来源徽标：默认（灰）/ 自定义（绿）/ 内置（蓝）；覆盖项显示「恢复默认」按钮。
- 全部恢复默认需 `confirm` 二次确认。
- 保存/恢复成功后刷新列表 + AI 状态。

## 四、测试（TDD）

### 4.1 `tests/routers/admin/test_config.py`（新增）

- 列表结构：summary / items / 分类齐全；每项含 source / editable / value_type。
- secret 掩码：`value` 与 `default_value` 均不含明文。
- PUT 覆盖：source 变 `db`，`get_config_value` 生效；值等于 env 默认 → 归一化回 `env`。
- PUT 校验：未知 key 404、不可编辑项 403、非法 url / bool / select 400。
- DELETE / POST reset：恢复默认。
- 权限：未登录 401；无 `system:config` 权限的管理员 403。
- 明文不泄漏：列表响应不含真实 key。

### 4.2 既有测试更新

- `tests/models/test_models_registry.py`：`EXPECTED_TABLES` 加 `system_configs`。
- `tests/routers/test_ai.py`：`fake_analyze_swing` 增加 `ai_config` 参数；新增「DB 覆盖 model/base_url 生效」用例。
- `tests/routers/admin/test_ai_gateway.py`：`ai-status` 走生效值（DB 覆盖 model 生效）。

## 五、验证

```bash
cd server && bash scripts/verify.sh    # ruff check + format + pytest
cd admin && pnpm build                # vue-tsc + vite
```

## 六、执行进度

- [x] 方案文档
- [x] 后端：注册表 / 模型 + 迁移 / 服务 / 路由 / 权限 / 运行时接线
- [x] 测试：新增 test_config.py + 更新既有测试
- [x] Admin 前端：api / 页面 / 路由
- [x] 验证与文档收尾
