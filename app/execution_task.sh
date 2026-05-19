set -e
BASE_URL="http://127.0.0.1:8000"
ADMIN_EMAIL="admin@beyo.dev"
ADMIN_PASS="Admin1234!"
WORKER_EMAIL="nw_1747655692@beyo.dev"
WORKER_PASS="Test1234!"

# 1. Login
ADMIN_TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/sign-in" -H "Content-Type: application/json" -d "{\"email\": \"$ADMIN_EMAIL\", \"password\": \"$ADMIN_PASS\"}" | jq -r ".access_token // .data.access_token")
if [ "$ADMIN_TOKEN" = "null" ]; then echo "Admin login failed"; exit 1; fi

WORKER_TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/sign-in" -H "Content-Type: application/json" -d "{\"email\": \"$WORKER_EMAIL\", \"password\": \"$WORKER_PASS\"}" | jq -r ".access_token // .data.access_token")
if [ "$WORKER_TOKEN" = "null" ]; then echo "Worker login failed"; exit 1; fi

# 2. Resolve worker client_id
WORKER_ID=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE_URL/api/v1/users?limit=200" | jq -r ".data.users[] | select(.email == \"$WORKER_EMAIL\") | .client_id")
if [ -z "$WORKER_ID" ]; then echo "Worker ID not found"; exit 1; fi

# 3. Pick first task+step
TASKS_JSON=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE_URL/api/v1/tasks?limit=10")
TASK_ID=$(echo "$TASKS_JSON" | jq -r ".data.tasks_pagination.items[0].task.client_id // empty")
if [ -z "$TASK_ID" ]; then echo "No task found"; exit 1; fi
STEP_ID=$(curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE_URL/api/v1/tasks/$TASK_ID" | jq -r ".data.task_steps[0].client_id // empty")
if [ -z "$STEP_ID" ]; then echo "No step found"; exit 1; fi

echo "Triggering assign: Task=$TASK_ID, Step=$STEP_ID, Worker=$WORKER_ID"

# 4. Trigger assign-worker
curl -s -X POST "$BASE_URL/api/v1/tasks/$TASK_ID/steps/$STEP_ID/assign-worker" -H "Authorization: Bearer $ADMIN_TOKEN" -H "Content-Type: application/json" -d "{\"worker_id\": \"$WORKER_ID\"}" -o /dev/null

# 5. Wait 3 seconds
sleep 3

# 6. Query latest 8 execution_tasks
echo "--- Execution Tasks ---"
PGPASSWORD=postgres psql -h localhost -p 5433 -U postgres -d beyo_manager -c "SELECT task_type::text, state, last_error, created_at FROM execution_tasks WHERE task_type::text IN ('send_push_notification','SEND_PUSH_NOTIFICATION','create_notifications','CREATE_NOTIFICATIONS') ORDER BY created_at DESC LIMIT 8;"

# 7. Tail log
echo "--- Log Excerpts ---"
tail -n 80 /tmp/mb_notification_worker.log | grep -Ei 'push failed|WebPush|status=' || echo "No matching lines in log."
