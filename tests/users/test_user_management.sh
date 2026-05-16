#!/bin/bash
# =============================================================================
# TEST: User Management Flow
# Purpose : Test self-service profile endpoints and admin user-management
#           endpoints including register-by-role_name, list/get/filter,
#           update, deactivate, and password rotation.
# Run from: <project>/backend/
# Usage   : bash tests/users/test_user_management.sh <email> <password>
# Example : bash tests/users/test_user_management.sh user_test@test.local Test1234!
# =============================================================================
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
TIMESTAMP=$(date +%s)
SELF_CLIENT_ID=""
ORIGINAL_PHONE=""
ORIGINAL_PROFILE_PICTURE=""
NEW_PASSWORD="${NEW_PASSWORD:-${2}X}"
TEMP_SECTION_ID=""
TEMP_USER_ID=""
TEMP_USER_USERNAME="user_mgmt_worker_${TIMESTAMP}"
TEMP_USER_EMAIL="user_mgmt_worker_${TIMESTAMP}@test.local"
TEMP_USER_PASSWORD="Temp1234!"
TEMP_SECTION_NAME="user_mgmt_section_${TIMESTAMP}"

if [ $# -lt 2 ]; then
  echo "Usage: $0 <email> <password>"
  echo "Example: $0 user_test@test.local Test1234!"
  exit 1
fi

EMAIL="$1"
PASSWORD="$2"
NEW_PASSWORD="${NEW_PASSWORD:-${PASSWORD}X}"

cleanup() {
  if [ -n "${TOKEN:-}" ] && [ -n "$TEMP_USER_ID" ]; then
    curl -s -X PATCH "$BASE_URL/api/v1/users/$TEMP_USER_ID/deactivate" \
      -H "Authorization: Bearer $TOKEN" >/dev/null || true
  fi
  if [ -n "${TOKEN:-}" ] && [ -n "$TEMP_SECTION_ID" ]; then
    curl -s -X DELETE "$BASE_URL/api/v1/working-sections/$TEMP_SECTION_ID" \
      -H "Authorization: Bearer $TOKEN" >/dev/null || true
  fi
  if [ -n "${TOKEN:-}" ]; then
    CLEANUP_RESTORE_PAYLOAD=$(jq -n \
      --arg phone "$ORIGINAL_PHONE" \
      --arg picture "$ORIGINAL_PROFILE_PICTURE" \
      '{phone_number: (if $phone == "" then null else $phone end), profile_picture: (if $picture == "" then null else $picture end)}')
    curl -s -X PATCH "$BASE_URL/api/v1/users/me" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "$CLEANUP_RESTORE_PAYLOAD" >/dev/null || true
  fi
}
trap cleanup EXIT

echo "════════════════════════════════════════════════════════════════"
echo "TEST: User Management Flow (run: $TIMESTAMP)"
echo "════════════════════════════════════════════════════════════════"
echo ""

echo "Step 1: Sign in with email: $EMAIL"
SIGNIN_RESP=$(curl -s -X POST "$BASE_URL/api/v1/auth/sign-in" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"app_scope\":\"admin\"}")

TOKEN=$(echo "$SIGNIN_RESP" | jq -r '.data.access_token' 2>/dev/null)
if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "❌ Failed to authenticate"
  echo "$SIGNIN_RESP" | jq .
  exit 1
fi

echo "✅ Authenticated successfully"
echo "   Token length: ${#TOKEN}"
echo ""

echo "Step 2: GET /api/v1/users/me"
GET_ME_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/users/me" \
  -H "Authorization: Bearer $TOKEN")
GET_ME_STATUS=$(echo "$GET_ME_RESP" | grep "_STATUS_:" | cut -d':' -f2)
GET_ME_BODY=$(echo "$GET_ME_RESP" | sed '/_STATUS_:/d')
if [ "$GET_ME_STATUS" != "200" ]; then
  echo "❌ GET /users/me failed (HTTP $GET_ME_STATUS)"
  echo "$GET_ME_BODY" | jq .
  exit 1
fi
SELF_CLIENT_ID=$(echo "$GET_ME_BODY" | jq -r '.data.user.client_id')
ORIGINAL_PHONE=$(echo "$GET_ME_BODY" | jq -r '.data.user.phone_number // empty')
ORIGINAL_PROFILE_PICTURE=$(echo "$GET_ME_BODY" | jq -r '.data.user.profile_picture // empty')
echo "✅ Retrieved self profile"
echo "   Client ID: $SELF_CLIENT_ID"
echo ""

echo "Step 3: PATCH /api/v1/users/me"
PATCH_ME_PAYLOAD="{\"phone_number\":\"+49-100-$TIMESTAMP\",\"profile_picture\":\"https://example.com/users/me_$TIMESTAMP.png\"}"
PATCH_ME_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X PATCH "$BASE_URL/api/v1/users/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PATCH_ME_PAYLOAD")
PATCH_ME_STATUS=$(echo "$PATCH_ME_RESP" | grep "_STATUS_:" | cut -d':' -f2)
PATCH_ME_BODY=$(echo "$PATCH_ME_RESP" | sed '/_STATUS_:/d')
if [ "$PATCH_ME_STATUS" != "200" ]; then
  echo "❌ PATCH /users/me failed (HTTP $PATCH_ME_STATUS)"
  echo "$PATCH_ME_BODY" | jq .
  exit 1
