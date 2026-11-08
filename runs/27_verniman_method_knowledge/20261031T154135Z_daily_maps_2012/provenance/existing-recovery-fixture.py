"""No-network recovery/projection guards using retained source evidence."""
import argparse
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


def run(root, recovery_path, precheck_path):
    spec = importlib.util.spec_from_file_location('recovery_fixture', root / 'studies/27_verniman_method_knowledge/recover_archived_daily_maps.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checks = {}
    retained = root / 'data/raw/blogspot/verniman/archive_discovery/20261021T040541Z_2016_probe_d91128ed/archived_older_outlook_1230.response.body'
    article = module.Article(retained.read_text(), 'https://verniman.blogspot.com/2015/12/outlook-1230.html')
    assert article.title == 'Outlook 12/30' and article.body_count == 1 and len(article.images) == 4 and article.navigation
    checks['exact_retained_article_and_actual_images'] = True
    dated = module.classify(article, '2016-01-01T17:15:38+00:00', 2015)
    assert dated['session_date'] == '2015-12-30' and dated['requires_year_review']
    checks['late_year_source_requires_explicit_review'] = True
    assert module.title_month_day('Opening 0407') == (4, 7) and module.title_month_day('Opening Print') is None
    checks['explicit_MMDD_and_unresolved_title_distinct'] = True
    try:
        module.Recovery(root, Path('/private/tmp/uncreated-verniman-pacing-fixture'), 2015, 1, 20)
    except ValueError:
        checks['minimum_wayback_pacing_enforced'] = True
    element = {'url': 'https://1.bp.blogspot.com/x/s1600/chart.png', 'inline_url': 'https://1.bp.blogspot.com/x/s400/chart.png'}
    capture = module.Recovery.__new__(module.Recovery)
    capture.fetch_image = lambda url, ordinal, label: {'url': url, 'path': 'synthetic.png'}
    result = capture.fetch_element(element, 1)
    assert result['rendition'] == 'linked_full_image' and result['original_image_url'] == element['url']
    checks['linked_image_preferred'] = True
    capture.fetch_image = lambda url, ordinal, label: ({'url': url, 'error': 'HTTP404', 'attempts': [{'url': url, 'http_status': 404}]} if label == 'full' else {'url': url, 'path': 'synthetic.png'})
    result = capture.fetch_element(element, 1)
    assert result['rendition'] == 'inline_thumbnail' and result['url'] == element['inline_url'] and result['original_image_url'] == element['url'] and result['full_size_attempts']
    checks['exact_inline_fallback_with_failed_full_identity'] = True
    capture.fetch_image = lambda url, ordinal, label: {'url': url, 'error': 'HTTP404', 'attempts': [{'url': url, 'http_status': 404}]}
    result = capture.fetch_element(element, 1)
    assert result['kind'] == 'missing_source_image' and 'path' not in result and len(result['attempts']) == 2
    checks['missing_actual_image_retained_without_fake_path'] = True
    recovery = json.loads(recovery_path.read_text())
    feed = next(p for p in recovery['posts'] if p.get('source_format') == 'archived_atom_feed')['atom']
    with tempfile.TemporaryDirectory(prefix='verniman-2015-review-fixture-', dir=root / 'work') as temporary:
        fixture = Path(temporary)
        stage = fixture / 'images'; stage.mkdir(); (stage / 'images').mkdir()
        (stage / 'source-recovery-manifest.json').write_text(json.dumps({'posts': [], 'files': [], 'image_capture_status': 'pending'}))
        query = {'requested_url': feed['url'], 'status': 200, 'final_url': feed['final_url'], 'body': {**feed, 'path': str(root / feed['path'])}, 'completed_at': feed['captured_at'], 'body_truncated': False}
        feed_input = fixture / 'feed.json'; feed_input.write_text(json.dumps({'queries': [query]}))
        original = module.Recovery.fetch_element
        module.Recovery.fetch_element = lambda self, element, ordinal: {'kind': 'missing_source_image', 'url': element['url'], 'original_image_url': element['url'], 'error': 'No-network synthetic response', 'attempts': [], 'historical_digest_match_verified': False, 'source_revision_status': 'current_image_response_historical_bytes_unverified'}
        with contextlib.redirect_stdout(io.StringIO()):
            module.complete_images(SimpleNamespace(root=root, stage=stage, year=2015, feed_manifest=[feed_input], supplement_posts=[]))
        module.Recovery.fetch_element = original
        result = json.loads((stage / 'recovery-manifest.json').read_text())
        assert len(result['posts']) == 25 and all(p['source_entry_selector'] and p['source_feed_entry_ordinal'] for p in result['posts'])
        typo = result['posts'][20]
        assert typo['title'] == 'Outlook 28/10' and typo['session_date'] == '2015-10-28' and typo['date_review']['date_order'] == 'day_month' and typo['date_review']['corroborating_published_at'] == typo['source_published_at']
        checks['all_exact_feed_entries_and_DDMM_corroboration'] = True
        assert all(len(p['images']) == len(p['actual_image_elements']) for p in result['posts'])
        checks['missing_image_rows_do_not_omit_elements'] = True
        def identity(path):
            raw = path.read_bytes()
            return {'path': path.relative_to(root).as_posix(), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        precheck = fixture / 'precheck.json'; precheck.write_bytes(precheck_path.read_bytes())
        scope = {'kind': 'synthetic_guard_fixture_not_a_new_source_review', 'requested_start_date': '2015-01-01', 'anchor_session_date': '2015-12-31', 'lower_boundary_observed': False, 'historical_full_year_completeness_claimed': False}
        chronology = fixture / 'chronology.json'; chronology.write_text(json.dumps(scope))
        completion = fixture / 'completion.json'; completion.write_text(json.dumps(scope))
        supporting_file = fixture / 'support.json'; supporting_file.write_text(json.dumps({'fixture': 'durable supporting evidence'}))
        reasons = {str(p['source_post_id']): 'Synthetic guard fixture only: year-context branch exercise.' for p in recovery['posts'] if p.get('requires_year_review')}
        review = {'schema_version': 'daily-map-archive-source-review-1', 'review_status': 'reviewed', 'requested_start_date': '2015-01-01', 'anchor_session_date': '2015-12-31', 'historical_full_year_completeness_claimed': False, 'source_recovery_manifest': identity(recovery_path), 'selection_precheck': identity(precheck), 'chronology_review': identity(chronology), 'collection_completion_review': identity(completion), 'year_context_reviews': reasons, 'supporting_files': [identity(supporting_file)]}
        review_file = fixture / 'review.json'; review_file.write_text(json.dumps(review))
        output = fixture / 'collection.json'
        with contextlib.redirect_stdout(io.StringIO()):
            module.reviewed_collection(SimpleNamespace(root=root, review_selection=review_file, reviewed_output=output))
        selected = json.loads(output.read_text())
        assert len(selected['posts']) == 79 and len(selected['coverage']) == 365 and len(selected['excluded_context_posts']) == 63 and len(selected['unselected_supporting_revisions']) == 9
        assert sum(p['session_date'] is None for p in selected['posts']) == 14
        assert selected['supporting_files'] == review['supporting_files']
        assert review['supporting_files'][0] in selected['files']
        reused = [p['html'] for p in selected['posts'] if (p.get('html') or {}).get('reused_response_identity')]
        assert reused
        for response in reused:
            origin = response['reused_response_identity']
            assert 'path' not in origin and origin['original_path']
            assert origin['retained_payload'] == {key: response[key] for key in ['path', 'bytes', 'sha256']}
            original = next(p['html'] for p in recovery['posts'] if (p.get('html') or {}).get('path') == response['path'])
            assert original['reused_response_identity']['path'] == origin['original_path']
            assert {key: item for key, item in response.items() if key != 'reused_response_identity'} == {key: item for key, item in original.items() if key != 'reused_response_identity'}
        review['supporting_files'][0]['sha256'] = '0' * 64
        review_file.write_text(json.dumps(review))
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                module.reviewed_collection(SimpleNamespace(root=root, review_selection=review_file, reviewed_output=fixture / 'bad-support.json'))
        except ValueError as error:
            assert 'retained input identity mismatch' in str(error)
        else:
            raise AssertionError('supporting-file byte mismatch was accepted')
        review['supporting_files'] = [identity(supporting_file)]
        checks['explicit_review_projection_preserves_null_dates_and_support'] = True
        review['year_context_reviews'] = {}; review_file.write_text(json.dumps(review))
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                module.reviewed_collection(SimpleNamespace(root=root, review_selection=review_file, reviewed_output=fixture / 'bad.json'))
        except ValueError:
            checks['missing_late_year_review_rejected'] = True
    assert len(checks) == 11 and all(checks.values())
    return {'status': 'passed', 'check_count': len(checks), 'checks': checks, 'network_requests': 0, 'temporary_fixture_only': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--recovery', type=Path, required=True)
    parser.add_argument('--selection-precheck', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.root.resolve(), args.recovery.resolve(), args.selection_precheck.resolve()), indent=2))
