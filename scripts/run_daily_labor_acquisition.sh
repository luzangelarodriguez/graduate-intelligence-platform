#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python}

exec "$PYTHON_BIN" "$ROOT_DIR/scripts/run_daily_labor_acquisition.py" "$@"
