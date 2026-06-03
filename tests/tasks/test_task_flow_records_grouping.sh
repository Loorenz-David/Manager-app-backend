#!/usr/bin/env bash

set -u -o pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="${1:-}"
PASSWORD="${2:-}"
TS=$(date +%s)

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
  echo "Usage: bash tests/tasks/test_task_flow_records_grouping.sh <email> <password>"
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

WORKING_SECTIONS_R=$(curl -s "$BASE_URL/api/v1/working-sections?limit=5" \
  -H "Authorization: Bearer $TOKEN")

mapfile -t SECTION_ROWS < <(echo "$WORKING_SECTIONS_R" | jq -r '.data.working_sections[:5][] | "\(.client_id)\t\(.name)"')
if [ "${#SECTION_ROWS[@]}" -lt 5 ]; then
  echo "FAIL - expected at least 5 working sections, got ${#SECTION_ROWS[@]}"
  exit 1
fi

SECTION_IDS=()
SECTION_NAMES=()
for row in "${SECTION_ROWS[@]}"; do
  SECTION_IDS+=("${row%%$'\t'*}")
  SECTION_NAMES+=("${row#*$'\t'}")
done

STEPS_JSON=$(printf '%s\n' "${SECTION_IDS[@]}" | jq -R '{working_section_id:.}' | jq -s '.')
TASK_PAYLOAD=$(jq -nc \
  --arg title "Grouped Flow Test ${TS}" \
  --argjson steps "$STEPS_JSON" \
  '{task_type:"return", title:$title, steps:$steps}')

CREATE_R=$(curl -s -w "\n_STATUS_:%{http_code}" -X PUT "$BASE_URL/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "$TASK_PAYLOAD")
CREATE_STATUS=$(http_status "$CREATE_R")
TASK_ID=$(http_body "$CREATE_R" | jq -r '.data.client_id')
if [ "$CREATE_STATUS" = "200" ] && [ -n "$TASK_ID" ] && [ "$TASK_ID" != "null" ]; then
  pass "create task with grouped steps"
else
  fail "create task with grouped steps (status=$CREATE_STATUS body=$(http_body "$CREATE_R"))"
  exit 1
fi

FLOW_R=$(curl -s -w "\n_STATUS_:%{http_code}" -X GET "$BASE_URL/api/v1/tasks/$TASK_ID/flow-records" \
  -H "Authorization: Bearer $TOKEN")
FLOW_STATUS=$(http_status "$FLOW_R")
FLOW_BODY=$(http_body "$FLOW_R")

if [ "$FLOW_STATUS" != "200" ]; then
  fail "flow-records request failed (status=$FLOW_STATUS)"
  exit 1
fi

GROUP_COUNT=$(echo "$FLOW_BODY" | jq '[.data.flow_records[] | select(.type == "task_step_group")] | length')
GROUP_DESCRIPTION=$(echo "$FLOW_BODY" | jq -r '.data.flow_records[] | select(.type == "task_step_group") | .description' | head -n 1)

if [ "$GROUP_COUNT" = "1" ]; then
  pass "one grouped flow record returned"
else
  fail "expected exactly one grouped flow record, got $GROUP_COUNT"
fi

if echo "$GROUP_DESCRIPTION" | grep -q "assigned to working sections"; then
  pass "grouped description uses assigned wording"
else
  fail "grouped description missing assigned wording: $GROUP_DESCRIPTION"
fi

for section_name in "${SECTION_NAMES[@]}"; do
  if echo "$GROUP_DESCRIPTION" | grep -q "$section_name"; then
    pass "grouped description includes $section_name"
  else
    fail "grouped description missing section name: $section_name"
  fi
done

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "ALL TESTS PASSED"
else
  echo "$FAIL TEST(S) FAILED"
  exit 1
fi