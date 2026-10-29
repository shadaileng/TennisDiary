#!/usr/bin/env bash
# ============================================================
# Tennis Diary Server - HuggingFace Spaces 部署脚本
# 将 server/ 代码推送为 Docker 空间，并通过 API 设置 Secrets。
#
# 配置优先级：环境变量 > .env.hf 文件 > 默认值
#
# 用法:
#   # 方式一：通过 GitHub Actions secrets（推荐生产）
#   # 在 GitHub Repo Settings → Secrets 配置：
#   #   HF_TOKEN, HF_USERNAME, HF_SPACE_NAME, DATABASE_URL, JWT_SECRET, WX_APPID, WX_SECRET
#
#   # 方式二：本地手动部署
#   cp .env.hf.example .env.hf
#   # 编辑 .env.hf 填入实际值
#   HF_TOKEN=hf_xxxx HF_USERNAME=yourname HF_SPACE_NAME=your-space \
#   DATABASE_URL=postgres://... \
#   JWT_SECRET=xxx WX_APPID=xxx WX_SECRET=xxx \
#   bash scripts/deploy-hf.sh
#
# 说明:
#   - 默认推送完成后即结束，不在 runner 上等待健康检查（避免 GitHub Actions 计费时长被浪费）
#   - 本地需要等待构建完成时，追加 WAIT_FOR_HEALTH=1:
#       WAIT_FOR_HEALTH=1 bash scripts/deploy-hf.sh
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
PROJECT_DIR="$(cd "$SERVER_DIR/.." && pwd)"

# ---------- 加载 .env.hf 文件 ----------
load_env_file() {
  local env_file="$PROJECT_DIR/.env.hf"
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
HF_TOKEN="${HF_TOKEN:-}"
HF_USERNAME="${HF_USERNAME:-}"
HF_SPACE_NAME="${HF_SPACE_NAME:-}"
JWT_SECRET="${JWT_SECRET:-}"
WX_APPID="${WX_APPID:-}"
WX_SECRET="${WX_SECRET:-}"
ADMIN_DEFAULT_PASSWORD="${ADMIN_DEFAULT_PASSWORD:-changeme}"
ADMIN_RESET_KEY="${ADMIN_RESET_KEY:-}"

# 必配数据库连接串
DATABASE_URL="${DATABASE_URL:-}"

# 可选配置（有明确默认值）
DEBUG="${DEBUG:-false}"
DATA_DIR="${DATA_DIR:-/data}"
JWT_EXPIRATION_HOURS="${JWT_EXPIRATION_HOURS:-720}"
UPLOAD_DIR="${UPLOAD_DIR:-/data/uploads}"
MAX_UPLOAD_SIZE_MB="${MAX_UPLOAD_SIZE_MB:-100}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
LOG_DIR="${LOG_DIR:-/data/logs}"
ADMIN_DEFAULT_USERNAME="${ADMIN_DEFAULT_USERNAME:-admin}"

# 可选配置 - 对象存储（KODO）
STORAGE_BACKEND="${STORAGE_BACKEND:-local}"
STORAGE_ENDPOINT="${STORAGE_ENDPOINT:-}"
STORAGE_REGION="${STORAGE_REGION:-}"
STORAGE_BUCKET="${STORAGE_BUCKET:-}"
STORAGE_ACCESS_KEY="${STORAGE_ACCESS_KEY:-}"
STORAGE_SECRET_KEY="${STORAGE_SECRET_KEY:-}"
STORAGE_PUBLIC_BASE_URL="${STORAGE_PUBLIC_BASE_URL:-}"

# 可选配置 - AI
AI_API_KEY="${AI_API_KEY:-}"
AI_BASE_URL="${AI_BASE_URL:-https://dashscope.aliyuncs.com/compatible-mode/v1}"
AI_MODEL="${AI_MODEL:-qwen-vl-max}"
AI_PROVIDER="${AI_PROVIDER:-}"

# 可选配置 - 数据库连接池
DB_POOL_SIZE="${DB_POOL_SIZE:-5}"
DB_MAX_OVERFLOW="${DB_MAX_OVERFLOW:-10}"
DB_POOL_RECYCLE="${DB_POOL_RECYCLE:-3600}"
DB_POOL_PRE_PING="${DB_POOL_PRE_PING:-true}"

# 是否在部署后等待健康检查。默认关闭（避免在 GitHub Actions runner 上长时间占用执行额度）。
# 本地手动部署需要等待时可设为 1: WAIT_FOR_HEALTH=1
WAIT_FOR_HEALTH="${WAIT_FOR_HEALTH:-0}"

# ---------- 校验变量 ----------
[ -n "$HF_TOKEN" ]        || fail "HF_TOKEN 未设置（检查 .env.hf 或环境变量）"
[ -n "$HF_USERNAME" ]     || fail "HF_USERNAME 未设置（检查 .env.hf 或环境变量）"
[ -n "$HF_SPACE_NAME" ]   || fail "HF_SPACE_NAME 未设置（检查 .env.hf 或环境变量）"
[ -n "$DATABASE_URL" ]    || fail "DATABASE_URL 未设置（必须配置 PostgreSQL 连接串）"
[ -n "$JWT_SECRET" ]      || fail "JWT_SECRET 未设置（检查 .env.hf 或环境变量）"
[ -n "$WX_APPID" ]        || fail "WX_APPID 未设置（检查 .env.hf 或环境变量）"
[ -n "$WX_SECRET" ]       || fail "WX_SECRET 未设置（检查 .env.hf 或环境变量）"

# 占位符校验
[ "$HF_TOKEN" != "hf_xxxxxxxxxxxxxxxxx" ]  || fail "请修改 HF_TOKEN 为实际值"
[ "$HF_USERNAME" != "your-hf-username" ]   || fail "请修改 HF_USERNAME 为实际值"

# ---------- API 封装 ----------
hf_get()  { curl -s -f -H "Authorization: Bearer ${HF_TOKEN}" "$1"; }
hf_post() { curl -s -H "Authorization: Bearer ${HF_TOKEN}" -H "Content-Type: application/json" -X POST -d "$2" "$1"; }

# ---------- 检查/创建 HF Space ----------
log_info "检查 HF Space: ${HF_USERNAME}/${HF_SPACE_NAME}..."

SPACE_INFO=$(curl -s -o /dev/null -w "%{http_code}" -L \
  "https://huggingface.co/api/spaces/${HF_USERNAME}/${HF_SPACE_NAME}" \
  -H "Authorization: Bearer ${HF_TOKEN}")

if [ "$SPACE_INFO" = "200" ]; then
  log_ok "  ✓ Space 已存在"
else
  log_info "Space 不存在，正在创建..."
  # 正确端点：POST /api/repos/create（创建 Space 本质是创建带 space 类型的 repo）
  CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "https://huggingface.co/api/repos/create" \
    -H "Authorization: Bearer ${HF_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"${HF_SPACE_NAME}\",
      \"type\": \"space\",
      \"sdk\": \"docker\",
      \"organization\": \"${HF_USERNAME}\",
      \"private\": false
    }")

  CREATE_STATUS=$(echo "$CREATE_RESPONSE" | tail -n1)

  if [ "$CREATE_STATUS" = "200" ] || [ "$CREATE_STATUS" = "201" ]; then
    log_ok "  ✓ Space 创建成功"
  else
    CREATE_BODY=$(echo "$CREATE_RESPONSE" | sed '$d')
    log_error "  ⚠ Space 创建失败 (HTTP $CREATE_STATUS)"
    if [ -n "$CREATE_BODY" ]; then
      log_error "     响应: $CREATE_BODY"
    fi
    log_error "     请确认 Space 名称是否可用，或访问 https://huggingface.co/new-space 手动创建"
    fail "Space 创建失败，终止部署（请创建后重新运行）"
  fi
