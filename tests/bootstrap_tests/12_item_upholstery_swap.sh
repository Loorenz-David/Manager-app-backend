#!/usr/bin/env bash
# =============================================================================
# TEST 12 — Item Upholstery Swap via PATCH
# Purpose : Validate swap behavior on PATCH /api/v1/item-upholsteries/{client_id}
#           including requirement lifecycle transition:
#           - old active requirement -> FAILED
#           - new active requirement created and linked
# Run from: <project>/backend/app/
# Requires:
#   - API running (default http://localhost:8000)
#   - APP .env contains bootstrap admin credentials
# =============================================================================
set -uo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "$0")/../../app" && pwd)}"
cd "$APP_DIR"
BASE_URL="${APP_URL:-http://localhost:8000}"

get_env_value() {
  local key="$1"
  local default_value="$2"
  local v
  v=$(grep "^${key}=" .env 2>/dev/null | head -n1 | cut -d= -f2-)
  if [ -z "$v" ]; then
    echo "$default_value"
  else
    echo "$v"
  fi
}

run_sql() {
  local sql="$1"
  python3 - <<PYEOF
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from beyo_manager.config import settings

SQL = """$sql"""

async def main():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.execute(text(SQL))
    await engine.dispose()

asyncio.run(main())
PYEOF
}

query_scalar() {
  local sql="$1"
  python3 - <<PYEOF
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from beyo_manager.config import settings

SQL = """$sql"""

async def main():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        res = await conn.execute(text(SQL))
        row = res.first()
        print(row[0] if row else "")
    await engine.dispose()

asyncio.run(main())
PYEOF
}

decode_jwt_claim() {
  local token="$1"
  local claim="$2"
  python3 - <<PYEOF
import base64
import json

token = '''$token'''
claim = '''$claim'''
parts = token.split('.')
if len(parts) < 2:
    print("")
    raise SystemExit(0)
payload = parts[1] + ("=" * (-len(parts[1]) % 4))
try:
    data = json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
except Exception:
    print("")
    raise SystemExit(0)
print(data.get(claim, ""))
PYEOF
}

ADMIN_EMAIL="$(get_env_value BOOTSTRAP_ADMIN_EMAIL admin@beyo.dev)"
ADMIN_PASSWORD="$(get_env_value BOOTSTRAP_ADMIN_PASSWORD Admin1234!)"

PASSED=0
FAILED=0

pass() { echo "   ✅ $1"; ((PASSED+=1)); return 0; }
fail() { echo "   ❌ $1"; ((FAILED+=1)); return 0; }

echo "════════════════════════════════════════════════════════════"
echo "TEST 12: Item Upholstery Swap via PATCH"
echo "════════════════════════════════════════════════════════════"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Sign in using stabilized .env bootstrap credentials
# ---------------------------------------------------------------------------
echo "Step 1 — Sign in as bootstrap admin"
SIGNIN=$(curl -s -w "\n_STATUS_:%{http_code}" \
  -X POST "$BASE_URL/api/v1/auth/sign-in" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\",\"app_scope\":\"admin\"}")
STATUS=$(echo "$SIGNIN" | grep "_STATUS_:" | cut -d: -f2)
BODY=$(echo "$SIGNIN" | sed '/_STATUS_:/d')
if [ "$STATUS" != "200" ]; then
  fail "Sign-in failed (HTTP $STATUS). Check BOOTSTRAP_ADMIN_* in .env"
  echo "   Response: $BODY"
  echo ""
  echo "TEST 12 RESULT: $PASSED Passed, $FAILED Failed"
  exit 1
fi
TOKEN=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('access_token',''))" 2>/dev/null)
if [ -z "$TOKEN" ]; then
  fail "No access token in sign-in response"
  echo ""
  echo "TEST 12 RESULT: $PASSED Passed, $FAILED Failed"
  exit 1
fi
pass "Admin sign-in succeeded"

# ---------------------------------------------------------------------------
# Step 2: Pick one upholstery id
# ---------------------------------------------------------------------------
echo "Step 2 — Pick an existing upholstery"
UPH_LIST=$(curl -s "$BASE_URL/api/v1/upholsteries?limit=1&offset=0" \
  -H "Authorization: Bearer $TOKEN")
UPH_ID=$(echo "$UPH_LIST" | python3 -c "import sys,json; d=json.load(sys.stdin); rows=d.get('data',{}).get('upholsteries',[]); print(rows[0].get('client_id','') if rows else '')" 2>/dev/null)
if [ -z "$UPH_ID" ]; then
  WORKSPACE_ID="$(decode_jwt_claim "$TOKEN" workspace_id)"
  USER_ID="$(decode_jwt_claim "$TOKEN" user_id)"
  if [ -z "$USER_ID" ]; then
    USER_ID="$(decode_jwt_claim "$TOKEN" sub)"
  fi
  if [ -z "$WORKSPACE_ID" ] && [ -n "$USER_ID" ]; then
    WORKSPACE_ID="$(query_scalar "SELECT workspace_id FROM workspace_memberships WHERE user_id = '$USER_ID' AND is_active IS true ORDER BY joined_at DESC LIMIT 1")"
  fi
  if [ -z "$WORKSPACE_ID" ]; then
    WORKSPACE_ID="ws_workspace_test"
  fi

  SEED_NAME="swap_seed_$(date +%s)"
  SEED_UPH_ID="uph_$(date +%s)"
  run_sql "
