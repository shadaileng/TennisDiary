#!/usr/bin/env bash
# ============================================================
# 诊断 admin 登录后 /me 401 问题
# 用 curl 手动复现 login → /me，判断是「后端 token 问题」
# 还是「前端/网关传输问题」。
#
# 用法:
#   bash scripts/diag-admin-auth.sh <API_BASE_URL> [用户名] [密码]
#
# 示例:
#   bash scripts/diag-admin-auth.sh https://{owner}-{studio}.ms.show admin 你的密码
#   bash scripts/diag-admin-auth.sh http://localhost:8000 admin admin123
# ============================================================
set -euo pipefail

BASE="${1:-}"
USERNAME="${2:-admin}"
PASSWORD="${3:-changeme}"

[ -n "$BASE" ] || { echo "用法: $0 <API_BASE_URL> [用户名] [密码]"; exit 1; }

echo "==> 1) POST ${BASE}/api/admin/auth/login"
LOGIN=$(curl -s -X POST "${BASE}/api/admin/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}")
echo "    响应: ${LOGIN:0:300}"

TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['access_token'])" 2>/dev/null || true)
if [ -z "$TOKEN" ]; then
  echo "    ❌ 未能从响应中解析出 access_token，请检查登录是否成功/密码是否正确"
  exit 1
fi
echo "    ✅ 成功签发 token: ${TOKEN:0:40}...  (长度 ${#TOKEN})"

echo "==> 2) GET ${BASE}/api/admin/auth/me   (携带 X-Auth-Token)"
HTTP=$(curl -s -o /tmp/_diag_me.json -w "%{http_code}" "${BASE}/api/admin/auth/me" \
  -H "X-Auth-Token: ${TOKEN}")
echo "    状态码: ${HTTP}"
echo "    响应体: $(cat /tmp/_diag_me.json)"
rm -f /tmp/_diag_me.json

echo "==> 3) GET ${BASE}/api/admin/auth/me   (故意不带 header，用于对照)"
HTTP2=$(curl -s -o /tmp/_diag_me2.json -w "%{http_code}" "${BASE}/api/admin/auth/me")
echo "    状态码: ${HTTP2}"
echo "    响应体: $(cat /tmp/_diag_me2.json)"
rm -f /tmp/_diag_me2.json

echo ""
echo "==> 判断依据："
echo "    - 若第2步=200：后端+token 正常，问题在前端/网关传输。"
echo "    - 若第2步=401 且 message='无效的token'：token 被网关篡改/截断，或部署版本不一致。"
echo "    - 若第3步=401（Not authenticated）：符合 FastAPI APIKeyHeader 无 header 行为。"
