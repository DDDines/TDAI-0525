#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:?APP_ROOT is required}"
ACTIVE_SLOT_FILE="${ACTIVE_SLOT_FILE:-$APP_ROOT/shared/active-slot}"
LAST_SLOT_FILE="${LAST_SLOT_FILE:-$APP_ROOT/shared/last-slot}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_BLUE_PORT="${BACKEND_BLUE_PORT:-8001}"
BACKEND_GREEN_PORT="${BACKEND_GREEN_PORT:-8002}"
HEALTHCHECK_PATH="${HEALTHCHECK_PATH:-/health}"
HEALTHCHECK_TIMEOUT_SECONDS="${HEALTHCHECK_TIMEOUT_SECONDS:-30}"
NGINX_UPSTREAM_PATH="${NGINX_UPSTREAM_PATH:-/etc/nginx/conf.d/catalogai-upstream.conf}"
NGINX_TEST_COMMAND="${NGINX_TEST_COMMAND:-nginx -t}"
NGINX_RELOAD_COMMAND="${NGINX_RELOAD_COMMAND:-nginx -s reload}"
SKIP_NGINX_RELOAD="${SKIP_NGINX_RELOAD:-0}"
TARGET_SLOT="${TARGET_SLOT:-}"

if [[ -z "$TARGET_SLOT" && -f "$LAST_SLOT_FILE" ]]; then
  TARGET_SLOT="$(tr -d '[:space:]' < "$LAST_SLOT_FILE")"
fi

if [[ "$TARGET_SLOT" != "blue" && "$TARGET_SLOT" != "green" ]]; then
  echo "TARGET_SLOT must be blue or green, or LAST_SLOT_FILE must contain one of them." >&2
  exit 1
fi

if [[ "$TARGET_SLOT" == "blue" ]]; then
  target_port="$BACKEND_BLUE_PORT"
else
  target_port="$BACKEND_GREEN_PORT"
fi

wait_for_health() {
  local url="$1"
  local deadline=$((SECONDS + HEALTHCHECK_TIMEOUT_SECONDS))
  until curl --silent --show-error --fail "$url" >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
      return 1
    fi
    sleep 2
  done
}

render_upstream_config() {
  local port="$1"
  cat > "$NGINX_UPSTREAM_PATH" <<EOF
upstream catalogai_backend {
    server 127.0.0.1:${port};
    keepalive 32;
}
EOF
}

if ! wait_for_health "http://${BACKEND_HOST}:${target_port}${HEALTHCHECK_PATH}"; then
  echo "Target rollback slot ${TARGET_SLOT} is unhealthy on port ${target_port}." >&2
  exit 1
fi

backup_upstream=""
if [[ -f "$NGINX_UPSTREAM_PATH" ]]; then
  backup_upstream="$(mktemp)"
  cp "$NGINX_UPSTREAM_PATH" "$backup_upstream"
fi

render_upstream_config "$target_port"

if [[ "$SKIP_NGINX_RELOAD" != "1" ]]; then
  if ! bash -lc "$NGINX_TEST_COMMAND"; then
    if [[ -n "$backup_upstream" ]]; then
      cp "$backup_upstream" "$NGINX_UPSTREAM_PATH"
    fi
    echo "Nginx config test failed during rollback." >&2
    exit 1
  fi
  bash -lc "$NGINX_RELOAD_COMMAND"
fi

echo "$TARGET_SLOT" > "$ACTIVE_SLOT_FILE"
echo "Rollback completed. Active slot: ${TARGET_SLOT} (port ${target_port})."
