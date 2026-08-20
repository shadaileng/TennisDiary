> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 54-Admin-7 |
> | 文档版本 | v1.0.0 |
> | 文档状态 | ✅ 已完成 |
> | 最后更新 | 2026-08-08 |
> | 对应功能/内容 | 后台管理前端测试与部署 |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-08 | v1.0.0 | 初版 |
>
> **关联文档**：[Phase Admin 后台管理前端总纲](./47-Admin-后台管理前端.md)

# Phase Admin-7：测试与部署

## 一、目标

配置 Nginx 部署方案，编写部署文档。

## 二、已完成内容

- 创建 Nginx 配置文件（nginx.conf）
- 创建 Dockerfile（容器化部署）
- 创建 .env.example 环境变量模板

## 三、部署方式

### 3.1 本地开发

```bash
cd admin
npm install
npm run dev
```

访问 `http://localhost:5173`

### 3.2 构建生产版本

```bash
npm run build
```

构建产物在 `dist/` 目录。

### 3.3 Nginx 部署

1. 将 `dist/` 目录内容复制到 Nginx 的 html 目录
2. 配置 Nginx（参考 `nginx.conf`）
3. 重启 Nginx

### 3.4 Docker 部署

```bash
cd admin
docker build -t tennis-diary-admin .
docker run -p 80:80 tennis-diary-admin
```

## 四、环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| VITE_APP_TITLE | 应用标题 | Tennis Diary Admin |
| VITE_APP_VERSION | 应用版本 | 1.0.0 |
| VITE_API_BASE_URL | API地址 | `http://localhost:8000` |

## 五、提交规范

```bash
chore(admin): 配置部署文件

- 创建Nginx配置
- 创建Dockerfile
- 创建环境变量模板
```