#!/usr/bin/env bash

set -u -o pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="${1:-}"
PASSWORD="${2:-}"
TS=$(date +%s)

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
  echo "Usage: bash tests/tasks/test_task_notes.sh <email> <password>"
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

TITLE_NO_NOTES="Task Notes None ${TS}"
TITLE_WITH_NOTES="Task Notes With ${TS}"

# 1) create task without notes
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X PUT "$BASE_URL/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"task_type\":\"return\",\"title\":\"$TITLE_NO_NOTES\"}")
S=$(http_status "$R")
B=$(http_body "$R")
TASK_NO_NOTES=$(echo "$B" | jq -r '.data.client_id')
if [ "$S" = "200" ] && [ "$TASK_NO_NOTES" != "null" ]; then pass "create task without notes"; else fail "create task without notes"; fi

# 2) create task with notes in payload
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X PUT "$BASE_URL/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"task_type\":\"return\",\"title\":\"$TITLE_WITH_NOTES\",\"notes\":[{\"note_type\":\"user_note\",\"content\":{\"text\":\"created inline\"}}]}")
S=$(http_status "$R")
B=$(http_body "$R")
TASK_WITH_NOTES=$(echo "$B" | jq -r '.data.client_id')
if [ "$S" = "200" ] && [ "$TASK_WITH_NOTES" != "null" ]; then pass "create task with notes"; else fail "create task with notes"; fi

R=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/tasks/$TASK_WITH_NOTES" -H "Authorization: Bearer $TOKEN")
S=$(http_status "$R")
B=$(http_body "$R")
NOTE_COUNT=$(echo "$B" | jq -r '.data.task_notes | length')
if [ "$S" = "200" ] && [ "$NOTE_COUNT" -ge 1 ]; then pass "notes appear in task detail"; else fail "notes in task detail"; fi

# 3) create note via route
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/$TASK_WITH_NOTES/notes" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"note_type":"system_note","content":{"text":"created by route"}}')
S=$(http_status "$R")
B=$(http_body "$R")
NOTE_ID=$(echo "$B" | jq -r '.data.client_id')
if [ "$S" = "200" ] && [ "$NOTE_ID" != "null" ]; then pass "create note route"; else fail "create note route"; fi

# 4) patch note
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X PATCH "$BASE_URL/api/v1/tasks/$TASK_WITH_NOTES/notes/$NOTE_ID" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"note_type":"correction_note","content":{"text":"updated"}}')
S=$(http_status "$R")
if [ "$S" = "200" ]; then pass "patch note"; else fail "patch note"; fi

# 5) delete note
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X DELETE "$BASE_URL/api/v1/tasks/$TASK_WITH_NOTES/notes/$NOTE_ID" \
  -H "Authorization: Bearer $TOKEN")
S=$(http_status "$R")
if [ "$S" = "200" ]; then pass "delete note"; else fail "delete note"; fi

R=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/tasks/$TASK_WITH_NOTES" -H "Authorization: Bearer $TOKEN")
S=$(http_status "$R")
B=$(http_body "$R")
IS_DELETED=$(echo "$B" | jq -r ".data.task_notes[] | select(.client_id==\"$NOTE_ID\") | .is_deleted" | head -1)
if [ "$S" = "200" ] && [ "$IS_DELETED" = "true" ]; then pass "deleted note visible as soft-deleted"; else fail "soft-delete visibility"; fi

# 6) patch deleted note -> conflict
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X PATCH "$BASE_URL/api/v1/tasks/$TASK_WITH_NOTES/notes/$NOTE_ID" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"content":{"text":"should fail"}}')
S=$(http_status "$R")
if [ "$S" = "409" ]; then pass "patch deleted note blocked"; else fail "patch deleted note expected 409 got $S"; fi

# 7) create note on non-existent task -> 404
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/tasks/tsk_nonexistent/notes" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"note_type":"user_note","content":{"text":"x"}}')
S=$(http_status "$R")
if [ "$S" = "404" ]; then pass "note on missing task blocked"; else fail "note on missing task expected 404 got $S"; fi

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "Task notes suite finished with FAILURES: $FAIL"
  exit 1
fi

echo ""
echo "Task notes suite finished: ALL PASS"
