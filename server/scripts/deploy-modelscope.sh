#!/usr/bin/env bash
# ============================================================
# Tennis Diary Server - 魔搭创空间(ModelScope Studio) 部署脚本
# 将 server/ 代码推送为 Docker 创空间，并通过 API 设置 Secrets。
#
# 配置优先级：环境变量 > .env.modelscope 文件 > 默认值
#
# 用法:
#   # 方式一：通过 GitHub Actions secrets（推荐生产）
#   # 在 GitHub Repo Settings → Secrets 配置：
#   #   MODEL_SCOPE_TOKEN, MODEL_SCOPE_USERNAME, MODEL_SCOPE_STUDIO_NAME,
#   #   JWT_SECRET, WX_APPID, WX_SECRET, ADMIN_DEFAULT_PASSWORD
#
#   # 方式二：本地手动部署
#   cp .env.modelscope.example .env.modelscope
#   # 编辑 .env.modelscope 填入实际值
#   MODEL_SCOPE_TOKEN=modelscope_xxx MODEL_SCOPE_USERNAME=yourname \
#   MODEL_SCOPE_STUDIO_NAME=tennis-diary-server \
#   JWT_SECRET=xxx WX_APPID=xxx WX_SECRET=xxx bash scripts/deploy-modelscope.sh
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

