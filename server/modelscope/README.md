# ============================================================
# Tennis Diary Server - 魔搭创空间(ModelScope Studio) 部署说明
# ============================================================
#
# 魔搭创空间云端免费托管，Docker 类型，CPU 免费档（2 vCPU / 16G）。
#
# ------------------------------------------------------------------
# 一、前置条件
# ------------------------------------------------------------------
# 1. 魔搭账号（阿里账号绑定 + 实名认证，Docker 构建前置条件）：
#    https://www.modelscope.cn
# 2. 个人 Access Token：
#    个人中心 → 访问令牌 → 创建（格式 modelscope_xxx...）
# 3. 已备案域名（用于微信小程序 request 合法域名反代）
#
# ------------------------------------------------------------------
# 二、Docker 创空间要求（关键）
# ------------------------------------------------------------------
# - 端口固定 7860：ms_deploy.json 中 port 必须为 7860，8080 被平台占用
# - ms_deploy.json 的 environment_variables 仅对 gradio/streamlit/static 生效，
#   docker 类型不生效 → 敏感环境变量通过 API Secrets 设置（见部署脚本）
# - 仓库默认分支 master（禁止 force push 到已存在的仓库）
# - 文件 >100MB 需 Git LFS
# - 首次构建 3-5 分钟
# - 免费 CPU 配额有时长限制
#
# ------------------------------------------------------------------
# 三、GitHub Actions 自动部署（推荐）
# ------------------------------------------------------------------
# 推送代码到 master 分支时自动部署到魔搭创空间。
#
# ① 在 GitHub Repo Settings → Secrets 添加：
#    - MODEL_SCOPE_TOKEN: 魔搭 Access Token
#    - MODEL_SCOPE_USERNAME: 魔搭用户名
#    - MODEL_SCOPE_STUDIO_NAME: 创空间名称（如 tennis-diary-server）
#    - JWT_SECRET、WX_APPID、WX_SECRET、ADMIN_DEFAULT_PASSWORD、ADMIN_RESET_KEY
#
#    JWT_SECRET 生成命令（任选其一）：
#      python -c "import secrets; print(secrets.token_hex(32))"
#      openssl rand -hex 32
#
# ② 触发部署：
#    - 推送 server/ 目录变更到 master 分支自动触发
#    - 或手动触发：Actions → Deploy Server to ModelScope → Run workflow
#
# ③ 部署流程：
#    GitHub Actions 运行 server/scripts/deploy-modelscope.sh
#    → 复制 server/ 核心文件 + ms_deploy.json + Dockerfile 到临时目录
#    → 通过 API 设置 Secrets（JWT_SECRET / WX_SECRET 等）
#    → 推送到魔搭创空间远程（仅代码，不含敏感信息）
#    → 魔搭自动构建 Docker 镜像并启动（监听 7860）
#
# ------------------------------------------------------------------
# 四、本地手动部署
# ------------------------------------------------------------------
# 复制 .env.modelscope.example 为 .env.modelscope，填入实际值后执行：
#
#   cd server
#   bash scripts/deploy-modelscope.sh
#
# 或使用环境变量：
#
#   MODEL_SCOPE_TOKEN=modelscope_xxx \
#   MODEL_SCOPE_USERNAME=your-name \
#   MODEL_SCOPE_STUDIO_NAME=tennis-diary-server \
#   JWT_SECRET=... WX_APPID=... WX_SECRET=... ADMIN_DEFAULT_PASSWORD=... \
#   bash scripts/deploy-modelscope.sh
#
# ------------------------------------------------------------------
# 五、部署架构
# ------------------------------------------------------------------
#   GitHub Actions / 本地
#        │  打包 server/** + Dockerfile + ms_deploy.json + API Secrets
#        ▼
#   魔搭创空间（Docker sdk，CPU 免费档 2vCPU/16G）
#   ├─ 自动用根 Dockerfile 构建镜像
#   ├─ 监听固定端口 7860
#   ├─ 数据卷：/mnt/workspace（重启持久，转移/重命名丢失）
#   └─ 访问域名：https://{owner}-{studio}.ms.show
#
# ------------------------------------------------------------------
# 六、环境变量配置（通过部署脚本自动设置）
# ------------------------------------------------------------------
# 魔搭 docker 类型不支持 ms_deploy.json 注入环境变量，
# 脚本通过魔搭 RTS API 将以下项设置为创空间 Secrets：
#
#   - JWT_SECRET               (Secret)
#   - WX_APPID                 (Secret)
#   - WX_SECRET                (Secret)
#   - ADMIN_DEFAULT_PASSWORD   (Secret)
#   - ADMIN_RESET_KEY          (Secret, 可留空)
#
# 非敏感运行时配置（DEBUG / DATA_DIR ...）已固化在 docker-entrypoint.sh
# 与 Dockerfile ENV 默认值中，无需单独注入。
#
# > DATA_DIR 已在 modelscope/Dockerfile 中固化指向魔搭持久化卷 /mnt/workspace，
# > 因此 SQLite 数据库、上传文件与日志重启后均不丢失（转移/重命名创空间除外）。
#
# ------------------------------------------------------------------
# 七、配置 Nginx 反代（微信小程序域名要求）
# ------------------------------------------------------------------
# 魔搭创空间域名（*.ms.show）无法备案，微信小程序 request 合法域名
# 必须已备案，因此需要自备域名 + Nginx 反代：
#
# ① 将域名 DNS CNAME 指向：
#    https://{owner}-{slug}.ms.show
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
#            proxy_pass https://{owner}-{slug}.ms.show;
#            proxy_set_header Host $host;
#            proxy_set_header X-Real-IP $remote_addr;
#            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#            proxy_set_header X-Forwarded-Proto $scheme;
#        }
#    }
#
# ③ 在微信小程序后台配置 request 合法域名：https://api.yourdomain.com
#
# ------------------------------------------------------------------
# 八、验证部署
# ------------------------------------------------------------------
# ① 等待魔搭构建完成（首次约 3-5 分钟）
# ② API 文档：https://{owner}-{slug}.ms.show/docs
# ③ 健康检查：curl https://{owner}-{slug}.ms.show/health
#    预期：{"code":0,"message":"ok","success":true,"data":{"status":"ok",...}}
#
# ------------------------------------------------------------------
# 九、注意事项
# ------------------------------------------------------------------
# ① 免费 CPU 配额有限，长时间高负载可能被限流/休眠
# ② SQLite 单文件锁限制并发，适合日活 < 100 演示场景
# ③ 数据持久化在 /mnt/workspace（Dockerfile 已把 DATA_DIR 指向该卷），
#    但转移/重命名创空间会丢数据
# ④ 生产正式环境推荐 Oracle Cloud（常驻 + 200GB 卷）
# ⑤ 禁止 force push：魔搭已存在的创空间只接受正向 push
#
# ------------------------------------------------------------------
# 十、故障排查
# ------------------------------------------------------------------
# ① 查看构建日志：
#    创空间主页 → 部署日志（build / run 两类）
# ② 端口冲突：
#    确认 Dockerfile EXPOSE 7860 且 entrypoint 监听 0.0.0.0:7860
# ③ 环境变量为空：
#    确认 Secrets 已通过 API 设置（scripts 会输出 OK 日志）
# ④ .ms.show 反代后 502：
#    确认 Nginx proxy_pass 末尾无多余斜杠，且创空间在运行