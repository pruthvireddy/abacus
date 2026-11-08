#!/usr/bin/env python3
"""Independent actual-body/context and empty daily selection review for 2013."""
import gzip
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin

sys.dont_write_bytecode = True
ROOT = Path('/Users/pruthvi/Documents/projects/abacus')
REC = ROOT / 'work/27_verniman_method_knowledge/20261031T152738Z_daily_maps_2013_recovery'
spec = importlib.util.spec_from_file_location('independent2013bodies', Path('/private/tmp/verniman-2013-audit-capture.py'))
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)
checked = {}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def textkey(value):
    return re.sub(r'\s+', '', value)

def identity(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)}

def read(record):
    path = (ROOT / record['path']).resolve()
    path.relative_to(ROOT)
    raw = path.read_bytes()
    assert len(raw) == record['bytes'] and sha(raw) == record['sha256'], str(path)
    checked[str(path)] = record['sha256']
    return raw

raw = (REC / 'recovery-manifest.json').read_bytes()
manifest = json.loads(raw)
assert manifest['requested_start_date'] == '2013-01-01' and manifest['anchor_session_date'] == '2013-12-31'
assert manifest['image_capture_status'] == 'completed'
for record in manifest['files']:
    read(record)
posts = manifest['posts']
assert len(posts) == 28
old_archive = ROOT / 'work/27_verniman_method_knowledge/20261031T044414Z_daily_maps_2022/archive'
old_inventory_record = identity(old_archive / 'archive-manifest.json')
old_inventory = json.loads(read(old_inventory_record))
old_sources = {}
for rec in old_inventory['posts']:
    path = old_archive / rec['capsule'] / 'article.json.gz'
    data = json.loads(gzip.decompress(path.read_bytes()))
    old_sources[sha(textkey(data['full_text']).encode())] = {
        'session_date': data['session_date'], 'title': data['title'],
        'reader_capsule': rec['capsule'], 'article_metadata': identity(path)}

contexts = []
later_matches = []
image_hashes = set()
missing = inline = body_instances = source_image_elements = 0
for ordinal, post in enumerate(posts, 1):
    assert post['source_format'] in {'archived_html', 'archived_page_post'}
    original = read(post['html'])
    bodies = parser.Bodies()
    bodies.feed(original.decode('utf-8', 'replace'))
    assert len(bodies.rows) == post['post_body_count']
    assert textkey(''.join(''.join(body['parts']) for body in bodies.rows)) == textkey(post['body_text'])
    read(post['post_record'])
    elements = [(body, image) for body in bodies.rows for image in body['images']]
    assert len(elements) == len(post['actual_image_elements']) == len(post['images'])
    for (_, element), declared, saved in zip(elements, post['actual_image_elements'], post['images']):
        inline_url = urljoin(post['url'], element['inline'])
        linked_url = urljoin(post['url'], element['linked']) if element['linked'] else inline_url
        preferred = linked_url if re.search(r'(?:blogger\.googleusercontent\.com|bp\.blogspot\.com)/', linked_url) else inline_url
        assert declared['url'] == preferred and declared['inline_url'] == inline_url
        assert saved['original_image_url'] == preferred
        assert saved['historical_digest_match_verified'] is False
        source_image_elements += 1
        if saved['kind'] == 'missing_source_image':
            assert saved.get('error') and not saved.get('path')
            missing += 1
        else:
            assert saved['kind'] == 'current_source_image_fallback'
            assert saved['url'] == (inline_url if saved.get('rendition') == 'inline_thumbnail' else preferred)
            if saved.get('rendition') == 'inline_thumbnail':
                assert saved.get('full_size_error')
                inline += 1
            read(saved)
            image_hashes.add(saved['sha256'])
    summaries = []
    for body in bodies.rows:
        title = ' '.join(body['title'].split())
        full_text = ''.join(body['parts'])
        digest = sha(textkey(full_text).encode())
        record = {'source_post_id': body['id'], 'title': title,
                  'normalized_body_sha256': digest, 'image_elements': len(body['images']),
                  'ordered_body_links_sha256': sha(json.dumps(body['links'], ensure_ascii=False, separators=(',', ':')).encode())}
        if title in {'Monday recover', 'Dollar surges', 'Summer Friday'}:
            prior = old_sources.get(digest)
            assert prior is not None and prior['session_date'] in {'2022-05-23', '2022-07-12', '2022-07-29'}
            read(prior['article_metadata'])
            record['exclusion_reason'] = 'Actual complete daily-plan body exactly matches a retained 2022 plan; 2013 permalink is only a locator.'
            record['exact_frozen_2022_match'] = prior
            later_matches.append({'source_ordinal': ordinal, **record})
        else:
            assert not re.match(r'^(?:Outlook|Opening(?:\s+Print)?|(?:Market\s+)?Update)\b', title, re.I), ('unexpected candidate needs independent review', ordinal, title)
            record['exclusion_reason'] = 'General method, platform, motivational or embedded-video source; no supported prospective 2013 daily-plan identity established from actual title and body.'
        summaries.append(record)
        body_instances += 1
    contexts.append({'ordinal': ordinal, 'source_post_id': post.get('source_post_id'),
                     'title': post['title'], 'url': post['url'], 'archive_url': post['archive_url'],
                     'source_format': post['source_format'], 'source_html': post['html'],
                     'source_post_record': post['post_record'], 'body_count': len(bodies.rows),
                     'body_reviews': summaries, 'actual_image_elements': len(elements),
                     'exclusion_reason': 'No in-scope 2013 morning plan established; raw context retained.' if summaries else 'Observed index has zero article bodies; no daily source inferred.'})
assert len(later_matches) == 3
result = {'status': 'passed', 'scope': 'Independent full actual-body classification and all raw-image retention review; an empty observed selection does not establish historical absence.',
          'recovery_manifest': identity(REC / 'recovery-manifest.json'),
          'checked_unique_files': len(checked), 'raw_source_revisions': len(posts),
          'actual_post_body_instances': body_instances,
          'selected_records': 0, 'dated': 0, 'undated': 0, 'image_references': 0,
          'unique_image_hashes': 0, 'selected_source_ids': [], 'overlaps': [],
          'excluded_context_records': len(contexts),
          'multi_body_context_records': sum(x['body_count'] > 1 for x in contexts),
          'single_body_context_records': sum(x['body_count'] == 1 for x in contexts),
          'zero_body_context_records': sum(x['body_count'] == 0 for x in contexts),
          'raw_image_references': source_image_elements, 'unique_retained_raw_images': len(image_hashes),
          'raw_missing_images': missing, 'raw_inline_fallbacks': inline,
          'exact_later_year_full_body_matches': later_matches,
          'frozen_2022_inventory': old_inventory_record,
          'excluded_contexts': contexts, 'lower_boundary_observed': False,
          'historical_full_year_completeness_claimed': False}
print(json.dumps(result, indent=2))
