#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="${1:-}"
PASSWORD="${2:-}"
TIMESTAMP=$(date +%s)

if [ -z "$EMAIL" ] || [ -z "$PASSWORD" ]; then
  echo "Usage: bash tests/items/test_find_or_create_item.sh <email> <password>"
  exit 1
fi

TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/sign-in" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"app_scope\":\"admin\"}" \
  | jq -r '.data.access_token')

echo "Token: ${#TOKEN} chars"

ART="ART_FIND_${TIMESTAMP}"
SKU="SKU_FIND_${TIMESTAMP}"

echo "--- Test 1: no article_number or sku -> ValidationError"
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/items/find-or-create" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"designer":"NoKey"}')
STATUS=$(echo "$R" | grep "_STATUS_:" | cut -d':' -f2)
[ "$STATUS" == "422" ] && echo "PASS (422)" || echo "FAIL (got $STATUS)"

echo "--- Test 2: create new item by article_number"
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/items/find-or-create" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"article_number\":\"$ART\",\"designer\":\"DesignerA\",\"quantity\":3}")
STATUS=$(echo "$R" | grep "_STATUS_:" | cut -d':' -f2)
BODY=$(echo "$R" | sed '/_STATUS_:/d')
ITEM_ID=$(echo "$BODY" | jq -r '.data.client_id')
WAS_CREATED=$(echo "$BODY" | jq -r '.data.was_created')
[ "$STATUS" == "200" ] && [ "$WAS_CREATED" == "true" ] && [ "$ITEM_ID" != "null" ] \
  && echo "PASS (created, id=$ITEM_ID)" || echo "FAIL (status=$STATUS was_created=$WAS_CREATED)"

echo "--- Test 3: find existing by article_number, update designer"
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/items/find-or-create" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"article_number\":\"$ART\",\"designer\":\"DesignerB\"}")
STATUS=$(echo "$R" | grep "_STATUS_:" | cut -d':' -f2)
BODY=$(echo "$R" | sed '/_STATUS_:/d')
ITEM_ID2=$(echo "$BODY" | jq -r '.data.client_id')
WAS_CREATED2=$(echo "$BODY" | jq -r '.data.was_created')
[ "$STATUS" == "200" ] && [ "$WAS_CREATED2" == "false" ] && [ "$ITEM_ID2" == "$ITEM_ID" ] \
  && echo "PASS (found same id, was_created=false)" || echo "FAIL (status=$STATUS was_created=$WAS_CREATED2 id=$ITEM_ID2)"

echo "--- Test 4: partial-update - quantity omitted, must stay 3"
GET_R=$(curl -s "$BASE_URL/api/v1/items/$ITEM_ID" -H "Authorization: Bearer $TOKEN")
QTY=$(echo "$GET_R" | jq -r '.data.item.quantity // empty')
[ "$QTY" == "3" ] && echo "PASS (quantity=3 preserved)" || echo "FAIL (quantity=$QTY)"

echo "--- Test 5: create by sku only"
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/items/find-or-create" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"sku\":\"$SKU\"}")
STATUS=$(echo "$R" | grep "_STATUS_:" | cut -d':' -f2)
BODY=$(echo "$R" | sed '/_STATUS_:/d')
ITEM_ID3=$(echo "$BODY" | jq -r '.data.client_id')
WAS_CREATED3=$(echo "$BODY" | jq -r '.data.was_created')
[ "$STATUS" == "200" ] && [ "$WAS_CREATED3" == "true" ] \
  && echo "PASS (sku create, id=$ITEM_ID3)" || echo "FAIL (status=$STATUS was_created=$WAS_CREATED3)"

echo "--- Test 6: find existing by sku"
R=$(curl -s -w "\n_STATUS_:%{http_code}" -X POST "$BASE_URL/api/v1/items/find-or-create" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"sku\":\"$SKU\"}")
STATUS=$(echo "$R" | grep "_STATUS_:" | cut -d':' -f2)
BODY=$(echo "$R" | sed '/_STATUS_:/d')
ITEM_ID4=$(echo "$BODY" | jq -r '.data.client_id')
WAS_CREATED4=$(echo "$BODY" | jq -r '.data.was_created')
[ "$STATUS" == "200" ] && [ "$WAS_CREATED4" == "false" ] && [ "$ITEM_ID4" == "$ITEM_ID3" ] \
  && echo "PASS (found same sku item, was_created=false)" || echo "FAIL (status=$STATUS was_created=$WAS_CREATED4)"

echo ""
echo "All find_or_create_item tests done."
