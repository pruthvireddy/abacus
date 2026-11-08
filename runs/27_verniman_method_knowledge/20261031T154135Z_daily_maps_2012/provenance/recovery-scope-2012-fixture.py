"""No-network supported-year and exact review-scope guards."""
import contextlib
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
spec = importlib.util.spec_from_file_location('recovery_scope_fixture', root / 'studies/27_verniman_method_knowledge/recover_archived_daily_maps.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
checks = {}


def identity(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(root).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value))
    return identity(path)


with tempfile.TemporaryDirectory(prefix='verniman-2012-scope-fixture-', dir=root / 'work') as temp:
    fixture = Path(temp)
    html = fixture / 'original.html'
    html.write_text('<h3 class="post-title">Outlook 01/02</h3><div class="post-body">Original opening plan.</div>')
    post = {'source_post_id': 'scope-fixture', 'role': 'daily_plan_candidate', 'reviewed_daily_plan': True,
            'title': 'Outlook 01/02', 'url': 'https://verniman.blogspot.com/2012/01/fixture.html',
            'session_date': '2012-01-02', 'year_evidence': {'year': 2012},
            'source_format': 'archived_html', 'html': identity(html), 'images': [],
            'archive_url': 'https://web.archive.org/web/20120103000000id_/http://verniman.blogspot.com/2012/01/fixture.html'}
    source_post = fixture / 'post.json'
    post['post_record'] = write(source_post, post.copy())
    recovery = {'requested_start_date': '2012-01-01', 'anchor_session_date': '2012-12-31',
                'image_capture_status': 'completed', 'posts': [post], 'files': [identity(html), identity(source_post)]}
    recovery_path = fixture / 'recovery.json'
    precheck = {'status': 'passed', 'selected_source_ids': ['scope-fixture'], 'selected_records': 1,
                'dated': 1, 'undated': 0, 'image_references': 0, 'unique_image_hashes': 0, 'overlaps': []}
    precheck_path = fixture / 'precheck.json'
    scope = {'requested_start_date': '2012-01-01', 'anchor_session_date': '2012-12-31',
             'lower_boundary_observed': False, 'historical_full_year_completeness_claimed': False}
    chronology = fixture / 'chronology.json'
    completion = fixture / 'completion.json'
    review = {'schema_version': 'daily-map-archive-source-review-1', 'review_status': 'reviewed',
              **scope, 'source_recovery_manifest': write(recovery_path, recovery),
              'selection_precheck': write(precheck_path, precheck), 'chronology_review': write(chronology, scope),
              'collection_completion_review': write(completion, scope), 'supporting_files': []}
    review_path = fixture / 'review.json'
    write(review_path, review)

    def project(name='selected.json', year=2012):
        with contextlib.redirect_stdout(io.StringIO()):
            module.reviewed_collection(SimpleNamespace(root=root, year=year, review_selection=review_path, reviewed_output=fixture / name))
        return json.loads((fixture / name).read_text())

    def reject(name, edit, restore, year=2012):
        edit()
        try:
            project(name + '.json', year)
        except ValueError:
            checks[name] = True
        else:
            raise AssertionError(name)
        restore()

    selected = project()
    assert selected['requested_start_date'] == '2012-01-01' and selected['anchor_session_date'] == '2012-12-31'
    assert len(selected['coverage']) == 366 and selected['coverage'][0]['session_date'] == '2012-01-01' and selected['coverage'][-1]['session_date'] == '2012-12-31'
    checks['explicit_2012_scope_and_366_calendar_projection'] = True
    assert sum(r['session_date'] == '2012-02-29' for r in selected['coverage']) == 1
    assert sum(r['session_date'].startswith('2012-02-') for r in selected['coverage']) == 29
    checks['leap_day_and_all_29_February_dates_retained'] = True
    reject('2012_review_rejected_for_requested_2015', lambda: None, lambda: None, 2015)
    original = recovery.copy()
    def recovery_changed():
        changed = {**recovery, 'requested_start_date': '2015-01-01', 'anchor_session_date': '2015-12-31'}
        review['source_recovery_manifest'] = write(recovery_path, changed); write(review_path, review)
    def recovery_restored():
        review['source_recovery_manifest'] = write(recovery_path, recovery); write(review_path, review)
    reject('cross_year_raw_recovery_rejected', recovery_changed, recovery_restored)
    def chronology_changed():
        review['chronology_review'] = write(chronology, {**scope, 'anchor_session_date': '2015-12-31'});write(review_path, review)
    def chronology_restored():
        review['chronology_review'] = write(chronology, scope);write(review_path, review)
    reject('cross_year_chronology_review_rejected', chronology_changed, chronology_restored)
    def source_changed():
        post['session_date'] = '2015-01-02';post['year_evidence'] = {'year': 2015}
        review['source_recovery_manifest'] = write(recovery_path, recovery);write(review_path, review)
    def source_restored():
        post['session_date'] = '2012-01-02';post['year_evidence'] = {'year': 2012}
        review['source_recovery_manifest'] = write(recovery_path, recovery);write(review_path, review)
    reject('cross_year_selected_source_rejected', source_changed, source_restored)
    for year in [2011, 2016]:
        try:
            module.requested_scope(year)
        except ValueError:
            checks[f'unsupported_year_{year}_rejected'] = True
    image_stage = fixture / 'image-stage';image_stage.mkdir()
    write(image_stage / 'source-recovery-manifest.json', {'requested_start_date': '2015-01-01', 'anchor_session_date': '2015-12-31', 'image_capture_status': 'pending', 'files': []})
    try:
        module.complete_images(SimpleNamespace(root=root, stage=image_stage, year=2012, feed_manifest=[], supplement_posts=[]))
    except ValueError:
        checks['cross_year_image_stage_rejected_before_mutation'] = True
    assert not (image_stage / 'capture-images-producer.py').exists()

assert len(checks) == 9 and all(checks.values())
print(json.dumps({'status': 'passed', 'checks': checks, 'check_count': len(checks), 'network_requests': 0, 'temporary_fixture_only': True}, indent=2))
