#!/bin/sh
set -e
pip install -r requirements-backend.txt
export FIRST_SUPERUSER_EMAIL="admin@example.com"
export FIRST_SUPERUSER_PASSWORD="adminpass"
export ADMIN_EMAIL="admin@example.com"
export ADMIN_PASSWORD="adminpass"
pytest "$@"
