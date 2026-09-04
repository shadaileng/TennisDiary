> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 130 |
> | 文档版本 | v1.1.0 |
> | 文档状态 | 🏁 已完成 |
> | 最后更新 | 2026-09-04 |
> | 对应功能/内容 | Admin 端浏览器原生资源请求（img/video/download）补齐后端域名，兼容 base64 dataURL |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-09-04 | v1.0.0 | 初版 |
> | 2026-09-04 | v1.1.0 | 实施完成：新增 `utils/fileUrl.ts` 并接入 files/gears/analyses/users/event-logs 六处；admin type-check + build 通过 |
>
> **关联文档**：[86：Admin 静态文件端点移除认证](./86-Admin静态文件端点移除认证.md)、[114：Admin 文件预览与下载](./114-文件预览与下载.md)、[125：Admin 文件管理简化与查询优化](./125-Admin文件管理简化与查询优化.md)、[104：微信内容安全API集成](./104-微信内容安全API集成.md)、[129：日记装备统计游客本地降级与登录同步](./129-日记装备统计游客本地降级与登录同步.md)

# Admin 跨域静态资源 URL 统一解析

## 一、背景与问题

线上反馈：Admin「文件管理 → 预览」打开的图片地址是

```
https://admin.example.com/api/admin/system/files/videos/1/105fdeae..._f2.jpg
```

该地址 **404**——它把后端接口路径拼到了 **Admin 静态站点自己的域名** 下。

### 部署拓扑（跨域，无同源反代）

| 端 | 域名 | 说明 |
|---|---|---|
| Admin 前端（静态托管） | `admin.example.com` | 浏览器页面 origin |
| 后端 API | `api.example.com` | `admin/.env.production` 的 `VITE_API_BASE_URL` |

两者**不同源且没有同源反向代理**，因此「相对路径 + 后端接口」的组合必然解析到 Admin 自身域名。

### 根因

`axios` 实例（`admin/src/api/index.ts`）已配置 `baseURL = import.meta.env.VITE_API_BASE_URL`，**所有走 axios 的接口请求都是安全的**。

但**浏览器原生请求**（`<img src>` / `<video src>` / `fetch()` / `<a download>`）**不经过 axios**，相对 URL 会被浏览器按**当前页面 origin** 解析 → 打到 Admin 域名 → 404。

## 二、问题清单（全量扫描结果）

扫描 `admin/src` 下所有原生资源访问点（`:src=`、`fetch(`、`<a download>`）：

| # | 位置 | 现状 | 是否受跨域影响 |
|:-:|---|---|---|
| A | `views/files/index.vue` `openPreview` | `preview_url: /api/admin/system/files/${rel_path}` | ❌ **BUG**：相对路径 → 404 |
| B | `views/gears/index.vue` 详情弹窗装备图 | `<img :src="selectedGear.photo">` 直出 | ❌ **BUG**：`photo` 为相对路径时 404 |
| C | `api/files.ts` `getDownloadUrl` | `/api/admin/files/${id}/download` | ❌ **BUG**：下载走 `fetch`/`<a>`，非 axios |
| D | `views/analyses/index.vue` `fileUrl` | 已拼 `VITE_API_BASE_URL` + 兼容 `data:` | ✅ 正确（参考实现） |
| E | `views/users/index.vue` `getAvatarUrl` | 已拼 base + `avatars/`→`avatar/` | ✅ 正确（未判 `data:`，见加固项） |
| F | `views/system/event-logs.vue` `resolveAvatarUrl` | 同上 | ✅ 正确（未判 `data:`，见加固项） |
| G | `views/system/backups.vue` 备份下载 | `${base}/api/admin/system/backup/download/...` | ✅ 正确 |

### 关键点：`gear.photo` 可能是 base64 dataURL

后端 `server/app/routers/gears.py` 的 `create_gear` / `update_gear` **不校验 `photo` 形态**，直接 `body.photo` 入库，实际存在三种取值：

| 来源 | 形态 | 说明 |
|---|---|---|
| 小程序登录态 `choosePhoto` → `/api/upload/gear-image` | 相对路径 `gears/<uid>/<uuid>.jpg` | 需拼 base（Step 104 后为 URL，非 base64） |
| 小程序游客态 `compressToDataURL` | `data:image/jpeg;base64,...` | **必须原样直出，不能拼 base** |
| 历史/外部数据 | 完整 `https://...` | 原样直出 |

