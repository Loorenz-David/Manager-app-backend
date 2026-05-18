#!/bin/bash
# =============================================================================
# TEST: Customer CRUD Flow
# Purpose : Test customer endpoints (create, get, list, update, delete, find-or-create)
#           including q filter, pagination shape, partial update semantics,
#           and soft-delete behavior.
# Run from: <project>/backend/
# Usage   : bash tests/costumer/test_costumer.sh <email> <password>
# Example : bash tests/costumer/test_costumer.sh admin@beyo.dev Admin1234!
# =============================================================================
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
TIMESTAMP=$(date +%s)

if [ $# -lt 2 ]; then
  echo "Usage: $0 <email> <password>"
  echo "Example: $0 admin@beyo.dev Admin1234!"
  exit 1
fi

EMAIL="$1"
PASSWORD="$2"

echo "════════════════════════════════════════════════════════════════"
echo "TEST: Customer CRUD Flow (run: $TIMESTAMP)"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Step 1: Sign in
echo "Step 1: Sign in with email: $EMAIL"
SIGNIN_RESP=$(curl -s -X POST "$BASE_URL/api/v1/auth/sign-in" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"app_scope\":\"admin\"}")

TOKEN=$(echo "$SIGNIN_RESP" | jq -r '.data.access_token' 2>/dev/null)
if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
  echo "❌ Failed to authenticate"
  echo "$SIGNIN_RESP" | jq .
  exit 1
fi

echo "✅ Authenticated successfully"
echo "   Token length: ${#TOKEN}"
echo ""

# Unique test data
DISPLAY_1="customer_test_${TIMESTAMP}"
EMAIL_1="customer_${TIMESTAMP}@example.com"
PHONE_2="+1415555${TIMESTAMP: -4}"

# Step 2: Create customer
echo "Step 2: CREATE customer (PUT /api/v1/customers)"
CREATE_PAYLOAD="{\"display_name\":\"$DISPLAY_1\",\"primary_email\":\"$EMAIL_1\"}"

CREATE_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X PUT "$BASE_URL/api/v1/customers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$CREATE_PAYLOAD")
CREATE_STATUS=$(echo "$CREATE_RESP" | grep "_STATUS_:" | cut -d':' -f2)
CREATE_BODY=$(echo "$CREATE_RESP" | sed '/_STATUS_:/d')

if [ "$CREATE_STATUS" != "200" ]; then
  echo "❌ Create failed (HTTP $CREATE_STATUS)"
  echo "$CREATE_BODY" | jq .
  exit 1
fi

CUS1_ID=$(echo "$CREATE_BODY" | jq -r '.data.client_id')
if [ -z "$CUS1_ID" ] || [ "$CUS1_ID" == "null" ]; then
  echo "❌ Missing client_id in create response"
  echo "$CREATE_BODY" | jq .
  exit 1
fi

echo "✅ Created customer"
echo "   ID: $CUS1_ID"
echo ""

# Step 3: Get customer detail
echo "Step 3: GET customer detail (GET /api/v1/customers/{id})"
GET1_RESP=$(curl -s "$BASE_URL/api/v1/customers/$CUS1_ID" \
  -H "Authorization: Bearer $TOKEN")

GET1_NAME=$(echo "$GET1_RESP" | jq -r '.data.customer.display_name')
GET1_EMAIL=$(echo "$GET1_RESP" | jq -r '.data.customer.primary_email')
LINKED_ITEMS_TYPE=$(echo "$GET1_RESP" | jq -r '.data.customer.linked_items | type')

if [ "$GET1_NAME" != "$DISPLAY_1" ]; then
  echo "❌ Unexpected display_name on GET"
  echo "$GET1_RESP" | jq .
  exit 1
fi

if [ "$LINKED_ITEMS_TYPE" != "array" ]; then
  echo "❌ linked_items is not an array"
  echo "$GET1_RESP" | jq .
  exit 1
fi

echo "✅ Retrieved customer detail"
echo "   Name: $GET1_NAME"
echo "   Email: $GET1_EMAIL"
echo "   linked_items type: $LINKED_ITEMS_TYPE"
echo ""

