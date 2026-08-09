#!/usr/bin/env bash
# ============================================================
# Tennis Diary Server - Oracle Cloud Always Free 初始化脚本
# 在 OCI VM 上一次性执行：安装 Docker + Compose + 可选 Nginx/Let's Encrypt
#
# 用法（在 VM 上执行，需要 root 或 sudo）：
#   bash oci-bootstrap.sh                  # 仅安装 Docker
#   bash oci-bootstrap.sh api.example.com  # Docker + Nginx HTTPS 反代
# ============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

fail() {
  log_error "$1"
  exit 1
}

# ---------- 参数 ----------
DOMAIN="${1:-}"

# ---------- 检查 root 权限 ----------
if [ "$(id -u)" -ne 0 ]; then
  # 尝试 sudo -v 缓冲权限
  if ! sudo -n true 2>/dev/null; then
    fail "请以 root 运行，或确保当前用户可免密 sudo"
  fi
  SUDO="sudo"
else
  SUDO=""
fi

# ---------- 系统更新 ----------
log_info "更新系统软件包..."
$SUDO apt-get update -y
$SUDO apt-get upgrade -y

# ---------- 安装 Docker Engine + Compose Plugin ----------
if command -v docker >/dev/null 2>&1; then
  log_ok "Docker 已安装: $(docker --version)"
else
  log_info "安装 Docker..."
  curl -fsSL https://get.docker.com | sh
  log_ok "Docker 安装完成"
fi

# 将当前用户加入 docker 组（免 sudo 运行 docker）
if ! id -nG "$(whoami)" | grep -qw docker; then
  $SUDO usermod -aG docker "$(whoami)"
  log_info "已把用户 $(whoami) 加入 docker 组（重新登录后生效）"
fi

# ---------- 校验 Compose Plugin ----------
if docker compose version >/dev/null 2>&1; then
  log_ok "Docker Compose 版本: $(docker compose version | awk '{print $NF}')"
else
  log_error "Docker compose 插件不可用，Docker 安装异常"
  fail "Docker 安装失败，请检查 apt 日志"
fi

# ---------- 创建部署目录 ----------
APP_DIR=/opt/tennis-diary
$SUDO mkdir -p "$APP_DIR/data" "$APP_DIR/server"
log_ok "部署目录: $APP_DIR"

# ---------- UFW 防火墙（可选启用） ----------
if command -v ufw >/dev/null 2>&1; then
  log_info "配置 UFW 防火墙..."
  $SUDO ufw allow 22/tcp
  $SUDO ufw allow 80/tcp
  $SUDO ufw allow 443/tcp
  $SUDO ufw allow 8000/tcp
  $SUDO ufw --force enable
  log_ok "UFW 已启用: 22/80/443/8000"
fi

# ---------- HTTPS（可选：Nginx + certbot） ----------
if [ -n "$DOMAIN" ]; then
  log_info "安装 Nginx + certbot，配置域名 $DOMAIN ..."

  $SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y nginx certbot python3-certbot-nginx || \
    fail "Nginx/certbot 安装失败"

  cat <<EOF | $SUDO tee /etc/nginx/sites-available/tennis-diary >/dev/null
server {
    listen 80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

  $SUDO ln -sf /etc/nginx/sites-available/tennis-diary /etc/nginx/sites-enabled/
  $SUDO nginx -t
  $SUDO systemctl enable nginx
  $SUDO systemctl start nginx

  # 签发证书（自动改为 443 + 反代）
  $SUDO certbot --nginx -d "$DOMAIN" --non-interactive --redirect --agree-tos \
    --register-unsafely-without-email || log_warn "certbot 签发失败，请手动执行: certbot --nginx -d $DOMAIN"

  log_ok "HTTPS 配置完成: https://$DOMAIN → 127.0.0.1:8000"
else
  log_info "未提供域名参数，跳过 HTTPS 配置"
  log_info " （如需 HTTPS：bash oci-bootstrap.sh -d api.example.com）"
fi

# ---------- 完成 ----------
cat <<EOF

============================================================
✅ Oracle VM 初始化完成！
下一步（本机执行）：
  cd server
  cp .env.oci.example .env.oci
  编辑 .env.oci 填入 OCI_VM_USER / OCI_VM_HOST / OCI_SSH_KEY
  bash scripts/deploy-oci.sh

若刚加入 docker 组，请先重新 SSH 登录使权限生效。

安全提示：
  - 公网 IP 由 OCI 保留（弹性 IP），重启不变
  - 请及时在 OCI 控制台为 Linux 配置安全更新（unattended-upgrades）
============================================================
EOF