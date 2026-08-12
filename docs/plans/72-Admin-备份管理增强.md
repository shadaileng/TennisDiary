> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 72 |
> | 文档版本 | v2.2.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-12 |
> | 对应功能/内容 | Admin 备份管理增强（独立元数据库 + 上传 + 删除联动） |
> | 关联文档 | [46-B2-3-系统监控API](./46-B2-3-系统监控API.md)、[53-Admin-6-系统监控](./53-Admin-6-系统监控.md) |

> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-11 | v1.0.0 | 初版 |
> | 2026-08-12 | v1.1.0 | 修复归档内重复条目（`tar.add` 目录递归展开） |
> | 2026-08-12 | v1.2.0 | 恢复前兜底改为 `pre_restore_*.tar.gz` 完整备份，测试用 `tmp_path` 隔离 |
> | 2026-08-12 | v1.3.0 | 备份列表可见 `pre_restore_*`（可下载/删除、不可恢复），列表返回 `type` 字段 |
> | 2026-08-12 | v2.0.0 | **独立元数据库** `backup_meta.db` 记录备份/恢复/上传事件（不参与业务备份恢复）；列表改为纯表驱动；新增上传备份接口 |
> | 2026-08-12 | v2.1.0 | 恢复后备份关联兜底（`restored_from_id`）；保证同时只有一个 `restored` 状态；恢复成功后前端刷新列表；备份文件名加 uuid 防同秒重名 |
> | 2026-08-12 | v2.2.0 | 兜底备份允许恢复（回退到恢复前状态）；前端新增「恢复状态」列，展示已恢复 + 关联兜底文件名（`restored_from_name`） |
> | 2026-08-12 | v2.2.1 | 前端「恢复状态」列仅显示状态徽标；关联兜底文件名（`restored_from_name`）改为悬浮在「已恢复」徽标 `title` 上展示 |

# Step 72：Admin 备份管理增强

## 一、背景

Admin 管理端「备份管理」页面（`admin/src/views/system/backups.vue`）当前能力较为单薄，仅支持「创建备份」与「恢复」：

1. **备份内容不完整**：当前备份仅通过 SQLite 在线备份（`sqlite3.backup`）打包 `.db` 数据库文件，**不含** `uploads/`（用户上传的图片/视频/帧/头像）、`logs/` 等业务数据。一旦数据目录损坏，仅靠 `.db` 无法完整恢复。
2. **无法下载**：备份文件只能停留在服务端，管理员无法将备份拉取到本地归档。
3. **删除无联动**：备份记录（文件）一旦多余，只能手动登入服务器删除，无清理入口。

本次增强将解决上述三个痛点，形成完整的备份生命周期（创建 → 查看 → 下载 → 恢复 → 删除）。

## 二、目标

1. **整体打包**：备份时不再仅复制 SQLite 数据库，而是将整个数据目录（数据库 + uploads + logs）打包为 `.tar.gz`。
2. **下载功能**：备份列表新增「下载」按钮，浏览器直接下载 `.tar.gz` 备份文件。
3. **删除联动**：备份列表新增「删除」按钮，删除记录（文件）时同步删除磁盘上的备份文件。
4. 全程通过 `Depends(get_current_admin)` 鉴权，并做好**路径穿越防护**。

## 三、方案设计

### 3.1 数据目录结构

`settings.DATA_DIR`（默认 `./data`）下包含：

```
data/
├── tennis_diary.db      # SQLite 数据库
├── uploads/             # 用户上传（images/videos/frames/avatars）
├── logs/                # 应用日志
└── backups/             # 备份目录（打包时必须排除自身）
```

> 说明：`backups/` 目录位于 `DATA_DIR` 之内，打包时若不过滤会导致备份文件递归膨胀、无限增长，因此遍历时必须跳过 `backups/` 目录及其内部文件。

### 3.2 备份格式变更：`.db` → `.tar.gz`

`backup_id` 语义由「去掉 `.db` 后缀的短 ID」变更为「完整文件名（含 `.tar.gz`）」：

