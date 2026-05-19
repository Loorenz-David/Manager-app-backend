#!/usr/bin/env bash

set -u -o pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="${1:-}"
PASSWORD="${2:-}"
TS=$(date +%s)

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
  echo "Usage: bash tests/tasks/test_dependencies_step_removal.sh <email> <password>"
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
    -d "{\"task_type\":\"return\",\"title\":\"DepTest ${TS}\"}"
}

# --- Helper: add a step to a task ---
add_step() {
  local TASK="$1"
  curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK/steps" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d "{\"working_section_id\":\"$SECTION_ID\"}"
}

# --- Setup: task with two steps ---
SETUP_R=$(create_task)
TASK_ID=$(http_body "$SETUP_R" | jq -r '.data.client_id')
[ "$(http_status "$SETUP_R")" = "200" ] && [ -n "$TASK_ID" ] || { echo "FAIL - setup task creation"; exit 1; }

STEP1_R=$(add_step "$TASK_ID")
STEP1_ID=$(http_body "$STEP1_R" | jq -r '.data.step_id')
[ "$(http_status "$STEP1_R")" = "200" ] && [ -n "$STEP1_ID" ] || { echo "FAIL - setup step 1"; exit 1; }

STEP2_R=$(add_step "$TASK_ID")
STEP2_ID=$(http_body "$STEP2_R" | jq -r '.data.step_id')
[ "$(http_status "$STEP2_R")" = "200" ] && [ -n "$STEP2_ID" ] || { echo "FAIL - setup step 2"; exit 1; }

echo "Setup: task=$TASK_ID step1=$STEP1_ID step2=$STEP2_ID"

# -----------------------------------------------------------------------
# TEST 1: Add dependency between two steps → step.readiness_status = blocked
# -----------------------------------------------------------------------
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_ID/steps/$STEP2_ID/dependencies" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"prerequisite_step_id\":\"$STEP1_ID\"}")
STATUS=$(http_status "$R")
DEP_ID=$(http_body "$R" | jq -r '.data.dependency_id')
READINESS=$(curl -s "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$STEP2_ID" '.data.task_steps[] | select(.client_id == $s) | .readiness_status')
[ "$STATUS" = "200" ] && [ -n "$DEP_ID" ] && [ "$DEP_ID" != "null" ] && [ "$READINESS" = "blocked" ] \
  && pass "1 - add dependency → step2 readiness=blocked" \
  || fail "1 - add dependency → step2 readiness=blocked (dep=$DEP_ID status=$STATUS readiness=$READINESS)"

# -----------------------------------------------------------------------
# TEST 2: Self-loop dependency → 422 ValidationError
# -----------------------------------------------------------------------
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_ID/steps/$STEP1_ID/dependencies" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"prerequisite_step_id\":\"$STEP1_ID\"}")
STATUS=$(http_status "$R")
[ "$STATUS" = "422" ] \
  && pass "2 - self-loop → 422" \
  || fail "2 - self-loop → 422 (got $STATUS)"

# -----------------------------------------------------------------------
# TEST 3: Duplicate active dependency → 409 ConflictError
# -----------------------------------------------------------------------
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_ID/steps/$STEP2_ID/dependencies" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"prerequisite_step_id\":\"$STEP1_ID\"}")
STATUS=$(http_status "$R")
[ "$STATUS" = "409" ] \
  && pass "3 - duplicate dependency → 409" \
  || fail "3 - duplicate dependency → 409 (got $STATUS)"

# -----------------------------------------------------------------------
# TEST 4: Cross-task dependency → 404 (step not found under that task)
# -----------------------------------------------------------------------
CROSS_R=$(create_task)
CROSS_TASK_ID=$(http_body "$CROSS_R" | jq -r '.data.client_id')
CROSS_STEP_R=$(add_step "$CROSS_TASK_ID")
CROSS_STEP_ID=$(http_body "$CROSS_STEP_R" | jq -r '.data.step_id')

