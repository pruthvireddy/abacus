#!/bin/sh
set -eu
# Run from the Abacus workspace root. Restore code/ and delivery-code/ snapshots
# and configured input files first if source has changed.
# Recreate the locked environment if needed: ./scripts/uv sync --locked
task_run_dir="${1:-work/20_camarilla_ema_cloud_reversals/$(date -u +%Y%m%dT%H%M%SZ)_reproduction}"
.venv/bin/python studies/20_camarilla_ema_cloud_reversals/run.py freeze --work "$task_run_dir"
.venv/bin/python studies/20_camarilla_ema_cloud_reversals/run.py audit --work "$task_run_dir"
.venv/bin/python -m unittest discover -s studies/20_camarilla_ema_cloud_reversals/tests -v
.venv/bin/python studies/20_camarilla_ema_cloud_reversals/run.py score --work "$task_run_dir"
.venv/bin/python studies/20_camarilla_ema_cloud_reversals/run.py summarize --work "$task_run_dir"
.venv/bin/python studies/20_camarilla_ema_cloud_reversals/examples.py --work "$task_run_dir"
./scripts/uv run --with matplotlib==3.10.8 python studies/20_camarilla_ema_cloud_reversals/figures.py --work "$task_run_dir"
.venv/bin/python studies/20_camarilla_ema_cloud_reversals/run.py report --work "$task_run_dir"
.venv/bin/python studies/20_camarilla_ema_cloud_reversals/run.py verify --work "$task_run_dir"
