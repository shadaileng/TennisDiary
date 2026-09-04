> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 132 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | 📋 待执行 |
> | 最后更新 | 2026-09-04 |
> | 对应功能/内容 | 全量测试 10 个失败用例治理：死测试清理 + fixture 作用域/污染修复 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-09-04 | v1.0.0 | 初版：三类根因分析与修复方案 |
>
> **关联文档**：[109-文件管理系统](./109-文件管理系统.md)、[115-pytest测试提速方案](./115-pytest测试提速方案.md)、[125-Admin文件管理简化与查询优化](./125-Admin文件管理简化与查询优化.md)、[131-文件登记MIME类型兜底与分类源补全](./131-文件登记MIME类型兜底与分类源补全.md)

# Step 132：测试脆弱性治理（死测试清理 + fixture 作用域修复）

## 一、背景与动机

Step 131 实施后跑全量回归，发现 `10 failed / 554 passed`。逐一定位后确认：**这 10 个失败全部是改动前既有的脆弱测试**（改动前基线同样是这 10 个），与 131 无关。

脆弱测试长期存在的危害：
1. 全量结果长期"带红"，真实回归被噪音掩盖，CI 失去拦截能力；
2. 失败面随执行顺序浮动（单跑通过、组合跑大面积红），排查成本高；
3. 死测试（引用已删除实现）误导后来者，以为能力仍存在。

目标：**全量 `pytest` 归零失败**，并消除顺序敏感性。

## 二、根因分类

### A 类：用例与实现不同步（5 个，单独跑必挂）

| 用例 | 根因 |
|------|------|
| `admin/test_files.py::TestAdminFileDelete::test_delete_keeps_disk_when_shared` | 连续插入两条 `original_name` 相同的 `File`（共用 `rel_path`），违反 `files.original_name` UNIQUE。真实上传经 `ensure_unique_name` 加后缀，用例直接构造 `File` 绕过了它 |
| `test_files_management.py::TestAIAnalysisFiles::test_register_ai_files_creates_records` | Step 125 删除了 `file_service.register_ai_files`，用例仍在引用 → `ImportError` |
| `test_files_management.py::TestSkeletonRegistration::test_skeleton_files_linked_to_analysis` | 同上 |
| `admin/test_files_download.py::TestPreviewFile::test_preview_info` | `GET /api/admin/files/{id}/preview` 端点已在 Step 125 删除 → 404 |
| `admin/test_files_download.py::TestPreviewFile::test_preview_mime_type_fallback` | 同上 |
| `test_video.py::TestProcessVideoTrim::test_trim_and_concat_used` | 断言"裁剪后原文件已删"，但 118 起实现明确保留原片（`video_service.py:422-423`） |

> `TestPreviewFile::test_preview_not_found` / `test_preview_file_not_on_disk` 断言 404，端点不存在反倒"蒙对"，属假绿，一并清理。

### B 类：admin conftest fixture 作用域错配（3 个）

`tests/routers/admin/conftest.py` 中 `test_db`/`client` 为 **module 级**，而根 `conftest.py` 的 `client` 为 **function 级**，二者都操作全局 `app.dependency_overrides`：

```python
saved = dict(app.dependency_overrides)
app.dependency_overrides[get_db] = override_get_db
yield _app_client
app.dependency_overrides.clear()      # ← 抹掉其它作用域的 override
app.dependency_overrides.update(saved)
```

后果：
- `clear()` 会抹掉 module 级 override，后续请求落到真实 `data_test` 库 → 数据"消失"；
- module 级 override 也可能残留到下一个模块，使请求打到上一个模块的 DB。

叠加 `auth_client` 把 admin token 直接写进 **session 级共享 TestClient** 的默认头且从不清理：

```python
client.headers["X-Auth-Token"] = admin_token
```