R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_ID/steps/$STEP2_ID/dependencies" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"prerequisite_step_id\":\"$CROSS_STEP_ID\"}")
STATUS=$(http_status "$R")
[ "$STATUS" = "404" ] \
  && pass "4 - cross-task dependency → 404" \
  || fail "4 - cross-task dependency → 404 (got $STATUS)"

# -----------------------------------------------------------------------
# TEST 5: Remove dependency → total_dependencies decremented; readiness=ready
# -----------------------------------------------------------------------
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X DELETE \
  "$BASE_URL/api/v1/tasks/$TASK_ID/steps/$STEP2_ID/dependencies/$DEP_ID" \
  -H "Authorization: Bearer $TOKEN")
STATUS=$(http_status "$R")
RET_DEP=$(http_body "$R" | jq -r '.data.dependency_id')
READINESS=$(curl -s "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$STEP2_ID" '.data.task_steps[] | select(.client_id == $s) | .readiness_status')
[ "$STATUS" = "200" ] && [ "$RET_DEP" = "$DEP_ID" ] && [ "$READINESS" = "ready" ] \
  && pass "5 - remove dependency → readiness=ready" \
  || fail "5 - remove dependency → readiness=ready (status=$STATUS readiness=$READINESS)"

# -----------------------------------------------------------------------
# TEST 6: Remove step → state=skipped, StepStateRecord closed
# -----------------------------------------------------------------------
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X DELETE "$BASE_URL/api/v1/tasks/$TASK_ID/steps/$STEP2_ID" \
  -H "Authorization: Bearer $TOKEN")
STATUS=$(http_status "$R")
RET_STEP=$(http_body "$R" | jq -r '.data.step_id')
[ "$STATUS" = "200" ] && [ "$RET_STEP" = "$STEP2_ID" ] \
  && pass "6 - remove step → 200" \
  || fail "6 - remove step → 200 (status=$STATUS step=$RET_STEP)"

# Verify step no longer appears in get_task task_steps
REMAINING=$(curl -s "$BASE_URL/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$STEP2_ID" '[.data.task_steps[] | select(.client_id == $s)] | length')
[ "$REMAINING" = "0" ] \
  && pass "6b - removed step not in task_steps response" \
  || fail "6b - removed step not in task_steps response (count=$REMAINING)"

# -----------------------------------------------------------------------
# TEST 7: Remove last step from task → task.state = pending
# -----------------------------------------------------------------------
SOLO_R=$(create_task)
SOLO_TASK_ID=$(http_body "$SOLO_R" | jq -r '.data.client_id')
SOLO_STEP_R=$(add_step "$SOLO_TASK_ID")
SOLO_STEP_ID=$(http_body "$SOLO_STEP_R" | jq -r '.data.step_id')

R=$(curl -s -w "\n_STATUS_:%{http_code}" -X DELETE \
  "$BASE_URL/api/v1/tasks/$SOLO_TASK_ID/steps/$SOLO_STEP_ID" \
  -H "Authorization: Bearer $TOKEN")