因此解析函数**不能简单拼 base**，必须先判 `data:` / `http(s)://`。

## 三、修复方案

### 3.1 抽取公共解析工具 `admin/src/utils/fileUrl.ts`

把 `views/analyses/index.vue` 中已验证的 `fileUrl` 提升为公共函数，并补齐头像、下载两类：

```ts
const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

/** 绝对 URL 判定：http(s) 完整地址 或 base64 dataURL —— 一律原样返回 */
const isAbsoluteUrl = (p: string) =>
  p.startsWith('http://') || p.startsWith('https://') || p.startsWith('data:')

/** 文件管理静态资源：相对路径 → {base}/api/admin/system/files/{rel_path} */
export function fileUrl(p?: string | null): string {
  if (!p) return ''
  if (isAbsoluteUrl(p)) return p
  return `${API_BASE}/api/admin/system/files/${p}`
}

/** 用户头像：avatars/ → avatar/，相对路径 → {base}/api/upload/{path} */
export function avatarUrl(p?: string | null): string {
  if (!p) return ''
  if (isAbsoluteUrl(p)) return p
  const path = p.replace(/^avatars\//, 'avatar/')
  return `${API_BASE}/api/upload/${path}`
}

/** 文件管理下载（与静态预览端点路径不同，需单独拼） */
export function fileDownloadUrl(fileId: number): string {
  return `${API_BASE}/api/admin/files/${fileId}/download`
}
```

### 3.2 接入点改造

| 文件 | 改动 |
|---|---|
| `views/files/index.vue` | `openPreview` 用 `fileUrl(file.rel_path)` |
| `views/gears/index.vue` | 装备图用 `fileUrl(selectedGear.photo)` |
| `api/files.ts` | `getDownloadUrl` 改用 `fileDownloadUrl` |
| `views/analyses/index.vue` | 删除本地 `fileUrl`，改为 `import { fileUrl } from '@/utils/fileUrl'` |
| `views/users/index.vue` | 删除本地 `getAvatarUrl`，改用 `avatarUrl` |
| `views/system/event-logs.vue` | 删除本地 `resolveAvatarUrl`，改用 `avatarUrl` |

### 3.3 后端加固（可选，本次不做）

`gears.py` 的 `update_gear` / `delete_gear` 在 `photo` 为 `data:` / `http` 时会拿它去 `file_service.decrement_ref_count` 查 `File.rel_path`。该函数查不到记录即返回 0，**不会误删、不会抛异常**，仅产生一次无效查询。

本次按最小改动原则**不动后端**；若后续要清理，可在调用前加守卫：

```python
def _is_rel_path(p: str | None) -> bool:
    return bool(p) and not p.startswith(('http://', 'https://', 'data:'))
```

## 四、执行步骤

1. [x] 新建 `admin/src/utils/fileUrl.ts`（`fileUrl` / `avatarUrl` / `fileDownloadUrl`）
2. [x] `api/files.ts`：`getDownloadUrl` → 复用 `fileDownloadUrl`
3. [x] `views/files/index.vue`：`openPreview` 接入 `fileUrl`
4. [x] `views/gears/index.vue`：装备图接入 `fileUrl`（兼容 `data:`）
5. [x] `views/analyses/index.vue`：本地 `fileUrl` 替换为公共导入
6. [x] `views/users/index.vue`、`views/system/event-logs.vue`：头像解析替换为 `avatarUrl`
7. [x] 验证：`cd admin && pnpm run type-check && pnpm run build` 均通过

## 五、验证标准

- `pnpm run type-check` 无错误
- `pnpm run build` 构建通过
- 线上抽检：
  - 文件管理预览图片地址以 `https://api.example.com/api/admin/system/files/` 开头
  - 装备详情装备图：相对路径图片可正常加载；base64 图片可正常加载
  - 文件下载可正常触发
  - 用户头像、事件日志头像显示正常

## 六、风险与影响面

| 风险 | 评估 |
|---|---|
| 本地开发 `VITE_API_BASE_URL` 为空 | `API_BASE` 回退 `''` → 相对路径，走 Vite dev proxy 或同源，行为与修复前一致 |
| base64 图片体积 | 仅渲染层直出，无网络请求；不落盘、不入库（Step 104 已把上传路径改为 URL） |
| 头像 `data:` 判定 | 头像理论上不会是 dataURL；显式判定只为防御，不改变现有行为 |
