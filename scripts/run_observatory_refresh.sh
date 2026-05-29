#!/usr/bin/env sh
set -eu

: "${OBSERVATORY_LIMIT:=2000}"
exec python intelligence/run_intelligence_pipeline.py --limit "${OBSERVATORY_LIMIT}"
