# Study 08: first countertrend Range XV bar

This study uses only the seven enhanced long-history Range XV files pinned in
[`inputs.lock.json`](inputs.lock.json). The [frozen plan](plan.md) and
[`study.yaml`](study.yaml) define the event, horizons, groups, exclusions, and
screen before outcome extraction. Older reports are context, not pooled input.

The completed local evidence is under
[`runs/08_countertrend_bar_continuation`](../../runs/08_countertrend_bar_continuation/).
The main answer is `P(C2 and C3 both follow C1)`; C1 itself is excluded from
the count of two more bars. Read the run's `report.md` and numerical CSVs together.

From the workspace root, using a new, sortable UTC run ID:

```sh
.venv/bin/python -m unittest discover -s studies/08_countertrend_bar_continuation/tests -v
.venv/bin/python studies/08_countertrend_bar_continuation/run.py --stage work/08_countertrend_bar_continuation/<new-run-id>
.venv/bin/python studies/08_countertrend_bar_continuation/summarize.py --stage work/08_countertrend_bar_continuation/<new-run-id>
.venv/bin/python studies/08_countertrend_bar_continuation/verify.py --stage work/08_countertrend_bar_continuation/<new-run-id>
.venv/bin/python studies/08_countertrend_bar_continuation/render.py --stage work/08_countertrend_bar_continuation/<new-run-id>
.venv/bin/python studies/08_countertrend_bar_continuation/seal.py --stage work/08_countertrend_bar_continuation/<new-run-id>
```

`run.py` refuses an existing staging directory and verifies the exact manifest,
source, and enhanced hashes. The run ID must be new; completed runs are never
regenerated. The `verify.py` check reconciles source-row traces, manifest
counts, event ledgers, and saved table numerators/denominators. `render.py`
reads only saved evidence. `seal.py` snapshots the study code and environment
and moves the verified stage into `runs/` after creating the artifact manifest.

A later [three-segment overlay](../10_range_xv_session_overlay/README.md)
combines New York morning and afternoon for exploratory comparison with Asia
and London/pre-NY, preserving this study's completed run.

## Presentation exporter maintenance

[publish_web.py](publish_web.py) uses Sahadeva's
[`project_table`](../../packages/sahadeva/src/abacus_sahadeva/saved_evidence.py)
for saved-CSV selection, conversion, and original source-cell bindings. Study
identities, claims, prose, and publication assembly remain local. Its guards
remain effective under `python -O`; preparation and source-hash checks finish
before a new output directory is created. `--check` reads and compares an existing
revision without writing; ordinary export refuses an existing revision.

Future revisions retain exact exporter/helper bytes and a private source-hash
inventory under `provenance/`: `publish_web.py`, `saved_evidence.py`,
`presentation_revision.py`, and `source-inventory.json`. The shared writer accepts
prepared bytes; projection, authored content and output ordering stay local.
This is producer provenance, not a replacement
for the [presentation manifest and completion workflow](../../templates/README.md#later-presentation-revisions).
Existing revisions and finalizers remain unchanged.

From the workspace root, these presentation checks do not rerun research:

```sh
./scripts/uv run --locked --no-sync python -m unittest discover -s packages/sahadeva/tests -p 'test_saved_evidence.py'
./scripts/uv run --locked --no-sync python -m unittest discover -s packages/sahadeva/tests -p 'test_*export*.py'
./scripts/uv run --locked --no-sync python -O -m unittest discover -s packages/sahadeva/tests -p 'test_*export*.py'
./scripts/uv run --locked --no-sync python studies/08_countertrend_bar_continuation/publish_web.py --revision 20261006T235500Z_web08r2 --check
```

New exporter tests stay in Sahadeva's package; operational guards stay under
`scripts/tests/`. Future sealing uses a structured ordinary numerical-test record
and permits test growth. Under separately authorized research/sealing scope:

```sh
./scripts/check-workspace --check study-08
./scripts/uv run --locked --no-sync python scripts/record-numerical-tests.py --study 08_countertrend_bar_continuation --stage work/08_countertrend_bar_continuation/<new-run-id>
./scripts/uv run --locked --no-sync python scripts/record-numerical-tests.py --study 08_countertrend_bar_continuation --stage work/08_countertrend_bar_continuation/<new-run-id> --check
./scripts/uv run --locked --no-sync python studies/08_countertrend_bar_continuation/seal.py --stage work/08_countertrend_bar_continuation/<new-run-id>
```

An old log-only stage requires the explicit `--legacy-test-log` sealing option;
only that path keeps the eight-test count and labels its source binding absent.
An adopted, failed or invalid structured attempt cannot fall back to logs.
Scientific chart/event completeness checks remain. See
[future-stage evidence](../README.md#future-stage-evidence) for strict pass and
provenance limits. Completed runs, snapshots, revisions and logs remain unchanged.
