#!/usr/bin/env bash
# ============================================================
# Tennis Diary Server - Oracle Cloud Always Free 部署脚本
# 将 server/ 目录同步到 OCI VM 并触发 docker compose 重建。
#
# 配置优先级：环境变量 > .env.oci 文件
#
# 用法:
#   # 方式一：本地手动部署
#   cp .env.oci.example .env.oci
#   # 编辑 .env.oci 填入 OCI_VM_USER / OCI_VM_HOST / OCI_SSH_KEY
#   bash scripts/deploy-oci.sh
#
#   # 方式二：全部使用环境变量（也用于 GitHub Actions）
#   OCI_VM_USER=ubuntu OCI_VM_HOST=1.2.3.4 OCI_SSH_KEY=~/.ssh/id_ed25519 \
#   JWT_SECRET=xxx WX_APPID=xxx WX_SECRET=xxx \
#   bash scripts/deploy-oci.sh
# ============================================================

set -euo pipefail

# ---------- 颜色输出 ----------
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

# ---------- 路径 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ---------- 加载 .env.oci 文件 ----------
load_env_file() {
  local env_file="$SERVER_DIR/.env.oci"
  if [ -f "$env_file" ]; then
    log_info "加载本地配置: $env_file"
    while IFS='=' read -r key value; do
      key=$(echo "$key" | xargs)
      value=$(echo "$value" | xargs)
      [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
      if [ -z "${!key:-}" ]; then
        export "$key=$value"
      fi
    done < "$env_file"
  fi
}

load_env_file

# ---------- 读取变量 ----------
OCI_VM_USER="${OCI_VM_USER:-}"
OCI_VM_HOST="${OCI_VM_HOST:-}"
OCI_SSH_PORT="${OCI_SSH_PORT:-22}"
OCI_SSH_KEY="${OCI_SSH_KEY:-}"
OCI_APP_DIR="${OCI_APP_DIR:-/opt/tennis-diary}"

# 微信/后台相关凭据（写入远端 .env）
JWT_SECRET="${JWT_SECRET:-}"
WX_APPID="${WX_APPID:-}"
WX_SECRET="${WX_SECRET:-}"
ADMIN_DEFAULT_PASSWORD="${ADMIN_DEFAULT_PASSWORD:-changeme}"
ADMIN_RESET_KEY="${ADMIN_RESET_KEY:-}"

# ---------- 校验变量 ----------
[ -n "$OCI_VM_USER" ] || fail "OCI_VM_USER 未设置（检查 .env.oci 或环境变量）"
[ -n "$OCI_VM_HOST" ] || fail "OCI_VM_HOST 未设置（检查 .env.oci 或环境变量）"
[ -n "$OCI_SSH_KEY" ] || fail "OCI_SSH_KEY 未设置（SSH 私钥路径 或 私钥内容）"

# ---------- 私钥处理：支持 路径 或 私钥内容两种形式 ----------
TMP_KEY=""
if [[ "$OCI_SSH_KEY" == "-----BEGIN"* ]]; then
  # CI / 环境变量直接传入私钥内容
  TMP_KEY="$(mktemp)"
  chmod 600 "$TMP_KEY"
  printf '%s\n' "$OCI_SSH_KEY" > "$TMP_KEY"
  OCI_SSH_KEY="$TMP_KEY"
  trap 'rm -f "$TMP_KEY"' EXIT
  log_info "  ✓ 已使用环境变量私钥（写入临时文件）"
else
  # 本机路径
  if [[ "$OCI_SSH_KEY" == "~/"* ]]; then
    OCI_SSH_KEY="$HOME/${OCI_SSH_KEY#\~/}"
  fi
  [ -f "$OCI_SSH_KEY" ] || fail "SSH 私钥文件不存在: $OCI_SSH_KEY"
  [ -r "$OCI_SSH_KEY" ] || fail "SSH 私钥文件不可读: $OCI_SSH_KEY"
fi

# ---------- StrictHostKeyChecking ----------
if [ -n "${OCI_KNOWN_HOSTS:-}" ]; then
  SSH_OPTS=(-i "$OCI_SSH_KEY" -p "$OCI_SSH_PORT")
else
  SSH_OPTS=(-i "$OCI_SSH_KEY" -p "$OCI_SSH_PORT" -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/dev/null)
fi

ssh_cmd() {
  ssh "${SSH_OPTS[@]}" "${OCI_VM_USER}@${OCI_VM_HOST}" "$1"
}

# ---------- SSH 连通性预检 ----------
log_info "SSH 预检: ${OCI_VM_USER}@${OCI_VM_HOST}:${OCI_SSH_PORT}"
if ! ssh "${SSH_OPTS[@]}" -o ConnectTimeout=10 "${OCI_VM_USER}@${OCI_VM_HOST}" "echo ok" >/dev/null 2>&1; then
  fail "无法 SSH 连接（请检查 OCI_VM_HOST / OCI_VM_USER / OCI_SSH_KEY / 安全组 22 端口）"
fi
log_ok "  ✓ SSH 连接成功"

# ---------- 检查远端 Docker ----------
log_info "检查远端 Docker..."
if ! ssh_cmd "command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1"; then
  log_warn "  ⚠ 远端未安装 Docker/Compose，请先在 VM 上执行初始化："
  log_warn "      ssh ${OCI_VM_USER}@${OCI_VM_HOST} 'bash -s' < server/scripts/oci-bootstrap.sh"
  fail "请在 OCI VM 上先运行 oci-bootstrap.sh"
fi
log_ok "  ✓ Docker 可用"

# ---------- 创建远端目录 ----------
ssh_cmd "mkdir -p ${OCI_APP_DIR}/server ${OCI_APP_DIR}/data"

# ---------- rsync 同步代码 ----------
# 姿态模型缺失时自动下载（本地仓库 gitignore 不含模型；国内网络可用 POSE_MODEL_URL 覆盖镜像源）
if [ ! -f "$SERVER_DIR/models/pose_landmarker_lite.task" ]; then
  log_info "姿态模型缺失，自动下载..."
  bash "$SERVER_DIR/scripts/download-pose-model.sh" || fail "姿态模型下载失败"
fi

log_info "同步代码到 ${OCI_VM_USER}@${OCI_VM_HOST}:${OCI_APP_DIR}/server ..."
if ! command -v rsync >/dev/null 2>&1; then
  fail "本机未安装 rsync（macOS 自带；Ubuntu: sudo apt install rsync）"
fi

rsync -az --delete \
  --exclude '.venv' \
  --exclude '.git' \
  --exclude '.pytest_cache' \
  --exclude '.ruff_cache' \
  --exclude 'data' \
  --exclude '*.log' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude '!*.env.example' \
  -e "ssh ${SSH_OPTS[*]}" \
  "${SERVER_DIR}/" "${OCI_VM_USER}@${OCI_VM_HOST}:${OCI_APP_DIR}/server/"
log_ok "  ✓ 代码同步完成"

# ---------- 生成远端 .env ----------
# 注意：docker-compose.yml 中 env_file: .env 相对 compose 文件加载，
# 因此 .env 须写入 server/ 同目录。DATA_DIR 沿用 Dockerfile 默认 /data，
# 持久化由 compose 的 server_data 命名卷负责（--delete 不会清除卷数据）。
DATA_DIR="/data"
log_info "生成远端 .env ..."
ENV_CONTENT="DEBUG=false
DATA_DIR=${DATA_DIR}
DATABASE_URL=sqlite:////data/tennis_diary.db
JWT_SECRET=${JWT_SECRET}
JWT_EXPIRATION_HOURS=720
WX_APPID=${WX_APPID}
WX_SECRET=${WX_SECRET}
UPLOAD_DIR=/data/uploads
MAX_UPLOAD_SIZE_MB=100
LOG_DIR=/data/logs
LOG_LEVEL=INFO
ADMIN_DEFAULT_USERNAME=admin
ADMIN_DEFAULT_PASSWORD=${ADMIN_DEFAULT_PASSWORD}
ADMIN_RESET_KEY=${ADMIN_RESET_KEY}
"
printf '%s' "$ENV_CONTENT" | ssh_cmd "cat > ${OCI_APP_DIR}/server/.env"
log_ok "  ✓ 远端 .env 已生成（不含敏感文件提交）"

# ---------- docker compose 重建 ----------
log_info "在远端执行 docker compose up -d --build ..."
if ! ssh_cmd "cd ${OCI_APP_DIR}/server && docker compose up -d --build"; then
  fail "Docker Compose 部署失败，请登录服务器查看日志"
fi
log_ok "  ✓ 容器已启动"

# ---------- 健康检查轮询 ----------
log_info "等待服务就绪并检查 /health ..."
HEALTH_URL="http://${OCI_VM_HOST}:8000/health"
HCODE=""
for _ in $(seq 1 15); do
  HCODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "$HEALTH_URL" || true)
  [ "$HCODE" = "200" ] && break
  sleep 3
done

if [ "$HCODE" = "200" ]; then
  log_ok "✅ 部署成功！"
  log_ok "   API 文档: http://${OCI_VM_HOST}:8000/docs"
  log_ok "   健康检查: $HEALTH_URL"
else
  log_warn "  ⚠ /health 未在 45s 内返回 200（HTTP ${HCODE:-无响应}）"
  log_warn "    请登录服务器排查: docker compose -f ${OCI_APP_DIR}/server/docker-compose.yml ps / logs api"
  exit 1
fi