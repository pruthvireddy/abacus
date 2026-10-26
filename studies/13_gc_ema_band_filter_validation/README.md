# GC outer-band long filter selection

[Plan](plan.md) · [Frozen settings](study.yaml) · [Input lock](inputs.lock.json)

This study evaluates nine prespecified causal filters on 2025 GC lower-band
signals, selects one by the frozen risk-aware criterion, and checks its
unchanged behavior in 2026 YTD. It reuses the pinned Bhishma releases and the
sealed study 12 event outcomes. No data release is rebuilt.

The [static HTML report](../../runs/13_gc_ema_band_filter_validation/20260926T000219Z_gc_band_filters_v1/report.html)
opens without scripts or a server. The [run manifest](../../runs/13_gc_ema_band_filter_validation/20260926T000219Z_gc_band_filters_v1/manifest.json)
pins inputs, code, settings, checks, and output hashes. The complete nine-filter
comparison and cooldown/horizon sensitivity are retained in that run's `tables/`.

For chart use, the [GC Band MAE/MFE TradingView companion](pine/README.md)
draws the band and labeled long signals on the price chart, and calculates
chart-local MAE/MFE statistics in a separate lower pane. It exposes the
selected upper-half close threshold and 10-bar cooldown as inputs, plus optional
oversized-signal rejection and delayed band-reclaim entries. All chart statistics
follow the chosen model; these new options are exploratory and were not part of
the sealed filter-validation run. The study's
pinned original Pine source and sealed run are unchanged.

From the workspace root, use a fresh stage ID for any later execution:

```sh
.venv/bin/python -m unittest discover -s studies/13_gc_ema_band_filter_validation/tests
.venv/bin/python studies/13_gc_ema_band_filter_validation/run.py --stage work/13_gc_ema_band_filter_validation/<new-run-id>
.venv/bin/python studies/13_gc_ema_band_filter_validation/render.py --stage work/13_gc_ema_band_filter_validation/<new-run-id>
.venv/bin/python studies/13_gc_ema_band_filter_validation/verify.py --stage work/13_gc_ema_band_filter_validation/<new-run-id>
.venv/bin/python studies/13_gc_ema_band_filter_validation/seal.py --stage work/13_gc_ema_band_filter_validation/<new-run-id>
```

## Future execution and sealing provenance

New stages retain declared execution source/settings/input-lock and environment
lock bytes before data loading; successful completion requires unchanged source
identities. Separate rendering, verification and sealing records identify their
own sources and actual commands. Verification binds the exact stage and checked
artifact hashes rather than merely claiming a successful workspace check.

Sealing requires completed execution/rendering, the scientific receipt with all
70 matching Study 12 baseline cells, and an actual ordinary owning numerical-test
record. It rechecks settings, input lock, tables, metrics and reports before
creating completed evidence. Missing/stale/incomplete records fail; old stages
are not reconstructed using current source. Supplementary unexecuted checks are
recorded `not_run` with reasons.

Under separately authorized research/sealing scope:

```sh
./scripts/check-workspace --check study-13
./scripts/uv run --locked --no-sync python scripts/record-numerical-tests.py --study 13_gc_ema_band_filter_validation --stage work/13_gc_ema_band_filter_validation/<new-run-id>
./scripts/uv run --locked --no-sync python scripts/record-numerical-tests.py --study 13_gc_ema_band_filter_validation --stage work/13_gc_ema_band_filter_validation/<new-run-id> --check
./scripts/uv run --locked --no-sync python scripts/check-study-provenance.py --study 13_gc_ema_band_filter_validation --stage work/13_gc_ema_band_filter_validation/<new-run-id>
./scripts/uv run --locked --no-sync python studies/13_gc_ema_band_filter_validation/seal.py --stage work/13_gc_ema_band_filter_validation/<new-run-id>
```

The [future-stage workflow](../README.md#future-stage-evidence) documents declared
scope and validation limits. Study 13 keeps its manifest family; full
`abacus.evidence/v1` adoption remains deferred. Retention proves declared bytes,
not complete dependencies, historical execution or an installed environment's
lock match. Sealing provenance covers preparation before the final move, with
move failures left as diagnostic evidence. Synthetic operational guard tests stay under `scripts/tests/`.
Historical studies/runs, findings, source snapshots and presentation revisions
remain unchanged; no real execution or sealing is part of maintenance.
