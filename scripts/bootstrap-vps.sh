#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:?APP_ROOT is required}"
DOMAIN="${DOMAIN:?DOMAIN is required}"
APP_USER="${APP_USER:-${SUDO_USER:-}}"
BACKEND_BLUE_PORT="${BACKEND_BLUE_PORT:-8001}"
BACKEND_GREEN_PORT="${BACKEND_GREEN_PORT:-8002}"
REDIS_PORT="${REDIS_PORT:-6379}"
NGINX_SITE_PATH="${NGINX_SITE_PATH:-/etc/nginx/sites-available/commercefolio.conf}"
NGINX_ENABLED_PATH="${NGINX_ENABLED_PATH:-/etc/nginx/sites-enabled/commercefolio.conf}"
NGINX_UPSTREAM_PATH="${NGINX_UPSTREAM_PATH:-/etc/nginx/conf.d/commercefolio-upstream.conf}"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
TEMPLATE_PATH="${TEMPLATE_PATH:-$PROJECT_ROOT/deploy/vps/nginx/commercefolio-site.conf.template}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute bootstrap-vps.sh as root." >&2
  exit 1
fi

apt-get update
apt-get install -y \
  curl \
  git \
  nginx \
  poppler-utils \
  ca-certificates \
  gnupg \
  python3 \
  python3-pip \
  python3-venv \
  redis-server \
  tesseract-ocr

if ! command -v node >/dev/null 2>&1 || ! node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 18 ? 0 : 1)'; then
  apt-get remove -y nodejs npm libnode-dev nodejs-doc >/dev/null 2>&1 || true
  apt-get autoremove -y >/dev/null 2>&1 || true
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi

systemctl enable redis-server nginx

if redis-cli -p "$REDIS_PORT" ping >/dev/null 2>&1; then
  echo "Redis ja esta acessivel na porta ${REDIS_PORT}; bootstrap vai reutilizar a instancia existente."
else
  systemctl restart redis-server
fi

mkdir -p \
  "$APP_ROOT/releases" \
  "$APP_ROOT/shared/logs" \
  "$APP_ROOT/shared/run"

touch "$APP_ROOT/shared/active-slot" "$APP_ROOT/shared/last-slot"

cat > "$NGINX_UPSTREAM_PATH" <<EOF
upstream commercefolio_backend {
    server 127.0.0.1:${BACKEND_BLUE_PORT};
    keepalive 32;
}
EOF

if [[ ! -f "$TEMPLATE_PATH" ]]; then
  echo "Nginx template not found: $TEMPLATE_PATH" >&2
  exit 1
fi

sed \
  -e "s|__DOMAIN__|${DOMAIN}|g" \
  -e "s|__APP_ROOT__|${APP_ROOT}|g" \
  "$TEMPLATE_PATH" > "$NGINX_SITE_PATH"

ln -sfn "$NGINX_SITE_PATH" "$NGINX_ENABLED_PATH"
nginx -t
systemctl reload nginx

if [[ -n "${APP_USER:-}" ]]; then
  chown -R "$APP_USER":"$APP_USER" "$APP_ROOT"
fi

cat <<EOF
Bootstrap concluido.
- APP_ROOT: $APP_ROOT
- DOMAIN: $DOMAIN
- blue port: $BACKEND_BLUE_PORT
- green port: $BACKEND_GREEN_PORT

Proximos passos:
1. Copie Project/.env.example para $APP_ROOT/shared/.env e ajuste os valores reais.
2. Configure os secrets do GitHub Actions: VPS_HOST, VPS_USER, VPS_APP_ROOT e VPS_SSH_KEY.
3. Rode o workflow Deploy CommerceFolio to VPS em modo deploy.
EOF