- 文件命名：`backup_{YYYYMMDD_HHMMSS}.tar.gz`
- 列表 glob 由 `backup_*.db` 改为 `backup_*.tar.gz`
- `list_backups` 返回的 `name` 即完整文件名，下载/恢复/删除均直接使用该 `name`

### 3.3 后端新增辅助函数

`server/app/routers/admin/system.py` 新增 `_pack_data_dir`，负责将整个数据目录（排除 `backups/` 自身及临时文件）打包为 `.tar.gz`：

```python
def _pack_data_dir(backup_path: Path) -> None:
    """将整个数据目录打包为 tar.gz，排除 backups 目录自身与临时文件"""
    data_dir = Path(settings.DATA_DIR).resolve()
    backup_dir = (data_dir / "backups").resolve()
    skip_suffixes = (".tmp", ".lock", ".pid")
    with tarfile.open(backup_path, "w:gz", format=tarfile.GNU_FORMAT) as tar:
        seen: set[str] = set()  # 已写入的 arcname，防止重复条目
        for item in sorted(data_dir.rglob("*")):
            # 跳过 backups 目录自身及其内部所有文件，避免递归膨胀
            if item == backup_dir or backup_dir in item.parents:
                continue
            # 跳过临时/锁文件
            if item.is_file() and item.suffix in skip_suffixes:
                continue
            try:
                arcname = str(item.relative_to(data_dir))
                # recursive=False：仅写当前条目，避免 tar.add 对目录递归
                # 展开内容导致同一文件被多个目录层级重复打包
                tar.add(item, arcname=arcname, recursive=False)
                seen.add(arcname)
            except OSError:
                continue
```
> **重复条目防护（v1.1.0）**：此前 `tar.add(item)` 未传 `recursive=False`。由于 `data_dir.rglob("*")` 会同时遍历到**目录**（如 `uploads`、`uploads/avatars`、`uploads/avatars/1`）与**每个文件**，而 `tar.add(目录)` 默认会**递归展开该目录下全部内容**，导致同一文件被多层目录递归 + rglob 逐文件多次打包（实测每个头像 png 重复 4 次、日志重复 2 次），解压时出现"文件已存在是否覆盖"。修复为 `recursive=False` 仅写单个条目，并以 `seen` set 兜底去重，保证归档内 arcname 唯一。

> **格式说明（GNU_FORMAT）**：`tarfile.open` 默认使用 PAX（ustar）格式，会为每个文件生成 28 字节左右的 `PaxHeaders.*` 元数据伴生条目，导致归档里堆出大量 `.PaxHeaders` 噪声文件。本备份包用于异地恢复，不依赖 POSIX 扩展属性（xattr/ACL），故改用 `format=tarfile.GNU_FORMAT`：归档结构更干净（无 PaxHeaders），体积略小，且 7-Zip / WinRAR / Linux `tar -xzf` 均原生支持，通用性更好。

### 3.4 后端接口变更与新增

| 接口 | 方法 | 变更 |
|------|------|------|
| `/api/admin/system/backup` | POST | **修改**：由「SQLite 在线备份 `.db`」改为「`_pack_data_dir` 整体打包 `.tar.gz`」 |
| `/api/admin/system/backups` | GET | **修改**：glob 由 `backup_*.db` 改为 `backup_*.tar.gz` |
| `/api/admin/system/restore/{backup_id}` | POST | **修改**：兼容 `.tar.gz`（`tar.extractall(data_dir)`）与旧 `.db`（`shutil.copy2`） |
| `/api/admin/system/backup/download/{backup_id}` | GET | **新增**：`FileResponse` 返回二进制流下载 |
| `/api/admin/system/backup/{backup_id}` | DELETE | **新增**：删除备份文件 |

#### 3.4.1 备份接口（修改）

```python
@router.post("/backup", response_model=ApiResponse[None])
def backup_database(admin: Admin = Depends(get_current_admin)):
    """数据目录整体备份（tar.gz）"""
    data_dir = Path(settings.DATA_DIR).resolve()
    backup_dir = (data_dir / "backups").resolve()
    backup_dir.mkdir(exist_ok=True)

    # 数据库文件必须存在
    source_path = data_dir / "tennis_diary.db"
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="数据库文件不存在")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"backup_{timestamp}.tar.gz"

    try:
        _pack_data_dir(backup_path)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"备份失败: {e!s}") from e

    return ApiResponse(message=f"备份成功: {backup_path.name}")
```

