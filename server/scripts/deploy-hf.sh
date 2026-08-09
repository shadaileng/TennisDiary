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
ADMIN_RESET_KEY="${ADMIN_RESET_KEY:-}"

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

# ---------- 检测运行环境 ----------
IS_GITHUB_ACTIONS="${GITHUB_ACTIONS:-false}"

if [ "$IS_GITHUB_ACTIONS" = "true" ]; then
  log_info "检测到 GitHub Actions 环境"
  log_info "校验 GitHub Secrets 配置..."

  # GitHub Actions 必需的 Secrets
  REQUIRED_SECRETS=("HF_TOKEN" "HF_USERNAME" "HF_SPACE_NAME" "JWT_SECRET" "WX_APPID" "WX_SECRET" "ADMIN_DEFAULT_PASSWORD")
  MISSING_SECRETS=()

  for secret in "${REQUIRED_SECRETS[@]}"; do
    if [ -z "${!secret:-}" ]; then
      MISSING_SECRETS+=("$secret")
    fi
  done

  if [ ${#MISSING_SECRETS[@]} -gt 0 ]; then
    log_error "以下 GitHub Secrets 未配置："
    for secret in "${MISSING_SECRETS[@]}"; do
      log_error "  - $secret"
    done
    log_error ""
    log_error "请在 GitHub Repo Settings → Secrets and variables → Actions 中添加："
    for secret in "${REQUIRED_SECRETS[@]}"; do
      log_error "  $secret"
    done
    fail "GitHub Secrets 配置不完整"
  fi

  log_ok "  ✓ GitHub Secrets 配置完整"
else
  log_info "本地部署模式"
  log_info "校验 .env.hf 配置文件..."

  # 本地部署必需的变量
  LOCAL_REQUIRED_VARS=("HF_TOKEN" "HF_USERNAME" "HF_SPACE_NAME" "JWT_SECRET" "WX_APPID" "WX_SECRET" "ADMIN_DEFAULT_PASSWORD")
  MISSING_VARS=()

  for var in "${LOCAL_REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
      MISSING_VARS+=("$var")
    fi
  done

  if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    log_error "以下环境变量未设置："
    for var in "${MISSING_VARS[@]}"; do
      log_error "  - $var"
    done
    log_error ""
    log_error "请执行以下操作："
    log_error "  1. cp .env.hf.example .env.hf"
    log_error "  2. 编辑 .env.hf 填入实际值"
    log_error "  3. 运行: bash scripts/deploy-hf.sh"
    fail "环境变量配置不完整"
  fi

  log_ok "  ✓ 环境变量配置完整"
fi

# ---------- 检查/创建 HF Space ----------
log_info "检查 HF Space: ${HF_USERNAME}/${HF_SPACE_NAME}..."

SPACE_INFO=$(curl -s -o /dev/null -w "%{http_code}" -L \
  "https://huggingface.co/api/spaces/${HF_USERNAME}/${HF_SPACE_NAME}" \
  -H "Authorization: Bearer ${HF_TOKEN}")

if [ "$SPACE_INFO" = "200" ]; then
  log_ok "  ✓ Space 已存在"
else
  log_info "Space 不存在，正在创建..."
  CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "https://huggingface.co/api/spaces" \
    -H "Authorization: Bearer ${HF_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"id\": \"${HF_USERNAME}/${HF_SPACE_NAME}\", \"sdk\": \"docker\", \"hardware\": \"cpu-basic\"}")
  
  CREATE_STATUS=$(echo "$CREATE_RESPONSE" | tail -n1)
  
  if [ "$CREATE_STATUS" = "200" ] || [ "$CREATE_STATUS" = "201" ]; then
    log_ok "  ✓ Space 创建成功"
  else
    log_warn "  ⚠ Space 创建失败 (HTTP $CREATE_STATUS)，请确认名称是否可用或手动创建"
    log_warn "     访问 https://huggingface.co/new-space 手动创建"
    log_warn "     创建后重新运行部署脚本"
  fi
fi

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

# ---------- 2. 设置 HF Space Secrets ----------
# 敏感配置通过 HF API 设置为 Secrets，不推送到 git repo
log_info "设置 HF Space Secrets..."

# 预检：for 循环前先验证 token 有效性与 Space secrets 端点可写
log_info "预检 HF API 鉴权..."
AUTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" -L \
  "https://huggingface.co/api/spaces/${HF_USERNAME}/${HF_SPACE_NAME}/secrets" \
  -H "Authorization: Bearer ${HF_TOKEN}")

if [ "$AUTH_CHECK" = "401" ] || [ "$AUTH_CHECK" = "403" ]; then
  fail "HF_TOKEN 无效或无权限访问该 Space (HTTP $AUTH_CHECK)"
elif [ "$AUTH_CHECK" = "404" ]; then
  fail "HF Space 不存在: ${HF_USERNAME}/${HF_SPACE_NAME}"
elif [ "$AUTH_CHECK" != "200" ]; then
  log_warn "  ⚠ 预检异常 (HTTP $AUTH_CHECK)，继续尝试设置 Secrets..."
else
  log_ok "  ✓ HF API 鉴权通过"
fi

SECRET_NAMES=("JWT_SECRET" "WX_APPID" "WX_SECRET" "ADMIN_DEFAULT_PASSWORD" "ADMIN_RESET_KEY")
SECRET_VALUES=("${JWT_SECRET}" "${WX_APPID}" "${WX_SECRET}" "${ADMIN_DEFAULT_PASSWORD}" "${ADMIN_RESET_KEY}")

for i in "${!SECRET_NAMES[@]}"; do
  name="${SECRET_NAMES[$i]}"
  value="${SECRET_VALUES[$i]}"
  
  SECRET_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -L -X POST \
    "https://huggingface.co/api/spaces/${HF_USERNAME}/${HF_SPACE_NAME}/secrets" \
    -H "Authorization: Bearer ${HF_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"key\": \"${name}\", \"value\": \"${value}\"}")
  
  if [ "$SECRET_RESPONSE" = "200" ]; then
    log_ok "  ✓ ${name} Secret 已设置"
  else
    log_warn "  ⚠ ${name} Secret 设置失败 (HTTP $SECRET_RESPONSE)"
  fi
done

# 设置非敏感配置为 Variables（可选，也可手动在 HF 后台设置）
VAR_NAMES=("DEBUG" "DATA_DIR" "DATABASE_URL" "JWT_EXPIRATION_HOURS" 
           "UPLOAD_DIR" "MAX_UPLOAD_SIZE_MB" "LOG_LEVEL" "LOG_DIR"
           "ADMIN_DEFAULT_USERNAME")
VAR_VALUES=("false" "/data" "sqlite:////data/tennis_diary.db" "720"
            "/data/uploads" "100" "INFO" "/data/logs" "admin")

for i in "${!VAR_NAMES[@]}"; do
  name="${VAR_NAMES[$i]}"
  value="${VAR_VALUES[$i]}"
  
  curl -s -o /dev/null -w "" -L -X POST \
    "https://huggingface.co/api/spaces/${HF_USERNAME}/${HF_SPACE_NAME}/secrets" \
    -H "Authorization: Bearer ${HF_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"key\": \"${name}\", \"value\": \"${value}\"}" || true
done

log_info "  ✓ 环境变量已配置（Secrets + Variables）"

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

log_ok "✅ 部署完成！请等待 HF Space 构建完成后访问 API 文档。"
log_ok "   构建完成后访问: https://${HF_USERNAME}-${HF_SPACE_NAME}.hf.space/docs"
