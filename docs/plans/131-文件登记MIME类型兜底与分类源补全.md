> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 131 |
> | 文档版本 | v1.1.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-09-04 |
> | 对应功能/内容 | 文件登记入口统一补齐 `mime_type` + 骨架类 `upload_source` 分类源补全 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-09-04 | v1.0.0 | 初版：全量登记入口排查 + 兜底方案 + 分类源补全 |
> | 2026-09-04 | v1.1.0 | 实施完成：登记函数 mime 兜底 + 分类源常量 + 报告落库 source 细化，25 用例通过 |
>
> **关联文档**：[109-文件管理系统](./109-文件管理系统.md)、[116-文件类型探测与修复](./116-文件类型探测与修复.md)、[118-分析流水线重构与视频信息表](./118-分析流水线重构与视频信息表.md)、[121-写表步骤批量插入优化](./121-写表步骤批量插入优化.md)、[125-Admin文件管理简化与查询优化](./125-Admin文件管理简化与查询优化.md)

# Step 131：文件登记 MIME 类型兜底与分类源补全

## 一、背景与动机

Admin 文件管理页观察到骨架封面 `1788331858328_8f1245f6_seg0_thumb.jpg` 的「文件类型」列显示为空（`--`）。该文件是裁剪段（`_seg0`）骨架视频的首帧缩略图，由姿态推理生成后登记入库。

排查后发现问题不止一处：**Step 116 只修了「上传端点」的 mime 探测，其余登记入口（骨架视频/封面、裁剪播放短片、报告落库、孤儿注册）依然依赖调用方手传 `mime_type`，而这些调用方全部没有传**，导致大量骨架衍生文件的 `mime_type` 落库为空字符串。

同时发现第二个隐患：分类逻辑里的 `upload_source` 集合与实际登记值不匹配（`skeleton` vs `skeleton_video`/`skeleton_thumb`/`skeleton_frame`），无 `business_id` 的骨架文件会被判为「未绑定业务记录」→ `unreferenced`，存在被误清理风险。

目标：**一处兜底覆盖全部登记入口**，并让分类源与实际登记值对齐；存量空值由既有「修复文件类型」功能补齐。

## 二、现状分析

### 2.1 登记入口 mime_type 全量排查

| # | 入口 | 位置 | 是否传 mime | 现状 |
|---|------|------|:-----------:|------|
| 1 | 视频上传 | `routers/video.py` | ✅ | 落盘后 `detect_media_mime` 覆盖，正确 |
| 2 | 播放短片登记 | `routers/video.py` | ✅ | 复用 `file_record.mime_type` |
| 3 | 抽帧帧图登记 | `routers/video.py` | ✅ | 写死 `image/jpeg` |
| 4 | 头像上传 | `routers/upload.py` | ✅ | 落盘后 `detect_image_mime` 覆盖 |
| 5 | 装备封面上传 | `routers/upload.py` | ✅ | `detect_image_mime` |
| 6 | 骨架视频/封面（单步姿态） | `routers/pose.py:_persist_pose` | ❌ | **空** |
| 7 | 骨架视频/封面（管线） | `services/pipeline.py:_write_pose_result` | ❌ | **空**（info dict 无 mime 字段） |
| 8 | 裁剪播放短片（管线） | `services/pipeline.py:_process_video` | ❌ | **空** |
| 9 | 报告落库 | `routers/analyses.py:create_analysis` | ❌ | **空**（thumb/video/highlights/骨架全量） |
| 10 | 孤儿文件注册 | `services/file_service.py:register_orphan_files` | ❌ | **空**（直接构造 `File`） |
| 11 | 统一分析上传 | `routers/analyses.py:start_analysis` | ⚠️ | 用 `file.content_type`，小程序常不带 → 空；也未像 video.py 那样落盘后 ffprobe 覆盖 |

### 2.2 根因

`get_or_create_file` / `batch_get_or_create_files` 的 `mime_type` 默认 `""`，**探测职责被推给调用方**；调用方（骨架/封面/孤儿）没有探测能力也无从获取，于是全量落空。而 `app/core/mime.py` 的 `detect_mime_type` 已具备探测能力，却只在上传端点与「修复文件类型」里被调用。

### 2.3 分类源不匹配

```python
CONSUMED_SOURCES = {"video_playback", "skeleton", "analysis_thumb", "avatar", "gear_image"}
```

但实际登记值是 `skeleton_video` / `skeleton_thumb` / `skeleton_frame`（`pose.py:150-155`）、`video_playback`、`analysis_thumb`、以及存量 `skeleton`（`analyses.py:181`）。

