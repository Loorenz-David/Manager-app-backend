#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://api-manager.beyoworkaroundtheclock.com"
ROOT_DIR="/Users/davidloorenz/Desktop/Developer/BeyoApps_2025/ManagerBeyo-app"
BACKEND_DIR="$ROOT_DIR/backend"
ENV_FILE="$BACKEND_DIR/app/.env"
SSH_KEY="$BACKEND_DIR/secretes/manager-app-beyo.pem"
SSH_HOST="ubuntu@16.16.19.181"

BOOTPASS="${BOOTSTRAP_ADMIN_PASSWORD:-$(grep '^BOOTSTRAP_ADMIN_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

fail() {
  echo "$1" >&2
  exit 1
}

jwt_claim() {
  local token="$1"
  local key="$2"
  local payload b64
  payload="$(printf '%s' "$token" | cut -d'.' -f2 | tr '_-' '/+')"
  b64="$payload"
  while (( ${#b64} % 4 != 0 )); do
    b64="${b64}="
  done
  printf '%s' "$b64" | base64 -d 2>/dev/null | jq -r --arg k "$key" '.[$k] // empty'
}

# 1) Inject case types in LIVE DB through remote host.
ssh -i "$SSH_KEY" "$SSH_HOST" 'set -euo pipefail
DB_URL=$(grep "^DATABASE_URL=" /home/ubuntu/config/managerbeyo/.env | cut -d= -f2- | sed "s|postgresql+asyncpg://|postgresql://|")
psql "$DB_URL" -v ON_ERROR_STOP=1
' <<'SQL'
insert into case_types (client_id,name,entity_type)
select 'cty_seed_out_of_upholstery','out of upholstery','task'::case_link_entity_type_enum
where not exists (select 1 from case_types where name='out of upholstery');

insert into case_types (client_id,name,entity_type)
select 'cty_seed_broken_tool','broken tool','task'::case_link_entity_type_enum
where not exists (select 1 from case_types where name='broken tool');

insert into case_types (client_id,name,entity_type)
select 'cty_seed_cant_find_item','can''t find item','task'::case_link_entity_type_enum
where not exists (select 1 from case_types where name='can''t find item');
SQL

# 2) Resolve admin token. Reuse provided token to avoid sign-in rate limits.
if [[ -z "$ADMIN_TOKEN" ]]; then
  admin_resp="$(curl -sS -X POST "$BASE_URL/api/v1/auth/sign-in" -H 'Content-Type: application/json' -d "{\"email\":\"admin@beyo.dev\",\"password\":\"$BOOTPASS\"}")"
  [[ "$(echo "$admin_resp" | jq -r '.ok // false')" == "true" ]] || fail "Admin sign-in failed: $admin_resp"
  ADMIN_TOKEN="$(echo "$admin_resp" | jq -r '.data.access_token')"
fi

me_resp="$(curl -sS -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE_URL/api/v1/users/me")"
[[ "$(echo "$me_resp" | jq -r '.ok // false')" == "true" ]] || fail "Admin token validation failed: $me_resp"
admin_id="$(echo "$me_resp" | jq -r '.data.user.client_id // .data.client_id // empty')"
[[ -n "$admin_id" ]] || fail "Could not resolve admin ID from /users/me"

workspace_id="$(ssh -i "$SSH_KEY" "$SSH_HOST" "set -euo pipefail
DB_URL=\$(grep '^DATABASE_URL=' /home/ubuntu/config/managerbeyo/.env | cut -d= -f2- | sed 's|postgresql+asyncpg://|postgresql://|')
psql \"\$DB_URL\" -Atc \"select workspace_id from working_section_memberships where user_id='${admin_id}' limit 1\"
")"
if [[ -z "$workspace_id" ]]; then
  workspace_id="$(jwt_claim "$ADMIN_TOKEN" "workspace_id")"
fi
[[ -n "$workspace_id" ]] || fail "Could not resolve workspace ID for admin user"

# 3) Ensure requested creators exist (register if missing).
usernames=(noah_woods_57 leo_young_95 sophia_morris_17 liam_santos_63)
for u in "${usernames[@]}"; do
  users_json="$(curl -sS -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE_URL/api/v1/users?q=$u&limit=50")"
  exists_id="$(echo "$users_json" | jq -r --arg u "$u" '.data.users[]? | select(.username==$u) | .client_id' | head -n1)"
  if [[ -z "$exists_id" ]]; then
    email="$u@workers.beyo.dev"
    reg_resp="$(curl -sS -X POST "$BASE_URL/api/v1/auth/register" -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' -d "{\"username\":\"$u\",\"email\":\"$email\",\"password\":\"$BOOTPASS\",\"role_name\":\"worker\"}")"
    if [[ "$(echo "$reg_resp" | jq -r '.ok // false')" != "true" ]]; then
      fail "Register failed for $u: $reg_resp"
    fi
  fi
done

# 4) Resolve user IDs and task IDs from live API.
users_all="$(curl -sS -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE_URL/api/v1/users?limit=200")"
if [[ "$(echo "$users_all" | jq -r '.ok // false')" != "true" ]]; then
  fail "List users failed: $users_all"
