#!/usr/bin/env sh
set -eu

exec python intelligence/run_intelligence_pipeline.py "$@"