后果：`classify_file_usage` 步骤 4 与 `bulk_classify_files` 的兜底匹配漏掉这三种骨架源 → 落到 `unreferenced / 未绑定业务记录`。有 `business_id` 的骨架文件因走步骤 3 `_check_analysis` 仍判 `in_use`（表面无感），无 `business_id` 的则是误判。

## 三、设计方案

### 3.1 登记函数内部兜底（核心）

原则：**调用方传了就尊重，没传就由登记函数补齐**，一处改动覆盖 6/7/8/9/10 五个入口。

新增 `file_service.resolve_mime_type(abs_path, upload_source, mime_type, probe=True)`：

- `mime_type` 非空 → 直接返回（不覆盖调用方的准确值）
- `probe=True` → `detect_mime_type(abs_path, upload_source)`（PIL/ffprobe 真实探测，读盘）
- `probe=False` → 仅确定性扩展名映射 `mime_type_from_ext`（**零磁盘 I/O**）
- 探测异常 → 回退扩展名映射，不抛错

接入点：

| 函数 | probe | 理由 |
|------|:-----:|------|
| `get_or_create_file` | True | 已读盘算 MD5，多一次探测开销可忽略 |
| `batch_get_or_create_files` | False | 121 优化明确要求「本函数不做任何磁盘读取」，用扩展名映射保证非空且不破坏契约 |
| `register_orphan_files` | True | 已读盘算 MD5 + size |

秒传分支同步修复：`mime_type=existing.mime_type or <本次探测值>`，避免存量空值被秒传复制扩散。

### 3.2 `mime.py` 新增公开扩展名映射入口

`detect_mime_type` 会走 PIL/ffprobe（有 I/O），批量登记路径需要无 I/O 版本：

```python
def mime_type_from_ext(path: str) -> str:
    """仅按扩展名推断 MIME（无磁盘 I/O），未知返回空字符串"""
    return _ext_mime(path) or ""
```

### 3.3 分类源补全

```python
# 需按 Analysis 路径匹配判定的上传源（骨架/封面/播放短片，含存量 skeleton）
ANALYSIS_MATCH_SOURCES = {
    "video_playback", "skeleton", "skeleton_video", "skeleton_thumb",
    "skeleton_frame", "analysis_thumb",
}
CONSUMED_SOURCES = ANALYSIS_MATCH_SOURCES | {"avatar", "gear_image"}
```

`classify_file_usage`（步骤 4）与 `bulk_classify_files`（用户 ID 预收集 + 兜底匹配）统一改用 `ANALYSIS_MATCH_SOURCES`，替换硬编码元组 `("video_playback", "skeleton", "analysis_thumb")`。

### 3.4 报告落库 upload_source 细化

`analyses.py:create_analysis` 目前 `source = "video" if rel_path == body.video_url else "skeleton"`，封面/骨架视频/骨架帧全部混为 `skeleton`。改为按文件名后缀区分：

| 文件 | 新 upload_source |
|------|------------------|
| `video_url` | `video` |
| `thumb` | `analysis_thumb` |
| `*_skeleton.mp4` | `skeleton_video` |
| `*_thumb.jpg` / `*_thumb.png` | `skeleton_thumb` |
| 其他图片（骨架帧） | `skeleton_frame` |
| 兜底 | `skeleton` |

新值均在 `ANALYSIS_MATCH_SOURCES` 内，分类行为与原先一致但更准确。

### 3.5 统一分析上传对齐 video.py

`start_analysis` 的 `mime_type=file.content_type or ""` 改为 `detect_media_mime(video_path)`，与 `video.py` 一致（服务端探测优先于客户端 Content-Type）。

### 3.6 存量数据修复

不改数据结构，复用 Step 116 已有的 `repair_file_mime_types`：

- Admin 文件管理页点「修复文件类型」→ `POST /api/admin/files/repair`
- 或 CLI：`uv run python scripts/repair-files.py`

## 四、实现步骤

### Step 1：`app/core/mime.py`
- 新增 `mime_type_from_ext(path) -> str`（公开，无 I/O）

### Step 2：`app/services/file_service.py`
- 新增 `resolve_mime_type(...)`
- `get_or_create_file`：函数入口解析 abs_path 并补齐 mime；秒传分支 `existing.mime_type or mime_type`
- `batch_get_or_create_files`：新记录 `info.get("mime_type") or mime_type_from_ext(rel_path)`；秒传分支同上
- `register_orphan_files`：`mime_type=resolve_mime_type(abs_path, upload_source)`
- 新增 `ANALYSIS_MATCH_SOURCES`，`CONSUMED_SOURCES` 改为并集；分类两处硬编码元组替换为常量

### Step 3：`app/routers/analyses.py`
- `create_analysis`：新增 `_infer_file_source()`，替换二元判定
- `start_analysis`：`mime_type=detect_media_mime(video_path)`