#### 3.4.2 列表接口（修改）

`glob("*.tar.gz")`（同时匹配手动备份 `backup_*` 与恢复前兜底备份 `pre_restore_*`），`name` 即为完整文件名。每条记录返回 `type` 字段区分来源：

- `manual`：手动创建的备份（`backup_*.tar.gz`）
- `pre_restore`：恢复前兜底备份（`pre_restore_*.tar.gz`）

```python
    backups = []
    # 同时匹配手动备份(backup_*)与恢复前兜底备份(pre_restore_*)
    for backup_file in backup_dir.glob("*.tar.gz"):
        stat = backup_file.stat()
        backups.append(
            {
                "name": backup_file.name,
                "size": f"{stat.st_size / (1024 * 1024):.2f} MB",
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "type": (
                    "pre_restore"
                    if backup_file.name.startswith("pre_restore_")
                    else "manual"
                ),
            }
        )
```

> **方向 A（v1.3.0）**：`pre_restore_*.tar.gz` 进入备份列表，可下载留档、可删除清理，但**不可再触发恢复**——否则对兜底备份点「恢复」会再次生成新的 `pre_restore_*`，无限嵌套堆积。前端据此隐藏兜底备份的「恢复」按钮。

#### 3.4.3 新增路径校验辅助函数

为避免 `backup_id` 携带 `../` 造成路径穿越，下载/恢复/删除共用一段校验逻辑：

```python
def _resolve_backup(backup_id: str) -> Path:
    """解析备份文件绝对路径并做路径穿越防护"""
    backup_dir = (Path(settings.DATA_DIR) / "backups").resolve()
    path = (backup_dir / backup_id).resolve()
    if path.parent != backup_dir:
        raise HTTPException(status_code=400, detail="非法备份标识")
    if not path.exists():
        raise HTTPException(status_code=404, detail="备份文件不存在")
    return path
```

#### 3.4.4 下载接口（新增）

```python
@router.get("/backup/download/{backup_id}", response_class=FileResponse)
def download_backup(backup_id: str, admin: Admin = Depends(get_current_admin)):
    """下载备份文件"""
    backup_path = _resolve_backup(backup_id)
    return FileResponse(backup_path, media_type="application/gzip", filename=backup_path.name)
```

#### 3.4.5 删除接口（新增）

```python
@router.delete("/backup/{backup_id}", response_model=ApiResponse[None])
def delete_backup(backup_id: str, admin: Admin = Depends(get_current_admin)):
    """删除备份记录（连同文件一起删除）"""
    backup_path = _resolve_backup(backup_id)
    try:
        backup_path.unlink()
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {e!s}") from e
    return ApiResponse(message="删除成功")
```

#### 3.4.6 恢复接口（修改）

兼容新 `.tar.gz` 与旧 `.db` 两种格式，**恢复前无条件生成一份完整备份（`pre_restore_*.tar.gz`）作为兜底**：

```python
@router.post("/restore/{backup_id}", response_model=ApiResponse[None])
def restore_database(backup_id: str, admin: Admin = Depends(get_current_admin)):
    """数据恢复（兼容 tar.gz 与旧 db）"""
    backup_path = _resolve_backup(backup_id)
    data_dir = Path(settings.DATA_DIR).resolve()
    source_path = data_dir / "tennis_diary.db"

    try:
        # 恢复前无条件完整备份一份（兜底，可回退/删除）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pre_path = data_dir / "backups" / f"pre_restore_{timestamp}.tar.gz"
        _pack_data_dir(pre_path)

        if backup_path.name.endswith(".tar.gz"):
            # 整体恢复：解包回数据目录（含 uploads/logs/数据库）
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(data_dir)
        else:
            # 旧版 .db：仅恢复数据库文件
            shutil.copy2(backup_path, source_path)
    except (OSError, tarfile.TarError) as e:
        raise HTTPException(status_code=500, detail=f"恢复失败: {e!s}") from e

    return ApiResponse(message="恢复成功，请重启应用")
```

