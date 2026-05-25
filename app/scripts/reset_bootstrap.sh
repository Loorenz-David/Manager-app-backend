#!/usr/bin/env bash
set -euo pipefail

# Reset + bootstrap helper for local/remote ManagerBeyo API.
#
# Usage examples:
#   bash scripts/reset_bootstrap.sh --base-url http://localhost:8000 --workspace-id ws_abc
#   BASE_URL=https://api.example.com WORKSPACE_ID=ws_abc RESET_SECRET=... BOOTSTRAP_SECRET=... bash scripts/reset_bootstrap.sh
#
# Required:
#   --workspace-id (or WORKSPACE_ID env var)
#
# Optional:
#   --base-url         Default: http://localhost:8000
#   --reset-secret     Default: local-reset-secret-dev
#   --bootstrap-secret Default: local-bootstrap-secret-dev
#   --skip-bootstrap   Only run reset
#   --skip-reset       Only run bootstrap

BASE_URL="${BASE_URL:-http://localhost:8000}"
WORKSPACE_ID="${WORKSPACE_ID:-}"
RESET_SECRET="${RESET_SECRET:-local-reset-secret-dev}"
BOOTSTRAP_SECRET="${BOOTSTRAP_SECRET:-local-bootstrap-secret-dev}"
SKIP_RESET=0
SKIP_BOOTSTRAP=0

log() {
    echo "[reset-bootstrap] $1"
}

usage() {
    cat <<'EOF'
Usage:
  reset_bootstrap.sh [options]

Options:
  --base-url <url>              API base URL (default: http://localhost:8000)
  --workspace-id <id>           Workspace ID to reset (or set WORKSPACE_ID env)
  --reset-secret <secret>       X-Reset-Secret value (or RESET_SECRET env)
  --bootstrap-secret <secret>   X-Bootstrap-Secret value (or BOOTSTRAP_SECRET env)
  --skip-reset                  Skip reset call
  --skip-bootstrap              Skip bootstrap call
  -h, --help                    Show this help

Environment equivalents:
  BASE_URL, WORKSPACE_ID, RESET_SECRET, BOOTSTRAP_SECRET
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-url)
            BASE_URL="$2"
            shift 2
            ;;
        --workspace-id)
            WORKSPACE_ID="$2"
            shift 2
            ;;
        --reset-secret)
            RESET_SECRET="$2"
            shift 2
            ;;
        --bootstrap-secret)
            BOOTSTRAP_SECRET="$2"
            shift 2
            ;;
        --skip-reset)
            SKIP_RESET=1
            shift
            ;;
        --skip-bootstrap)
            SKIP_BOOTSTRAP=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if [[ "$SKIP_RESET" -eq 0 && -z "$WORKSPACE_ID" ]]; then
    echo "Error: --workspace-id (or WORKSPACE_ID) is required unless --skip-reset is used." >&2
    usage
    exit 1
fi

if [[ "$SKIP_RESET" -eq 1 && "$SKIP_BOOTSTRAP" -eq 1 ]]; then
    echo "Error: both --skip-reset and --skip-bootstrap are set; nothing to do." >&2
    exit 1
fi

BASE_URL="${BASE_URL%/}"

call_endpoint() {
    local method="$1"
    local url="$2"
    local secret_header_name="$3"
    local secret_value="$4"

    local response
    response=$(curl -sS -w '\n%{http_code}' -X "$method" "$url" \
        -H "${secret_header_name}: ${secret_value}" \
        -H "Content-Type: application/json")

    local status
    local body
    status=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    echo "$status" "$body"
}

if [[ "$SKIP_RESET" -eq 0 ]]; then
    RESET_URL="${BASE_URL}/api/v1/reset?workspace_id=${WORKSPACE_ID}"
    log "Calling reset: DELETE ${RESET_URL}"

    read -r reset_status reset_body < <(call_endpoint "DELETE" "$RESET_URL" "X-Reset-Secret" "$RESET_SECRET")
    echo "reset.status=${reset_status}"
    echo "reset.body=${reset_body}"

    if [[ "$reset_status" -lt 200 || "$reset_status" -ge 300 ]]; then
        log "Reset failed"
        exit 1
    fi
fi

if [[ "$SKIP_BOOTSTRAP" -eq 0 ]]; then
    BOOTSTRAP_URL="${BASE_URL}/api/v1/bootstrap"
    log "Calling bootstrap: POST ${BOOTSTRAP_URL}"

    read -r bootstrap_status bootstrap_body < <(call_endpoint "POST" "$BOOTSTRAP_URL" "X-Bootstrap-Secret" "$BOOTSTRAP_SECRET")
    echo "bootstrap.status=${bootstrap_status}"
    echo "bootstrap.body=${bootstrap_body}"

    if [[ "$bootstrap_status" -lt 200 || "$bootstrap_status" -ge 300 ]]; then
        log "Bootstrap failed"
        exit 1
    fi

    if command -v jq >/dev/null 2>&1; then
        new_workspace_id=$(echo "$bootstrap_body" | jq -r '.data.workspace_id // empty' 2>/dev/null || true)
        if [[ -n "$new_workspace_id" ]]; then
            echo "bootstrap.workspace_id=${new_workspace_id}"
        fi
    fi
fi

log "Done"
