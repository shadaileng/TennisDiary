> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 125 |
> | 文档版本 | v1.1.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-09-02 |
> | 对应功能/内容 | Admin 文件管理端简化与查询性能优化 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-09-02 | v1.0.0 | 初版 |
> | 2026-09-02 | v1.1.0 | 实施完成：删除 get_file/preview/register-all 端点 + 移除 DerivedFileInfo + 统一 bulk_classify_files |
>
> **关联文档**：[109：文件管理系统](./109-文件管理系统.md)、[110：文件扫描功能](./110-文件扫描功能.md)、[111：文件使用标记](./111-文件使用标记.md)、[114：Admin 文件预览与下载](./114-文件预览与下载.md)、[116：文件类型探测与修复](./116-文件类型探测与修复.md)

# Admin 文件管理简化与查询优化

## 一、背景与动机

Admin 文件管理（`/api/admin/files`）自 Step 109 逐步叠加功能后，存在以下问题：

1. **列表查询 N+1**：每条文件记录单独查询派生文件（`derived_files`），表格不展示但每页 20 条触发 20 次额外查询
2. **分类查询未统一**：非 `usage_status` 筛选路径逐条调 `classify_file_usage`（每次查 3 张表），已有批量版本 `bulk_classify_files` 但未全量使用
3. **冗余端点**：`preview` 端点前端未调用、`register` 和 `register-all` 功能重叠、`get_file` 详情端点未使用
4. **Schema 冗余**：`DerivedFileInfo` 仅支撑列表无意义查询

目标：**删减 2 个端点 + 2 个 Schema，列表页查询从 O(N×K) 降到 O(N)**。

## 二、现状分析

### 端点清单（13 个）

| 端点 | 方法 | 使用频率 | 问题 |
|------|------|---------|------|
| `GET /api/admin/files` | 列表 | 高 | N+1（derived + classify） |
| `GET /api/admin/files/{file_id}` | 详情 | **未使用** | 前端 `viewFile` 直接用列表数据 |
| `GET /api/admin/files/stats/summary` | 统计 | 高 | 全表逐条 classify |
| `DELETE /api/admin/files/{file_id}` | 删除 | 中 | 正常 |
| `POST /api/admin/files/batch-delete` | 批量删除 | 中 | N+1（逐条查询） |
| `POST /api/admin/files/cleanup` | 清理软删 | 低 | 正常 |
| `POST /api/admin/files/cleanup-orphans` | 清理磁盘孤儿 | 低 | 正常 |
| `POST /api/admin/files/scan` | 扫描孤儿 | 低 | 保留 |
| `POST /api/admin/files/register` | 注册孤儿 | 低 | 与 register-all 重叠 |
| `POST /api/admin/files/register-all` | 一键注册 | 低 | 冗余 |
| `GET /api/admin/files/{file_id}/download` | 下载 | 中 | 正常（手动鉴权是技术需要） |
| `GET /api/admin/files/{file_id}/preview` | 预览元数据 | **未使用** | 前端可从列表数据构造 |
| `POST /api/admin/files/repair` | 修复 MIME | 低 | 保留 |

### 查询性能问题定位

#### 问题 1：`_file_to_response` 派生文件 N+1

```python
# files.py:44-53 — 每个文件单独查一次
derived_records = (
    db.query(File)
    .filter(
        File.business_type == file_record.business_type,
        File.business_id == file_record.business_id,
        File.id != file_record.id,
        File.deleted_at.is_(None),
    )
    .all()
)
```

- 表格列：ID / 用户 / 文件名 / 大小 / 来源 / 状态 / 引用 / 时间 — **无 derived_files**
- 仅在详情弹窗展示，但详情端点 `get_file` 前端未调用
- 每页 20 条 = 20 次额外查询

#### 问题 2：`list_files` 非筛选路径 classify N+1

```python
# files.py:133 — 无 classifications 参数
items=[_file_to_response(f, db) for f in files]
# → _file_to_response 内部调 classify_file_usage(db, file_record)
# → 每次查 User/Gear/Analysis 表
```

#### 问题 3：`file_stats` 全表逐条分类

```python
# files.py:171-174 — 加载全部文件到内存逐条分类
for f in db.query(File).filter(File.deleted_at.is_(None)).all():
    status, _ = file_service.classify_file_usage(db, f)
    if status != "in_use":
        unreferenced_count += 1
```