# ---------- 加载 .env.modelscope 文件 ----------
load_env_file() {
  local env_file="$SERVER_DIR/.env.modelscope"
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
MODEL_SCOPE_TOKEN="${MODEL_SCOPE_TOKEN:-}"
MODEL_SCOPE_USERNAME="${MODEL_SCOPE_USERNAME:-}"
MODEL_SCOPE_STUDIO_NAME="${MODEL_SCOPE_STUDIO_NAME:-tennis-diary-server}"
MS_API_BASE="${MS_API_BASE:-https://modelscope.cn/openapi/v1}"
JWT_SECRET="${JWT_SECRET:-}"
WX_APPID="${WX_APPID:-}"
WX_SECRET="${WX_SECRET:-}"
ADMIN_DEFAULT_PASSWORD="${ADMIN_DEFAULT_PASSWORD:-changeme}"
ADMIN_RESET_KEY="${ADMIN_RESET_KEY:-}"

# ---------- 校验变量 ----------
[ -n "$MODEL_SCOPE_TOKEN" ]    || fail "MODEL_SCOPE_TOKEN 未设置（检查 .env.modelscope 或环境变量）"
[ -n "$MODEL_SCOPE_USERNAME" ] || fail "MODEL_SCOPE_USERNAME 未设置（检查 .env.modelscope 或环境变量）"
[ -n "$MODEL_SCOPE_STUDIO_NAME" ] || fail "MODEL_SCOPE_STUDIO_NAME 未设置（检查 .env.modelscope 或环境变量）"
[ -n "$JWT_SECRET" ]           || fail "JWT_SECRET 未设置（检查 .env.modelscope 或环境变量）"
[ -n "$WX_APPID" ]             || fail "WX_APPID 未设置（检查 .env.modelscope 或环境变量）"
[ -n "$WX_SECRET" ]            || fail "WX_SECRET 未设置（检查 .env.modelscope 或环境变量）"

# 占位符校验
[ "$MODEL_SCOPE_TOKEN" != "modelscope_xxxxxxxxxxxxxxxxx" ] || fail "请修改 MODEL_SCOPE_TOKEN 为实际值"
[ "$MODEL_SCOPE_USERNAME" != "your-modelscope-username" ] || fail "请修改 MODEL_SCOPE_USERNAME 为实际值"

# ---------- API 封装 ----------
ms_get()  { curl -s -f -H "Authorization: Bearer ${MODEL_SCOPE_TOKEN}" "$1"; }
ms_post() { curl -s -H "Authorization: Bearer ${MODEL_SCOPE_TOKEN}" -H "Content-Type: application/json" -X POST -d "$2" "$1"; }

# ---------- 预检 Token 与创空间 ----------
log_info "预检魔搭 API 鉴权..."
WHOAMI=$(ms_get "$MS_API_BASE/studios/${MODEL_SCOPE_USERNAME}/${MODEL_SCOPE_STUDIO_NAME}" 2>/dev/null || true)
if [ -n "$WHOAMI" ]; then
  log_ok "  ✓ 创空间已存在（自动复用）"
else
  log_info "创空间不存在，通过 API 创建..."
  CREATE_RESP=$(ms_post "$MS_API_BASE/studios" "{
    \"owner\": \"${MODEL_SCOPE_USERNAME}\",
    \"repo_name\": \"${MODEL_SCOPE_STUDIO_NAME}\",
    \"sdk_type\": \"docker\",
    \"display_name\": \"Tennis Diary Server\",
    \"private\": true
  }" || true)
  if [ -n "$CREATE_RESP" ] && ! echo "$CREATE_RESP" | grep -q "error"; then
    log_ok "  ✓ 创空间创建成功"
  else
    log_warn "  ⚠ 创建响应: ${CREATE_RESP:-空}"
    log_warn "    若返回 404/409 请检查 Token 权限，或到网页手动创建后重试"
  fi
fi

# ---------- 临时目录 ----------
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# ---------- 1. 复制核心文件 ----------
log_info "打包 server/ 到临时目录: $TMP_DIR"
MS_DIR="$SERVER_DIR/modelscope"

# Dockerfile（魔搭用根目录 Dockerfile 构建）
[ -f "$SERVER_DIR/Dockerfile" ] && cp "$SERVER_DIR/Dockerfile" "$TMP_DIR/Dockerfile" \
  || fail "Dockerfile 不存在: $SERVER_DIR/Dockerfile"

# ms_deploy.json（魔搭部署配置）
[ -f "$MS_DIR/ms_deploy.json" ] && cp "$MS_DIR/ms_deploy.json" "$TMP_DIR/ms_deploy.json" \
  || fail "ms_deploy.json 不存在: $MS_DIR/ms_deploy.json"

# .dockerignore
[ -f "$SERVER_DIR/.dockerignore" ] && cp "$SERVER_DIR/.dockerignore" "$TMP_DIR/.dockerignore"

# 核心代码文件
FILES_TO_COPY=("pyproject.toml" "uv.lock" "alembic.ini" "app" "alembic" "scripts")
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

# 验证打包结果
file_count=$(find "$TMP_DIR" -maxdepth 1 -type f | wc -l)
[ "$file_count" -gt 0 ] || fail "临时目录为空，打包失败"

# ---------- 2. 通过 API 设置 Secrets ----------
# 魔搭 docker 类型不支持 ms_deploy.json 注入环境变量，
# 只能通过创空间 Secrets API 设置。
log_info "通过 API 设置创空间 Secrets..."
SECRET_NAMES=("JWT_SECRET" "WX_APPID" "WX_SECRET" "ADMIN_DEFAULT_PASSWORD" "ADMIN_RESET_KEY")
SECRET_VALUES=("${JWT_SECRET}" "${WX_APPID}" "${WX_SECRET}" "${ADMIN_DEFAULT_PASSWORD}" "${ADMIN_RESET_KEY}")

for i in "${!SECRET_NAMES[@]}"; do
  name="${SECRET_NAMES[$i]}"
  value="${SECRET_VALUES[$i]}"
  RESP=$(ms_post "$MS_API_BASE/studios/${MODEL_SCOPE_USERNAME}/${MODEL_SCOPE_STUDIO_NAME}/secrets" \
    "{\"key\": \"${name}\", \"value\": \"${value}\"}" || true)
  if echo "$RESP" | grep -qiE "error|fail|invalid" 2>/dev/null; then
    log_warn "  ⚠ ${name} Secret 设置失败: $RESP"
  else
    log_ok "  ✓ ${name} Secret 已设置"
  fi
done

# ---------- 3. 初始化 Git 并推送 ----------
# 魔搭 Git 认证：用户名固定 oauth2，密码为 Access Token
#   https://oauth2:<token>@www.modelscope.cn/studios/<user>/<studio>.git
MS_HOST="${MS_HOST:-www.modelscope.cn}"
log_info "推送至魔搭: ${MODEL_SCOPE_USERNAME}/${MODEL_SCOPE_STUDIO_NAME}"

cd "$TMP_DIR"
git init -q
git config user.name  "$MODEL_SCOPE_USERNAME"
git config user.email "${MODEL_SCOPE_USERNAME}@users.modelscope.cn"
git remote add origin "https://oauth2:${MODEL_SCOPE_TOKEN}@${MS_HOST}/studios/${MODEL_SCOPE_USERNAME}/${MODEL_SCOPE_STUDIO_NAME}.git"

git checkout -b main
git add -A
git commit -m "deploy: $(date -u +'%Y-%m-%dT%H:%M:%SZ')" --quiet

log_info "注意: 魔搭默认分支为 master，推送 main:master ..."
if git push -u origin main:master 2>&1; then
  log_ok "✅ 代码推送成功！"
else
  log_error "推送失败，请检查 MODEL_SCOPE_TOKEN / MODEL_SCOPE_USERNAME / 分支"
  exit 1
fi

# ---------- 4. 触发部署（可选，推送通常自动触发） ----------
log_info "触发创空间部署..."
DEPLOY_RESP=$(ms_post "$MS_API_BASE/studios/${MODEL_SCOPE_USERNAME}/${MODEL_SCOPE_STUDIO_NAME}/deploy" "{}" || true)
if [ -n "$DEPLOY_RESP" ]; then
  log_info "  ✓ 部署请求已提交"
else
  log_warn "  ⚠ 部署触发失败（推送后魔搭通常会自动构建）"
fi

# ---------- 5. 健康检查 ----------
STUDIO_URL="https://${MODEL_SCOPE_USERNAME}-${MODEL_SCOPE_STUDIO_NAME}.ms.show"
HEALTH_URL="${STUDIO_URL}/health"
log_info "等待构建与部署（首次约 3-5 分钟）..."
log_info "健康检查: $HEALTH_URL"

HCODE=""
for _ in $(seq 1 40); do
  HCODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$HEALTH_URL" || true)
  [ "$HCODE" = "200" ] && break
  sleep 10
done

if [ "$HCODE" = "200" ]; then
  log_ok "✅ 部署成功！"
  log_ok "   创空间: $STUDIO_URL"
  log_ok "   API 文档: ${STUDIO_URL}/docs"
else
  log_warn "  ⚠ /health 未在约 7 分钟内返回 200（HTTP ${HCODE:-无响应}）"
  log_warn "    请在魔搭创空间页面查看构建日志（build / run）"
  log_warn "    常见问题：端口非 7860、环境变量缺失、构建超时"
  exit 1
fi