fi

echo "✅ Updated self profile"
echo "   Phone: $(echo "$PATCH_ME_BODY" | jq -r '.data.user.phone_number')"
echo ""

echo "Step 4: PATCH /api/v1/users/me/password and verify sign-in"
PATCH_PW_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X PATCH "$BASE_URL/api/v1/users/me/password" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"current_password\":\"$PASSWORD\",\"new_password\":\"$NEW_PASSWORD\"}")
PATCH_PW_STATUS=$(echo "$PATCH_PW_RESP" | grep "_STATUS_:" | cut -d':' -f2)
PATCH_PW_BODY=$(echo "$PATCH_PW_RESP" | sed '/_STATUS_:/d')
if [ "$PATCH_PW_STATUS" != "200" ]; then
  echo "❌ PATCH /users/me/password failed (HTTP $PATCH_PW_STATUS)"
  echo "$PATCH_PW_BODY" | jq .
  exit 1
fi

ROTATED_SIGNIN=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/auth/sign-in" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$NEW_PASSWORD\",\"app_scope\":\"admin\"}")
ROTATED_SIGNIN_STATUS=$(echo "$ROTATED_SIGNIN" | grep "_STATUS_:" | cut -d':' -f2)
ROTATED_SIGNIN_BODY=$(echo "$ROTATED_SIGNIN" | sed '/_STATUS_:/d')
if [ "$ROTATED_SIGNIN_STATUS" != "200" ]; then
  echo "❌ Sign-in with rotated password failed (HTTP $ROTATED_SIGNIN_STATUS)"
  echo "$ROTATED_SIGNIN_BODY" | jq .
  exit 1
fi
TOKEN=$(echo "$ROTATED_SIGNIN_BODY" | jq -r '.data.access_token')

echo "✅ Password rotated and verified"
echo ""

echo "Step 5: Restore original password"
RESTORE_PW_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X PATCH "$BASE_URL/api/v1/users/me/password" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"current_password\":\"$NEW_PASSWORD\",\"new_password\":\"$PASSWORD\"}")
RESTORE_PW_STATUS=$(echo "$RESTORE_PW_RESP" | grep "_STATUS_:" | cut -d':' -f2)
RESTORE_PW_BODY=$(echo "$RESTORE_PW_RESP" | sed '/_STATUS_:/d')
if [ "$RESTORE_PW_STATUS" != "200" ]; then
  echo "❌ Password restore failed (HTTP $RESTORE_PW_STATUS)"
  echo "$RESTORE_PW_BODY" | jq .
  exit 1
fi

