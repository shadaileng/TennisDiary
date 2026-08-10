> **本页信息**
>
> | 项目 | 内容 |
> |------|------|
> | 文档编号 | 64 |
> | 文档版本 | v1.1.0 |
> | 文档状态 | ✅ 已完成（代码）· 待建 VM 启用 |
> | 最后更新 | 2026-08-10 |
> | 对应功能/内容 | Server 部署方案（Oracle Cloud Always Free） |
>
> **变更历史**
>
> | 日期 | 版本 | 说明 |
> |------|:----:|------|
> | 2026-08-09 | v1.0.0 | 初版 |
> | 2026-08-10 | v1.1.0 | 代码已实现（脚本/指南/CI/env 模板）；因尚未创建 OCI VM，CI workflow 已移至 `workflows-disabled/`，待建机后启用 |
>
> **关联文档**：[01-Tennis Diary 迁移微信小程序分析](./01-tennis-diary-迁移微信小程序分析.md) · [63-Server 部署方案-Docker 与 HF Space](./63-Server部署方案-Docker与HF-Space.md) · [65-Server 部署方案-ModelScope 创空间](./65-Server部署方案-ModelScope-创空间.md)

# Phase Server-2：Server 部署方案（Oracle Cloud Always Free）

## 一、背景与选型

Hugging Face Space 免费 Docker 档已改为要求 PRO 订阅（HTTP 402），无法免费部署。
Oracle Cloud Always Free 免费档**始终在线、无休眠、自带 200GB 持久化存储**，更适合承载
SQLite 数据库与上传文件的 FastAPI 后台。

### 1.1 免费档现状（2026-06-15 更新）

| 资源 | 内容 | 说明 |
|------|------|------|
| AMD Micro | 2 × `VM.Standard.E2.1.Micro`（1/8 OCPU，1GB RAM） | 轻量场景 |
| Ampere A1 | 2 OCPU / 12GB RAM 总配额（**原 4 OCPU/24GB，已削减**） | 推荐，可拆 1~2 台 |
| Block Volume | 200GB 免费（含 Boot Volume，最小 47GB） | 持久化卷挂载 `/data` |
| 公网带宽 | 每月 10TB 出站（约） | 充足 |
| 运行模式 | **常驻运行，不休眠** | 优于 HF/Koyeb |

### 1.2 方案优势与局限

| 维度 | 说明 |
|------|------|
| ✅ 常驻 | 无 scale-to-zero，无冷启动 |
| ✅ 持久化 | Block Volume 挂载，容器重建数据不丢 |
| ✅ 权限 | 完整 root/Sudo，可自装 Nginx、HTTPS |
| ❌ 运维 | 需自行维护 OS、Docker、安全更新 |
| ❌ 备案 | 出口 IP 为 OCI 机房，微信小程序仍需自备已备案域名反代 |

## 二、产出文件

| 文件 | 路径 | 说明 |
|------|------|------|
| 部署指南 | `server/oci/README.md` | Oracle Cloud 建机 + 绑定 SSH/安全组完整指引 |
| 初始化脚本 | `server/scripts/oci-bootstrap.sh` | 在 OCI VM 上一次执行（装 Docker/Compose/Nginx/certbot） |
| 部署脚本 | `server/scripts/deploy-oci.sh` | 本地/CI 一键同步代码并滚动重建容器 |
| 配置模板 | `server/.env.oci.example` | OCI SSH 连接参数模板 |
| CI | `.github/workflows/deploy-server-oci.yml` | push `server/**` 自动部署到 OCI VM |

> 复用已有 `Dockerfile`、`docker-compose.yml`、`docker-entrypoint.sh`，无镜像改动。

---

## 三、部署流程

### 3.1 一句话

```
              GitHub Actions / 本地
                     │  rsync + ssh
                     ▼
    Oracle VM (Ubuntu 24.04, A1.Flex 1 OCPU/6GB)
    ├─ Docker + Compose Plugin
    ├─ /opt/tennis-diary/server/   (代码)
    ├─ /opt/tennis-diary/.env      (密钥)
    └─ /opt/tennis-diary/data/     (Block Volume 挂载 /data，SQLite + 上传)
```

### 3.2 前置步骤（一次性，详见 oci/README.md）

1. 注册 Oracle Cloud Free Tier（选 home region：Seoul/Osaka/Tokyo 等）
2. 创建实例 `VM.Standard.A1.Flex`（1 OCPU / 6GB，Ubuntu 24.04），上传 SSH 公钥
3. 安全组（Security List）放行：`22`、`80`、`443`、`8000`
4. 创建 Block Volume（最小 100GB）并挂载 `/dev/sdb`，fstab 持久化后 mount 到 `/data`
5. 首次登录执行 `oci-bootstrap.sh`（装 Docker/Compose，可选 Nginx+certbot）

### 3.3 部署步骤

```bash
# 在本地 server/ 目录
cp .env.oci.example .env.oci
# 编辑填入 OCI_VM_USER / OCI_VM_HOST / OCI_SSH_KEY 等
bash scripts/deploy-oci.sh
```