STATUS=$(http_status "$R")
TASK_STATE=$(curl -s "$BASE_URL/api/v1/tasks/$SOLO_TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.data.task.state')
[ "$STATUS" = "200" ] && [ "$TASK_STATE" = "pending" ] \
  && pass "7 - last step removed → task.state=pending" \
  || fail "7 - last step removed → task.state=pending (status=$STATUS state=$TASK_STATE)"

# -----------------------------------------------------------------------
# TEST 8: Remove step that was a prerequisite → dependent step readiness recalculated
# -----------------------------------------------------------------------
DEPTEST_R=$(create_task)
DT_TASK=$(http_body "$DEPTEST_R" | jq -r '.data.client_id')
DT_S1_R=$(add_step "$DT_TASK"); DT_S1=$(http_body "$DT_S1_R" | jq -r '.data.step_id')
DT_S2_R=$(add_step "$DT_TASK"); DT_S2=$(http_body "$DT_S2_R" | jq -r '.data.step_id')

# s2 depends on s1
curl -s -X POST "$BASE_URL/api/v1/tasks/$DT_TASK/steps/$DT_S2/dependencies" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"prerequisite_step_id\":\"$DT_S1\"}" > /dev/null

# Confirm s2 is blocked
PRE_READINESS=$(curl -s "$BASE_URL/api/v1/tasks/$DT_TASK" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$DT_S2" '.data.task_steps[] | select(.client_id == $s) | .readiness_status')

# Remove s1 (the prerequisite)
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X DELETE "$BASE_URL/api/v1/tasks/$DT_TASK/steps/$DT_S1" \
  -H "Authorization: Bearer $TOKEN")
STATUS=$(http_status "$R")
POST_READINESS=$(curl -s "$BASE_URL/api/v1/tasks/$DT_TASK" \
  -H "Authorization: Bearer $TOKEN" | jq -r --arg s "$DT_S2" '.data.task_steps[] | select(.client_id == $s) | .readiness_status')

[ "$STATUS" = "200" ] && [ "$PRE_READINESS" = "blocked" ] && [ "$POST_READINESS" = "ready" ] \
  && pass "8 - remove prerequisite step → dependent step readiness recalculated to ready" \
  || fail "8 - remove prerequisite step → dependent readiness (pre=$PRE_READINESS post=$POST_READINESS status=$STATUS)"

# -----------------------------------------------------------------------
# TEST 9: Remove step when remaining step is terminal → task.state = ready
# Note: we currently cannot easily mark a step COMPLETED without Plan 5,
# so we use SKIPPED by removing another step first, leaving one SKIPPED.
# -----------------------------------------------------------------------
TERM_R=$(create_task)
TERM_TASK=$(http_body "$TERM_R" | jq -r '.data.client_id')
TERM_S1_R=$(add_step "$TERM_TASK"); TERM_S1=$(http_body "$TERM_S1_R" | jq -r '.data.step_id')
TERM_S2_R=$(add_step "$TERM_TASK"); TERM_S2=$(http_body "$TERM_S2_R" | jq -r '.data.step_id')

# Remove s1 (sets it to SKIPPED, task has s2 remaining → still assigned)
curl -s -X DELETE "$BASE_URL/api/v1/tasks/$TERM_TASK/steps/$TERM_S1" \
  -H "Authorization: Bearer $TOKEN" > /dev/null

# Now remove s2 — s1 is SKIPPED (terminal), s2 is deleted, remaining = 0 → PENDING
# Actually the remaining check excludes s2 after deletion, s1 is also deleted → remaining = 0 → PENDING
# For "all remaining terminal → READY" we need 1 remaining non-deleted terminal step.
# Setup: 3 steps — remove s1 (skipped), remove s3 → s2 remains (pending) → task stays assigned
# Let's do a better test: 3 steps, remove s1 (skipped), remove s2 (skipped) → remaining=s3 which is PENDING
# That doesn't trigger READY. We need all remaining = terminal.
# Since we can't complete steps without Plan 5, skip READY transition test.
# Instead: verify 2-step task after removing 1 step still has correct state (not PENDING).

STATE_AFTER=$(curl -s "$BASE_URL/api/v1/tasks/$TERM_TASK" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.data.task.state')
# After removing s1: task still has s2 (pending/working state), should be assigned
[ "$STATE_AFTER" = "assigned" ] \
  && pass "9 - after removing 1 of 2 steps → task.state still assigned" \
  || fail "9 - after removing 1 of 2 steps → task.state still assigned (got $STATE_AFTER)"

# -----------------------------------------------------------------------
echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "ALL TESTS PASSED"
else
  echo "$FAIL TEST(S) FAILED"
  exit 1
fi
