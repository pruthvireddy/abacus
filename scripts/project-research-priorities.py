#!/usr/bin/env python3
"""Explicit Sahadeva-to-Narada metadata publication; no research execution."""
import argparse
import datetime as dt
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
from research_priorities import Context, check_reviewed_inputs, date, project, read_json, validate_registry


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--check', action='store_true', help='Validate current registry/public projection without writing (default).')
    action.add_argument('--write', action='store_true', help='Explicitly project bounded public fields into the authored catalog.')
    action.add_argument('--check-reviewed-inputs', action='store_true', help='Separately hash the explicitly recorded local review materials.')
    action.add_argument('--mark-needs-review', metavar='STUDY_ID', help='Flag reassessment without replacing the dated score or evidence bindings.')
    parser.add_argument('--reason')
    parser.add_argument('--date', default=dt.datetime.now(ZoneInfo('America/New_York')).date().isoformat())
    args = parser.parse_args(argv)
    require_reason = bool(args.mark_needs_review)
    if require_reason != bool(args.reason):
        parser.error('--reason is required only with --mark-needs-review.')
    context = Context(args.root.resolve())
    file = context.root / 'strategies/research-priorities.json'
    registry = validate_registry(read_json(file), context)
    if args.mark_needs_review:
        date(args.date)
        records = [a for a in registry['assessments'] if a['studyId'] == args.mark_needs_review]
        if len(records) != 1:
            raise ValueError('Select one existing assessment study ID.')
        records[0]['reassessment'] = {'required': True, 'reason': args.reason, 'markedAt': args.date}
        validate_registry(registry, context)
        file.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
        print('Reassessment flagged; previous assessment retained. Run --write to publish its Needs review state.')
        return 0
    if args.check_reviewed_inputs:
        findings = check_reviewed_inputs(registry, context.root)
        print(json.dumps({'reviewedMaterials': sum(len(a['reviewedMaterials']) for a in registry['assessments']), 'findings': findings}, indent=2))
        return int(bool(findings))
    expected = project(registry, context)
    if args.write:
        context.catalog_path.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + '\n')
        print(f'Projected {len(registry["assessments"])} current editorial assessments into the app-owned catalog. No research executed.')
        return 0
    if context.catalog != expected:
        raise ValueError('Public priority projection is stale or manually changed; review the registry, then run --write.')
    print(f'Research-priority projection is current: {len(registry["assessments"])} assessments; exact public bindings verified. This is not scientific validation.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
