#!/usr/bin/env bash
# ============================================================
# Tennis Diary Server - 姿态模型下载脚本
# 下载 MediaPipe pose_landmarker_lite.task 到 server/models/
#
# 用法:
#   bash scripts/download-pose-model.sh                 # 默认官方源（float16/1 固定版本）
#   POSE_MODEL_URL=https://... bash scripts/download-pose-model.sh   # 国内镜像覆盖
#
# 行为:
#   - 幂等：目标文件已存在且大小 > 1MB 时跳过（打印现有 sha256）
#   - 校验：下载后比对 sha256（EXPECTED_SHA256 固化），失败即删除并报错
#   - 生产以"随镜像打包"为准，本脚本用于本地开发与部署脚本打包前补齐
# ============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${CYAN}[INFO]${NC}  $*"; }
log_ok()   { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error(){ echo -e "${RED}[ERROR]${NC} $*"; }

fail() {
  log_error "$1"
  exit 1
}

# ---------- 路径 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MODEL_NAME="pose_landmarker_lite.task"
TARGET="$SERVER_DIR/models/$MODEL_NAME"

# ---------- 下载源 ----------
# 官方固定版本（可复现）；国内网络可用 POSE_MODEL_URL 指向镜像副本
DEFAULT_URL="https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
POSE_MODEL_URL="${POSE_MODEL_URL:-$DEFAULT_URL}"

# ---------- 校验常量 ----------
# 固化的官方模型 sha256（下载后核对，防止传输损坏/镜像污染）。
EXPECTED_SHA256="59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"
MIN_SIZE_BYTES=$((1 * 1024 * 1024))

# ---------- 幂等：已存在则跳过 ----------
if [ -f "$TARGET" ] && [ "$(stat -c%s "$TARGET" 2>/dev/null || stat -f%z "$TARGET" 2>/dev/null)" -gt "$MIN_SIZE_BYTES" ]; then
  log_info "$MODEL_NAME 已存在，跳过下载：$TARGET"
  log_ok "  现有 sha256: $(sha256sum "$TARGET" | awk '{print $1}')"
  exit 0
fi

# ---------- 下载到临时文件 ----------
mkdir -p "$(dirname "$TARGET")"
TMP_FILE="$(mktemp "${TARGET}.XXXXXX")"
trap 'rm -f "$TMP_FILE"' EXIT

log_info "下载姿态模型: $POSE_MODEL_URL"
if ! curl -fSL --retry 3 --retry-delay 2 -o "$TMP_FILE" "$POSE_MODEL_URL"; then
  fail "下载失败（请检查网络；国内环境可用 POSE_MODEL_URL 指定镜像源）"
fi

# ---------- 校验 ----------
ACTUAL_SIZE=$(stat -c%s "$TMP_FILE" 2>/dev/null || stat -f%z "$TMP_FILE" 2>/dev/null)
ACTUAL_SHA256=$(sha256sum "$TMP_FILE" | awk '{print $1}')

if [ "$ACTUAL_SIZE" -lt "$MIN_SIZE_BYTES" ]; then
  fail "文件异常（大小 ${ACTUAL_SIZE} 字节，预期 > ${MIN_SIZE_BYTES}），已删除"
fi

if [ -n "$EXPECTED_SHA256" ]; then
  if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
    fail "sha256 不匹配（期望 $EXPECTED_SHA256，实际 $ACTUAL_SHA256），已删除"
  fi
  log_ok "sha256 校验通过"
else
  log_warn "EXPECTED_SHA256 未固化，本次仅按大小校验。建议固化：$ACTUAL_SHA256"
fi

# ---------- 落位 ----------
mv "$TMP_FILE" "$TARGET"
trap - EXIT

log_ok "$MODEL_NAME 下载完成（${ACTUAL_SIZE} 字节）"
log_ok "  路径: $TARGET"
log_ok "  sha256: $ACTUAL_SHA256"