fi

NOAH_ID="$(echo "$users_all" | jq -r '.data.users[] | select(.username=="noah_woods_57") | .client_id' | head -n1)"
LEO_ID="$(echo "$users_all" | jq -r '.data.users[] | select(.username=="leo_young_95") | .client_id' | head -n1)"
SOPHIA_ID="$(echo "$users_all" | jq -r '.data.users[] | select(.username=="sophia_morris_17") | .client_id' | head -n1)"
LIAM_ID="$(echo "$users_all" | jq -r '.data.users[] | select(.username=="liam_santos_63") | .client_id' | head -n1)"

if [[ -z "$NOAH_ID" || -z "$LEO_ID" || -z "$SOPHIA_ID" || -z "$LIAM_ID" ]]; then
  fail "Could not resolve requested user IDs"
fi

task_ids=()
while IFS= read -r line; do
  [[ -n "$line" ]] && task_ids+=("$line")
done < <(ssh -i "$SSH_KEY" "$SSH_HOST" "set -euo pipefail
DB_URL=\$(grep '^DATABASE_URL=' /home/ubuntu/config/managerbeyo/.env | cut -d= -f2- | sed 's|postgresql+asyncpg://|postgresql://|')
psql \"\$DB_URL\" -Atc \"select client_id from tasks where workspace_id='${workspace_id}' and coalesce(is_deleted,false)=false order by created_at asc\"
")

if (( ${#task_ids[@]} < 4 )); then
  fail "Need at least 4 tasks, found ${#task_ids[@]}"
fi

create_case() {
  local case_type_id="$1"
  local resp
  resp="$(curl -sS -X POST "$BASE_URL/api/v1/cases" -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' -d "{\"case_type_id\":\"$case_type_id\"}")"
  if [[ "$(echo "$resp" | jq -r '.ok // false')" != "true" ]]; then
    echo "Create case failed: $resp" >&2
    return 1
  fi
  echo "$resp" | jq -r '.data.case.client_id'
}

link_task() {
  local case_id="$1"
  local task_id="$2"
  local resp
  resp="$(curl -sS -X POST "$BASE_URL/api/v1/cases/$case_id/links" -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' -d "{\"case_client_id\":\"$case_id\",\"entity_type\":\"task\",\"entity_client_id\":\"$task_id\",\"role\":\"subject\"}")"
  [[ "$(echo "$resp" | jq -r '.ok // false')" == "true" ]] || { echo "Link task failed: $resp" >&2; return 1; }
}

add_participants() {
  local case_id="$1"
  local creator_id="$2"
  local resp
  resp="$(curl -sS -X POST "$BASE_URL/api/v1/cases/$case_id/participants" -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' -d "{\"case_client_id\":\"$case_id\",\"user_ids\":[\"$admin_id\",\"$creator_id\"]}")"
  [[ "$(echo "$resp" | jq -r '.ok // false')" == "true" ]] || { echo "Add participants failed: $resp" >&2; return 1; }
}

set_resolving() {
  local case_id="$1"
  local resp
  resp="$(curl -sS -X PATCH "$BASE_URL/api/v1/cases/$case_id/state" -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' -d "{\"case_client_id\":\"$case_id\",\"new_state\":\"resolving\"}")"
  [[ "$(echo "$resp" | jq -r '.ok // false')" == "true" ]] || { echo "Set resolving failed: $resp" >&2; return 1; }
}

# 5) Create six cases: 2,2,1,1 across first four tasks.
creators=(noah_woods_57 leo_young_95 sophia_morris_17 liam_santos_63 noah_woods_57 leo_young_95)
creator_ids=("$NOAH_ID" "$LEO_ID" "$SOPHIA_ID" "$LIAM_ID" "$NOAH_ID" "$LEO_ID")
case_types=(cty_seed_out_of_upholstery cty_seed_broken_tool cty_seed_cant_find_item cty_seed_out_of_upholstery cty_seed_broken_tool cty_seed_cant_find_item)
case_tasks=("${task_ids[0]}" "${task_ids[0]}" "${task_ids[1]}" "${task_ids[1]}" "${task_ids[2]}" "${task_ids[3]}")

: > /tmp/live_cases_created.tsv
for i in {0..5}; do
  uname="${creators[$i]}"
  uid="${creator_ids[$i]}"
  ct="${case_types[$i]}"
  tid="${case_tasks[$i]}"

  cid="$(create_case "$ct")"
  link_task "$cid" "$tid"
  add_participants "$cid" "$uid"

  printf "%s\t%s\t%s\t%s\topen\n" "$cid" "$tid" "$uname" "$uid" >> /tmp/live_cases_created.tsv
done

last_case_id="$(tail -n1 /tmp/live_cases_created.tsv | cut -f1)"
set_resolving "$last_case_id"

# Align created_by to requested creators in LIVE DB.
while IFS=$'\t' read -r cid _ _ uid _; do
  ssh -n -i "$SSH_KEY" "$SSH_HOST" "set -euo pipefail
DB_URL=\$(grep '^DATABASE_URL=' /home/ubuntu/config/managerbeyo/.env | cut -d= -f2- | sed 's|postgresql+asyncpg://|postgresql://|')
psql \"\$DB_URL\" -Atc \"update cases set created_by_id='${uid}', updated_by_id='${uid}' where client_id='${cid}'; update case_conversations set created_by_id='${uid}' where case_id='${cid}';\" >/dev/null
"
done < /tmp/live_cases_created.tsv

awk 'BEGIN{FS=OFS="\t"} {if(NR==6)$5="resolving"; print}' /tmp/live_cases_created.tsv > /tmp/live_cases_created_final.tsv

list_cases="$(curl -sS -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE_URL/api/v1/cases?limit=200")"

echo "Case types:"
echo "  out of upholstery -> cty_seed_out_of_upholstery"
echo "  broken tool -> cty_seed_broken_tool"
echo "  can't find item -> cty_seed_cant_find_item"
echo "Created cases:"
while IFS=$'\t' read -r cid tid who _ expected; do
  st="$(echo "$list_cases" | jq -r --arg cid "$cid" '.data.cases[]? | select(.client_id==$cid) | .state' | head -n1)"
  by="$(echo "$list_cases" | jq -r --arg cid "$cid" '.data.cases[]? | select(.client_id==$cid) | .created_by.username' | head -n1)"
  echo "  $cid | task=$tid | creator=$who | created_by=${by:-missing} | state=${st:-missing}"
done < /tmp/live_cases_created_final.tsv
