# Asia session VP levels study

Study `14_asia_session_vp_levels` · NQ · Frozen protocols 1.0.0 and 1.1.0 · Local evidence

The user confirmed setup A as **buy long at POC** after an excursion above
overnight VAH, and **sell short at POC** after an excursion below overnight VAL.
The entry is the next contiguous one-minute open after the POC-touch candle.
This direction was fixed before any real study outcomes were examined. The
opposite value-area re-entry trade targeting POC is outside this execution.

The [frozen protocol](protocol-1.0.0.md), [executed settings](study.yaml),
[pinned inputs](inputs.lock.json), and [decision notes](notes.md) define this
study. The [independent feature contract](protocol-features-1.0.0.md) and
[Bhishma release](../../catalog/datasets/nq_causal_vp_hvn__1.0.0.json) retain
causal raw and adjusted-coordinate snapshots, HVN candidates, selection
decisions, source hashes, and limitations. The original
[Pine source](reference/vp_hvn_levels_dev.pine) remains byte-identical.

The original locally sealed evidence is
[run 20260929T124500Z_asiavp_b2](../../runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/report.html).
It includes yearly opportunity/exclusion funnels, event ledgers, five fixed
horizons and separate paths to midnight, threshold races, matched-minute
controls, dependence-aware intervals, prespecified sensitivities, and
fixed-rule representative profile charts. Its 2026 slice is YTD. Read the
run's report for denominators and interpretation; MAE/MFE extrema are not
realized trading P&L or a strategy recommendation. Reports remain local.

The separate [previous-RTH extension protocol](protocol-1.1.0.md) and
[settings](study-1.1.yaml) add a fixed previous-RTH POC approach fade and
previous-RTH VAH/VAL breakout/retest continuation. Its
[sealed 5/10/20-bar report](../../runs/14_asia_session_vp_levels/20260929T141000Z_prev_rth_de/report.html)
includes average MAE, MFE and signed terminal close delta in points and
prior-60-minute true-range units, with event counts and exclusions. It treats
2024–2025 and 2026 as previously inspected, exploratory periods. The strict
combined-reference quality gate yields no complete horizons before 2018.
The POC fade direction is a documented working interpretation pending any
correction from the user. The two current evidence cards are
[POC fade](../../strategies/nq_prev_rth_poc_fade.md) and
[VA breakout/retest](../../strategies/nq_prev_rth_va_breakout_retest.md).

The earlier feature preparation at
`work/14_asia_session_vp_levels/20260927T180756Z_preparation_2281/report.html`
contains input-quality and evening-volume evidence only. This ignored local
artifact requires the separately retained workspace files and is absent from a
source-only clone. A later failed
staging directory is marked unsuitable for sealing; it is not a second run.

To verify the study and its saved evidence from the workspace root:

```sh
UV_CACHE_DIR=work/.uv-cache ./scripts/uv run --locked --no-sync python -m unittest discover -s studies/14_asia_session_vp_levels/tests
UV_CACHE_DIR=work/.uv-cache ./scripts/uv run --locked --no-sync python studies/14_asia_session_vp_levels/verify_run.py --stage runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2
UV_CACHE_DIR=work/.uv-cache ./scripts/uv run --locked --no-sync python studies/14_asia_session_vp_levels/verify_previous_day_run.py --stage runs/14_asia_session_vp_levels/20260929T141000Z_prev_rth_de
```

The report renderer reads saved numerical tables. `run.py --execute --stage
work/14_asia_session_vp_levels/<new-run-id>` executes a new run; the exact
commands for the completed run are in its manifest. Use a new ID for any
changed calculations or interpretations. Do not overwrite the feature release
or the completed run. External publication and deployment are outside scope.
`run.py --execute-prev-day --stage work/14_asia_session_vp_levels/<new-run-id>`
executes the separately frozen previous-RTH extension.

## Consumer maintenance

Feature loading uses `abacus_bhishma.vp_hvn_loader.load_release`; hashing uses
`abacus_bhishma.provenance.sha256_file` through compatibility aliases. The six
consumers in `src/preparation.py`, `src/study_run.py`, `src/previous_day_run.py`,
`seal.py`, `verify_previous_day_run.py` and `feature_audit.py` do not import the
VP/HVN publication builder. [src/evidence.py](src/evidence.py) keeps the existing
dataset identity, minute scalar and JSON writer local. The writer creates parents,
uses `indent=2`, `allow_nan=False` and default escaping, and adds a trailing newline.

The manifest-selected per-year snapshot reads, grouping, signal/outcome rules
and sealing sequence retain their existing behavior. Future source inventories
include the executed consumer/hash/path helpers; historical snapshots and frozen
protocols remain unchanged.

From the root, inspect `./scripts/check-workspace --context study-14` and select
`./scripts/check-workspace --check study-14-consumer-imports`. The
[import fixtures](tests/test_consumer_imports.py) use fresh processes, reject
builder/native activation and subprocess work during import, and invoke no
preparation, execution, audit, export or sealing functions. They are study-owned
and also participate in `--profile bhishma-loaders` as a separate process.
Use `--check study-14` for its affected synthetic numerical fixtures; a passing
maintenance suite does not rerun or revalidate the saved research results.