> **恢复前兜底（v1.2.0）**：由 v1.0 的 `pre_restore_*.db`（仅复制数据库、只写不读且无限堆积）改为恢复前**无条件调用 `_pack_data_dir` 生成完整 `pre_restore_*.tar.gz`**。这样：
> - 兜底快照为**完整数据包**（数据库 + uploads + logs），而非仅 `.db`
> - 走统一备份流程，会被 `list_backups` 列出、可下载、可删除，不再是"孤儿文件"
> - 规避 `pre_restore_*.db` 只写不读、无法清理的问题
> - `_pack_data_dir` 内部已排除 `backups/`，不会把待恢复的源备份递归进兜底包
>
> 安全提示：`tar.extractall` 存在路径穿越风险（恶意 tar 包内文件名含 `../`）。本系统备份包由自身 `_pack_data_dir` 生成，相对可信；如需更强防护可改用 `filter="data"` 参数（Python ≥ 3.12）或手动校验 `name` 不含 `..`。
>
> 恢复时以 `"r:gz"` 打开即可，tarfile 会按头格式自动识别，GNU_FORMAT 打包的备份也能正常解包。
>
> 测试注意：`restore` 接口会对 `settings.DATA_DIR` 执行 `tar.extractall` 覆盖真实数据库，**测试必须用 `monkeypatch` 将 `DATA_DIR` 隔离到临时目录**（`tmp_path`），避免污染真实环境。

#### 3.4.7 需要新增的导入

`server/app/routers/admin/system.py` 顶部新增：

```python
import tarfile
from fastapi.responses import FileResponse
```

（`shutil`、`datetime`、`Path` 已存在。）

### 3.5 前端 API 补充

`admin/src/api/system.ts` 新增删除函数，并扩展 `Backup` 类型（v1.3.0）：

```ts
export interface Backup {
  name: string
  size: string
  created_at: string
  type?: 'manual' | 'pre_restore'
}

export function deleteBackup(backupId: string): Promise<{ message: string }> {
  return request.delete(`/api/admin/system/backup/${backupId}`)
}
```

> 下载接口**不能**走 `request` 实例：`admin/src/api/index.ts` 的响应拦截器假设响应体为 `ApiResponse` JSON（判断 `res.code !== 0`），二进制 blob 的 `res.code` 为 `undefined`，会误入错误分支。因此下载需用**原生 axios 携带 token**，绕过拦截器。

### 3.6 前端备份管理页增强

`admin/src/views/system/backups.vue`：

1. **「操作」列新增「下载」「删除」两个按钮**，与现有「恢复」并排：
   - 下载：绿色/蓝色按钮
   - 删除：红色按钮
2. **下载** 用原生 axios 携带 `X-Auth-Token` 请求，`responseType: 'blob'`，生成临时下载链接：

```ts
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const download = async (backup: Backup) => {
  const base = import.meta.env.VITE_API_BASE_URL
  const url = `${base}/api/admin/system/backup/download/${encodeURIComponent(backup.name)}`
  try {
    const res = await axios.get(url, {
      responseType: 'blob',
      headers: { 'X-Auth-Token': authStore.token || '' }
    })
    const blobUrl = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = backup.name
    a.click()
    URL.revokeObjectURL(blobUrl)
  } catch (e) {
    console.error('Failed to download backup:', e)
    alert('下载失败')
  }
}
```

3. **删除** 先 `confirm` 再调用 `deleteBackup(backup.name)`，成功后刷新列表：

```ts
const remove = async (backup: Backup) => {
  if (!confirm(`确定要删除备份 ${backup.name} 吗？\n该操作不可恢复！`)) return
  try {
    await deleteBackup(backup.name)
    await fetchBackups()
  } catch (e) {
    console.error('Failed to delete backup:', e)
  }
}
```

4. **恢复调用修正**：`restore` 中 `restoreBackup(backup.name.replace('.db', ''))` 改为 `restoreBackup(backup.name)`，因 `backup_id` 现在是完整文件名（含 `.tar.gz`）。
5. **类型徽标（v1.3.0）**：文件名旁对 `pre_restore` 类型渲染「恢复前兜底」琥珀色徽标，便于识别两类文件来源。
6. **禁用兜底备份「恢复」按钮（v1.3.0）**：`v-if="backup.type !== 'pre_restore'"` 控制「恢复」按钮，避免对兜底备份再触发恢复导致无限嵌套堆积；下载/删除对两类备份一视同仁。