RESTORED_SIGNIN=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/auth/sign-in" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"app_scope\":\"admin\"}")
RESTORED_SIGNIN_STATUS=$(echo "$RESTORED_SIGNIN" | grep "_STATUS_:" | cut -d':' -f2)
RESTORED_SIGNIN_BODY=$(echo "$RESTORED_SIGNIN" | sed '/_STATUS_:/d')
if [ "$RESTORED_SIGNIN_STATUS" != "200" ]; then
  echo "❌ Sign-in after password restore failed (HTTP $RESTORED_SIGNIN_STATUS)"
  echo "$RESTORED_SIGNIN_BODY" | jq .
  exit 1
fi
TOKEN=$(echo "$RESTORED_SIGNIN_BODY" | jq -r '.data.access_token')
echo "✅ Original password restored"
echo ""

echo "Step 6: CREATE temporary working section for section-filter coverage"
CREATE_SECTION_PAYLOAD="{\"name\":\"$TEMP_SECTION_NAME\",\"image\":\"https://example.com/section_$TIMESTAMP.png\",\"working_section_dependencies\":[],\"working_section_item_categories\":[],\"working_section_supported_issue_types\":[]}"
CREATE_SECTION_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X PUT "$BASE_URL/api/v1/working-sections" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$CREATE_SECTION_PAYLOAD")
CREATE_SECTION_STATUS=$(echo "$CREATE_SECTION_RESP" | grep "_STATUS_:" | cut -d':' -f2)
CREATE_SECTION_BODY=$(echo "$CREATE_SECTION_RESP" | sed '/_STATUS_:/d')
if [ "$CREATE_SECTION_STATUS" != "200" ]; then
  echo "❌ Working section create failed (HTTP $CREATE_SECTION_STATUS)"
  echo "$CREATE_SECTION_BODY" | jq .
  exit 1
fi
TEMP_SECTION_ID=$(echo "$CREATE_SECTION_BODY" | jq -r '.data.client_id')
echo "✅ Created working section"
echo "   ID: $TEMP_SECTION_ID"
echo ""

echo "Step 7: REGISTER temporary worker using role_name convenience input"
REGISTER_PAYLOAD="{\"username\":\"$TEMP_USER_USERNAME\",\"email\":\"$TEMP_USER_EMAIL\",\"password\":\"$TEMP_USER_PASSWORD\",\"role_name\":\"worker\",\"working_section_ids\":[\"$TEMP_SECTION_ID\"]}"
REGISTER_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/auth/register" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$REGISTER_PAYLOAD")
REGISTER_STATUS=$(echo "$REGISTER_RESP" | grep "_STATUS_:" | cut -d':' -f2)
REGISTER_BODY=$(echo "$REGISTER_RESP" | sed '/_STATUS_:/d')
if [ "$REGISTER_STATUS" != "200" ]; then
  echo "❌ Register failed (HTTP $REGISTER_STATUS)"
  echo "$REGISTER_BODY" | jq .
  exit 1
fi
TEMP_USER_ID=$(echo "$REGISTER_BODY" | jq -r '.data.user.client_id')
echo "✅ Registered temporary worker"
echo "   User ID: $TEMP_USER_ID"
echo ""

echo "Step 8: LIST users"
LIST_USERS_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/users?limit=5&offset=0" \
  -H "Authorization: Bearer $TOKEN")
LIST_USERS_STATUS=$(echo "$LIST_USERS_RESP" | grep "_STATUS_:" | cut -d':' -f2)
LIST_USERS_BODY=$(echo "$LIST_USERS_RESP" | sed '/_STATUS_:/d')
if [ "$LIST_USERS_STATUS" != "200" ]; then
  echo "❌ List users failed (HTTP $LIST_USERS_STATUS)"
  echo "$LIST_USERS_BODY" | jq .
  exit 1
fi

echo "✅ Listed users"
echo "   Returned users: $(echo "$LIST_USERS_BODY" | jq '.data.users | length')"
echo ""

echo "Step 9: GET temporary user"
GET_USER_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/users/$TEMP_USER_ID" \
  -H "Authorization: Bearer $TOKEN")
