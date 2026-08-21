> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 53-Admin-6 |
> | 文档版本 | v2.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-21 |
> | 对应功能/内容 | 后台管理前端系统监控（健康检查/配置/日志/备份/事件日志） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
> | 2026-08-21 | v2.0.0 | 根据实际代码更新：增加系统配置、事件日志、AI状态 |
>
> **关联文档**：[Phase Admin 后台管理前端总纲](./47-Admin-后台管理前端.md)

# Phase Admin-6：系统监控

## 一、目标

实现系统监控页面，包括健康检查、系统配置、日志查看、备份管理、事件日志。

## 二、前置条件

- Phase Admin-2 已完成（布局与登录）
- Phase B2-3 已完成（系统监控API）

## 三、已完成内容

### 3.1 健康检查 `/system/health`

- 系统状态（状态、版本、运行时长）
- 资源使用（数据库、磁盘）
- AI 网关状态（AI评分、ffmpeg、MediaPipe、姿态模型）
- AI 连接测试

### 3.2 系统配置 `/system/config`

- 配置项概览（总数、可编辑、已覆盖）
- AI 服务商管理（直选/自定义）
- 分类配置卡片（按类别分组）
- 配置项编辑/恢复默认
- 服务商管理弹窗（新增/编辑/删除）

### 3.3 日志查看 `/system/logs`

- 日志列表（支持按级别/关键字筛选）
- 分页加载（倒序，最新优先）
- 实时刷新

### 3.4 备份管理 `/system/backups`

- 备份列表
- 创建备份
- 恢复备份
- 删除备份
- 上传备份

### 3.5 事件日志 `/system/event-logs`

- 事件日志列表
- 分页加载

## 四、API接口

### 系统状态

| 函数 | 方法 | 端点 | 说明 |
|------|------|------|------|
| getHealthStatus | GET | /api/admin/system/health | 健康状态 |
| getSystemStats | GET | /api/admin/system/stats | 系统统计 |
| getAiStatus | GET | /api/admin/system/ai-status | AI网关状态 |
| testAiConnect | GET | /api/admin/system/ai-connect | AI连接测试 |

### 系统配置

| 函数 | 方法 | 端点 | 说明 |
|------|------|------|------|
| getConfigs | GET | /api/admin/system/configs | 获取配置列表 |
| updateConfig | PUT | /api/admin/system/configs/:key | 更新配置 |
| resetConfig | DELETE | /api/admin/system/configs/:key | 恢复默认 |
| resetAllConfigs | DELETE | /api/admin/system/configs | 全部恢复默认 |
| getProviders | GET | /api/admin/system/ai-providers | 获取服务商列表 |
| addProvider | POST | /api/admin/system/ai-providers | 新增服务商 |
| updateProvider | PUT | /api/admin/system/ai-providers/:id | 更新服务商 |
| deleteProvider | DELETE | /api/admin/system/ai-providers/:id | 删除服务商 |
| checkProviderModels | POST | /api/admin/system/ai-providers/check-models | 校验模型 |

### 日志与备份

| 函数 | 方法 | 端点 | 说明 |
|------|------|------|------|
| getLogs | GET | /api/admin/system/logs | 获取日志 |
| getBackups | GET | /api/admin/system/backups | 获取备份列表 |
| createBackup | POST | /api/admin/system/backup | 创建备份 |
| restoreBackup | POST | /api/admin/system/restore/:id | 恢复备份 |
| deleteBackup | DELETE | /api/admin/system/backup/:id | 删除备份 |
| uploadBackup | POST | /api/admin/system/backup/upload | 上传备份 |

## 五、验收标准

| 验收项 | 标准 |
|--------|------|
| 健康检查 | 系统状态、AI网关状态显示正常 |
| 系统配置 | 配置列表、编辑、恢复默认正常 |
| 服务商管理 | 新增/编辑/删除服务商正常 |
| 日志查看 | 日志列表、筛选、分页正常 |
| 备份管理 | 创建/恢复/删除/上传备份正常 |
| 事件日志 | 事件日志列表正常 |

## 六、提交规范

```bash
feat(admin): 实现系统监控页面

- 实现健康检查页面（含AI网关状态）
- 实现系统配置页面（服务商管理、配置编辑）
- 实现日志查看页面
- 实现备份管理页面
- 实现事件日志页面
```
