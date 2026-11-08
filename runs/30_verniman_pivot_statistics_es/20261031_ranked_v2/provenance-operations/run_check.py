"""Retain actual exit-bound local check attempts; never predeclare success."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
slug, *argv = sys.argv[1:]
if argv and argv[0] == '--':
    argv = argv[1:]
if not slug.replace('-', '').replace('_', '').isalnum() or not argv:
    raise SystemExit('Usage: run_check.py UNIQUE_SLUG -- COMMAND ARG ...')
directory = HERE / 'checks'
directory.mkdir(exist_ok=True)
log = directory / f'{slug}.log'
record = directory / f'{slug}.json'
if log.exists() or record.exists():
    raise SystemExit('Refusing to replace an existing check attempt')
started = time.time()
environment = {**os.environ, 'UV_CACHE_DIR': '/private/tmp/abacus-ranked-uv'}
try:
    result = subprocess.run(argv, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=1800)
    output, code = result.stdout + result.stderr, result.returncode
except subprocess.TimeoutExpired as exc:
    output, code = f'Timeout after 1800 seconds: {exc}', 124
log.write_text(output)
receipt = {'argv': argv, 'cwd': str(ROOT), 'exit_code': code,
           'status': 'passed' if code == 0 else 'failed',
           'elapsed_seconds': time.time() - started,
           'environment_overrides': {'UV_CACHE_DIR': environment['UV_CACHE_DIR']},
           'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()}
record.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
print(output[-4000:])
raise SystemExit(code)
