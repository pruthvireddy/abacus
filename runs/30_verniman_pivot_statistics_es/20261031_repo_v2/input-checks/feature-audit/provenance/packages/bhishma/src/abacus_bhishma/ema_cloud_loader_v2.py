"""Explicit pinned loader for the continuous 1.1.0 cloud delivery.

The 1.0.0 branch delegates to its existing public loader without changing that
loader's behavior. This module never rebuilds or repairs released files.
"""
from pathlib import Path

import pyarrow.parquet as pq

from .ema_cloud import load_release as load_v1
from .manifest_selection import read_pinned_manifest, require_identity, selected_files

DATASET_ID = 'same_contract_ema_cloud__1.1.0'
VERSION = '1.1.0'


def load_release(project_root: Path | str, *, product: str, interval: int,
                 manifest_path: Path | str, expected_manifest_sha256: str,
                 verify_selected_files: bool = True):
    manifest = read_pinned_manifest(project_root, manifest_path,
                                    expected_manifest_sha256, verify_selected_files)
    if manifest.get('dataset_id') == 'same_contract_ema_cloud__1.0.0':
        return load_v1(project_root, product=product, interval=interval,
                       manifest_path=manifest_path, expected_manifest_sha256=expected_manifest_sha256,
                       verify_selected_files=verify_selected_files)
    require_identity(manifest, {'dataset_id': DATASET_ID, 'version': VERSION})
    product = product.upper()
    if product not in ('ES', 'GC', 'NQ') or type(interval) is not int or interval not in (3, 5):
        raise ValueError('unsupported cloud product/interval')
    records = [r for r in manifest['output_files']
               if r.get('product') == product and r.get('interval_minutes') == interval]
    if len(records) != 1:
        raise ValueError('release must declare exactly one selected product/interval file')
    record = records[0]
    if record.get('role') != ('bars3' if interval == 3 else 'bars5features'):
        raise ValueError('incorrect cloud partition role')
    files = selected_files(project_root, manifest, lambda name: name == record['path'],
                           verify=verify_selected_files)
    frame = pq.ParquetFile(files[0]).read().to_pandas()
    if type(record.get('rows')) is not int or len(frame) != record['rows']:
        raise ValueError('cloud partition declared row count mismatch')
    if frame.empty or not frame['product'].eq(product).all() or not frame.interval_minutes.eq(interval).all():
        raise ValueError('cloud partition scientific identity mismatch')
    if frame.timestamp.duplicated().any() or not frame.timestamp.is_monotonic_increasing:
        raise ValueError('cloud partition must be unique and chronological')
    return frame
