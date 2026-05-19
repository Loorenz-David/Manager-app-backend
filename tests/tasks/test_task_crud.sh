#!/usr/bin/env bash

set -u -o pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="${1:-}"
PASSWORD="${2:-}"
TS=$(date +%s)

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
  echo "Usage: bash tests/tasks/test_task_crud.sh <email> <password>"
  exit 1
fi

FAIL=0

pass() { echo "PASS - $1"; }
fail() { echo "FAIL - $1"; FAIL=$((FAIL + 1)); }

http_status() { echo "$1" | grep "_STATUS_:" | cut -d':' -f2; }
http_body() { echo "$1" | sed '/_STATUS_:/d'; }

TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/sign-in" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"app_scope\":\"admin\"}" \
  | jq -r '.data.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "FAIL - sign-in did not return token"
  exit 1
fi

echo "Token: ${#TOKEN} chars"

TASK_TITLE_1="Task CRUD A ${TS}"
TASK_TITLE_2="Task CRUD B ${TS}"
TASK_TITLE_3="Task CRUD C ${TS}"
ART1="ART_TASK_${TS}"
ART2="ART_TASK_${TS}_B"

# 1) create task
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X PUT "$BASE_URL/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"task_type\":\"return\",\"title\":\"$TASK_TITLE_1\"}")
S=$(http_status "$R")
B=$(http_body "$R")
TASK_ID=$(echo "$B" | jq -r '.data.client_id')
TASK_SCALAR_1=$(echo "$B" | jq -r '.data.task_scalar_id')
if [ "$S" = "200" ] && [ "$TASK_ID" != "null" ] && [ "$TASK_SCALAR_1" != "null" ]; then pass "create task returns client_id + task_scalar_id"; else fail "create task"; fi

# 2) create second task and compare scalar id
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X PUT "$BASE_URL/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"task_type\":\"return\",\"title\":\"$TASK_TITLE_2\"}")
S=$(http_status "$R")
B=$(http_body "$R")
TASK_ID_2=$(echo "$B" | jq -r '.data.client_id')
TASK_SCALAR_2=$(echo "$B" | jq -r '.data.task_scalar_id')
if [ "$S" = "200" ] && [ "$TASK_SCALAR_2" != "$TASK_SCALAR_1" ]; then pass "task_scalar_id unique"; else fail "task_scalar_id uniqueness"; fi

# 3) patch partial update
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X PATCH "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"summary":"patched-summary"}')
S=$(http_status "$R")
if [ "$S" = "200" ]; then pass "patch task"; else fail "patch task"; fi

# 4) resolve task
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_ID/resolve" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
S=$(http_status "$R")
if [ "$S" = "200" ]; then pass "resolve task"; else fail "resolve task"; fi

# 5) resolve again should conflict
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_ID/resolve" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
S=$(http_status "$R")
if [ "$S" = "409" ]; then pass "terminal guard conflict"; else fail "terminal guard expected 409 got $S"; fi

# 6) create task for cancel/fail
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X PUT "$BASE_URL/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"task_type\":\"return\",\"title\":\"$TASK_TITLE_3\"}")
S=$(http_status "$R")
B=$(http_body "$R")
TASK_ID_3=$(echo "$B" | jq -r '.data.client_id')
if [ "$S" = "200" ]; then pass "create third task"; else fail "create third task"; fi

R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_ID_3/cancel" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
S=$(http_status "$R")
if [ "$S" = "200" ]; then pass "cancel task"; else fail "cancel task"; fi

# 7) create item and attach to task2
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/items/find-or-create" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"article_number\":\"$ART1\"}")
S=$(http_status "$R")
B=$(http_body "$R")
ITEM1=$(echo "$B" | jq -r '.data.client_id')
if [ "$S" = "200" ] && [ "$ITEM1" != "null" ]; then pass "create/find item1"; else fail "create/find item1"; fi

R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_ID_2/items" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"item_id\":\"$ITEM1\",\"role\":\"primary\"}")
S=$(http_status "$R")
if [ "$S" = "200" ]; then pass "add primary item"; else fail "add primary item"; fi

R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/items/find-or-create" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"article_number\":\"$ART2\"}")
S=$(http_status "$R")
B=$(http_body "$R")
ITEM2=$(echo "$B" | jq -r '.data.client_id')
if [ "$S" = "200" ] && [ "$ITEM2" != "null" ]; then pass "create/find item2"; else fail "create/find item2"; fi

R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_ID_2/items" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"item_id\":\"$ITEM2\",\"role\":\"primary\"}")
S=$(http_status "$R")
if [ "$S" = "409" ]; then pass "second primary blocked"; else fail "second primary expected 409 got $S"; fi

R=$(curl -s -w "\n_STATUS_:%{http_code}" -X DELETE "$BASE_URL/api/v1/tasks/$TASK_ID_2/items/$ITEM1" \
  -H "Authorization: Bearer $TOKEN")
S=$(http_status "$R")
if [ "$S" = "200" ]; then pass "remove task item"; else fail "remove task item"; fi

# 8) list query filter and detail
R=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/tasks?limit=20&offset=0&q=Task%20CRUD" \
  -H "Authorization: Bearer $TOKEN")
S=$(http_status "$R")
if [ "$S" = "200" ]; then pass "list tasks query"; else fail "list tasks query"; fi

R=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/tasks/$TASK_ID_2" \
  -H "Authorization: Bearer $TOKEN")
S=$(http_status "$R")
if [ "$S" = "200" ]; then pass "get task detail"; else fail "get task detail"; fi

# 9) delete and verify not found
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X DELETE "$BASE_URL/api/v1/tasks/$TASK_ID_2" \
  -H "Authorization: Bearer $TOKEN")
S=$(http_status "$R")
if [ "$S" = "200" ]; then pass "delete task"; else fail "delete task"; fi

R=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/tasks/$TASK_ID_2" \
  -H "Authorization: Bearer $TOKEN")
S=$(http_status "$R")
if [ "$S" = "404" ]; then pass "deleted task hidden"; else fail "deleted task expected 404 got $S"; fi

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "Task CRUD suite finished with FAILURES: $FAIL"
  exit 1
fi

echo ""
echo "Task CRUD suite finished: ALL PASS"