### Step 4：测试
- 新增 `server/tests/test_file_service_mime.py`（见第五节）

### Step 5：存量修复与验收
- 本地 Admin 点「修复文件类型」，确认 `1788331858328_8f1245f6_seg0_thumb.jpg` 类型补为 `image/jpeg`

## 五、TDD 测试用例

文件：`server/tests/test_file_service_mime.py`

| 编号 | 用例 | 断言 | 标记 |
|------|------|------|:----:|
| 1 | test_mime_type_from_ext_jpg | `.jpg` → `image/jpeg` | fast |
| 2 | test_mime_type_from_ext_mp4 | `.mp4` → `video/mp4` | fast |
| 3 | test_mime_type_from_ext_unknown | `.bin` → `""` | fast |
| 4 | test_resolve_mime_respects_caller | 传入非空值时不覆盖 | fast |
| 5 | test_resolve_mime_probe_jpg | 空值 + probe=True，假内容 .jpg → 回退 `image/jpeg` | fast |
| 6 | test_resolve_mime_no_probe | probe=False 且文件不存在 → 仍返回扩展名映射（零 I/O） | fast |
| 7 | test_get_or_create_file_fills_mime | 不传 mime 登记 `.jpg` → 落库 `image/jpeg` | - |
| 8 | test_get_or_create_file_fills_mime_mp4 | 不传 mime 登记 `.mp4` → 落库 `video/mp4` | - |
| 9 | test_reuse_fills_empty_mime | 秒传命中且 `existing.mime_type` 为空 → 新记录补上探测值 | - |
| 10 | test_batch_fills_mime_by_ext | 批量登记（`skeleton_video`/`skeleton_thumb`）→ `video/mp4` / `image/jpeg` | - |
| 11 | test_register_orphan_files_fills_mime | 孤儿注册后 mime 非空 | - |
| 12 | test_classify_skeleton_video_source | `skeleton_video` 无 business_id → 按 Analysis 匹配判 `in_use` | - |
| 13 | test_bulk_classify_skeleton_thumb | `bulk_classify_files` 对 `skeleton_thumb` 走 Analysis 兜底匹配 | - |
| 14 | test_infer_file_source | `_infer_file_source` 对 video/thumb/骨架视频/骨架封面/骨架帧判定正确 | fast |

## 六、产出物清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `server/app/core/mime.py` | 新增 `mime_type_from_ext` |
| 修改 | `server/app/services/file_service.py` | `resolve_mime_type` + 三处登记兜底 + 分类源常量 |
| 修改 | `server/app/routers/analyses.py` | `_infer_file_source` + start_analysis 探测 |
| 新增 | `server/tests/test_file_service_mime.py` | 14 用例 |
| 修改 | `docs/README.md` | 文档一览与执行进度 |
| 修改 | `AGENTS.md` | 进度表新增 131 |

## 七、验收标准

- [x] 骨架视频/封面登记后 `mime_type` 分别为 `video/mp4` / `image/jpeg`（不再为空）
- [x] 裁剪播放短片、报告落库文件、孤儿注册文件 `mime_type` 非空
- [x] `get_or_create_file` 传入非空 mime 时不被覆盖（调用方优先）
- [x] `batch_get_or_create_files` 全程无磁盘 I/O（仅扩展名映射）
- [x] `skeleton_video` / `skeleton_thumb` / `skeleton_frame` 在无 `business_id` 时按 Analysis 路径匹配，不再误判「未绑定业务记录」
- [ ] Admin 点「修复文件类型」后存量空 mime 全部补齐（待人工在本地 8000 触发）
- [x] `ruff check` / `ruff format` / `pytest -m fast` 通过；全量 `pytest` 无回归（基线 10 failed/529 passed → 改动后 10 failed/554 passed，失败集合一致）

## 八、注意事项

1. **不覆盖调用方**：上传端点（video/upload）已传入服务端探测值，兜底仅在空值时生效，避免重复探测与值被降级。
2. **批量路径零 I/O**：`batch_get_or_create_files` 处于 121 优化后的写表热路径，绝不可引入 ffprobe/PIL 读盘；扩展名映射对 `.mp4`/`.jpg` 已足够准确，真实类型纠正交给 `repair_file_mime_types`。
3. **秒传语义**：秒传复用 `existing.mime_type`，仅在其为空时用本次探测值补齐，不改变既有复用逻辑。
4. **存量 `skeleton` 值保留**：`ANALYSIS_MATCH_SOURCES` 保留 `skeleton`，兼容 118 之前落库的历史记录。
5. **日志规范**：异常统一 `%s` 风格，禁止 f-string 插值异常对象（见 AGENTS.md 核心约束 5）。
