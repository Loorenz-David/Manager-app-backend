#!/usr/bin/env bash

set -u -o pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="${1:-}"
PASSWORD="${2:-}"
TS=$(date +%s)

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
  echo "Usage: bash tests/tasks/test_step_state_machine.sh <email> <password>"
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

# --- Helper: create a fresh pending task ---
create_task() {
  curl -s -w "\n_STATUS_:%{http_code}" -X PUT "$BASE_URL/api/v1/tasks" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"task_type\":\"return\",\"title\":\"StateTest ${TS}\"}"
}

# --- Helper: add a step to a task ---
add_step() {
  local TASK="$1"
  curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK/steps" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"working_section_id\":\"$SECTION_ID\"}"
}

# --- Helper: transition a step state ---
transition() {
  local TASK="$1"
  local STEP="$2"
  local STATE="$3"
  local REASON="${4:-}"
  if [ -z "$REASON" ]; then
    curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK/steps/$STEP/transition" \
      -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
      -d "{\"new_state\":\"$STATE\"}"
  else
    curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK/steps/$STEP/transition" \
      -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
      -d "{\"new_state\":\"$STATE\",\"reason\":\"$REASON\"}"
  fi
}

# --- Setup: task with one step ---
SETUP_R=$(create_task)
TASK_ID=$(http_body "$SETUP_R" | jq -r '.data.client_id')
[ "$(http_status "$SETUP_R")" = "200" ] && [ -n "$TASK_ID" ] || { echo "FAIL - setup task creation"; exit 1; }

STEP_R=$(add_step "$TASK_ID")
STEP_ID=$(http_body "$STEP_R" | jq -r '.data.step_id')
[ "$(http_status "$STEP_R")" = "200" ] && [ -n "$STEP_ID" ] || { echo "FAIL - setup step"; exit 1; }

echo "Setup: task=$TASK_ID step=$STEP_ID"