fi

log_info "项目目录: $PROJECT_DIR"
log_info "Server 目录: $SERVER_DIR"
log_info "用户名: $HF_USERNAME"
log_info "Space: $HF_SPACE_NAME"

# ---------- 临时目录 ----------
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT
cd "$TMP_DIR"

# ---------- 1. 初始化 Git 并推送 ----------
SPACE_REMOTE="https://${HF_USERNAME}:${HF_TOKEN}@huggingface.co/spaces/${HF_USERNAME}/${HF_SPACE_NAME}"

log_info "初始化本地 Git 仓库..."
git init -q
git config user.name  "$HF_USERNAME"
git config user.email "${HF_USERNAME}@users.huggingface.co"
git remote add origin "$SPACE_REMOTE"

# 拉取远端 main 历史作为基底（远端已存在内容时避免历史不相关导致 push 被拒）
if git fetch origin main 2>/dev/null; then
  git checkout -q -B main FETCH_HEAD
  log_info "已基于远端 main 建立基底（包含 ${HF_SPACE_NAME} 已有内容）"
else
  git checkout -q -B main
  log_info "远端暂无 main，创建空分支（首次部署）"
fi

# ---------- 2. 复制核心文件 ----------
log_info "打包 server/ 到临时目录: $TMP_DIR"

# 姿态模型缺失时自动下载（本地仓库 gitignore 不含模型，须在此补齐；
# GitHub runner 可访问官方源，国内手动部署可用 POSE_MODEL_URL 覆盖镜像源）
if [ ! -f "$SERVER_DIR/models/pose_landmarker_lite.task" ]; then
  log_info "姿态模型缺失，自动下载..."
  bash "$SERVER_DIR/scripts/download-pose-model.sh" || fail "姿态模型下载失败"
fi

# Dockerfile
if [ -f "$SERVER_DIR/Dockerfile" ]; then
  cp "$SERVER_DIR/Dockerfile" "$TMP_DIR/Dockerfile"
  log_ok "  ✓ Dockerfile"
