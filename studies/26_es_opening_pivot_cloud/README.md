# ES Opening Pivot–Cloud Rejection/Support

Study `26_es_opening_pivot_cloud` compares early and confirmed opening ES reactions
around the saved Verne pivot and five-minute EMA20/50 cloud, with mirrored long and
short rules. CVD is excluded. Read the [plan](plan.md), [protocol](protocol-1.0.0.md),
[settings](study.yaml), [input lock](inputs.lock.json), and [decisions](notes.md).

Historical Verne availability remains null/unverified. The prior chart date is
2026-09-15, with no date-specific exclusion by user instruction; regular contract/readiness gates apply. This is retrospective temporal research;
2026 is a temporal test with disclosed prior exposure. No native TradingView parity
or prospective pre-open source availability is established.

## Reproduce

Use the prepared workspace environment without synchronization. All commands run
from the workspace root and require the retained pinned data resolved by path
configuration. New audit/freeze/execution/sealing targets must have a fresh run ID.

```sh
export UV_CACHE_DIR=/tmp/abacus-study26-uv-cache
./scripts/check-workspace --check study-26
./scripts/uv run --locked --no-sync python studies/26_es_opening_pivot_cloud/run.py audit --run-id <new-run-id>
./scripts/uv run --locked --no-sync python studies/26_es_opening_pivot_cloud/run.py freeze --run-id <new-run-id>
./scripts/uv run --locked --no-sync python studies/26_es_opening_pivot_cloud/run.py execute --run-id <new-run-id>
./scripts/uv run --locked --no-sync python studies/26_es_opening_pivot_cloud/run.py render --run-id <new-run-id>
python3 studies/26_es_opening_pivot_cloud/package_publication.py --stage work/26_es_opening_pivot_cloud/<new-run-id>
./scripts/uv run --locked --no-sync python studies/26_es_opening_pivot_cloud/run.py verify --run-id <new-run-id>
./scripts/uv run --locked --no-sync python studies/26_es_opening_pivot_cloud/run.py seal --run-id <new-run-id>
```

Audit is descriptive inputs/features only; freeze snapshots protocol, scientific
source and environment before strategy calculations. Execute refuses changed
frozen source/settings/input identities. Render uses saved statistics; verify
independently reconciles ledgers, statistics and publication cells. Seal refuses
missing/failed receipts or an existing completed destination. Numerical and
source-integrity verification remain distinct from Narada/local browser checks.

Selected report content is prepared in the stage before sealing. Use Narada's
explicit publisher, app verification/test/lint/build and loopback preview. Hosted
deployment requires a later instruction.

`package_publication.py` is a separate presentation-only step: it compacts JSON whitespace so the unchanged report fits the source byte budget. It retains the original bytes and producer, asserts exact parsed equality, and updates the publication-source hash. It does not change frozen scientific source, saved cells, statistics or interpretation.

## Completed evidence

The explicitly reviewed reference run is [20261021T044616Z_reportfix_v1](../../runs/26_es_opening_pivot_cloud/20261021T044616Z_reportfix_v1/report.md). It corrects the initial report's target wording and distinguishes slope-filter dollar/R expectancy. All 20 numerical ledgers, metrics and tables are byte-identical to the [original run](../../runs/26_es_opening_pivot_cloud/20261021T042230Z_opening_pivot_v1/report.md); no strategy settings or calculations changed. Original outcomes were viewed before this reproduction, as disclosed in its correction context. The original pre-outcome freeze remains retained. This reference was selected for those audited corrections, not by recency or performance.

Both directions and all 16 variants remain included. Primary early/confirmed net expectancy was −$20.46/−$16.56 per eligible session; every fixed-2R variant lost after costs. Early superiority is inconclusive. See [findings](../../runs/26_es_opening_pivot_cloud/20261021T044616Z_reportfix_v1/findings.md), [paired evidence](../../runs/26_es_opening_pivot_cloud/20261021T044616Z_reportfix_v1/tables/primary_comparison.csv), [variant evidence](../../runs/26_es_opening_pivot_cloud/20261021T044616Z_reportfix_v1/tables/variant_summary.csv), [coverage](../../runs/26_es_opening_pivot_cloud/20261021T044616Z_reportfix_v1/coverage.csv), [numerical parity](../../runs/26_es_opening_pivot_cloud/20261021T044616Z_reportfix_v1/checks/numerical-parity.json) and [independent verification](../../runs/26_es_opening_pivot_cloud/20261021T044616Z_reportfix_v1/scientific-verification.json).

The local board is at `http://127.0.0.1:4173/studies/es-opening-pivot-cloud/` while Narada preview runs. Its selected immutable publication is `es-opening-pivot-cloud-26-v1-20261021t044616zreportfixv1`; the earlier local publication remains accessible and qualified. No hosted deployment was performed. Large ignored evidence has [retained locators/checksums](../../runs/26_es_opening_pivot_cloud/20261021T044616Z_reportfix_v1/events.manifest.json); no external backup is asserted.

Verification passed the fresh 83-test suite, independent scientific/source-cell checks, and Narada verify/168 tests/lint/build/smoke plus desktop/mobile browser checks. Selected CSV bytes equal the previously tested native browser download. The default workspace gate failed on two existing historical Bhishma integration prerequisites; its other four checks and 194 tooling tests passed separately. Exact inherited logs and fresh local checks are distinguished in the run.

The original publication needed a private [source-audit receipt adapter](../../reports/exports/26_es_opening_pivot_cloud/20261021T042230Z_opening_pivot_v1/20261021T044645Z_private_audit_adapter_v1/manifest.json). It preserves exact original public bytes and adds the generic receipt keys required by Narada. It does not alter the sealed run, results or public bundle. `prepare_source_audit.py` reproduces that bounded compatibility export; the corrected run's source receipt uses the native generic format.