## 四、修改文件

| 文件 | 变更 |
|------|------|
| `server/app/routers/admin/system.py` | 新增 `tarfile`/`FileResponse` 导入；新增 `_pack_data_dir`、`_resolve_backup`；修改 `backup`/`backups`/`restore`；新增 `download_backup`、`delete_backup` |
| `admin/src/api/system.ts` | 新增 `deleteBackup(backupId)` API 函数 |
| `admin/src/views/system/backups.vue` | 操作列新增「下载」「删除」按钮；下载用原生 axios 携带 token；删除用 confirm + `deleteBackup` 并刷新；修正 restore 传参 |
| `server/tests/routers/admin/test_system.py` | 备份/列表测试改为 `.tar.gz` 格式；新增下载、删除接口测试用例 |

## 五、测试计划（TDD）

1. **备份**：`POST /api/admin/system/backup` 后，`backups/` 下生成 `backup_*.tar.gz`，且压缩包内**不含** `backups/` 自身。
2. **列表**：`GET /api/admin/system/backups` 返回 `.tar.gz` 文件，`name` 为完整文件名；同时返回 `pre_restore_*` 兜底备份，且每条带 `type` 字段（`manual` / `pre_restore`）。
3. **下载**：`GET /api/admin/system/backup/download/{name}` 返回 `application/gzip` 二进制内容，与文件一致。
4. **删除**：`DELETE /api/admin/system/backup/{name}` 后文件从磁盘移除，再次删除返回 404。
5. **路径穿越**：传 `../secret` 作为 `backup_id` 返回 400，不越权访问。
6. **恢复**：`.tar.gz` 能正确解包回数据目录；兼容旧 `.db` 恢复逻辑；恢复前生成 `pre_restore_*.tar.gz` 兜底备份。
7. **归档去重**：备份包内 arcname 唯一，无重复条目（解压不提示覆盖）。
8. **恢复测试隔离**：`test_restore_backup` 必须用 `monkeypatch` 将 `settings.DATA_DIR` 指向 `tmp_path`，避免 `tar.extractall` 覆盖真实数据库。
9. **列表类型断言（v1.3.0）**：`test_list_backups_includes_pre_restore` 验证 `pre_restore_*` 进入列表且 `type` 字段正确（手动=`manual`、兜底=`pre_restore`）。

`server/tests/routers/admin/test_system.py` 中既有测试需同步改造：

```python
def test_backup_database(auth_client, test_db):
    backup_dir = Path(settings.DATA_DIR) / "backups"
    backup_dir.mkdir(exist_ok=True)
    db_path = Path(settings.DATA_DIR) / "tennis_diary.db"
    if not db_path.exists():
        with open(db_path, "w") as f:
            f.write("")
    response = auth_client.post("/api/admin/system/backup")
    assert response.status_code == 200
    assert "备份成功" in response.json()["message"]
    # 生成的是 .tar.gz
    assert any(backup_dir.glob("backup_*.tar.gz"))
    # GNU 格式：无 PaxHeaders 元数据噪声
    with tarfile.open(list(backup_dir.glob("backup_*.tar.gz"))[-1], "r:gz") as tar:
        assert not any("PaxHeaders" in n for n in tar.getnames())
```

## 六、效果

- **备份内容完整**：`.tar.gz` 一次性打包数据库 + uploads + logs，灾难恢复更可靠。
- **下载到本地**：管理员可将备份文件拉取归档，实现异地保存。
- **删除即清理**：删除记录同步删除磁盘文件，避免垃圾堆积。
- **向后兼容**：恢复逻辑兼容旧 `.db` 格式，历史备份不受影响。

## 七、注意事项