| 用例 | 表现 |
|------|------|
| `test_media.py::TestMediaQueryToken::test_query_token_authorizes` | admin 模块先跑后，共享 TestClient 残留 admin token 头（ADMIN_JWT_SECRET 签发），media 用例虽带用户 JWT query 参数，端点优先读 header → `Signature verification failed` → 401。**对照实验：media 先跑则通过** |
| `admin/test_roles.py::test_create_role_duplicate` | 依赖同文件前一用例预置 `code=test_role`（module 级 DB 顺序依赖）；override 丢失后落到真实库，重名角色不存在 → 200 而非 400 |
| `admin/test_ai_providers.py::TestCheckModels::test_forbidden_without_permission` | `Role.query(code=="admin")` 依赖 module 级 `test_roles` fixture 曾被执行；DB 被串改后查不到角色 → `NoneType.id`。单独跑该文件 30 passed |

### C 类：脏 session 级联（1 个 + 组合跑时十几个）

module 级 `test_db` 在前一用例 flush 失败后未 rollback，同模块后续用例全部 `PendingRollbackError`（`admin/test_files.py::TestAdminFileDelete::test_delete_not_found` 及组合跑时的连锁失败）。

## 三、修复方案

### 3.1 A 类：清理/改写

| 用例 | 处置 |
|------|------|
| `test_delete_keeps_disk_when_shared` | 第二条记录使用独立 `original_name`（模拟秒传真实语义：同 `rel_path` + 同 MD5，但展示名唯一），保留"共享路径不删物理文件"断言 |
| `test_register_ai_files_creates_records` | 改用现存 `batch_get_or_create_files`（`upload_source=skeleton_frame`） |
| `test_skeleton_files_linked_to_analysis` | 同上 |
| `TestPreviewFile`（4 个用例） | 整类删除（端点已下线，Step 125 有意移除） |
| `test_trim_and_concat_used` | 断言改为**原文件保留**，与 `video_service.py:422-423` 的 118 语义一致 |

### 3.2 B/C 类：fixture 治理

1. **精准增删替代 `clear()`**：根 `conftest.py` 与 admin `conftest.py` 的 `client` fixture 均改为保存被覆盖键的旧值、teardown 时精准 `pop` + 恢复，不再 `clear()` 全表。
2. **清理共享请求头**：admin `auth_client` teardown 执行 `client.headers.pop("X-Auth-Token", None)`。
3. **会话自动回滚**：admin `conftest.py` 新增 autouse function 级 fixture，每个用例前后 `test_db.rollback()`，杜绝 `PendingRollbackError` 级联。
4. **用例自包含**：
   - `test_create_role_duplicate`：用例内先创建、再重复创建，不依赖同文件前序用例；
   - `test_forbidden_without_permission`：显式依赖 `test_roles` fixture 取 `admin` 角色，不依赖隐式执行顺序。

## 四、实现步骤

1. `tests/conftest.py`：`client` / `auth_client` 精准恢复 overrides
2. `tests/routers/admin/conftest.py`：精准恢复 + header 清理 + autouse rollback
3. `tests/routers/admin/test_files.py`：修共享删除用例
4. `tests/routers/admin/test_files_download.py`：删除 `TestPreviewFile`
5. `tests/routers/test_files_management.py`：改用 `batch_get_or_create_files`
6. `tests/routers/test_video.py`：原文件保留断言
7. `tests/routers/admin/test_roles.py`：自包含
8. `tests/routers/admin/test_ai_providers.py`：依赖 `test_roles`

## 五、验收标准

- [ ] 全量 `uv run pytest -n auto` **0 failed**
- [ ] 单独运行此前失败的每个文件/用例均通过
- [ ] `admin + media` 组合（两种先后顺序）均无失败，验证顺序不敏感
- [ ] `ruff check` / `ruff format` 通过
- [ ] 不修改任何生产代码（`app/` 零改动），仅动测试与 fixture

## 六、注意事项

1. **不改生产代码**：本次仅治理测试，业务语义（保留原片、无 preview 端点、无 `register_ai_files`）均维持现状。
2. **秒传语义**：`files.original_name` 有 UNIQUE 约束是 109 的既定设计（展示名唯一、物理路径可复用），测试构造须遵守。
3. **module 级 DB 共享**：autouse rollback 只回滚未提交事务，不影响用例内已 `commit` 的数据。
4. **日志规范**：异常统一 `%s` 风格（AGENTS.md 核心约束 5）。
