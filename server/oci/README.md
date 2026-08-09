# ============================================================
# Tennis Diary Server - Oracle Cloud Always Free 部署说明
# ============================================================
#
# Oracle Cloud 免费 VM（Always Free）托管国内可访问的 FastAPI 后台。
# 免费档常驻运行、无休眠，自带 200GB Block Volume 可持久化 SQLite 与上传文件。
#
# ------------------------------------------------------------------
# 一、免费档资源（Always Free）
# ------------------------------------------------------------------
# 1. Ampere A1（Arm，推荐）：
#    - 免费额度：2 OCPU / 12GB RAM（2026-06-15 起由 4 OCPU/24GB 削减）
#    - 推荐配置：1 OCPU / 6GB 单台实例（留余量，避免触顶被停机）
# 2. AMD Micro：
#    - 2 × VM.Standard.E2.1.Micro（1/8 OCPU / 1GB RAM，适合极轻量）
# 3. Block Volume：200GB（含 Boot Volume，最小 47GB）
# 4. 10TB/月 出站带宽，常驻运行不休眠
#
# ------------------------------------------------------------------
# 二、创建实例（一次性）
# ------------------------------------------------------------------
# 1. 注册：https://signup.cloud.oracle.com（选 home region，如 Seoul/Osaka/Tokyo）
# 2. 控制台 → Compute → Instances → Create instance
#    - Name: tennis-diary-server
#    - Image: Canonical Ubuntu 24.04（默认自用 apt，社区资料充足）
#    - Shape: VM.Standard.A1.Flex（Edit → OCPU:1, Memory:6GB）
#    - SSH keys: 上传 / 粘贴本地公钥 ~/.ssh/id_ed25519.pub
#    - Boot volume: 默认即可（47GB 计入 200GB 免费配额）
# 3. 记下实例的公网 IP（Public IP，弹性保留）
#
# ------------------------------------------------------------------
# 三、放行端口（防火墙/Security List）
# ------------------------------------------------------------------
# 实例创建时所在 VCN，Security List 需放行：
#    - 22/tcp（入站，SSH）
#    - 80/tcp（HTTP，Nginx/Let's Encrypt）
#    - 443/tcp（HTTPS，微信小程序必需）
#    - 8000/tcp（直连 API，仅开发期，或仅来源 IP 限定）
#
# 若默认 VCN 未放行，在 VCN → Security Lists 添加 Ingress Rule：
#    Source: 0.0.0.0/0  | IP Protocol: TCP  | Destination Port: 22,80,443,8000
#
# ------------------------------------------------------------------
# 四、配置持久化存储 Block Volume（推荐，可选）
# ------------------------------------------------------------------
# SQLite 数据库与上传文件默认写入容器内 /data。容器重建默认不丢，
# 但为了彻底持久化（机器迁移/故障时安全），建议挂独立 Block Volume：
#
# 1. OCI 控制台 → Block Storage → Block Volumes → Create
#    - Size: 最小 50GB（计入 200GB 免费配额）
#    - 与实例同可用域（AD）
# 2. 选择刚创建的 Volume → Attach → 附加到 tennis-diary-server
#    - Attachment type: ISCSI
# 3. SSH 到实例，记录设备名（如 /dev/sdb），执行：
#
#     sudo mkfs.ext4 /dev/sdb
#     sudo mkdir -p /data
#     echo '/dev/sdb /data ext4 defaults,noatime 0 0' | sudo tee -a /etc/fstab
#     sudo mount -a
#     df -h /data
#
# ------------------------------------------------------------------
# 五、初始化服务器（Docker + Nginx，一次性）
# ------------------------------------------------------------------
#     ssh ubuntu@<公网IP> 'bash -s' < server/scripts/oci-bootstrap.sh
#
# 若需自动配置 HTTPS 反代（域名须已备案归属解析到本机）：
#
#     ssh ubuntu@<公网IP> 'bash -s' -- api.example.com < server/scripts/oci-bootstrap.sh
#
# ------------------------------------------------------------------
# 六、部署应用（写库 + 启动，可反复执行）
# ------------------------------------------------------------------
# 本地执行（无需在服务器编译 Dockerfile）：
#
#   cd server
#   cp .env.oci.example .env.oci
#   # 编辑 .env.oci：OCI_VM_USER / OCI_VM_HOST / OCI_SSH_KEY / OCI_SSH_PORT
#   bash scripts/deploy-oci.sh
#
# 或用环境变量：
#
#   OCI_VM_USER=ubuntu OCI_VM_HOST=<公网IP> OCI_SSH_KEY=~/.ssh/id_ed25519 \
#   bash scripts/deploy-oci.sh
#
# 脚本完成同步后自动执行远端：
#
#   cd /opt/tennis-diary && docker compose up -d --build
#
# ------------------------------------------------------------------
# 七、自动部署（GitHub Actions）
# ------------------------------------------------------------------
# push server/** 到 master 自动触发 .github/workflows/deploy-server-oci.yml，
# 需在 GitHub 仓库 Settings → Secrets 配置：
#
#   OCI_VM_HOST    ：公网 IP 或已解析域名
#   OCI_VM_USER    ：实例用户名（ubuntu / opc）
#   OCI_SSH_KNOWN  ：（可选）known_hosts 内容，用于 StrictHostKeyChecking
#   OCI_SSH_KEY    ：SSH 私钥内容（OpenSSH PEM 格式，允许 RSA）
#   JWT_SECRET / WX_APPID / WX_SECRET / ADMIN_DEFAULT_PASSWORD / ADMIN_RESET_KEY
#
# Actions 会将上述非 SSH 配置写为服务器 /opt/tennis-diary/.env，
# SSH 私钥仅用于 rsync 连接，不会写入代码或 .env。
#
# ⚠️ 注意：GitHub 会剔除 Secrets 值首尾的空白字符。若私钥末尾缺少换行，
# 会导致 "error: could not load host key" 或 "key" 不完整。
# 建议在 Secrets 中粘贴私钥时在结尾 **额外加一个空行**；或改用精细化密钥
# （grep 权限，见 https://weblog.roguecell.net/2016/04/03/ssh-git-key-restrictions 反转 Key）。
#
# ------------------------------------------------------------------
# 八、验证
# ------------------------------------------------------------------
#   // 页面
#   http://<公网IP>:8000/docs
#
#   // 健康检查
#   curl http://<公网IP>:8000/health
#   {"code":0,"message":"ok","success":true,"data":{"status":"ok","version":"1.x.y"}}
#
#   // 容器状态
#   ssh ubuntu@<ip> 'docker compose -f /opt/tennis-diary/docker-compose.yml ps'
#
# ------------------------------------------------------------------
# 九、HTTPS 域名与微信小程序
# ------------------------------------------------------------------
# 微信小程序 request 合法域名要求：HTTPS + 域名已 ICP 备案。
# bootstrap 脚本若带域名参数会自动签发 Let's Encrypt 证书并配 Nginx：
#
#   ssh ubuntu@<ip> 'sudo bash -s' -- api.example.com < server/scripts/oci-bootstrap.sh
#
# 预期效果：
#   https://api.example.com/health          → Nginx → 127.0.0.1:8000/health
#   https://api.example.com/docs            → Swagger 文档
#
# 然后在微信公众平台 → 开发设置 → 服务器域名：
#   request 合法域名: https://api.example.com
#   uploadFile / downloadFile 合法域名: https://api.example.com
#
# ------------------------------------------------------------------
# 十、低成本与注意事项
# ------------------------------------------------------------------
# ① Ampere A1 免费上限 2 OCPU/12GB，超额会被 Oracle 强制停机
#    → 建议用 1 OCPU/6GB，留 6GB 余量
# ② Block Volume 最小 47GB（Boot），总计 200GB 内免费，超出按量计费
# ③ 长期闲置实例可能被回收，生产环境建议定期使用备份接口
#    （POST /api/admin/system/backup，见 Admin 系统监控）
# ④ 服务器默认无防火墙（OCI Security List 控制入站），
#    若启用 UFW 请自行放行 22/80/443/8000
#
# ------------------------------------------------------------------
# 十一、故障排查
# ------------------------------------------------------------------
# ① 容器启动失败：ssh 后 docker compose logs api
# ② 端口不通：检查 OCI Security List 是否放行 + 实例公网 IP 是否变化
# ③ 数据库迁移失败：日志搜 "Migrations complete."，检查 .env 里 DATABASE_URL
# ④ SSH 连接慢：确认安全组 22 端口放行，且使用 PEM 私钥 (-i)