脚本自动：
1. rsync 同步代码（排除 `.venv/.git/data` 等）
2. 若本地存在 `.env`，同步到远端（不含 git 提交）
3. 远端 `docker compose up -d --build`
4. 本地轮询 `/health` 确认健康

### 3.4 HTTPS 与微信域名

微信小程序 `request` 合法域名要求 **HTTPS + 已备案域名**。
- bootstrap 支持 `--domain api.example.com`：自动签发 Let's Encrypt 证书 + Nginx 反代到 `127.0.0.1:8000`
- 若域名已备案，在微信后台配置 request 合法域名为 `https://api.example.com`

---

## 四、脚本设计

### 4.1 `oci-bootstrap.sh`（VM 内一次性执行）

```bash
# 用法（在 VM 上，须以 root 运行）
bash oci-bootstrap.sh [-d api.example.com]
```

- 安装 Docker Engine + Compose 插件 + UFW
- 放行 `22/80/443/8000`
- 若提供 `-d`，安装 nginx 与 certbot，自动签发并反代

### 4.2 `deploy-oci.sh`

```bash
set -euo pipefail
# 读取 .env.oci
# 校验 OCI_VM_USER / OCI_VM_HOST / OCI_SSH_KEY
# rsync --delete server/ → ${OCI_VM_USER}@${OCI_VM_HOST}:/opt/tennis-diary/server/
# （可选）cp .env 同步到远端
# ssh docker compose up -d --build
# 浏览器到 ${OCI_VM_HOST}/health 轮询
```

### 4.3 环境变量校验（沿用 HF 方案的校验风格）

- 必填：`OCI_VM_USER`、`OCI_VM_HOST`、`OCI_SSH_KEY`（私钥路径）
- 可选：`OCI_SSH_PORT=22`、`OCI_APP_DIR=/opt/tennis-diary`
- GitHub Actions 模式额外校验 Secrets：`OCI_SSH_KEY`（私钥内容）

---

## 五、目录结构变更（diff）

```
server/
├── .env.oci.example              # ← 新建（OCI SSH 配置模板）
├── scripts/
│   ├── oci-bootstrap.sh              # ← 新建（VM 初始化）
│   └── deploy-oci.sh                 # ← 新建（本地/CI 部署）
└── oci/
    └── README.md                     # ← 新建（OCI 部署指南）

.github/workflows/
└── deploy-server-oci.yml             # ← 新建（GitHub Actions）
```

---

## 六、部署验证清单

| 检查项 | 命令/操作 | 预期结果 |
|--------|----------|---------|
| SSH 可达 | `ssh -i ~/.ssh/<key> ubuntu@<ip>` | 登录成功 |
| Docker 已装 | `docker --version` | ≥ 24 |
| 容器健康 | `docker compose ps` | `healthy` |
| API 文档 | `http://<EIP>:8000/docs` | Swagger 正常 |
| 健康检查 | `curl http://<ip>:8000/health` | `{"code":0,...}` |
| 数据持久化 | 重启容器后查库 | 数据不丢失（volume 挂载） |
| HTTPS（如配置） | `curl https://api.example.com/health` | 证书有效 |

---

## 七、成本与风险提示

- A1.Flex 免费上限**仅 2 OCPU/12GB**，超出会被停机（Oracle 会发邮件），请预留余量
- Block Volume 免费 Cent table；最小 Boot Volume 47GB，200GB 总配额按需分配
- 长期闲置可能触发 Oracle 回收（低频、低频、谨慎）
- 生产建议开启每日备份（`admin/system/backup` 已有接口可配合 cron）

---

## 八、提交规范

```bash
feat(server): 添加 Oracle Cloud Always Free 部署方案

- 创建 oci/README.md 部署指南（建机-安全组-挂卷-初始化）
- 创建 oci-bootstrap.sh（安装 Docker/Nginx/certbot）
- 创建 deploy-oci.sh（rsync 同步 + compose 重建）
- 创建 .env.oci.example 与 GitHub Actions
```

---

## 九、当前状态说明（2026-08-10）

- **代码已全部实现**：`oci/README.md`、`scripts/oci-bootstrap.sh`、`scripts/deploy-oci.sh`、`.env.oci.example`、GitHub Actions workflow 均已创建（CHANGELOG 1.41.1）。
- **CI 待启用**：因尚未创建 Oracle Cloud 免费 VM，`deploy-server-oci.yml` 已移至 `.github/workflows-disabled/`。建机并完成 `oci-bootstrap.sh` 初始化后，将 workflow 移回 `.github/workflows/` 即可启用自动部署。
- **当前启用方案**：魔搭创空间（[65](./65-Server部署方案-ModelScope-创空间.md)），适合快速演示；OCI 常驻 + 200GB 卷适合作为正式生产目标。
- **本地手动部署不受影响**：即使不启用 CI，也可按第三节 `deploy-oci.sh` 手动部署。