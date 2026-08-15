# 86：Admin 静态文件端点移除认证

## 背景

`GET /api/admin/system/files/{filename:path}` 要求 `X-Auth-Token` 头部认证（`get_current_admin` 依赖），但 Admin 前端通过 `<img :src="...">` 加载图片，浏览器原生请求不经过 axios 拦截器，导致 401 Unauthorized。

## 方案

移除 `serve_admin_file` 端点的 `get_current_admin` 依赖，使文件端点无需认证即可访问。

### 安全说明

- 端点保留路径穿越防护（`normpath` + `UPLOAD_DIR` 前缀检查）
- Admin 仪表盘本身已有登录门槛
- 文件仅限 `UPLOAD_DIR` 内的媒体文件（图片/视频）

## 变更文件

| 文件 | 变更 |
|------|------|
| `server/app/routers/admin/system.py` | 移除 `Depends(get_current_admin)` |
| `server/tests/routers/admin/test_ai_gateway.py` | 更新测试期望 |

## TDD

1. **RED**：修改测试期望无认证返回 200 → 失败
2. **GREEN**：移除端点认证 → 通过
