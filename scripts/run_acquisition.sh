#!/usr/bin/env sh
set -eu

exec python pipelines/run_labor_acquisition_platform.py "$@"

