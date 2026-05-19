#!/usr/bin/env bash

set -u -o pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="${1:-}"
PASSWORD="${2:-}"
TS=$(date +%s)

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
  echo "Usage: bash tests/tasks/test_task_steps_creation.sh <email> <password>"
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

SECTION_ID="wsec_01KRP1PGJHRAQ4XYWVA105MP8M"
WORKER_ID="usr_worker_test"
INVALID_SECTION_ID="wsec_does_not_exist_00000000000"

# --- Helper: create a fresh pending task ---
create_task() {
  curl -s -w "\n_STATUS_:%{http_code}" -X PUT "$BASE_URL/api/v1/tasks" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"task_type\":\"return\",\"title\":\"Steps Test ${TS}\"}"
}

# 1) Add step to pending task → step created, task.state = assigned
R=$(create_task)
TASK_ID=$(http_body "$R" | jq -r '.data.client_id')
[ "$(http_status "$R")" = "200" ] && [ -n "$TASK_ID" ] || { fail "create task for step test"; exit 1; }

R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_ID/steps" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"working_section_id\":\"$SECTION_ID\"}")
S=$(http_status "$R")
STEP1_ID=$(http_body "$R" | jq -r '.data.step_id')
if [ "$S" = "200" ] && [ -n "$STEP1_ID" ] && [ "$STEP1_ID" != "null" ]; then
  pass "add step to pending task"
else
  fail "add step to pending task (status=$S body=$(http_body "$R"))"
fi

# Verify task.state transitioned to assigned
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X GET "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN")
TASK_STATE=$(http_body "$R" | jq -r '.data.task.state')
  if [ "$TASK_STATE" = "assigned" ]; then
  pass "task.state = assigned after first step"
else
  fail "task.state = assigned after first step (got=$TASK_STATE)"
fi

# 2) Add second step → task.state still assigned
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_ID/steps" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"working_section_id\":\"$SECTION_ID\",\"sequence_order\":2}")
S=$(http_status "$R")
STEP2_ID=$(http_body "$R" | jq -r '.data.step_id')
if [ "$S" = "200" ] && [ -n "$STEP2_ID" ] && [ "$STEP2_ID" != "null" ]; then
  pass "add second step to assigned task"
else
  fail "add second step to assigned task (status=$S)"
fi

R=$(curl -s -w "\n_STATUS_:%{http_code}" -X GET "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN")
TASK_STATE2=$(http_body "$R" | jq -r '.data.task.state')
if [ "$TASK_STATE2" = "assigned" ]; then
  pass "task.state still assigned after second step"
else
  fail "task.state still assigned after second step (got=$TASK_STATE2)"
fi

# 3) Assign worker to step
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_ID/steps/$STEP1_ID/assign-worker" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"worker_id\":\"$WORKER_ID\"}")
S=$(http_status "$R")
ASSIGN1_ID=$(http_body "$R" | jq -r '.data.assignment_id')
if [ "$S" = "200" ] && [ -n "$ASSIGN1_ID" ] && [ "$ASSIGN1_ID" != "null" ]; then
  pass "assign worker to step"
else
  fail "assign worker to step (status=$S body=$(http_body "$R"))"
fi

# 4) Reassign worker → old assignment closed, new created
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_ID/steps/$STEP1_ID/assign-worker" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"worker_id\":\"$WORKER_ID\"}")
S=$(http_status "$R")
ASSIGN2_ID=$(http_body "$R" | jq -r '.data.assignment_id')
if [ "$S" = "200" ] && [ -n "$ASSIGN2_ID" ] && [ "$ASSIGN2_ID" != "null" ] && [ "$ASSIGN2_ID" != "$ASSIGN1_ID" ]; then
  pass "reassign worker creates new assignment record"
else
  fail "reassign worker creates new assignment record (status=$S assign2=$ASSIGN2_ID assign1=$ASSIGN1_ID)"
fi

# 5) Add step to terminal (resolved) task → 409
R=$(create_task)
TERM_TASK_ID=$(http_body "$R" | jq -r '.data.client_id')
# Resolve the task
curl -s -X POST "$BASE_URL/api/v1/tasks/$TERM_TASK_ID/resolve" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TERM_TASK_ID/steps" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"working_section_id\":\"$SECTION_ID\"}")
S=$(http_status "$R")
if [ "$S" = "409" ]; then
  pass "add step to terminal task blocked (409)"
else
  fail "add step to terminal task blocked (expected 409 got=$S)"
fi

# 6) Add step with invalid working_section_id → 404
R=$(create_task)
NEW_TASK_ID=$(http_body "$R" | jq -r '.data.client_id')
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$NEW_TASK_ID/steps" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"working_section_id\":\"$INVALID_SECTION_ID\"}")
S=$(http_status "$R")
if [ "$S" = "404" ]; then
  pass "add step with invalid section_id returns 404"
else
  fail "add step with invalid section_id returns 404 (got=$S)"
fi

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "ALL TESTS PASSED"
else
  echo "$FAIL TEST(S) FAILED"
  exit 1
fi