GET_USER_STATUS=$(echo "$GET_USER_RESP" | grep "_STATUS_:" | cut -d':' -f2)
GET_USER_BODY=$(echo "$GET_USER_RESP" | sed '/_STATUS_:/d')
if [ "$GET_USER_STATUS" != "200" ]; then
  echo "❌ Get user failed (HTTP $GET_USER_STATUS)"
  echo "$GET_USER_BODY" | jq .
  exit 1
fi

echo "✅ Retrieved temporary user"
echo "   Username: $(echo "$GET_USER_BODY" | jq -r '.data.user.username')"
echo ""

echo "Step 10: PATCH temporary user salary and profile fields"
PATCH_USER_PAYLOAD="{\"phone_number\":\"+49-200-$TIMESTAMP\",\"profile_picture\":\"https://example.com/temp_user_$TIMESTAMP.png\",\"salary_per_hour_before_tax\":\"25.5000\",\"salary_per_hour_after_tax\":\"20.1000\"}"
PATCH_USER_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X PATCH "$BASE_URL/api/v1/users/$TEMP_USER_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PATCH_USER_PAYLOAD")
PATCH_USER_STATUS=$(echo "$PATCH_USER_RESP" | grep "_STATUS_:" | cut -d':' -f2)
PATCH_USER_BODY=$(echo "$PATCH_USER_RESP" | sed '/_STATUS_:/d')
if [ "$PATCH_USER_STATUS" != "200" ]; then
  echo "❌ Patch user failed (HTTP $PATCH_USER_STATUS)"
  echo "$PATCH_USER_BODY" | jq .
  exit 1
fi

echo "✅ Updated temporary user"
echo "   Salary before tax: $(echo "$PATCH_USER_BODY" | jq -r '.data.user.work_profile.salary_per_hour_before_tax')"
echo ""

echo "Step 11: FILTER users by role and search query"
FILTER_ROLE_Q_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/users?role=worker&q=$TEMP_USER_USERNAME" \
  -H "Authorization: Bearer $TOKEN")
FILTER_ROLE_Q_STATUS=$(echo "$FILTER_ROLE_Q_RESP" | grep "_STATUS_:" | cut -d':' -f2)
FILTER_ROLE_Q_BODY=$(echo "$FILTER_ROLE_Q_RESP" | sed '/_STATUS_:/d')
if [ "$FILTER_ROLE_Q_STATUS" != "200" ]; then
  echo "❌ Role/q filter failed (HTTP $FILTER_ROLE_Q_STATUS)"
  echo "$FILTER_ROLE_Q_BODY" | jq .
  exit 1
fi
FILTER_MATCH=$(echo "$FILTER_ROLE_Q_BODY" | jq -r --arg uid "$TEMP_USER_ID" '.data.users[]?.client_id | select(. == $uid)' | head -n 1)
if [ "$FILTER_MATCH" != "$TEMP_USER_ID" ]; then
  echo "❌ Role/q filter did not return temp user"
  echo "$FILTER_ROLE_Q_BODY" | jq .
  exit 1
fi

echo "✅ Role/q filter returned temp user"
echo ""

echo "Step 12: FILTER users by working section"
FILTER_SECTION_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/users?working_sections=$TEMP_SECTION_NAME" \
  -H "Authorization: Bearer $TOKEN")
FILTER_SECTION_STATUS=$(echo "$FILTER_SECTION_RESP" | grep "_STATUS_:" | cut -d':' -f2)
FILTER_SECTION_BODY=$(echo "$FILTER_SECTION_RESP" | sed '/_STATUS_:/d')
if [ "$FILTER_SECTION_STATUS" != "200" ]; then
  echo "❌ Working section filter failed (HTTP $FILTER_SECTION_STATUS)"
  echo "$FILTER_SECTION_BODY" | jq .
  exit 1
fi
FILTER_SECTION_MATCH=$(echo "$FILTER_SECTION_BODY" | jq -r --arg uid "$TEMP_USER_ID" '.data.users[]?.client_id | select(. == $uid)' | head -n 1)
if [ "$FILTER_SECTION_MATCH" != "$TEMP_USER_ID" ]; then
  echo "❌ Working section filter did not return temp user"
  echo "$FILTER_SECTION_BODY" | jq .
  exit 1
