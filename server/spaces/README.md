# ============================================================
# Tennis Diary Server - HF Space 部署说明
# ============================================================
#
# Hugging Face Space 免费 CPU 档部署指南
#
# ------------------------------------------------------------------
# 一、前置条件
# ------------------------------------------------------------------
# 1. Hugging Face 账号：https://huggingface.co/join
# 2. 已备案的域名（用于微信小程序合法域名配置）
# 3. 微信小程序 AppID 和 Secret
#
# ------------------------------------------------------------------
# 二、创建 HF Space
# ------------------------------------------------------------------
# 1. 访问 https://huggingface.co/new-space
# 2. 填写：
#    - Space name: tennis-diary-server
#    - SDK: Docker
#    - Hardware: CPU basic (free)
#    - Visibility: Public（开源项目）或 Private
# 3. 点击 Create Space
#
# ------------------------------------------------------------------
# 三、GitHub Actions 自动部署（推荐）
# ------------------------------------------------------------------
# 推送代码到 master 分支时，GitHub Actions 自动部署到 HF Space。
#
# ① 在 GitHub Repo Settings → Secrets 配置：
#    - HF_TOKEN: Hugging Face Access Token（需有 Space 写入权限）
#    - HF_USERNAME: HF 用户名
#    - HF_SPACE_NAME: HF Space 名称（如 tennis-diary-server）
#    - JWT_SECRET: JWT 签名密钥
#    - WX_APPID: 微信小程序 AppID
#    - WX_SECRET: 微信小程序 Secret
#
# ② 触发部署：
#    - 推送 server/ 目录变更到 master 分支自动触发
#    - 或手动触发：Actions → Deploy Server to HuggingFace Spaces → Run workflow
#
# ③ 部署流程：
#    GitHub Actions 运行 server/scripts/deploy-hf.sh
#    → 将 server/ 文件复制到临时目录
#    → 生成 .env.hf（包含敏感环境变量）
#    → 推送到 HF Space git repo
#    → HF 自动构建 Docker 镜像并启动
#
# ------------------------------------------------------------------
# 四、本地手动部署
# ------------------------------------------------------------------
# 复制 .env.hf.example 为 .env.hf，填入实际值后执行：
#
#   cd server
#   bash scripts/deploy-hf.sh
#
# 或使用环境变量：
#
#   HF_TOKEN=hf_xxxx HF_USERNAME=yourname HF_SPACE_NAME=your-space \
#   JWT_SECRET=xxx WX_APPID=xxx WX_SECRET=xxx \
#   bash scripts/deploy-hf.sh
#
# ------------------------------------------------------------------
# 五、推送镜像到 HF Container Registry（备选方案）
#
# 方法 A：使用 HF Space 自动构建（推荐）
# 在 Space 设置中配置 Git 仓库，推送代码后 HF 自动构建镜像
#
# 方法 B：本地构建并推送
#
# ① 登录 HF Container Registry
#    docker login docker.io/huggingface
#
# ② 构建镜像（在 server/ 目录执行）
#    docker build -t docker.io/huggingface/your-username/tennis-diary-server:latest .
#
# ③ 推送镜像
#    docker push docker.io/huggingface/your-username/tennis-diary-server:latest
#
# ④ 在 HF Space Settings → Container 中填写镜像地址：
#    docker.io/huggingface/your-username/tennis-diary-server:latest
#
# ------------------------------------------------------------------
# 四、配置环境变量（HF Space Settings → Variables）
# ------------------------------------------------------------------
# 复制 .env.example，按需填写后在 HF 后台设置：
#
#   JWT_SECRET=<强随机 32 位以上字符串>
#   WX_APPID=<微信小程序 AppID>
#   WX_SECRET=<微信小程序 Secret>
#   ADMIN_DEFAULT_PASSWORD=<修改默认密码>
#
# 注意：JWT_SECRET 和 WX_SECRET 是敏感信息，切勿提交到代码仓库！
#
# ------------------------------------------------------------------
# 六、配置持久化存储（关键）
# ------------------------------------------------------------------
# HF Space Docker Runner 默认不持久化数据，需手动挂载 volume：
#
# 1. 进入 HF Space Settings → Storage
# 2. 添加 Volume：
#    - Name: data
#    - Mount path: /data
#    - Size: 5 GB（足够 SQLite + 图片上传）
#
# 这样数据库和上传文件会持久保存在 HF 后端，容器重建不丢失。
#
# ------------------------------------------------------------------
# 七、配置 Nginx 反代（微信小程序域名要求）
# ------------------------------------------------------------------
# HF Space 默认域名（*.hf.space）无法备案，微信小程序要求
# request 合法域名必须已备案，因此需要自备域名 + Nginx 反代：
#
# ① 将域名 DNS CNAME 指向 HF Space 实例域名
#    例：api.yourdomain.com → your-username-tennis-diary-server.hf.space
#
# ② Nginx 配置（示例）
#    server {
#        listen 443 ssl;
#        server_name api.yourdomain.com;
#
#        ssl_certificate     /etc/nginx/ssl/fullchain.pem;
#        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
#
#        location / {
#            proxy_pass https://your-username-tennis-diary-server.hf.space;
#            proxy_set_header Host $host;
#            proxy_set_header X-Real-IP $remote_addr;
#            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#            proxy_set_header X-Forwarded-Proto $scheme;
#        }
#    }
#
# ③ 在微信小程序后台配置：
#    开发 → 开发管理 → 开发设置 → 服务器域名
#    request 合法域名：https://api.yourdomain.com
#
# ------------------------------------------------------------------
# 八、验证部署
# ------------------------------------------------------------------
# ① 等待 HF Space 构建完成（首次约 3-5 分钟）
#
# ② 访问 API 文档：
#    https://your-username-tennis-diary-server.hf.space/docs
#
# ③ 健康检查：
#    curl https://your-username-tennis-diary-server.hf.space/health
#    预期：{"code":0,"message":"ok","success":true,"data":{"status":"ok","version":"1.0.0"}}
#
# ④ 登录接口测试（需要小程序 code）：
#    curl -X POST https://your-username-tennis-diary-server.hf.space/api/auth/login \
#         -H "Content-Type: application/json" \
#         -d '{"code":"your_wx_login_code"}'
#
# ------------------------------------------------------------------
# 九、注意事项
# ------------------------------------------------------------------
# ① HF Space 免费版有休眠机制：30 分钟无请求会自动休眠，
#    下次请求需等待约 30 秒唤醒。生产环境建议升级付费档。
#
# ② SQLite 单文件锁限制并发，HF Space CPU 档适合低流量场景
#    （日活 < 100）。如需更高并发，部署到自有服务器 + PostgreSQL。
#
# ③ 数据持久化必须挂载 volume 到 /data，否则容器重建后数据丢失。
#
# ④ 每次修改代码后重新推送镜像或重新触发 HF 构建。
#
# ------------------------------------------------------------------
# 十、故障排查
# ------------------------------------------------------------------
# ① 查看容器日志：
#    HF Space → Logs 标签页
#
# ② 重启 Space：
#    HF Space → Settings → Factory restart
#
# ③ 检查数据库迁移是否成功：
#    日志中搜索 "Migrations complete." 关键词
#
# ④ 检查环境变量是否生效：
#    HF Space → Settings → Variables（确认值已设置）
#
# ------------------------------------------------------------------
# 十一、备份与恢复
# ------------------------------------------------------------------
# SQLite 数据库为单个 .db 文件，备份方法：
#
#   # 从 HF Space 下载数据库文件（需要 SSH 或 volume 访问）
#   # 或使用 HF Space 的 volume 导出功能
#
# 恢复方法：
#   # 将备份的 .db 文件放回挂载的 volume 目录 /data/
#   # 重启容器
#
# ------------------------------------------------------------------
