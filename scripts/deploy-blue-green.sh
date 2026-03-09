#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:?APP_ROOT is required}"
RELEASE_DIR="${RELEASE_DIR:?RELEASE_DIR is required}"
ENV_FILE="${ENV_FILE:-$APP_ROOT/shared/.env}"
ACTIVE_SLOT_FILE="${ACTIVE_SLOT_FILE:-$APP_ROOT/shared/active-slot}"
LAST_SLOT_FILE="${LAST_SLOT_FILE:-$APP_ROOT/shared/last-slot}"
RUN_DIR="${RUN_DIR:-$APP_ROOT/shared/run}"
LOG_DIR="${LOG_DIR:-$APP_ROOT/shared/logs}"
CURRENT_LINK="${CURRENT_LINK:-$APP_ROOT/current}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_BLUE_PORT="${BACKEND_BLUE_PORT:-8001}"
BACKEND_GREEN_PORT="${BACKEND_GREEN_PORT:-8002}"
HEALTHCHECK_PATH="${HEALTHCHECK_PATH:-/health}"
HEALTHCHECK_TIMEOUT_SECONDS="${HEALTHCHECK_TIMEOUT_SECONDS:-60}"
KEEP_PREVIOUS_SLOT_RUNNING="${KEEP_PREVIOUS_SLOT_RUNNING:-1}"
NGINX_UPSTREAM_PATH="${NGINX_UPSTREAM_PATH:-/etc/nginx/conf.d/catalogai-upstream.conf}"
NGINX_TEST_COMMAND="${NGINX_TEST_COMMAND:-nginx -t}"
NGINX_RELOAD_COMMAND="${NGINX_RELOAD_COMMAND:-nginx -s reload}"
SKIP_NGINX_RELOAD="${SKIP_NGINX_RELOAD:-0}"
API_V1_PREFIX="${API_V1_PREFIX:-/api/v1}"
SMOKE_RELEASE_ON_DEPLOY="${SMOKE_RELEASE_ON_DEPLOY:-1}"
SMOKE_TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-30}"
SMOKE_SCRIPT_PATH="${SMOKE_SCRIPT_PATH:-$RELEASE_DIR/scripts/smoke_release.py}"
SMOKE_ADMIN_EMAIL="${SMOKE_ADMIN_EMAIL:-${ADMIN_EMAIL:-}}"
SMOKE_ADMIN_PASSWORD="${SMOKE_ADMIN_PASSWORD:-${ADMIN_PASSWORD:-}}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
BACKEND_REQUIREMENTS_FILE="${BACKEND_REQUIREMENTS_FILE:-$RELEASE_DIR/requirements-backend-prod.txt}"

mkdir -p "$APP_ROOT/shared" "$RUN_DIR" "$LOG_DIR" "$APP_ROOT/releases"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [[ ! -d "$RELEASE_DIR" ]]; then
  echo "Release directory not found: $RELEASE_DIR" >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is required to build the frontend release." >&2
  exit 1
fi

if ! node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 18 ? 0 : 1)'; then
  echo "Node.js 18 or newer is required to build the frontend release." >&2
  exit 1
fi

current_slot=""
if [[ -f "$ACTIVE_SLOT_FILE" ]]; then
  current_slot="$(tr -d '[:space:]' < "$ACTIVE_SLOT_FILE")"
fi

if [[ "$current_slot" == "blue" ]]; then
  target_slot="green"
elif [[ "$current_slot" == "green" ]]; then
  target_slot="blue"
else
  target_slot="blue"
fi

if [[ "$target_slot" == "blue" ]]; then
  target_port="$BACKEND_BLUE_PORT"
else
  target_port="$BACKEND_GREEN_PORT"
fi

target_backend_pid="$RUN_DIR/backend-${target_slot}.pid"
target_worker_pid="$RUN_DIR/celery-${target_slot}.pid"
target_backend_log="$LOG_DIR/backend-${target_slot}.log"
target_worker_log="$LOG_DIR/celery-${target_slot}.log"

stop_pidfile() {
  local pid_file="$1"
  if [[ ! -f "$pid_file" ]]; then
    return 0
  fi
  local pid
  pid="$(tr -d '[:space:]' < "$pid_file")"
  if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
    sleep 2
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  fi
  rm -f "$pid_file"
}

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

stop_pidfile "$target_backend_pid"
stop_pidfile "$target_worker_pid"

if [[ ! -d "$RELEASE_DIR/.venv" ]]; then
  "$PYTHON_BIN" -m venv "$RELEASE_DIR/.venv"
fi