已有 `bulk_classify_files`（`file_service.py:852`）通过 `IN` 查询批量预加载，但未在此使用。

## 三、精简方案

### 改动 1：列表移除 derived_files 查询（P0）

**影响范围**：`files.py`、`admin_file.py`、`test_files.py`

| 文件 | 改动 | 行数变化 |
|------|------|---------|
| `files.py:44-53` | 删除 `_file_to_response` 中 derived_files 查询逻辑 | -22 行 |
| `files.py:141-152` | 删除 `get_file` 端点（前端未调用） | -12 行 |
| `admin_file.py:23-32` | 删除 `DerivedFileInfo` 类 | -10 行 |
| `admin_file.py:50-52` | `AdminFileResponse` 移除 `derived_files` 字段 | -3 行 |
| `test_files.py:111-136` | 删除 `TestAdminFileDetail` 类（含 `test_detail_includes_derived`） | -26 行 |

**效果**：列表页每页省 20 次查询。

### 改动 2：统一 bulk_classify_files（P0）

**影响范围**：`files.py`

| 位置 | 改动 |
|------|------|
| `files.py:128-138` | 非筛选路径：先调 `bulk_classify_files` 获取全部分类，传入 `_file_to_response` |
| `files.py:170-174` | `file_stats`：用 `bulk_classify_files` 替代逐条 `classify_file_usage` 循环 |

**改动后 list_files 非筛选路径**：

```python
# 先批量分类
all_files = query.order_by(File.created_at.desc()).offset(offset).limit(limit).all()
classifications = file_service.bulk_classify_files(db, all_files)

return ApiResponse(
    data=AdminFileListResponse(
        items=[_file_to_response(f, db, classifications) for f in all_files],
        total=total,
        offset=offset,
        limit=limit,
    )
)
```

**改动后 file_stats**：

```python
# 批量分类替代逐条循环
all_files = db.query(File).filter(File.deleted_at.is_(None)).all()
classifications = file_service.bulk_classify_files(db, all_files)
unreferenced_count = sum(
    1 for fid, (st, _) in classifications.items() if st != "in_use"
)
```

**效果**：classify 查询从 O(N×K) 降到 O(N)（1 次批量 IN 查询）。

### 改动 3：删除 preview 端点（P1）

**影响范围**：`files.py`、`admin/src/api/files.ts`、`admin/src/views/files/index.vue`、`test_files.py`

| 文件 | 改动 |
|------|------|
| `files.py:485-519` | 删除 `preview_file` 端点 |
| `admin/src/api/files.ts:116-127` | 删除 `PreviewInfo` 接口和 `getPreviewInfo` 函数 |
| `admin/src/views/files/index.vue:699-706` | `openPreview` 改为直接用列表数据构造 URL |
| `test_files.py:453-467` | 删除 `test_preview_fallback_mp4_empty_mime` |

**前端改动**：

```ts
// 改前：调 API 获取 preview 信息
const openPreview = async (file: AdminFile) => {
  const info = await getPreviewInfo(file.id)
  previewInfo.value = info
  previewVisible.value = true
}

// 改后：直接用列表数据构造
const openPreview = (file: AdminFile) => {
  previewInfo.value = {
    id: file.id,
    original_name: file.original_name,
    mime_type: file.mime_type,
    size_bytes: file.size_bytes,
    preview_url: `/api/admin/system/files/${file.rel_path}`,
  }
  previewVisible.value = true
}
```

**效果**：删 1 端点 + 1 API 函数 + 减 1 网络请求。

### 改动 4：合并 register + register-all（P1）

**影响范围**：`files.py`、`admin_file.py`、`admin/src/api/files.ts`、`admin/src/views/files/index.vue`、`test_files.py`

| 文件 | 改动 |
|------|------|
| `files.py:318-374` | 合并为一个 `POST /register`，`files: []` 时自动 scan 全量注册 |
| `files.py:344-374` | 删除 `register_all_files` 端点 |
| `admin_file.py:90-94` | `RegisterFilesRequest.files` 改为 `default_factory=list` |
| `admin/src/api/files.ts:108-110` | 删除 `registerAllFiles` |
| `admin/src/views/files/index.vue:856-869` | `confirmRegisterAll` 改为调 `registerFiles([])` |
| `test_files.py:405-418` | 删除 `TestAdminFileRegisterAll`，在 `TestAdminFileRegister` 增加空列表用例 |

**合并后 register 端点逻辑**：

