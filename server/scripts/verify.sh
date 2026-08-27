#!/usr/bin/env bash
# 后台验证脚本：ruff 静态检查 + 格式化检查 + pytest 测试
# 用法：
#   uv run verify           # 通过 project 脚本（见 pyproject.toml [tool.uv.scripts]）
#   bash scripts/verify.sh  # 直接运行
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> [1/3] ruff 静态检查"
uv run ruff check .

echo "==> [2/3] ruff 格式化检查"
uv run ruff format --check . || {
    echo "提示：运行 'uv run ruff format .' 可自动格式化"
    exit 1
}

echo "==> [3/3] pytest 测试（testmon 只跑受影响用例 + 并行加速）"
# testmon 基于上次覆盖率仅重跑被改动代码影响的用例（首次/大改会跑全量以重建缓存）；
# 全量并行测试交由 CI（.github/workflows/test-server.yml）执行，与提交门禁解耦。
uv run pytest -v -n auto --testmon

echo ""
echo "✅ 全部验证通过（ruff check + ruff format + pytest）"