INSERT INTO upholsteries (client_id, workspace_id, name, code, created_at, created_by_id, is_deleted)
VALUES ('$SEED_UPH_ID', '$WORKSPACE_ID', '$SEED_NAME', NULL, NOW(), NULL, false)
ON CONFLICT (client_id) DO NOTHING;
" 2>/dev/null || true

  UPH_ID="$(query_scalar "SELECT client_id FROM upholsteries WHERE workspace_id = '$WORKSPACE_ID' AND name = '$SEED_NAME' ORDER BY created_at DESC LIMIT 1")"
  if [ -z "$UPH_ID" ]; then
    fail "No upholstery found and auto-seed failed for workspace $WORKSPACE_ID"
    echo ""
    echo "TEST 12 RESULT: $PASSED Passed, $FAILED Failed"
    exit 1
  fi
  pass "No upholstery existed; seeded upholstery_id=$UPH_ID"
else
  pass "Using upholstery_id=$UPH_ID"
fi

# ---------------------------------------------------------------------------
# Step 3: Ensure inventory exists and has stored stock for selected upholstery
# ---------------------------------------------------------------------------
echo "Step 3 — Ensure inventory exists and has stock"
INV_LIST=$(curl -s "$BASE_URL/api/v1/upholstery-inventories?limit=200&offset=0" \
  -H "Authorization: Bearer $TOKEN")
INV_ID=$(echo "$INV_LIST" | python3 -c "import sys,json; d=json.load(sys.stdin); rows=d.get('data',{}).get('upholstery_inventories_pagination',{}).get('items',[]); uph='$UPH_ID'; m=[r for r in rows if r.get('upholstery_id')==uph]; print(m[0].get('client_id','') if m else '')" 2>/dev/null)

if [ -z "$INV_ID" ]; then
  CREATED_INV=$(curl -s -w "\n_STATUS_:%{http_code}" \
    -X PUT "$BASE_URL/api/v1/upholstery-inventories" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"upholstery_id\":\"$UPH_ID\",\"low_stock_threshold_meters\":1}")
  CSTATUS=$(echo "$CREATED_INV" | grep "_STATUS_:" | cut -d: -f2)
  CBODY=$(echo "$CREATED_INV" | sed '/_STATUS_:/d')
  if [ "$CSTATUS" != "200" ]; then
    fail "Create inventory failed (HTTP $CSTATUS)"
    echo "   Response: $CBODY"
    echo ""
    echo "TEST 12 RESULT: $PASSED Passed, $FAILED Failed"
    exit 1
  fi
  INV_ID=$(echo "$CBODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('client_id',''))" 2>/dev/null)
fi

if [ -z "$INV_ID" ]; then
  fail "Could not determine inventory id"
  echo ""
  echo "TEST 12 RESULT: $PASSED Passed, $FAILED Failed"
  exit 1
fi

# Add and confirm ordered stock to guarantee AVAILABLE on initial requirement.
curl -s -X POST "$BASE_URL/api/v1/upholstery-inventories/$INV_ID/add-ordered" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"quantity":5}' >/dev/null
curl -s -X POST "$BASE_URL/api/v1/upholstery-inventories/$INV_ID/confirm-ordered" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"quantity":5}' >/dev/null
pass "Inventory prepared with available stock"

# ---------------------------------------------------------------------------
# Step 4: Create item with INTERNAL item_upholstery
# ---------------------------------------------------------------------------
echo "Step 4 — Create item with internal upholstery"
ARTICLE="SWAP-ART-$(date +%s)"
CREATE_ITEM=$(curl -s -w "\n_STATUS_:%{http_code}" \
  -X PUT "$BASE_URL/api/v1/items" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"article_number\":\"$ARTICLE\",\"item_upholstery\":{\"source\":\"internal\",\"upholstery_id\":\"$UPH_ID\",\"amount_meters\":1.5,\"name\":\"Swap Test Upholstery\",\"code\":\"SWP-T\",\"time_to_fix_in_seconds\":900}}")
ISTATUS=$(echo "$CREATE_ITEM" | grep "_STATUS_:" | cut -d: -f2)
IBODY=$(echo "$CREATE_ITEM" | sed '/_STATUS_:/d')
if [ "$ISTATUS" != "200" ]; then
  fail "Create item failed (HTTP $ISTATUS)"
  echo "   Response: $IBODY"
  echo ""
  echo "TEST 12 RESULT: $PASSED Passed, $FAILED Failed"
  exit 1
