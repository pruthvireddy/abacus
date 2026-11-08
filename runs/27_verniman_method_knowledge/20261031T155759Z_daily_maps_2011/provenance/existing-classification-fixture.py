"""No-network exact-source classification guards, not historical membership advice."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode = True
root = Path('/Users/pruthvi/Documents/projects/abacus')
spec = importlib.util.spec_from_file_location('morning_fixture', root / 'studies/27_verniman_method_knowledge/recover_archived_daily_maps.py')
module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
verifier = module.PARSER.Adapter(root)
recovery = json.loads((root / 'work/27_verniman_method_knowledge/20261031T151152Z_daily_maps_2014_recovery/recovery-manifest.json').read_text())
chosen = [next(p for p in recovery['posts'] if p['title'] == title) for title in ['Market Update 0603', 'Update 0904', 'Market Update']]
checks = {}


def descriptor(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(root).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value));return descriptor(path)


def decision(post, day):
    return {'status': 'reviewed_morning_plan', 'source_post_id': post['source_post_id'], 'source_title': post['title'],
            'source_post_record': post['post_record'], 'normalized_body_sha256': module.sha(module.PARSER.text_identity(post['body_text']).encode()),
            'session_date': day, 'reason': 'Synthetic fixture guard only; does not establish historical morning-plan membership.',
            'year_context_reason': 'Synthetic fixture scope branch only; not a historical year-context assessment.'}


with tempfile.TemporaryDirectory(prefix='verniman-2014-classification-fixture-', dir=root / 'work') as temporary:
    fixture = Path(temporary);review_path = fixture / 'review.json'
    write(review_path, {'fixture': 'temporary independent review identity'})
    review_record = descriptor(review_path)
    decisions = [decision(p, d) for p, d in zip(chosen, ['2014-06-03', '2014-09-04', None])]
    def classify(post, review, year=2014):
        return module.reviewed_morning_classification(copy.deepcopy(post), copy.deepcopy(review), review_record, verifier, year)
    dated = classify(chosen[0], decisions[0]);assert dated['session_date'] == '2014-06-03' and dated['role'] == 'daily_plan_candidate'
    checks['exact_dated_market_update_review_accepted_without_raw_change'] = True
    updated = classify(chosen[1], decisions[1]);assert updated['session_date'] == '2014-09-04' and any('publication claim' in w for w in updated['date_warnings'])
    assert updated['source_published_at'] == chosen[1]['source_published_at']
    checks['exact_update_MMDD_keeps_publication_conflict_warning'] = True
    undated = classify(chosen[2], decisions[2]);assert undated['session_date'] is None and undated['date_review']['status'] == 'undated_title_missing_month_day' and undated['date_warnings']
    checks['exact_reviewed_generic_market_update_remains_undated'] = True
    assert all(p.get('role') == 'excluded_context_candidate' and not p.get('reviewed_daily_plan') for p in chosen)
    assert dated['daily_plan_classification_review']['review_record'] == review_record
    checks['raw_classification_unchanged_and_review_pin_retained'] = True
    def reject(name, change, post=chosen[0], year=2014):
        review = copy.deepcopy(decisions[0]);change(review)
        try:classify(post, review, year)
        except ValueError:checks[name] = True
        else:raise AssertionError(name)
    reject('classification_cross_year_rejected', lambda d: None, year=2015)
    reject('classification_post_id_drift_rejected', lambda d: d.update(source_post_id='wrong'))
    reject('classification_post_record_drift_rejected', lambda d: d['source_post_record'].update(sha256='0' * 64))
    reject('classification_title_drift_rejected', lambda d: d.update(source_title='Market Update 0604'))
    reject('classification_body_hash_drift_rejected', lambda d: d.update(normalized_body_sha256='0' * 64))
    reject('classification_title_date_repair_rejected', lambda d: d.update(session_date='2014-06-04'))
    reject('classification_empty_reason_rejected', lambda d: d.update(reason=''))
    reject('classification_missing_year_context_rejected', lambda d: d.update(year_context_reason=''))
    wrong = copy.deepcopy(chosen[0]);wrong['body_text'] += 'metadata drift'
    reject('classification_metadata_body_drift_rejected', lambda d: None, post=wrong)
    wrong = copy.deepcopy(chosen[0]);wrong['title'] = '$ES_F Update';wrong_decision = decision(wrong, None)
    try:classify(wrong, wrong_decision)
    except ValueError:checks['unsupported_generic_update_family_rejected'] = True
    synthetic = fixture / 'generic-update.html';synthetic.write_text('<a name="fixture"></a><h3 class="post-title">Update</h3><div class="post-body">Synthetic body.</div>')
    raw = {'source_post_id': 'fixture', 'title': 'Update', 'url': 'https://verniman.blogspot.com/2014/01/fixture.html', 'body_text': 'Synthetic body.', 'source_format': 'archived_html', 'html': descriptor(synthetic)}
    raw_record = fixture / 'generic-post.json';raw['post_record'] = write(raw_record, raw.copy())
    try:classify(raw, decision(raw, None))
    except ValueError:checks['undated_bare_update_without_approved_grammar_rejected'] = True

    precheck = {'status': 'passed', 'selected_source_ids': [p['source_post_id'] for p in chosen], 'selected_records': 3, 'dated': 2, 'undated': 1,
                'image_references': sum(len(p['images']) for p in chosen), 'unique_image_hashes': len({im['sha256'] for p in chosen for im in p['images']}), 'overlaps': []}
    scope = {'requested_start_date': '2014-01-01', 'anchor_session_date': '2014-12-31', 'lower_boundary_observed': False, 'historical_full_year_completeness_claimed': False}
    recovery_file = fixture / 'recovery.json';selected_raw = {**recovery, 'posts': chosen}
    review = {'schema_version': 'daily-map-archive-source-review-1', 'review_status': 'reviewed', **scope,
              'source_recovery_manifest': write(recovery_file, selected_raw), 'selection_precheck': write(fixture / 'precheck.json', precheck),
              'chronology_review': write(fixture / 'chronology.json', scope), 'collection_completion_review': write(fixture / 'completion.json', scope),
              'daily_plan_classification_reviews': {d['source_post_id']: d for d in decisions}}
    write(review_path, review)
    def project(name):
        output = fixture / name
        with contextlib.redirect_stdout(io.StringIO()):module.reviewed_collection(SimpleNamespace(root=root, year=2014, review_selection=review_path, reviewed_output=output))
        return json.loads(output.read_text())
    selected = project('collection.json');assert len(selected['posts']) == 3 and len(selected['coverage']) == 365 and sum(p['session_date'] is None for p in selected['posts']) == 1
    assert all(p['daily_plan_classification_review']['review_record'] == descriptor(review_path) for p in selected['posts'])
    checks['projection_requires_and_pins_explicit_classification_reviews'] = True
    review['daily_plan_classification_reviews'] = {};write(review_path, review)
    try:project('missing-review.json')
    except ValueError:checks['raw_context_without_explicit_review_not_promoted'] = True

assert len(checks) == 17 and all(checks.values())
print(json.dumps({'status': 'passed', 'checks': checks, 'check_count': len(checks), 'network_requests': 0, 'temporary_fixture_only': True}, indent=2))