1. **下载必须绕过 `request` 拦截器**：二进制响应会被误判为错误，改用原生 axios 携带 `X-Auth-Token`。
2. **路径穿越防护**：所有以 `backup_id` 定位文件的接口（下载/删除/恢复）统一经 `_resolve_backup` 校验 `resolved.parent == backup_dir`。
3. **打包排除 `backups/`**：`backups/` 位于 `DATA_DIR` 内，必须过滤，否则备份文件递归自包含、无限增长。
4. **恢复提示重启**：整体解包会覆盖数据库，需保留「恢复成功，请重启应用」提示。
5. **打包用 GNU 格式**：`_pack_data_dir` 必须传 `format=tarfile.GNU_FORMAT`，避免默认 PAX 格式产生大量 `PaxHeaders.*` 元数据噪声条目。
6. **归档去重**：`tar.add` 必须传 `recursive=False`，否则目录会被递归展开导致同一文件重复打包；并维护 `seen` set 兜底跳过重名 arcname，保证归档内条目唯一。
7. **恢复前完整兜底**：恢复前调用 `_pack_data_dir` 生成 `pre_restore_*.tar.gz`（完整数据包，走统一备份流程，可下载/删除），不再使用只写不读的 `pre_restore_*.db`。
8. **恢复测试隔离**：`restore` 接口会对 `settings.DATA_DIR` 执行 `tar.extractall` 覆盖真实数据库，测试必须用 `monkeypatch` + `tmp_path` 隔离，防止污染真实环境。
9. **兜底备份允许恢复（v2.2.0 修订）**：~~v1.3.0 曾对 `pre_restore_*` 隐藏「恢复」按钮，理由是防嵌套堆积。~~ 引入独立元数据库后，兜底备份的「恢复」按钮放开——恢复到兜底备份即**回退到恢复前状态**，是有效操作。嵌套不构成数据风险（文件名 uuid 唯一，仅多生成兜底记录）。

---

## 八、v2.0.0：独立元数据库 + 上传备份

### 8.1 设计目标

备份/恢复/上传的**记录**不再存于业务库 `tennis_diary.db`，而是独立的 SQLite 文件 **`backup_meta.db`**。这样：

- **记录不参与业务备份恢复**：业务库会被整体备份与恢复，而 `backup_meta.db` 被 `_pack_data_dir` 排除、不被 `tar.extractall` 覆盖，因此备份/恢复历史始终保留。
- **纯表驱动列表**：备份列表只查 `backup_records` 表，不扫描磁盘。上传的备份、恢复前的兜底备份都自动进入列表。
- **上传备份可恢复**：管理端可将本地 `.tar.gz`/`.db` 备份文件上传到 `backups/` 目录，上传后进入列表并可执行恢复。

### 8.2 独立元数据库架构

新增 `server/app/core/backup_meta.py`：

- **独立 Base / engine / Session**：`MetaBase`（独立 `declarative_base()`）、`backup_meta_engine`、`BackupMetaSession`，完全隔离于业务库的 `Base.metadata`。
- **DB 文件**：`{DATA_DIR}/backup_meta.db`。
- **自包含建表**：模块加载时 `MetaBase.metadata.create_all` 幂等建表，**不依赖业务库初始化、不引入 Alembic、不触碰 `main.py`/`models/__init__.py`**。
- **FastAPI 依赖**：`get_backup_meta_db()` 供备份相关接口使用。

新增模型 `server/app/models/backup_record.py`，表 `backup_records`：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer PK | 自增 |
| `name` | String(256) unique | 完整文件名 |
| `size` | Integer | 文件字节数 |
| `type` | String(16) | `manual` / `pre_restore` / `upload` |
| `status` | String(16) | `created` / `restored` / `deleted` |
| `note` | String(256) | 备注（如上传来源） |
| `created_by` | Integer | 操作管理员 id |
| `restored_by` / `restored_at` | Integer / DateTime | 最近恢复操作 |
| `restored_from_id` | Integer | **关联字段（v2.1.0）**：被恢复的备份指向本次恢复前生成的兜底备份记录 id |
| `deleted_at` | DateTime | 软删除标记 |
| `created_at` / `updated_at` | DateTime | 时间戳 |

> **为什么不用 Alembic？** Alembic 是业务库的演进式迁移工具，绑定 `app.core.database.Base.metadata`。独立元数据库是单表、无演进、与业务库完全隔离的新系统，用模块级 `create_all` 幂等建表更简洁，且不污染业务迁移链。

