#!/usr/bin/env bash
# ============================================================
# Tennis Diary Server - HuggingFace Spaces 部署脚本
# 推送 server/ 目录到 HF Space git repo，HF 自动构建 Docker 镜像
#
# 配置优先级：环境变量 > .env.hf 文件 > 默认值
#
# 用法:
#   # 方式一：通过 GitHub Actions secrets（推荐生产）
#   # 在 GitHub Repo Settings → Secrets 配置：
#   #   HF_TOKEN, HF_USERNAME, HF_SPACE_NAME, JWT_SECRET, WX_APPID, WX_SECRET
#
#   # 方式二：本地手动部署
#   cp .env.hf.example .env.hf
#   # 编辑 .env.hf 填入实际值
#   HF_TOKEN=hf_xxxx HF_USERNAME=yourname HF_SPACE_NAME=your-space bash scripts/deploy-hf.sh
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
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SERVER_DIR="$PROJECT_DIR/server"

# ---------- 加载 .env.hf 文件 ----------
load_env_file() {
  local env_file="$PROJECT_DIR/.env.hf"
  if [ -f "$env_file" ]; then
    log_info "加载配置文件: $env_file"
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
HF_TOKEN="${HF_TOKEN:-}"
HF_USERNAME="${HF_USERNAME:-}"
HF_SPACE_NAME="${HF_SPACE_NAME:-}"
JWT_SECRET="${JWT_SECRET:-}"
WX_APPID="${WX_APPID:-}"
WX_SECRET="${WX_SECRET:-}"
ADMIN_DEFAULT_PASSWORD="${ADMIN_DEFAULT_PASSWORD:-changeme}"

# ---------- 校验变量 ----------
[ -n "$HF_TOKEN" ]        || fail "HF_TOKEN 未设置（检查 .env.hf 或环境变量）"
[ -n "$HF_USERNAME" ]     || fail "HF_USERNAME 未设置（检查 .env.hf 或环境变量）"
[ -n "$HF_SPACE_NAME" ]   || fail "HF_SPACE_NAME 未设置（检查 .env.hf 或环境变量）"
[ -n "$JWT_SECRET" ]      || fail "JWT_SECRET 未设置（检查 .env.hf 或环境变量）"
[ -n "$WX_APPID" ]        || fail "WX_APPID 未设置（检查 .env.hf 或环境变量）"
[ -n "$WX_SECRET" ]       || fail "WX_SECRET 未设置（检查 .env.hf 或环境变量）"

# 占位符校验
[ "$HF_TOKEN" != "hf_xxxxxxxxxxxxxxxxx" ]  || fail "请修改 HF_TOKEN 为实际值"
[ "$HF_USERNAME" != "your-hf-username" ]   || fail "请修改 HF_USERNAME 为实际值"

log_info "项目目录: $PROJECT_DIR"
log_info "Server 目录: $SERVER_DIR"
log_info "用户名: $HF_USERNAME"
log_info "Space: $HF_SPACE_NAME"

# ---------- 临时目录 ----------
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# ---------- 1. 复制 server/ 文件到临时目录 ----------
log_info "复制 server/ 文件到临时目录..."

# 复制 Dockerfile（HF 构建用）
if [ -f "$SERVER_DIR/Dockerfile" ]; then
  cp "$SERVER_DIR/Dockerfile" "$TMP_DIR/Dockerfile"
  log_info "  ✓ Dockerfile"
else
  fail "Dockerfile 不存在: $SERVER_DIR/Dockerfile"
fi

# 复制 .dockerignore
if [ -f "$SERVER_DIR/.dockerignore" ]; then
  cp "$SERVER_DIR/.dockerignore" "$TMP_DIR/.dockerignore"
  log_info "  ✓ .dockerignore"
else
  log_warn "  ✗ .dockerignore (不存在，跳过)"
fi

# 复制 server/ 核心文件
FILES_TO_COPY=(
  "pyproject.toml"
  "uv.lock"
  "alembic.ini"
  "app"
  "alembic"
  "scripts"
)

for item in "${FILES_TO_COPY[@]}"; do
  src="$SERVER_DIR/$item"
  if [ -e "$src" ]; then
    if [ -d "$src" ]; then
      cp -r "$src" "$TMP_DIR/"
    else
      cp "$src" "$TMP_DIR/"
    fi
    log_info "  ✓ $item"
  else
    log_warn "  ✗ $item (不存在，跳过)"
  fi
done

# ---------- 2. 创建 .env（包含敏感配置） ----------
# HF Docker Runner 会自动读取 repo 根目录的 .env 文件作为环境变量注入容器
log_info "创建 .env（包含 HF Space 环境变量）..."

cat > "$TMP_DIR/.env" <<EOF
# ============================================================
# Tennis Diary Server - 环境变量
# 此文件由 deploy-hf.sh 自动生成，包含敏感配置
# HF Docker Runner 会自动读取此文件并注入环境变量
# ============================================================

# 应用
DEBUG=false

# 数据库（HF Space 持久化卷 /data）
DATA_DIR=/data
DATABASE_URL=sqlite:////data/tennis_diary.db

# JWT
JWT_SECRET=${JWT_SECRET}
JWT_EXPIRATION_HOURS=720

# 微信小程序
WX_APPID=${WX_APPID}
WX_SECRET=${WX_SECRET}

# 文件上传
UPLOAD_DIR=/data/uploads
MAX_UPLOAD_SIZE_MB=100

# 日志
LOG_LEVEL=INFO
LOG_DIR=/data/logs
LOG_FILE=app.log
LOG_ROTATION=10 MB
LOG_RETENTION=7 days
LOG_JSON_ENABLED=false

# 管理员
ADMIN_DEFAULT_USERNAME=admin
ADMIN_DEFAULT_PASSWORD=${ADMIN_DEFAULT_PASSWORD}
ADMIN_RESET_KEY=

# 日志分离
LOG_ADMIN_FILE=admin.log
LOG_USER_FILE=user.log
EOF

log_info "  ✓ .env 已创建"

# ---------- 3. 验证临时目录 ----------
file_count=$(find "$TMP_DIR" -maxdepth 1 -type f | wc -l)
dir_count=$(find "$TMP_DIR" -maxdepth 1 -type d ! -path "$TMP_DIR" | wc -l)
total=$((file_count + dir_count))

if [ "$total" -eq 0 ]; then
  log_error "临时目录为空，没有任何文件被复制"
  log_error "目录: $TMP_DIR"
  fail "文件复制失败，请检查 server/ 目录结构"
fi

log_info "共复制 $total 个文件/目录到临时目录"

# ---------- 4. 初始化 Git 并推送 ----------
SPACE_REMOTE="https://${HF_USERNAME}:${HF_TOKEN}@huggingface.co/spaces/${HF_USERNAME}/${HF_SPACE_NAME}"

cd "$TMP_DIR"

git init -q
git config user.name  "$HF_USERNAME"
git config user.email "${HF_USERNAME}@users.huggingface.co"
git remote add origin "$SPACE_REMOTE"

git checkout -b main
git add -A

if ! git commit -m "deploy: $(date -u +'%Y-%m-%dT%H:%M:%SZ')" --quiet 2>&1; then
  log_error "git commit 失败"
  log_error "当前目录: $(pwd)"
  log_error "目录内容:"
  ls -la
  log_error "git status:"
  git status
  fail "无法创建提交，请检查文件是否正确复制"
fi

log_info "推送至: https://huggingface.co/spaces/${HF_USERNAME}/${HF_SPACE_NAME}"
log_info "正在推送..."

if git push -u origin main --force 2>&1; then
  log_ok "✅ 代码推送成功！"
  log_ok "Space 地址: https://huggingface.co/spaces/${HF_USERNAME}/${HF_SPACE_NAME}"
  log_ok "API 文档:   https://${HF_USERNAME}-${HF_SPACE_NAME}.hf.space/docs"
  log_ok "健康检查:   https://${HF_USERNAME}-${HF_SPACE_NAME}.hf.space/health"
else
  log_error "推送失败，请检查 HF_TOKEN / HF_USERNAME / HF_SPACE_NAME 是否正确"
  log_error "Remote: $SPACE_REMOTE"
  exit 1
fi

# ---------- 5. 验证 HF Space 是否启动 ----------
log_info "等待 HF Space 构建启动（约 2-3 分钟）..."
log_info "可在 HF Space → Logs 标签页查看构建进度"

log_ok "✅ 部署完成！请等待 HF Space 构建完成后访问 API 文档。"
log_ok "   构建完成后访问: https://${HF_USERNAME}-${HF_SPACE_NAME}.hf.space/docs"