```python
@router.post("/register", response_model=ApiResponse[dict])
def register_files(body: RegisterFilesRequest, ...):
    if not body.files:
        # 空列表 = 扫描并注册全部孤儿
        scan_result = file_service.scan_orphan_files(db)
        rel_paths = [o["rel_path"] for o in scan_result["orphans"]]
    else:
        rel_paths = body.files

    registered = file_service.register_orphan_files(db, rel_paths=rel_paths, ...)
    # ...
```

**效果**：删 1 端点 + 1 Schema 字段简化。

### 改动 5：Schema 精简

**影响范围**：`admin_file.py`

| 删除 | 说明 |
|------|------|
| `DerivedFileInfo`（23-32 行） | 仅支撑列表无意义查询 |
| `AdminFileResponse.derived_files`（50-52 行） | 列表不展示，详情端点删除 |

保留 `OrphanFileInfo`、`ScanResultResponse`、`RegisterFilesRequest`、`CleanupOrphansRequest`、`BatchDeleteRequest`。

## 四、不改动部分

| 保留 | 原因 |
|------|------|
| `scan` 端点 | 用户要求保留 |
| `repair` 端点 | 用户要求保留 |
| `cleanup` 端点 | 清理软删文件，独立功能 |
| `cleanup-orphans` 端点 | 清理磁盘孤儿，独立功能 |
| `download` 端点 | 手动鉴权是技术需要（`<a download>` 无法带 header） |
| `batch_delete_files` | 批量删除核心功能（N+1 问题不在本次范围） |

## 五、执行步骤

### Step 1：后端 Schema 精简

- [ ] `admin_file.py`：删除 `DerivedFileInfo` 类
- [ ] `admin_file.py`：`AdminFileResponse` 移除 `derived_files` 字段
- [ ] `admin_file.py`：`RegisterFilesRequest.files` 改为 `default_factory=list`
- [ ] 运行 `ruff check` + `ruff format`

### Step 2：后端路由简化

- [ ] `files.py`：`_file_to_response` 移除 derived_files 查询逻辑
- [ ] `files.py`：删除 `get_file` 端点
- [ ] `files.py`：删除 `preview_file` 端点
- [ ] `files.py`：删除 `register_all_files` 端点
- [ ] `files.py`：`register_files` 支持空列表触发 scan-and-register
- [ ] `files.py`：`list_files` 非筛选路径统一使用 `bulk_classify_files`
- [ ] `files.py`：`file_stats` 使用 `bulk_classify_files` 替代逐条循环
- [ ] 运行 `ruff check` + `ruff format`

### Step 3：后端测试更新

- [ ] `test_files.py`：删除 `TestAdminFileDetail` 类
- [ ] `test_files.py`：删除 `test_preview_fallback_mp4_empty_mime`
- [ ] `test_files.py`：删除 `TestAdminFileRegisterAll`
- [ ] `test_files.py`：`TestAdminFileRegister` 增加空列表注册全部用例
- [ ] 运行 `pytest -m fast` 确认通过

### Step 4：前端 API 层

- [ ] `admin/src/api/files.ts`：删除 `PreviewInfo` 接口
- [ ] `admin/src/api/files.ts`：删除 `getPreviewInfo` 函数
- [ ] `admin/src/api/files.ts`：删除 `registerAllFiles` 函数

### Step 5：前端页面

- [ ] `admin/src/views/files/index.vue`：`openPreview` 改为直接构造 URL
- [ ] `admin/src/views/files/index.vue`：`confirmRegisterAll` 改为调 `registerFiles([])`
- [ ] 运行 `pnpm run type-check` + `pnpm run build`

### Step 6：文档与提交

- [ ] 更新本方案状态为 🚧 进行中 → 🏁 已完成
- [ ] 更新 `docs/README.md` 执行进度
- [ ] 同步侧边栏

## 六、预期效果

| 指标 | 改前 | 改后 |
|------|------|------|
| 列表页查询数 | O(N×K)（N=文件数，K≈3 次分类查询） | O(N)（1 次批量分类） |
| stats 查询数 | O(N×K)（全表逐条分类） | O(N)（1 次批量分类） |
| 后端端点数 | 13 | 11 |
| Schema 类数 | 7 | 5 |
| 前端代码量 | 887 行 | ≈800 行（减 ~87 行） |
| 列表页额外查询 | 20 次/页（derived） | 0 次/页 |
