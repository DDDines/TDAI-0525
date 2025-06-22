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
    else
        echo "pdftoppm not found. Install poppler-utils or set POPPLER_PATH." >&2
        exit 1
    fi
fi
pytest "$@"
