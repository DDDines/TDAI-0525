#!/bin/sh
set -e
pip install -r requirements-backend.txt
export FIRST_SUPERUSER_EMAIL="admin@example.com"
export FIRST_SUPERUSER_PASSWORD="adminpass"
export ADMIN_EMAIL="admin@example.com"
export ADMIN_PASSWORD="adminpass"
if ! command -v pdftoppm >/dev/null 2>&1; then
    if [ -n "$POPPLER_PATH" ] && [ -x "$POPPLER_PATH/pdftoppm" ]; then
        export PATH="$POPPLER_PATH:$PATH"
    elif command -v apt-get >/dev/null 2>&1; then
        apt-get update && apt-get install -y poppler-utils
    fi
fi
if ! command -v pdftoppm >/dev/null 2>&1; then
    echo "pdftoppm not found. Install poppler-utils or set POPPLER_PATH." >&2
    exit 1
fi
pytest "$@"
