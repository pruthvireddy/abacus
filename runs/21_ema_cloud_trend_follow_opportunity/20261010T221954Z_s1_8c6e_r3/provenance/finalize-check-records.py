"""Retain actual independent review commands and close presentation review."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shlex

stage = Path(__file__).resolve().parents[1]
root = stage.parents[2]
commands_path = stage / 'provenance/commands.json'
commands = json.loads(commands_path.read_text())

def append(value):
    item = {key: value[key] for key in ('argv', 'cwd', 'environment') if key in value}
    assert item['argv'] and all(isinstance(x, str) and x for x in item['argv'])
    commands.append(item)

for name in ('comparisons-uncertainty-completion.json', 'comparisons-uncertainty-v2-completion.json'):
    append(json.loads((stage / 'provenance/reviews' / name).read_text())['exact_command'])
overlay = json.loads((stage / 'provenance/reviews/coverage-overlay-completion.json').read_text())
append({'argv': overlay['actual_argv'], 'cwd': overlay['cwd'], 'environment': overlay['environment_overrides']})
reporting = json.loads((stage / 'provenance/reviews/reporting-review-commands.json').read_text())
for item in reporting['commands']:
    tokens = shlex.split(item['exact_executed_command'])
    assert tokens.pop(0) == 'UV_CACHE_DIR=/private/tmp/abacus-study21-uv-cache'
    if '>' in tokens:
        tokens = tokens[:tokens.index('>')]
    append({'argv': tokens, 'cwd': item['cwd'], 'environment': {'UV_CACHE_DIR': '/private/tmp/abacus-study21-uv-cache'}})

for script in ('finalize-check-records.py', 'prepare-sealing.py', 'preflight-manifest.py'):
    append({'argv': ['./scripts/uv', 'run', '--locked', '--no-sync', 'python', str(stage / 'provenance' / script)],
            'cwd': str(root), 'environment': {'UV_CACHE_DIR': '/private/tmp/abacus-study21-uv-cache'}})
append({'argv': ['python3', 'scripts/check-evidence-bundle.py', str(stage), '--json'], 'cwd': str(root)})
append({'argv': ['./scripts/uv', 'run', '--locked', '--no-sync', 'python',
                 'studies/21_ema_cloud_trend_follow_opportunity/run.py', 'seal', '--stage', str(stage)],
        'cwd': str(root), 'environment': {'UV_CACHE_DIR': '/private/tmp/abacus-study21-uv-cache'}})
commands_path.write_text(json.dumps(commands, indent=2) + '\n')

correction_path = stage / 'provenance/presentation-correction.json'
correction = json.loads(correction_path.read_text())
correction['status'] = 'passed'
correction['independent_review_completed_at_utc'] = datetime.now(timezone.utc).isoformat()
correction['final_verification'] = []
for path in ('provenance/reviews/report-review.json', 'provenance/scientific-reconciliation.json'):
    data = (stage / path).read_bytes()
    assert json.loads(data)['status'] == 'passed'
    correction['final_verification'].append({'path': path, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
correction_path.write_text(json.dumps(correction, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'command_records': len(commands), 'presentation_review': 'passed'}))