fi
ITEM_ID=$(echo "$IBODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('client_id',''))" 2>/dev/null)
if [ -z "$ITEM_ID" ]; then
  fail "Create item did not return client_id"
  echo ""
  echo "TEST 12 RESULT: $PASSED Passed, $FAILED Failed"
  exit 1
fi
pass "Item created: $ITEM_ID"

# ---------------------------------------------------------------------------
# Step 5: Resolve item_upholstery id and active requirement before swap
# ---------------------------------------------------------------------------
echo "Step 5 — Resolve item_upholstery and old active requirement"
ITEM_GET=$(curl -s "$BASE_URL/api/v1/items/$ITEM_ID" -H "Authorization: Bearer $TOKEN")
IUP_ID=$(echo "$ITEM_GET" | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('data',{}).get('item',{}).get('item_upholstery',{}) or {}).get('client_id',''))" 2>/dev/null)
OLD_ACTIVE_REQ=$(echo "$ITEM_GET" | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('data',{}).get('item',{}).get('item_upholstery',{}) or {}).get('active_requirement_id',''))" 2>/dev/null)
if [ -z "$IUP_ID" ] || [ -z "$OLD_ACTIVE_REQ" ]; then
  fail "Missing item_upholstery or active_requirement_id in item response"
  echo ""
  echo "TEST 12 RESULT: $PASSED Passed, $FAILED Failed"
  exit 1
fi
pass "Resolved iup_id=$IUP_ID, old_active_requirement_id=$OLD_ACTIVE_REQ"

# ---------------------------------------------------------------------------
# Step 6: Swap PATCH (INTERNAL -> CUSTOMER)
# ---------------------------------------------------------------------------
echo "Step 6 — PATCH swap source to customer"
SWAP=$(curl -s -w "\n_STATUS_:%{http_code}" \
  -X PATCH "$BASE_URL/api/v1/item-upholsteries/$IUP_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source":"customer"}')
SSTATUS=$(echo "$SWAP" | grep "_STATUS_:" | cut -d: -f2)
SBODY=$(echo "$SWAP" | sed '/_STATUS_:/d')
if [ "$SSTATUS" != "200" ]; then
  fail "Swap PATCH failed (HTTP $SSTATUS)"
  echo "   Response: $SBODY"
  echo ""
  echo "TEST 12 RESULT: $PASSED Passed, $FAILED Failed"
  exit 1
fi
pass "Swap PATCH returned 200"

# ---------------------------------------------------------------------------
# Step 7: Validate lifecycle outcomes
# ---------------------------------------------------------------------------
echo "Step 7 — Validate requirement transition"
IUP_AFTER=$(curl -s "$BASE_URL/api/v1/item-upholsteries/$IUP_ID" -H "Authorization: Bearer $TOKEN")
NEW_ACTIVE_REQ=$(echo "$IUP_AFTER" | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('data',{}).get('item_upholstery',{}) or {}).get('active_requirement_id',''))" 2>/dev/null)
NEW_SOURCE=$(echo "$IUP_AFTER" | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('data',{}).get('item_upholstery',{}) or {}).get('source',''))" 2>/dev/null)

REQS=$(curl -s "$BASE_URL/api/v1/item-upholsteries/$IUP_ID/requirements?limit=50&offset=0" -H "Authorization: Bearer $TOKEN")
OLD_STATE=$(echo "$REQS" | python3 -c "import sys,json; d=json.load(sys.stdin); rows=d.get('data',{}).get('upholstery_requirements_pagination',{}).get('items',[]); old='$OLD_ACTIVE_REQ'; m=[r for r in rows if r.get('client_id')==old]; print(m[0].get('state','') if m else '')" 2>/dev/null)
NEW_STATE=$(echo "$REQS" | python3 -c "import sys,json; d=json.load(sys.stdin); rows=d.get('data',{}).get('upholstery_requirements_pagination',{}).get('items',[]); new='$NEW_ACTIVE_REQ'; m=[r for r in rows if r.get('client_id')==new]; print(m[0].get('state','') if m else '')" 2>/dev/null)

[ "$NEW_SOURCE" = "customer" ] && pass "Item upholstery source updated to customer" || fail "Expected source=customer, got $NEW_SOURCE"
if [ -n "$NEW_ACTIVE_REQ" ] && [ "$NEW_ACTIVE_REQ" != "$OLD_ACTIVE_REQ" ]; then
  pass "Active requirement rotated to new id"
else
  fail "Active requirement did not rotate"
fi
[ "$OLD_STATE" = "failed" ] && pass "Old requirement marked failed" || fail "Expected old requirement state=failed, got $OLD_STATE"
case "$NEW_STATE" in
  available|missing_quantity)
    pass "New requirement created in expected state ($NEW_STATE)"
    ;;
  *)
    fail "Unexpected new requirement state: $NEW_STATE"
    ;;
esac

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "════════════════════════════════════════════════════════════"
echo "TEST 12 RESULT: $PASSED Passed, $FAILED Failed"
echo "════════════════════════════════════════════════════════════"
if [ "$FAILED" -gt "0" ]; then
  exit 1
fi
exit 0