else
  fail "Dockerfile 不存在: $SERVER_DIR/Dockerfile"
fi

# README.hf.md → README.md（HF Space 配置：SDK/Docker + 卡片元数据）
if [ -f "$SERVER_DIR/README.hf.md" ]; then
  cp "$SERVER_DIR/README.hf.md" "$TMP_DIR/README.md"
  log_ok "  ✓ README.md (from README.hf.md)"
else
  log_warn "  ⚠ README.hf.md (不存在，跳过)"
fi

# .dockerignore
if [ -f "$SERVER_DIR/.dockerignore" ]; then
  cp "$SERVER_DIR/.dockerignore" "$TMP_DIR/.dockerignore"
  log_ok "  ✓ .dockerignore"
else
  log_warn "  ⚠ .dockerignore (不存在，跳过)"
fi

# 核心代码文件
FILES_TO_COPY=(
  "pyproject.toml"
  "uv.lock"
  "alembic.ini"
  "app"
  "alembic"
  "scripts"
  "models"
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
    log_warn "  ⚠ $item (不存在，跳过)"
  fi
done

# 验证打包结果
file_count=$(find "$TMP_DIR" -maxdepth 1 -type f | wc -l)
dir_count=$(find "$TMP_DIR" -maxdepth 1 -type d ! -path "$TMP_DIR" | wc -l)
total=$((file_count + dir_count))

if [ "$total" -eq 0 ]; then
  log_error "临时目录为空，没有任何文件被复制"
  log_error "目录: $TMP_DIR"
  fail "文件复制失败，请检查 server/ 目录结构"
fi

log_info "共复制 $total 个文件/目录到临时目录"

# ---------- 3. 通过 API 设置 HF Space Secrets ----------
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

# 必设 Secrets
log_info "  设置必填 Secrets..."
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

# 可选 Secrets（对象存储/AI 需要）
if [ ${#OPTIONAL_SECRETS[@]} -gt 0 ]; then
  log_info "  设置可选 Secrets..."
  for i in "${!OPTIONAL_SECRETS[@]}"; do
    name="${OPTIONAL_SECRETS[$i]}"
    value="${OPTIONAL_VALUES[$i]}"

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
fi

# 设置 Variables（包含数据库连接串和其他配置）
log_info "  设置 HF Space Variables (共 ${#VAR_NAMES[@]} 项)..."
for i in "${!VAR_NAMES[@]}"; do
  name="${VAR_NAMES[$i]}"
  value="${VAR_VALUES[$i]}"

  curl -s -o /dev/null -w "" -L -X POST \
    "https://huggingface.co/api/spaces/${HF_USERNAME}/${HF_SPACE_NAME}/secrets" \
    -H "Authorization: Bearer ${HF_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"key\": \"${name}\", \"value\": \"${value}\"}" || true
done

log_ok "  ✓ 环境变量已配置（Secrets + Variables）"

# ---------- 4. 提交并推送 ----------
log_info "提交并推送至: https://huggingface.co/spaces/${HF_USERNAME}/${HF_SPACE_NAME}"

git add -A
# 兜底：确保 uv.lock / pyproject.toml 一定入库（即使被 .gitignore 忽略）
git add -f uv.lock pyproject.toml 2>/dev/null || true

if ! git commit -m "deploy: $(date -u +'%Y-%m-%dT%H:%M:%SZ')" --quiet 2>&1; then
  log_error "  ⚠ git commit 失败（若提示 nothing to commit 表示与远端内容一致）"
  log_error "     当前目录: $(pwd)"
  log_error "     目录内容:"
  ls -la
  log_error "     git status:"
  git status
  fail "无法创建提交，请检查文件是否正确复制"
fi

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

log_ok "✅ 部署成功，已触发 HF 自动构建！"
log_ok "   Space 地址: https://huggingface.co/spaces/${HF_USERNAME}/${HF_SPACE_NAME}"
log_ok "   API 文档:   https://${HF_USERNAME}-${HF_SPACE_NAME}.hf.space/docs"
log_info "构建在 HF 侧异步进行，可在 Space 页面查看日志。"

if [ "$WAIT_FOR_HEALTH" = "1" ]; then
  HEALTH_URL="${HF_USERNAME}-${HF_SPACE_NAME}.hf.space/health"
  log_info "等待构建与部署（首次约 3-5 分钟）..."
  log_info "健康检查: https://$HEALTH_URL"

  HCODE=""
  for _ in $(seq 1 40); do
    HCODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "https://$HEALTH_URL" || true)
    [ "$HCODE" = "200" ] && break
    sleep 10
  done

  if [ "$HCODE" = "200" ]; then
    log_ok "✅ 部署成功，服务已就绪！"
  else
    log_warn "  ⚠ /health 未在约 7 分钟内返回 200（HTTP ${HCODE:-无响应}）"
    log_warn "    请在 HF Space 页面查看构建日志"
    log_warn "    常见问题：端口非 7860、环境变量缺失、构建超时"
  fi
fi
