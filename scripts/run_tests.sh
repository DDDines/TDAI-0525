#!/bin/sh
set -e
pip install -r requirements-backend.txt
pytest "$@"
