#!/bin/bash
# =============================================================================
# TEST: User View Records Flow
# Purpose : Validate HTTP endpoints for view-record interactions (self + admin)
# Run from: <project>/backend/
# Usage   : bash tests/users/test_user_view_records.sh <email> <password>
# Example : bash tests/users/test_user_view_records.sh user_test@test.local Test1234!
# =============================================================================
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
TIMESTAMP=$(date +%s)

if [ $# -lt 2 ]; then
  echo "Usage: $0 <email> <password>"
  echo "Example: $0 user_test@test.local Test1234!"
  exit 1
fi

EMAIL="$1"
PASSWORD="$2"

START_ENTITY_ID="case_test_${TIMESTAMP}"
STARTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
ENDED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")


wait_for_history_entity() {
  local entity_id="$1"
  local attempts="${2:-20}"

  for ((i=1; i<=attempts; i++)); do
    local resp status body
    resp=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/users/me/view-records?limit=100&offset=0" \
      -H "Authorization: Bearer $TOKEN")
    status=$(echo "$resp" | grep "_STATUS_:" | cut -d':' -f2)
    body=$(echo "$resp" | sed '/_STATUS_:/d')

    if [ "$status" = "200" ] && echo "$body" | jq -e --arg eid "$entity_id" '.data.view_records | map(select(.entity_client_id == $eid)) | length > 0' >/dev/null; then
      echo "$body"
      return 0
    fi

    sleep 1
  done

  return 1
}

echo "════════════════════════════════════════════════════════════════"
echo "TEST: User View Records Flow (run: $TIMESTAMP)"
echo "════════════════════════════════════════════════════════════════"
echo ""

echo "Step 1: Sign in as admin"
SIGNIN_RESP=$(curl -s -X POST "$BASE_URL/api/v1/auth/sign-in" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"app_scope\":\"admin\"}")

TOKEN=$(echo "$SIGNIN_RESP" | jq -r '.data.access_token' 2>/dev/null)
if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "❌ Failed to authenticate"
  echo "$SIGNIN_RESP" | jq .
  exit 1
fi
echo "✅ Authenticated"
echo ""

echo "Step 2: Get self user ID"
ME_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/users/me" \
  -H "Authorization: Bearer $TOKEN")
ME_STATUS=$(echo "$ME_RESP" | grep "_STATUS_:" | cut -d':' -f2)
ME_BODY=$(echo "$ME_RESP" | sed '/_STATUS_:/d')
if [ "$ME_STATUS" != "200" ]; then
  echo "❌ GET /users/me failed (HTTP $ME_STATUS)"
  echo "$ME_BODY" | jq .
  exit 1
fi
SELF_USER_ID=$(echo "$ME_BODY" | jq -r '.data.user.client_id')
echo "✅ Self user: $SELF_USER_ID"
echo ""

echo "Step 3: POST START view event"
START_PAYLOAD=$(jq -n --arg entity_id "$START_ENTITY_ID" --arg started_at "$STARTED_AT" '{records:[{entity_type:"case",entity_client_id:$entity_id,started_at:$started_at}]}')
START_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/users/me/view-records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$START_PAYLOAD")
START_STATUS=$(echo "$START_RESP" | grep "_STATUS_:" | cut -d':' -f2)
START_BODY=$(echo "$START_RESP" | sed '/_STATUS_:/d')
if [ "$START_STATUS" != "200" ]; then
  echo "❌ POST /me/view-records START failed (HTTP $START_STATUS)"
  echo "$START_BODY" | jq .
  exit 1
fi
echo "✅ START event accepted"
echo ""

echo "Step 4: GET current view (should match START entity)"
CURRENT_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/users/me/view-records/current" \
  -H "Authorization: Bearer $TOKEN")
CURRENT_STATUS=$(echo "$CURRENT_RESP" | grep "_STATUS_:" | cut -d':' -f2)
CURRENT_BODY=$(echo "$CURRENT_RESP" | sed '/_STATUS_:/d')
if [ "$CURRENT_STATUS" != "200" ]; then
  echo "❌ GET /me/view-records/current failed (HTTP $CURRENT_STATUS)"
  echo "$CURRENT_BODY" | jq .
  exit 1
fi
CUR_ENTITY_TYPE=$(echo "$CURRENT_BODY" | jq -r '.data.current_view.entity_type // empty')
CUR_ENTITY_ID=$(echo "$CURRENT_BODY" | jq -r '.data.current_view.entity_client_id // empty')
if [ "$CUR_ENTITY_TYPE" != "case" ] || [ "$CUR_ENTITY_ID" != "$START_ENTITY_ID" ]; then
  echo "❌ Current view mismatch"
  echo "$CURRENT_BODY" | jq .
  exit 1
fi
echo "✅ Current view is set"
echo ""

echo "Step 5: POST completed event for same entity (START + END in one record)"
COMPLETE_PAYLOAD=$(jq -n --arg entity_id "$START_ENTITY_ID" --arg started_at "$STARTED_AT" --arg ended_at "$ENDED_AT" '{records:[{entity_type:"case",entity_client_id:$entity_id,started_at:$started_at,ended_at:$ended_at}]}')
COMPLETE_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/users/me/view-records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$COMPLETE_PAYLOAD")
COMPLETE_STATUS=$(echo "$COMPLETE_RESP" | grep "_STATUS_:" | cut -d':' -f2)
COMPLETE_BODY=$(echo "$COMPLETE_RESP" | sed '/_STATUS_:/d')
if [ "$COMPLETE_STATUS" != "200" ]; then
  echo "❌ POST /me/view-records completed event failed (HTTP $COMPLETE_STATUS)"
  echo "$COMPLETE_BODY" | jq .
  exit 1
fi
echo "✅ Completed event accepted"
echo ""

echo "Step 6: GET current view (should be null after matching END)"
CURRENT2_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/users/me/view-records/current" \
  -H "Authorization: Bearer $TOKEN")
CURRENT2_STATUS=$(echo "$CURRENT2_RESP" | grep "_STATUS_:" | cut -d':' -f2)
CURRENT2_BODY=$(echo "$CURRENT2_RESP" | sed '/_STATUS_:/d')
if [ "$CURRENT2_STATUS" != "200" ]; then
  echo "❌ GET /me/view-records/current (2) failed (HTTP $CURRENT2_STATUS)"
  echo "$CURRENT2_BODY" | jq .
  exit 1
fi
CUR2_IS_NULL=$(echo "$CURRENT2_BODY" | jq -r '.data.current_view == null')
if [ "$CUR2_IS_NULL" != "true" ]; then
  echo "❌ Expected current_view to be null"
  echo "$CURRENT2_BODY" | jq .
  exit 1
fi
echo "✅ Current view cleared"
echo ""

echo "Step 7: GET self view-record history (pagination shape)"
HISTORY_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/users/me/view-records?limit=100&offset=0" \
  -H "Authorization: Bearer $TOKEN")
HISTORY_STATUS=$(echo "$HISTORY_RESP" | grep "_STATUS_:" | cut -d':' -f2)
HISTORY_BODY=$(echo "$HISTORY_RESP" | sed '/_STATUS_:/d')
if [ "$HISTORY_STATUS" != "200" ]; then
  echo "❌ GET /me/view-records failed (HTTP $HISTORY_STATUS)"
  echo "$HISTORY_BODY" | jq .
  exit 1
fi
if ! echo "$HISTORY_BODY" | jq -e '.data.view_records_pagination.has_more != null and .data.view_records_pagination.limit != null and .data.view_records_pagination.offset != null' >/dev/null; then
  echo "❌ Pagination object missing required fields"
  echo "$HISTORY_BODY" | jq .
  exit 1
fi

# Ensure background processing actually happened (task-router + presence worker)
if ! HISTORY_BODY=$(wait_for_history_entity "$START_ENTITY_ID" 20); then
  echo "❌ View record for entity '$START_ENTITY_ID' was not persisted within timeout"
  echo "   Check that task-router and presence worker are running"
  exit 1
fi
echo "✅ Self history pagination shape is valid and entity was persisted"
echo ""

echo "Step 8: Admin GET /users/{user_id}/view-records for active member"
ADMIN_HISTORY_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/users/$SELF_USER_ID/view-records?limit=10&offset=0" \
  -H "Authorization: Bearer $TOKEN")
ADMIN_HISTORY_STATUS=$(echo "$ADMIN_HISTORY_RESP" | grep "_STATUS_:" | cut -d':' -f2)
ADMIN_HISTORY_BODY=$(echo "$ADMIN_HISTORY_RESP" | sed '/_STATUS_:/d')
if [ "$ADMIN_HISTORY_STATUS" != "200" ]; then
  echo "❌ GET /users/{user_id}/view-records failed (HTTP $ADMIN_HISTORY_STATUS)"
  echo "$ADMIN_HISTORY_BODY" | jq .
  exit 1
fi
if ! echo "$ADMIN_HISTORY_BODY" | jq -e --arg eid "$START_ENTITY_ID" '.data.view_records | map(select(.entity_client_id == $eid)) | length > 0' >/dev/null; then
  echo "❌ Admin history does not contain expected entity '$START_ENTITY_ID'"
  echo "$ADMIN_HISTORY_BODY" | jq .
  exit 1
fi
echo "✅ Admin per-user history works"
echo ""

echo "Step 9: Admin GET /users/{user_id}/view-records for unknown member -> 404"
UNKNOWN_ID="usr_not_in_workspace_${TIMESTAMP}"
UNKNOWN_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/users/$UNKNOWN_ID/view-records?limit=10&offset=0" \
  -H "Authorization: Bearer $TOKEN")
UNKNOWN_STATUS=$(echo "$UNKNOWN_RESP" | grep "_STATUS_:" | cut -d':' -f2)
UNKNOWN_BODY=$(echo "$UNKNOWN_RESP" | sed '/_STATUS_:/d')
if [ "$UNKNOWN_STATUS" != "404" ]; then
  echo "❌ Expected 404 for non-workspace member, got HTTP $UNKNOWN_STATUS"
  echo "$UNKNOWN_BODY" | jq .
  exit 1
fi
echo "✅ 404 guard for non-member works"
echo ""

echo "Step 10: GET /users/live (presence shape and self entry)"
LIVE_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/users/live" \
  -H "Authorization: Bearer $TOKEN")
LIVE_STATUS=$(echo "$LIVE_RESP" | grep "_STATUS_:" | cut -d':' -f2)
LIVE_BODY=$(echo "$LIVE_RESP" | sed '/_STATUS_:/d')
if [ "$LIVE_STATUS" != "200" ]; then
  echo "❌ GET /users/live failed (HTTP $LIVE_STATUS)"
  echo "$LIVE_BODY" | jq .
  exit 1
fi
if ! echo "$LIVE_BODY" | jq -e --arg uid "$SELF_USER_ID" '.data.presence | map(select(.client_id == $uid)) | length >= 1' >/dev/null; then
  echo "❌ Self user not found in /users/live presence"
  echo "$LIVE_BODY" | jq .
  exit 1
fi
if ! echo "$LIVE_BODY" | jq -e '.data.presence[0] | has("current_view") and has("is_online") and has("role_name")' >/dev/null; then
  echo "❌ Presence entry missing required keys"
  echo "$LIVE_BODY" | jq .
  exit 1
fi
echo "✅ Live presence shape is valid"
echo ""

echo "Step 11: POST /me/view-records with invalid entity_type -> 422"
BAD_ENTITY_PAYLOAD=$(jq -n --arg started_at "$STARTED_AT" '{records:[{entity_type:"invalid_entity",entity_client_id:"x",started_at:$started_at}]}')
BAD_ENTITY_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/users/me/view-records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$BAD_ENTITY_PAYLOAD")
BAD_ENTITY_STATUS=$(echo "$BAD_ENTITY_RESP" | grep "_STATUS_:" | cut -d':' -f2)
BAD_ENTITY_BODY=$(echo "$BAD_ENTITY_RESP" | sed '/_STATUS_:/d')
if [ "$BAD_ENTITY_STATUS" != "422" ]; then
  echo "❌ Expected 422 for invalid entity_type, got HTTP $BAD_ENTITY_STATUS"
  echo "$BAD_ENTITY_BODY" | jq .
  exit 1
fi
echo "✅ Invalid entity_type validation works"
echo ""

echo "Step 12: POST /me/view-records with batch size > 50 -> 422"
TOO_BIG_PAYLOAD=$(jq -n --arg now "$STARTED_AT" '{records: [range(0;51) | {entity_type:"case", entity_client_id:("bulk_" + (. | tostring)), started_at:$now}] }')
TOO_BIG_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/users/me/view-records" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$TOO_BIG_PAYLOAD")
TOO_BIG_STATUS=$(echo "$TOO_BIG_RESP" | grep "_STATUS_:" | cut -d':' -f2)
TOO_BIG_BODY=$(echo "$TOO_BIG_RESP" | sed '/_STATUS_:/d')
if [ "$TOO_BIG_STATUS" != "422" ]; then
  echo "❌ Expected 422 for oversized batch, got HTTP $TOO_BIG_STATUS"
  echo "$TOO_BIG_BODY" | jq .
  exit 1
fi
echo "✅ Batch-size validation works"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "✅ ALL VIEW RECORD TESTS PASSED"
echo "════════════════════════════════════════════════════════════════"