fi

echo "✅ Working section filter returned temp user"
echo ""

echo "Step 13: DEACTIVATE temporary user"
DEACTIVATE_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X PATCH "$BASE_URL/api/v1/users/$TEMP_USER_ID/deactivate" \
  -H "Authorization: Bearer $TOKEN")
DEACTIVATE_STATUS=$(echo "$DEACTIVATE_RESP" | grep "_STATUS_:" | cut -d':' -f2)
DEACTIVATE_BODY=$(echo "$DEACTIVATE_RESP" | sed '/_STATUS_:/d')
if [ "$DEACTIVATE_STATUS" != "200" ]; then
  echo "❌ Deactivate failed (HTTP $DEACTIVATE_STATUS)"
  echo "$DEACTIVATE_BODY" | jq .
  exit 1
fi
TEMP_USER_ID=""
echo "✅ Deactivated temporary user"
echo ""

echo "Step 14: Verify deactivated user returns 404"
GET_DEACTIVATED_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/users/$(echo "$REGISTER_BODY" | jq -r '.data.user.client_id')" \
  -H "Authorization: Bearer $TOKEN")
GET_DEACTIVATED_STATUS=$(echo "$GET_DEACTIVATED_RESP" | grep "_STATUS_:" | cut -d':' -f2)
if [ "$GET_DEACTIVATED_STATUS" != "404" ]; then
  echo "❌ Expected 404 after deactivate, got HTTP $GET_DEACTIVATED_STATUS"
  echo "$GET_DEACTIVATED_RESP" | sed '/_STATUS_:/d' | jq .
  exit 1
fi

echo "✅ Deactivated user is no longer accessible"
echo ""

echo "Step 15: DELETE temporary working section"
DELETE_SECTION_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X DELETE "$BASE_URL/api/v1/working-sections/$TEMP_SECTION_ID" \
  -H "Authorization: Bearer $TOKEN")
DELETE_SECTION_STATUS=$(echo "$DELETE_SECTION_RESP" | grep "_STATUS_:" | cut -d':' -f2)
DELETE_SECTION_BODY=$(echo "$DELETE_SECTION_RESP" | sed '/_STATUS_:/d')
if [ "$DELETE_SECTION_STATUS" != "200" ]; then
  echo "❌ Working section delete failed (HTTP $DELETE_SECTION_STATUS)"
  echo "$DELETE_SECTION_BODY" | jq .
  exit 1
fi
TEMP_SECTION_ID=""
echo "✅ Deleted temporary working section"
echo ""

echo "Step 16: Restore original self profile fields"
RESTORE_ME_PAYLOAD=$(jq -n \
  --arg phone "$ORIGINAL_PHONE" \
  --arg picture "$ORIGINAL_PROFILE_PICTURE" \
  '{phone_number: (if $phone == "" then null else $phone end), profile_picture: (if $picture == "" then null else $picture end)}')
RESTORE_ME_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X PATCH "$BASE_URL/api/v1/users/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$RESTORE_ME_PAYLOAD")
RESTORE_ME_STATUS=$(echo "$RESTORE_ME_RESP" | grep "_STATUS_:" | cut -d':' -f2)
RESTORE_ME_BODY=$(echo "$RESTORE_ME_RESP" | sed '/_STATUS_:/d')
if [ "$RESTORE_ME_STATUS" != "200" ]; then
  echo "❌ Restore self profile failed (HTTP $RESTORE_ME_STATUS)"
  echo "$RESTORE_ME_BODY" | jq .
  exit 1
fi

echo "✅ Restored original self profile fields"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "✅ ALL TESTS PASSED"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Test Summary:"
echo "  ✓ Authentication with provided credentials"
echo "  ✓ Self-service get/update/password rotation and restore"
echo "  ✓ Temporary worker registration with role_name"
echo "  ✓ Admin list/get/update/deactivate user management"
echo "  ✓ Role + q filtering"
echo "  ✓ Working-section filtering"
echo "  ✓ Cleanup of temporary user and working section"