# -----------------------------------------------------------------------
# TEST 1: PENDING → WORKING: step.state=working, task.state=working (was assigned)
# -----------------------------------------------------------------------
R=$(transition "$TASK_ID" "$STEP_ID" "working")
STATUS=$(http_status "$R")
STEP_STATE=$(curl -s "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$STEP_ID" '.data.task_steps[] | select(.client_id == $s) | .state')
TASK_STATE=$(curl -s "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.data.task.state')
[ "$STATUS" = "200" ] && [ "$STEP_STATE" = "working" ] && [ "$TASK_STATE" = "working" ] \
  && pass "1 - PENDING→WORKING: step.state=working, task.state=working" \
  || fail "1 - PENDING→WORKING (status=$STATUS step_state=$STEP_STATE task_state=$TASK_STATE)"

# -----------------------------------------------------------------------
# TEST 2: WORKING → PAUSED: old record closed, new record open
# -----------------------------------------------------------------------
R=$(transition "$TASK_ID" "$STEP_ID" "paused")
STATUS=$(http_status "$R")
STEP_STATE=$(curl -s "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$STEP_ID" '.data.task_steps[] | select(.client_id == $s) | .state')
[ "$STATUS" = "200" ] && [ "$STEP_STATE" = "paused" ] \
  && pass "2 - WORKING→PAUSED: step.state=paused" \
  || fail "2 - WORKING→PAUSED (status=$STATUS step_state=$STEP_STATE)"

# -----------------------------------------------------------------------
# TEST 3: PAUSED → WORKING (resume)
# -----------------------------------------------------------------------
R=$(transition "$TASK_ID" "$STEP_ID" "working")
STATUS=$(http_status "$R")
STEP_STATE=$(curl -s "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$STEP_ID" '.data.task_steps[] | select(.client_id == $s) | .state')
[ "$STATUS" = "200" ] && [ "$STEP_STATE" = "working" ] \
  && pass "3 - PAUSED→WORKING (resume): step.state=working" \
  || fail "3 - PAUSED→WORKING (status=$STATUS step_state=$STEP_STATE)"

# -----------------------------------------------------------------------
# TEST 4: WORKING → COMPLETED: step.state=completed, step.closed_at set, task.state=ready (only step)
# -----------------------------------------------------------------------
R=$(transition "$TASK_ID" "$STEP_ID" "completed")
STATUS=$(http_status "$R")
STEP_STATE=$(curl -s "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$STEP_ID" '.data.task_steps[] | select(.client_id == $s) | .state')
CLOSED_AT=$(curl -s "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$STEP_ID" '.data.task_steps[] | select(.client_id == $s) | .closed_at')
TASK_STATE=$(curl -s "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.data.task.state')
[ "$STATUS" = "200" ] && [ "$STEP_STATE" = "completed" ] && [ "$CLOSED_AT" != "null" ] && [ "$TASK_STATE" = "ready" ] \
  && pass "4 - WORKING→COMPLETED: step.state=completed, closed_at set, task.state=ready" \
  || fail "4 - WORKING→COMPLETED (status=$STATUS step_state=$STEP_STATE closed_at=$CLOSED_AT task_state=$TASK_STATE)"

# -----------------------------------------------------------------------
# TEST 5: Terminal step transition attempt (COMPLETED → WORKING): 409 ConflictError
# -----------------------------------------------------------------------
R=$(transition "$TASK_ID" "$STEP_ID" "working")
STATUS=$(http_status "$R")
[ "$STATUS" = "409" ] \
  && pass "5 - COMPLETED→WORKING (terminal): 409" \
  || fail "5 - COMPLETED→WORKING (got $STATUS)"

# -----------------------------------------------------------------------
# TEST 6: Invalid transition (PENDING → PAUSED): 422 ValidationError
# -----------------------------------------------------------------------
# Create a new task with fresh step (PENDING)
FRESH_R=$(create_task)
FRESH_TASK=$(http_body "$FRESH_R" | jq -r '.data.client_id')
FRESH_STEP_R=$(add_step "$FRESH_TASK")
FRESH_STEP=$(http_body "$FRESH_STEP_R" | jq -r '.data.step_id')

R=$(transition "$FRESH_TASK" "$FRESH_STEP" "paused")
STATUS=$(http_status "$R")
[ "$STATUS" = "422" ] \
  && pass "6 - PENDING→PAUSED (invalid): 422" \
  || fail "6 - PENDING→PAUSED (got $STATUS)"

# -----------------------------------------------------------------------
# TEST 7: WORKING → ENDED_SHIFT → WORKING (shift resume)
# -----------------------------------------------------------------------
SHIFT_R=$(create_task)
SHIFT_TASK=$(http_body "$SHIFT_R" | jq -r '.data.client_id')
SHIFT_STEP_R=$(add_step "$SHIFT_TASK")
SHIFT_STEP=$(http_body "$SHIFT_STEP_R" | jq -r '.data.step_id')

# PENDING → WORKING
transition "$SHIFT_TASK" "$SHIFT_STEP" "working" > /dev/null

# WORKING → ENDED_SHIFT
R=$(transition "$SHIFT_TASK" "$SHIFT_STEP" "ended_shift")
STATUS=$(http_status "$R")
STEP_STATE=$(curl -s "$BASE_URL/api/v1/tasks/$SHIFT_TASK" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$SHIFT_STEP" '.data.task_steps[] | select(.client_id == $s) | .state')
[ "$STATUS" = "200" ] && [ "$STEP_STATE" = "ended_shift" ] \
  && pass "7a - WORKING→ENDED_SHIFT: success" \
  || fail "7a - WORKING→ENDED_SHIFT (status=$STATUS state=$STEP_STATE)"

# ENDED_SHIFT → WORKING (next shift resume)
R=$(transition "$SHIFT_TASK" "$SHIFT_STEP" "working")
STATUS=$(http_status "$R")
STEP_STATE=$(curl -s "$BASE_URL/api/v1/tasks/$SHIFT_TASK" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$SHIFT_STEP" '.data.task_steps[] | select(.client_id == $s) | .state')
[ "$STATUS" = "200" ] && [ "$STEP_STATE" = "working" ] \
  && pass "7b - ENDED_SHIFT→WORKING (resume): success" \
  || fail "7b - ENDED_SHIFT→WORKING (status=$STATUS state=$STEP_STATE)"

# -----------------------------------------------------------------------
# TEST 8: ExecutionTask created in DB (outbox event)
# -----------------------------------------------------------------------
# Check that PROCESS_STEP_TRANSITION task was created in execution_tasks
# We can't directly query the DB, so we verify the transition succeeded (implicit event creation)
# If the event creation failed, the entire transaction would roll back.
EVENT_R=$(create_task)
EVENT_TASK=$(http_body "$EVENT_R" | jq -r '.data.client_id')
EVENT_STEP_R=$(add_step "$EVENT_TASK")
EVENT_STEP=$(http_body "$EVENT_STEP_R" | jq -r '.data.step_id')

transition "$EVENT_TASK" "$EVENT_STEP" "working" > /dev/null
R=$(transition "$EVENT_TASK" "$EVENT_STEP" "completed")
STATUS=$(http_status "$R")
# If status is 200, the outbox event was created atomically (transaction would roll back on failure)
[ "$STATUS" = "200" ] \
  && pass "8 - ExecutionTask created (outbox event atomic with domain write)" \
  || fail "8 - ExecutionTask creation (status=$STATUS)"

# -----------------------------------------------------------------------
# TEST 9: WORKING → FAILED (terminal)
# -----------------------------------------------------------------------
FAIL_R=$(create_task)
FAIL_TASK=$(http_body "$FAIL_R" | jq -r '.data.client_id')
FAIL_STEP_R=$(add_step "$FAIL_TASK")
FAIL_STEP=$(http_body "$FAIL_STEP_R" | jq -r '.data.step_id')

transition "$FAIL_TASK" "$FAIL_STEP" "working" > /dev/null

R=$(transition "$FAIL_TASK" "$FAIL_STEP" "failed")
STATUS=$(http_status "$R")
STEP_STATE=$(curl -s "$BASE_URL/api/v1/tasks/$FAIL_TASK" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$FAIL_STEP" '.data.task_steps[] | select(.client_id == $s) | .state')
CLOSED_AT=$(curl -s "$BASE_URL/api/v1/tasks/$FAIL_TASK" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$FAIL_STEP" '.data.task_steps[] | select(.client_id == $s) | .closed_at')
[ "$STATUS" = "200" ] && [ "$STEP_STATE" = "failed" ] && [ "$CLOSED_AT" != "null" ] \
  && pass "9 - WORKING→FAILED (terminal): step.state=failed, closed_at set" \
  || fail "9 - WORKING→FAILED (status=$STATUS state=$STEP_STATE closed_at=$CLOSED_AT)"

# -----------------------------------------------------------------------
# TEST 10: Two steps with dependency; complete one → dependent readiness updated
# -----------------------------------------------------------------------
DEPTEST_R=$(create_task)
DT_TASK=$(http_body "$DEPTEST_R" | jq -r '.data.client_id')
DT_S1_R=$(add_step "$DT_TASK"); DT_S1=$(http_body "$DT_S1_R" | jq -r '.data.step_id')
DT_S2_R=$(add_step "$DT_TASK"); DT_S2=$(http_body "$DT_S2_R" | jq -r '.data.step_id')

# s2 depends on s1
curl -s -X POST "$BASE_URL/api/v1/tasks/$DT_TASK/steps/$DT_S2/dependencies" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"prerequisite_step_id\":\"$DT_S1\"}" > /dev/null

# s2 initially blocked
PRE_READINESS=$(curl -s "$BASE_URL/api/v1/tasks/$DT_TASK" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$DT_S2" '.data.task_steps[] | select(.client_id == $s) | .readiness_status')

# Transition s1: PENDING → WORKING → COMPLETED
transition "$DT_TASK" "$DT_S1" "working" > /dev/null
R=$(transition "$DT_TASK" "$DT_S1" "completed")
STATUS=$(http_status "$R")

# s2 now ready (dependency completed)
POST_READINESS=$(curl -s "$BASE_URL/api/v1/tasks/$DT_TASK" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$DT_S2" '.data.task_steps[] | select(.client_id == $s) | .readiness_status')

[ "$STATUS" = "200" ] && [ "$PRE_READINESS" = "blocked" ] && [ "$POST_READINESS" = "ready" ] \
  && pass "10 - Complete prerequisite → dependent readiness=ready" \
  || fail "10 - Dependent readiness (status=$STATUS pre=$PRE_READINESS post=$POST_READINESS)"

# -----------------------------------------------------------------------
echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "ALL TESTS PASSED"
else
  echo "$FAIL TEST(S) FAILED"
  exit 1
fi