# Step 4: List customers with q filter
echo "Step 4: LIST customers with q filter (GET /api/v1/customers)"
LIST_RESP=$(curl -s "$BASE_URL/api/v1/customers?limit=50&offset=0&q=$TIMESTAMP&string_filters=display_name,primary_email" \
  -H "Authorization: Bearer $TOKEN")

LIST_COUNT=$(echo "$LIST_RESP" | jq '.data.customers_pagination.items | length')
HAS_MORE=$(echo "$LIST_RESP" | jq -r '.data.customers_pagination.has_more')
LIMIT_VAL=$(echo "$LIST_RESP" | jq -r '.data.customers_pagination.limit')
OFFSET_VAL=$(echo "$LIST_RESP" | jq -r '.data.customers_pagination.offset')
MATCHED_ID=$(echo "$LIST_RESP" | jq -r --arg id "$CUS1_ID" '.data.customers_pagination.items[] | select(.client_id == $id) | .client_id' | head -1)

if [ "$LIMIT_VAL" == "null" ] || [ "$OFFSET_VAL" == "null" ] || [ "$HAS_MORE" == "null" ]; then
  echo "❌ Pagination shape missing"
  echo "$LIST_RESP" | jq .
  exit 1
fi

if [ "$MATCHED_ID" != "$CUS1_ID" ]; then
  echo "❌ Created customer not found in q-filtered list"
  echo "$LIST_RESP" | jq .
  exit 1
fi

echo "✅ List with q filter works"
echo "   Items count: $LIST_COUNT"
echo "   Pagination: has_more=$HAS_MORE limit=$LIMIT_VAL offset=$OFFSET_VAL"
echo ""

# Step 5: Partial update semantics
echo "Step 5: PATCH customer (partial update semantics)"
UPDATED_NAME="${DISPLAY_1}_updated"
PATCH_PAYLOAD="{\"display_name\":\"$UPDATED_NAME\"}"

PATCH_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X PATCH "$BASE_URL/api/v1/customers/$CUS1_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PATCH_PAYLOAD")
PATCH_STATUS=$(echo "$PATCH_RESP" | grep "_STATUS_:" | cut -d':' -f2)
PATCH_BODY=$(echo "$PATCH_RESP" | sed '/_STATUS_:/d')

if [ "$PATCH_STATUS" != "200" ]; then
  echo "❌ Patch failed (HTTP $PATCH_STATUS)"
  echo "$PATCH_BODY" | jq .
  exit 1
fi

GET2_RESP=$(curl -s "$BASE_URL/api/v1/customers/$CUS1_ID" \
  -H "Authorization: Bearer $TOKEN")
GET2_NAME=$(echo "$GET2_RESP" | jq -r '.data.customer.display_name')
GET2_EMAIL=$(echo "$GET2_RESP" | jq -r '.data.customer.primary_email')

if [ "$GET2_NAME" != "$UPDATED_NAME" ]; then
  echo "❌ display_name did not update"
  echo "$GET2_RESP" | jq .
  exit 1
fi

if [ "$GET2_EMAIL" != "$EMAIL_1" ]; then
  echo "❌ primary_email changed unexpectedly (partial semantics broken)"
  echo "$GET2_RESP" | jq .
  exit 1
fi

echo "✅ Partial update semantics verified"
echo "   Updated name: $GET2_NAME"
echo "   Email preserved: $GET2_EMAIL"
echo ""

# Step 6: find-or-create returns existing
echo "Step 6: FIND-OR-CREATE existing (POST /api/v1/customers/find-or-create)"
FOC_EXIST_PAYLOAD="{\"display_name\":\"ignored_name\",\"primary_email\":\"$EMAIL_1\"}"

FOC_EXIST_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/customers/find-or-create" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$FOC_EXIST_PAYLOAD")
FOC_EXIST_STATUS=$(echo "$FOC_EXIST_RESP" | grep "_STATUS_:" | cut -d':' -f2)
FOC_EXIST_BODY=$(echo "$FOC_EXIST_RESP" | sed '/_STATUS_:/d')

if [ "$FOC_EXIST_STATUS" != "200" ]; then
  echo "❌ find-or-create existing failed (HTTP $FOC_EXIST_STATUS)"
  echo "$FOC_EXIST_BODY" | jq .
  exit 1
fi

