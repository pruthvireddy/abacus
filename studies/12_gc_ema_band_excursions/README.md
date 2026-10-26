# GC EMA outer-band excursion study

See [plan.md](plan.md) and [study.yaml](study.yaml). [Bhishma's request](../../requests/inbox/gc_ema_deviation_bands__1.0.0.yaml)
defines the reusable input; this study owns the entry, cooldown, excursions,
and interpretation.

The study's `accepted_indices` mask adapter delegates to Sahadeva's shared
[`accepted_bar_indices`](../../packages/sahadeva/src/abacus_sahadeva/cooldown.py),
using original chart-bar positions. Future path exclusions are evaluated after
signal acceptance. Future sealed runs include that helper and its focused tests
in their declared execution/test scope and retain actual source/lock bytes.
Existing sealed inventories and findings remain unchanged.

The [corrected interactive offline HTML report](../../reports/exports/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/20260925T224602Z_html_interactivity_v1/report.html)
contains every year, cooldown, and horizon. The [saved yearly table](../../runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/tables/yearly.csv)
and [run manifest](../../runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/manifest.json)
pin the numerical evidence and provenance.

From the workspace root, after the pinned input release is available:

```sh
.venv/bin/python -m unittest discover -s studies/12_gc_ema_band_excursions/tests
.venv/bin/python studies/12_gc_ema_band_excursions/run.py --stage work/12_gc_ema_band_excursions/<new-run-id>
.venv/bin/python studies/12_gc_ema_band_excursions/render.py --stage work/12_gc_ema_band_excursions/<new-run-id>
.venv/bin/python studies/12_gc_ema_band_excursions/verify.py --stage work/12_gc_ema_band_excursions/<new-run-id>
node studies/12_gc_ema_band_excursions/tests/verify_report_interactivity.mjs <rendered-report.html>
```

Rendering consumes saved result tables. A verified stage is sealed once under
`runs/12_gc_ema_band_excursions/<new-run-id>/`; later numerical changes require
a new run.

## Future execution and sealing provenance

New stages retain declared source, frozen settings/input-lock and environment-lock
bytes before data loading. Execution completion requires unchanged declared
source identities. Rendering and verification retain separate phase records;
the verifier receipt binds the exact stage and checked artifact bytes. Missing
historical execution records are refused rather than reconstructed at seal time.

The required gates are completed execution/rendering, an ordinary scientific
verification receipt with all 595 statistic cells, and the actual owned numerical
test record. Study 12 refuses `python -O` verification because its analytical
assertions require ordinary Python. Preflight rechecks verified settings, input
lock, tables, metrics and reports before completed-run destinations are created.
Supplementary checks not executed have explicit `not_run` reasons.

Under separately authorized research/sealing scope, run, record, validate and
seal as distinct operations:

```sh
./scripts/check-workspace --check study-12
./scripts/uv run --locked --no-sync python scripts/record-numerical-tests.py --study 12_gc_ema_band_excursions --stage work/12_gc_ema_band_excursions/<new-run-id>
./scripts/uv run --locked --no-sync python scripts/record-numerical-tests.py --study 12_gc_ema_band_excursions --stage work/12_gc_ema_band_excursions/<new-run-id> --check
./scripts/uv run --locked --no-sync python scripts/check-study-provenance.py --study 12_gc_ema_band_excursions --stage work/12_gc_ema_band_excursions/<new-run-id>
./scripts/uv run --locked --no-sync python studies/12_gc_ema_band_excursions/seal.py --stage work/12_gc_ema_band_excursions/<new-run-id>
```

Read [future-stage evidence](../README.md#future-stage-evidence) for phase records
and limits. The current manifest family remains; full `abacus.evidence/v1`
adoption is deferred. Retained scope does not prove dependency closure or that
the installed environment matched the lock. Source captured today cannot prove
an old execution. Failed stages remain diagnostic evidence; guards are not a
multi-artifact transaction. Sealing provenance covers preparation before the final
move; it does not claim that a later move succeeded. Historical results and presentation revisions remain
unchanged. Maintenance verification uses synthetic fixtures, not real recounts.
