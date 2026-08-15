# 87：Admin 时间显示统一东八区

## 背景

Admin 前端 8 个视图各自定义 `formatDate` 函数，使用 `toLocaleString('zh-CN')` 格式化时间。`'zh-CN'` 是语言标签，不控制时区——时区取浏览器/OS 系统时区。若运行环境非 UTC+8，时间显示会偏移。

此外，后端 `isoformat()` 返回的 ISO 字符串缺少 `Z` 后缀，导致 JavaScript 将 UTC 时间误判为本地时间。

## 方案

### 前端

新建 `admin/src/utils/date.ts` 共享工具，所有格式化函数显式指定 `timeZone: 'Asia/Shanghai'`，8 个视图统一导入。

```ts
/** Unix 秒级时间戳 → 完整日期时间（东八区） */
export function formatTs(ts: number | null | undefined): string

/** ISO 字符串 → 完整日期时间（东八区） */
export function formatIso(iso: string | null | undefined): string

/** ISO 字符串 → 仅日期（东八区） */
export function formatDate(iso: string | null | undefined): string
```

### 后端

`isoformat()` → `strftime("%Y-%m-%dT%H:%M:%SZ")`，添加 `Z` 后缀标明 UTC，确保前端 `new Date()` 正确解析。

## 变更文件

### 前端

| 文件 | 操作 |
|------|------|
| `admin/src/utils/date.ts` | 新建 |
| `admin/src/views/diaries/index.vue` | 删除 formatDate，导入 formatTs |
| `admin/src/views/weights/index.vue` | 删除 formatDate，导入 formatTs |
| `admin/src/views/gears/index.vue` | 删除 formatDate，导入 formatTs |
| `admin/src/views/users/index.vue` | 删除 formatDate/formatDateTime，导入 formatDate/formatIso |
| `admin/src/views/admins/index.vue` | 删除 formatDate，导入 formatIso |
| `admin/src/views/analyses/index.vue` | 删除 formatDate，导入 formatDate |
| `admin/src/views/system/event-logs.vue` | 删除 formatServerTime，导入 formatTs |
| `admin/src/views/system/backups.vue` | 删除 formatDate，导入 formatIso |

### 后端

| 文件 | 变更 |
|------|------|
| `server/app/routers/admin/system.py` | `isoformat()` → `strftime("...Z")` |
| `server/app/services/config_service.py` | 同上 |
| `server/app/services/ai_provider_service.py` | 同上 |
