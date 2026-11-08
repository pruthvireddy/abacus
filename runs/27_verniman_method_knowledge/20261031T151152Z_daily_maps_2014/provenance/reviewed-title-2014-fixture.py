import copy
import hashlib
import html
import importlib.util
import json
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path('/Users/pruthvi/Documents/projects/abacus')
spec = importlib.util.spec_from_file_location('market_title_adapter', ROOT / 'studies/27_verniman_method_knowledge/capture_retained_daily_maps.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
checks = {}
with tempfile.TemporaryDirectory(prefix='daily-map-2014-reviewed-title-') as temporary:
    root = Path(temporary)
    def write(name, raw):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return {'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    review = write('review.json', b'{"synthetic":true,"status":"reviewed"}')
    def make(title='Market Update 0603', year=2014):
        body = 'Overnight inventory is short. First idea is an opening auction above value.'
        raw = ('<html><a name="12345"></a><h3 class="post-title">' + html.escape(title) + '</h3><div class="post-body">' + body + '</div></html>').encode()
        source = write('source.html', raw)
        post_record = write('post.json', b'{"source_post_id":"12345"}')
        classification = {'status': 'reviewed_morning_plan', 'source_post_id': '12345',
                          'source_title': title, 'source_post_record': post_record,
                          'normalized_body_sha256': adapter.digest(adapter.text_identity(body).encode()),
                          'session_date': f'{year}-06-03', 'reason': 'Synthetic body describes the expected open and overnight inventory.',
                          'year_context_reason': 'Synthetic contemporaneous archive observation.', 'review_record': review}
        post = {'url': f'https://verniman.blogspot.com/{year}/06/fixture.html', 'title': title,
                'session_date': f'{year}-06-03', 'html': source, 'post_record': post_record,
                'source_post_id': '12345', 'source_format': 'archived_html', 'images': [],
                'year_evidence': {'year': year}, 'reviewed_daily_plan': True,
                'date_review': {'status': 'dated_title', 'source_title': title},
                'daily_plan_classification_review': classification}
        document = {'requested_start_date': f'{year}-01-01', 'anchor_session_date': f'{year}-12-31',
                    'chronology_review': review, 'collection_completion_review': review,
                    'archive_capture_manifest': review, 'posts': [post], 'files': []}
        return document
    def prepare(document):
        record = write('collection.json', json.dumps(document).encode())
        year = int(document['requested_start_date'][:4])
        return adapter.Adapter(root).prepare(root / record['path'], date(year, 1, 1), date(year, 12, 31), record['sha256'])
    def reject(name, edit, **kwargs):
        document = make(**kwargs)
        edit(document['posts'][0])
        try:
            prepare(document)
        except (ValueError, KeyError):
            checks[name] = True
        else:
            raise AssertionError(name)
    for title in ['Market Update 0603', 'Market Update 06/03', 'Update 0603', 'Update 06/03']:
        _, prepared = prepare(make(title))
        assert prepared[0][0]['session_date'] == '2014-06-03'
    checks['explicit_market_title_MMDD_and_month_day_accepted'] = True
    undated = make('Market Update')
    upost = undated['posts'][0]
    upost['session_date'] = None
    upost['daily_plan_classification_review']['session_date'] = None
    upost['date_review']['status'] = 'undated_title_missing_month_day'
    upost['date_warnings'] = ['Source title omits exact date; retained without URL or image-date repair.']
    _, prepared = prepare(undated)
    assert prepared[0][0]['session_date'] is None
    checks['reviewed_undated_morning_plan_remains_null'] = True
    conflicted = copy.deepcopy(undated)
    raw = (root / 'source.html').read_text().replace('Overnight inventory', 'Market Update 0603. Overnight inventory').encode()
    conflicted['posts'][0]['html'] = write('source.html', raw)
    conflicted['posts'][0]['daily_plan_classification_review']['normalized_body_sha256'] = adapter.digest(adapter.text_identity('Market Update 0603. Overnight inventory is short. First idea is an opening auction above value.').encode())
    try:
        prepare(conflicted)
    except ValueError:
        checks['undated_body_explicit_date_requires_new_review'] = True
    else:
        raise AssertionError('undated body explicit date was ignored')
    reject('unreviewed_market_title_rejected', lambda p: p.pop('daily_plan_classification_review'))
    reject('missing_daily_review_rejected', lambda p: p.update(reviewed_daily_plan=False))
    reject('source_id_drift_rejected', lambda p: p['daily_plan_classification_review'].update(source_post_id='999'))
    reject('source_title_drift_rejected', lambda p: p['daily_plan_classification_review'].update(source_title='Market Update 0604'))
    reject('source_record_drift_rejected', lambda p: p['daily_plan_classification_review'].update(source_post_record={}))
    reject('body_hash_drift_rejected', lambda p: p['daily_plan_classification_review'].update(normalized_body_sha256='0' * 64))
    reject('classification_date_drift_rejected', lambda p: p['daily_plan_classification_review'].update(session_date='2014-06-04'))
    reject('empty_classification_reason_rejected', lambda p: p['daily_plan_classification_review'].update(reason=''))
    reject('empty_year_context_reason_rejected', lambda p: p['daily_plan_classification_review'].update(year_context_reason=''))
    reject('missing_review_pin_rejected', lambda p: p['daily_plan_classification_review'].pop('review_record'))
    reject('changed_review_pin_rejected', lambda p: p['daily_plan_classification_review']['review_record'].update(sha256='0' * 64))
    reject('unsupported_title_date_drift_rejected', lambda p: p.update(session_date='2014-06-04'))
    reject('new_family_not_implicitly_enabled_in_2015', lambda p: None, year=2015)
    reject('generic_undated_title_does_not_gain_date_from_URL', lambda p: None, title='Market Update')
    assert all(checks.values())
print(json.dumps({'status': 'passed', 'scope': 'Synthetic exact morning-classification identity and title-date guards only.', 'check_count': len(checks), 'checks': checks}, indent=2))
