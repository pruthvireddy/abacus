#!/usr/bin/env python3
"""Explicit ranked extension lifecycle; all writes use a fresh work stage."""
import argparse
import json
from pathlib import Path
import sys

STUDY = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY / 'src'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['freeze', 'audit', 'execute', 'render', 'parity', 'verify', 'publish', 'seal'])
    parser.add_argument('--run-id')
    parser.add_argument('--stage', type=Path)
    args = parser.parse_args()
    import lifecycle
    import ranked_lifecycle
    if args.command == 'freeze':
        if not args.run_id:
            parser.error('freeze requires --run-id')
        frozen_stage = lifecycle.freeze_run(args.run_id)
        lifecycle.dump(frozen_stage / 'config.json', {
            'protocol_version': '2.0.0', 'settings_yaml': (STUDY / 'study.yaml').read_text(),
            'settings_sha256': lifecycle.digest(STUDY / 'study.yaml'),
            'qualification': 'Exact frozen settings text; numerical execution also pins its study-local source constants.'})
        (frozen_stage / 'inputs.lock.json').write_bytes((STUDY / 'inputs.lock.json').read_bytes())
        result = str(frozen_stage)
    else:
        if not args.stage:
            parser.error('command requires --stage')
        if args.command == 'verify':
            import verify_saved
            import verify_ranked
            result = {'baseline': verify_saved.verify(args.stage), 'ranked': verify_ranked.verify(args.stage)}
        elif args.command == 'publish':
            import publish_ranked
            result = publish_ranked.build(args.stage, run_id=args.run_id or lifecycle.load(args.stage / 'freeze.json')['run_id'])
        else:
            result = getattr(ranked_lifecycle, args.command)(args.stage)
    print(json.dumps(result, sort_keys=True, default=str))


if __name__ == '__main__':
    main()