"$RELEASE_DIR/.venv/bin/python" -m pip install --upgrade pip
if [[ ! -f "$BACKEND_REQUIREMENTS_FILE" ]]; then
  BACKEND_REQUIREMENTS_FILE="$RELEASE_DIR/requirements-backend.txt"
fi
"$RELEASE_DIR/.venv/bin/pip" install -r "$BACKEND_REQUIREMENTS_FILE"

if [[ -f "$RELEASE_DIR/Frontend/app/package-lock.json" ]]; then
  (
    cd "$RELEASE_DIR/Frontend/app"
    npm ci
    npm run build
  )
fi

(
  cd "$RELEASE_DIR"
  export PYTHONPATH="$RELEASE_DIR"
  "$RELEASE_DIR/.venv/bin/python" "$RELEASE_DIR/scripts/upgrade_or_bootstrap_database.py" --config "$RELEASE_DIR/Backend/alembic.ini"
)

(
  cd "$RELEASE_DIR"
  export PYTHONPATH="$RELEASE_DIR"
  export BACKEND_HOST="$BACKEND_HOST"
  export BACKEND_PORT="$target_port"
  export BACKEND_RELOAD="false"
  export BACKEND_WORKERS="1"
  nohup "$RELEASE_DIR/.venv/bin/python" run_backend.py --host "$BACKEND_HOST" --port "$target_port" --reload false --workers 1 > "$target_backend_log" 2>&1 &
  echo $! > "$target_backend_pid"
)

(
  cd "$RELEASE_DIR"
  export PYTHONPATH="$RELEASE_DIR"
  nohup "$RELEASE_DIR/.venv/bin/celery" -A Backend.celery_app:celery_app worker --loglevel=INFO > "$target_worker_log" 2>&1 &
  echo $! > "$target_worker_pid"
)

if ! wait_for_health "http://${BACKEND_HOST}:${target_port}${HEALTHCHECK_PATH}"; then
  stop_pidfile "$target_backend_pid"
  stop_pidfile "$target_worker_pid"
  echo "New slot failed healthcheck on port ${target_port}." >&2
  exit 1
fi

if [[ "$SMOKE_RELEASE_ON_DEPLOY" == "1" ]]; then
  if [[ ! -f "$SMOKE_SCRIPT_PATH" ]]; then
    stop_pidfile "$target_backend_pid"
    stop_pidfile "$target_worker_pid"
    echo "Smoke script not found: $SMOKE_SCRIPT_PATH" >&2
    exit 1
  fi

  smoke_args=(
    --base-url "http://${BACKEND_HOST}:${target_port}"
    --api-prefix "$API_V1_PREFIX"
    --timeout "$SMOKE_TIMEOUT_SECONDS"
  )
  if [[ -n "$SMOKE_ADMIN_EMAIL" ]]; then
    smoke_args+=(--email "$SMOKE_ADMIN_EMAIL")
  fi
  if [[ -n "$SMOKE_ADMIN_PASSWORD" ]]; then
    smoke_args+=(--password "$SMOKE_ADMIN_PASSWORD")
  fi

  if ! "$RELEASE_DIR/.venv/bin/python" "$SMOKE_SCRIPT_PATH" "${smoke_args[@]}"; then
    stop_pidfile "$target_backend_pid"
    stop_pidfile "$target_worker_pid"
    echo "Smoke release checks failed for slot ${target_slot}." >&2
    exit 1
  fi
fi

backup_upstream=""
if [[ -f "$NGINX_UPSTREAM_PATH" ]]; then
  backup_upstream="$(mktemp)"
  cp "$NGINX_UPSTREAM_PATH" "$backup_upstream"
fi

ln -sfn "$RELEASE_DIR" "$CURRENT_LINK"
render_upstream_config "$target_port"

if [[ "$SKIP_NGINX_RELOAD" != "1" ]]; then
  if ! bash -lc "$NGINX_TEST_COMMAND"; then
    if [[ -n "$backup_upstream" ]]; then
      cp "$backup_upstream" "$NGINX_UPSTREAM_PATH"
    fi
    echo "Nginx config test failed after rendering upstream." >&2
    exit 1
  fi
  bash -lc "$NGINX_RELOAD_COMMAND"
fi

echo "${current_slot}" > "$LAST_SLOT_FILE"
echo "${target_slot}" > "$ACTIVE_SLOT_FILE"

if [[ "$KEEP_PREVIOUS_SLOT_RUNNING" != "1" ]]; then
  if [[ "$current_slot" == "blue" || "$current_slot" == "green" ]]; then
    stop_pidfile "$RUN_DIR/backend-${current_slot}.pid"
    stop_pidfile "$RUN_DIR/celery-${current_slot}.pid"
  fi
fi

echo "Blue-green deploy completed. Active slot: ${target_slot} (port ${target_port})."