FOC_EXIST_ID=$(echo "$FOC_EXIST_BODY" | jq -r '.data.client_id')
FOC_EXIST_CREATED=$(echo "$FOC_EXIST_BODY" | jq -r '.data.was_created')

if [ "$FOC_EXIST_ID" != "$CUS1_ID" ] || [ "$FOC_EXIST_CREATED" != "false" ]; then
  echo "❌ find-or-create existing behavior invalid"
  echo "$FOC_EXIST_BODY" | jq .
  exit 1
fi

echo "✅ find-or-create matched existing customer"
echo "   ID: $FOC_EXIST_ID"
echo "   was_created: $FOC_EXIST_CREATED"
echo ""

# Step 7: find-or-create creates new
echo "Step 7: FIND-OR-CREATE new customer by phone"
FOC_NEW_PAYLOAD="{\"display_name\":\"customer_foc_${TIMESTAMP}\",\"primary_phone_number\":\"$PHONE_2\"}"

FOC_NEW_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/customers/find-or-create" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$FOC_NEW_PAYLOAD")
FOC_NEW_STATUS=$(echo "$FOC_NEW_RESP" | grep "_STATUS_:" | cut -d':' -f2)
FOC_NEW_BODY=$(echo "$FOC_NEW_RESP" | sed '/_STATUS_:/d')

if [ "$FOC_NEW_STATUS" != "200" ]; then
  echo "❌ find-or-create new failed (HTTP $FOC_NEW_STATUS)"
  echo "$FOC_NEW_BODY" | jq .
  exit 1
fi

CUS2_ID=$(echo "$FOC_NEW_BODY" | jq -r '.data.client_id')
FOC_NEW_CREATED=$(echo "$FOC_NEW_BODY" | jq -r '.data.was_created')

if [ -z "$CUS2_ID" ] || [ "$CUS2_ID" == "null" ] || [ "$FOC_NEW_CREATED" != "true" ]; then
  echo "❌ find-or-create new behavior invalid"
  echo "$FOC_NEW_BODY" | jq .
  exit 1
fi

echo "✅ find-or-create created new customer"
echo "   ID: $CUS2_ID"
echo "   was_created: $FOC_NEW_CREATED"
echo ""

# Step 8: Delete + not found verification
echo "Step 8: DELETE first customer"
DEL_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" -X DELETE "$BASE_URL/api/v1/customers/$CUS1_ID" \
  -H "Authorization: Bearer $TOKEN")
DEL_STATUS=$(echo "$DEL_RESP" | grep "_STATUS_:" | cut -d':' -f2)
DEL_BODY=$(echo "$DEL_RESP" | sed '/_STATUS_:/d')

if [ "$DEL_STATUS" != "200" ]; then
  echo "❌ Delete failed (HTTP $DEL_STATUS)"
  echo "$DEL_BODY" | jq .
  exit 1
fi

echo "✅ Soft-deleted customer: $CUS1_ID"
echo ""

echo "Step 9: GET deleted customer should return 404"
GET_DEL_RESP=$(curl -s -w "\n_STATUS_:%{http_code}" "$BASE_URL/api/v1/customers/$CUS1_ID" \
  -H "Authorization: Bearer $TOKEN")
GET_DEL_STATUS=$(echo "$GET_DEL_RESP" | grep "_STATUS_:" | cut -d':' -f2)

if [ "$GET_DEL_STATUS" != "404" ]; then
  echo "❌ Expected 404 for deleted customer, got $GET_DEL_STATUS"
  echo "$GET_DEL_RESP" | sed '/_STATUS_:/d' | jq .
  exit 1
fi

echo "✅ Deleted customer not accessible (404)"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "✅ ALL TESTS PASSED"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Test Summary:"
echo "  ✓ Authentication and JWT flow"
echo "  ✓ Create customer (CMD-1)"
echo "  ✓ Get customer detail with linked_items shape (QUERY-2)"
echo "  ✓ List customers with q + string_filters + pagination (QUERY-1)"
echo "  ✓ Partial update semantics (CMD-2)"
echo "  ✓ Find-or-create existing path (CMD-4: was_created=false)"
echo "  ✓ Find-or-create create path (CMD-4: was_created=true)"
echo "  ✓ Soft-delete and 404 on get after delete (CMD-3)"