### 8.3 后端接口变化

| 接口 | 变更 |
|------|------|
| `POST /api/admin/system/backup` | 备份后写入 `backup_records`（`type=manual`） |
| `GET /api/admin/system/backups` | **纯表驱动**：只查 `backup_records`（过滤 `deleted_at IS NULL`），返回 `name/size/created_at/type/status/note` |
| `POST /api/admin/system/restore/{id}` | 恢复前写入 `pre_restore` 记录；重置旧 `restored` 状态；标记目标记录 `status=restored` 并 `restored_from_id` 关联兜底 |
| `DELETE /api/admin/system/backup/{id}` | **软删**：置 `deleted_at` 保留审计，物理删除磁盘文件 |
| `POST /api/admin/system/backup/upload` | **新增**：`multipart` 上传 `.tar.gz`/`.db`，写 `backups/` 目录 + `type=upload` 记录 |

新增上传接口：

```python
@router.post("/backup/upload", response_model=ApiResponse[dict])
def upload_backup(
    file: UploadFile = File(...),
    admin: Admin = Depends(get_current_admin),
    meta_db: Session = Depends(get_backup_meta_db),
):
    """上传备份文件到 backups/ 目录（multipart 字段名 file）"""
    original_name = file.filename or ""
    ext = "".join(Path(original_name).suffixes).lower()  # 取全部后缀（如 .tar.gz）
    if ext not in _BACKUP_ALLOWED_EXT:  # {".tar.gz", ".db"}
        raise HTTPException(status_code=400, detail="仅支持上传 .tar.gz 或 .db 备份文件")

    backup_dir = (Path(settings.DATA_DIR) / "backups").resolve()
    backup_dir.mkdir(exist_ok=True)

    # 以 uuid 命名，避免与现有文件/记录冲突
    if ext == ".tar.gz":
        dest_path = backup_dir / f"upload_{uuid.uuid4().hex}.tar.gz"
    else:
        dest_path = backup_dir / f"upload_{uuid.uuid4().hex}.db"

    try:
        # 分块写入（复用上传模式，避免一次性读入内存）
        with open(dest_path, "wb") as out:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {e!s}") from e
    finally:
        file.file.close()

    record = BackupRecord(
        name=dest_path.name,
        size=dest_path.stat().st_size,
        type="upload",
        status="created",
        created_by=admin.id,
        note=f"上传自 {original_name}",
    )
    meta_db.add(record)
    meta_db.commit()

    return ApiResponse(
        data={"name": dest_path.name, "size": dest_path.stat().st_size},
        message="上传成功",
    )
```

### 8.4 `_pack_data_dir` 排除独立元数据库

备份打包时额外排除 `backup_meta.db`，避免它被卷入备份包（进而被恢复覆盖）：

```python
# 跳过独立元数据库（不参与业务备份恢复，避免恢复时覆盖记录表）
if item.is_file() and item.name == BACKUP_META_DB_NAME:
    continue
```

### 8.5 前端

- `admin/src/api/system.ts`：`Backup` 类型新增 `type`/`status`/`note`/`restored_from_id`；新增 `uploadBackup(file)`（`FormData` multipart）。
- `admin/src/views/system/backups.vue`：新增「上传备份」按钮 + 隐藏 `<input type="file" accept=".tar.gz,.db">`；类型徽标（`pre_restore`=琥珀色、`upload`=绿色）；新增「恢复状态」列（`status='restored'` 显示蓝色「已恢复」徽标，关联兜底文件名经 `:title` 悬浮展示；否则显示灰色「未使用」）；所有类型均显示「恢复」按钮；`restore()` 成功后刷新列表。

### 8.6 测试

- `test_upload_backup`：multipart 上传 tar.gz 成功、落盘、记录 `type=upload`、可恢复；上传非法扩展名返回 400。
- `test_list_backups` / `test_list_backups_includes_types`：纯表驱动，验证 `manual`/`pre_restore`/`upload` 三种类型与 `status`/`note` 字段。
- `test_delete_backup`：软删（`deleted_at` 非空、列表不再展示）仍保留记录。
- `test_restore_backup`：恢复后写 `pre_restore` 记录、目标标记 `restored`、`restored_from_id` 关联兜底。
- `test_restore_resets_previous_restored`：恢复新备份时旧 `restored` 被重置，始终只有一个 `restored`。
- **测试隔离**：所有触碰 `settings.DATA_DIR` 的备份测试均用 `monkeypatch + tmp_path` 隔离，防止污染真实 `data/`；`test_meta_db` fixture 用临时文件隔离元数据库。

### 8.7 注意事项（v2.0.0）

1. **独立库不参与业务备份恢复**：这是核心设计。恢复业务数据时 `backup_meta.db` 不会被覆盖，记录完整保留。
2. **纯表驱动**：列表只查 `backup_records`。`backups/` 目录中表里没有的存量文件不再展示（除非通过备份/恢复/上传接口写入记录）。
3. **上传命名**：上传文件以 `upload_{uuid}` 命名，避免与现有文件名冲突；`note` 记录原始文件名。
4. **软删除**：删除记录保留在表中（`deleted_at` 标记），列表过滤隐藏，实现审计留存。

### 8.8 恢复状态管理与兜底关联（v2.1.0）

**恢复操作的状态语义：**

1. **兜底关联**：恢复某备份时，先生成 `pre_restore_*` 兜底备份并写入记录；随后将该备份记录的 `status` 置为 `restored`，且 `restored_from_id` 指向本次生成的兜底备份记录 id，实现「被恢复的备份 → 恢复前兜底」的关联。

2. **状态唯一**：恢复新备份时，先将所有 `status='restored'` 的旧记录重置为 `created`（清空 `restored_at`/`restored_by`/`restored_from_id`），再标记当前目标为 `restored`。从而**同时只有一个备份处于 `restored` 状态**，准确反映「当前最后一次恢复用的是哪个备份」。

```python
# 保证同时只有一个备份处于 restored 状态：先重置旧的 restored 记录
(
    meta_db.query(BackupRecord)
    .filter(BackupRecord.status == "restored")
    .update(
        {
            BackupRecord.status: "created",
            BackupRecord.restored_at: None,
            BackupRecord.restored_by: None,
            BackupRecord.restored_from_id: None,
        },
        synchronize_session=False,
    )
)

# 标记目标备份已用于恢复，并关联到本次恢复前生成的兜底备份
if target is not None:
    target.status = "restored"
    target.restored_at = now
    target.restored_by = admin.id
    target.restored_from_id = pre_record.id
```

3. **文件名唯一**：`backup_*` 与 `pre_restore_*` 命名追加 `uuid4().hex[:6]` 后缀，避免同一秒内多次备份/恢复生成同名文件（`backup_records.name` 有唯一约束）。

4. **前端刷新**：`backups.vue` 的 `restore()` 成功后再调用 `fetchBackups()` 刷新列表，让「已恢复」徽标与兜底关联立即生效。

### 8.9 允许恢复兜底备份 + 关联展示（v2.2.0）

1. **兜底备份可恢复**：放开 `pre_restore_*` 的「恢复」按钮（v1.3.0 曾禁用）。恢复到兜底备份即**回退到恢复前的状态**，是有效操作；状态唯一机制保证当前只有一个备份处于 `restored`。嵌套仅多生成兜底记录，不构成数据风险。

2. **列表返回关联文件名**：`list_backups` 构建 `id → name` 映射，返回 `restored_from_name`（被恢复备份关联到的兜底备份文件名），前端可直接展示：

```python
id_to_name = {r.id: r.name for r in records}
# ...
"restored_from_id": r.restored_from_id,
"restored_from_name": (
    id_to_name.get(r.restored_from_id) if r.restored_from_id else None
),
```

3. **前端「恢复状态」列**：`backups.vue` 新增独立列——`status='restored'` 显示蓝色「已恢复」徽标，关联兜底文件名（`restored_from_name`）通过 `:title` 悬浮提示展示（`恢复时生成的兜底备份：<完整文件名>`），不再在徽标内渲染截断文件名；否则显示灰色「未使用」。类型徽标（恢复前兜底/上传）与状态徽标分离，更清晰。
