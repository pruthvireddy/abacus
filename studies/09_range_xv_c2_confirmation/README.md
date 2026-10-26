# Study 09: C2 confirmation after a first countertrend Range XV bar

This study uses the seven pinned enhanced long-history Range XV files in
[`inputs.lock.json`](inputs.lock.json). The [plan](plan.md) and
[`study.yaml`](study.yaml) froze the candidate, ordinary baseline, common C1
opportunity set, price references, exclusions, and 70-cell screen before
extraction. The age-two ordinary baseline in [notes](notes.md) is an explicitly
post-result diagnostic. Study 08 motivates the question but is not an event
input.

The completed local evidence is under
[`runs/09_range_xv_c2_confirmation`](../../runs/09_range_xv_c2_confirmation/).
The primary chart-behavior outcome is `P(C3 and C4 both follow C1 | C2
confirms)`, compared at C2 completion with an ordinary same-direction B1/B2
pair. For the decision to wait, use the common-C1 opportunity tables and
price proxy alongside the conditional result. Read the run's report and saved
CSV tables together.

From the workspace root, use a **new** sortable UTC run ID:

```sh
.venv/bin/python -m unittest discover -s studies/09_range_xv_c2_confirmation/tests -v
.venv/bin/python studies/09_range_xv_c2_confirmation/run.py --stage work/09_range_xv_c2_confirmation/<new-run-id>
.venv/bin/python studies/09_range_xv_c2_confirmation/summarize.py --stage work/09_range_xv_c2_confirmation/<new-run-id>
.venv/bin/python studies/09_range_xv_c2_confirmation/verify.py --stage work/09_range_xv_c2_confirmation/<new-run-id>
.venv/bin/python studies/09_range_xv_c2_confirmation/render.py --stage work/09_range_xv_c2_confirmation/<new-run-id>
.venv/bin/python studies/09_range_xv_c2_confirmation/seal.py --stage work/09_range_xv_c2_confirmation/<new-run-id>
```

`run.py` refuses an existing stage and verifies exact input hashes. `verify.py`
reconciles ledger counts, source rows, timing, numeric tables, and price means.
`render.py` reads saved numerical evidence. `seal.py` snapshots this study's
code and environment and moves the checked stage into a unique local run.
Completed runs must not be regenerated.

A later [three-segment overlay](../10_range_xv_session_overlay/README.md)
combines the saved New York morning and afternoon rows and compares the C2
candidate with ordinary pairs and the other broad sessions.

## Presentation exporter maintenance

[publish_web.py](publish_web.py) uses Sahadeva's
[`project_table`](../../packages/sahadeva/src/abacus_sahadeva/saved_evidence.py)
for saved-CSV selection, conversion, and original source-cell bindings. Study
identities, claims, prose, and publication assembly remain local. Its explicit
guards work under `python -O`. Preparation and source-integrity checks finish
before output creation; export refuses an existing revision. `--check` compares
an existing publication/source map without writes.

Future revisions retain exact exporter/helper source bytes and a compact private
hash inventory under `provenance/`: `publish_web.py`, `saved_evidence.py`,
`presentation_revision.py`, and `source-inventory.json`. The small shared writer
handles prepared bytes; identities, authored content and projection stay local.
It identifies the producer implementation;
the [presentation workflow](../../templates/README.md#later-presentation-revisions)
still owns manifests and completion records. Historical revisions and finalizers
remain unchanged.

Run presentation checks from the workspace root:

```sh
./scripts/uv run --locked --no-sync python -m unittest discover -s packages/sahadeva/tests -p 'test_saved_evidence.py'
./scripts/uv run --locked --no-sync python -m unittest discover -s packages/sahadeva/tests -p 'test_*export*.py'
./scripts/uv run --locked --no-sync python -O -m unittest discover -s packages/sahadeva/tests -p 'test_*export*.py'
./scripts/uv run --locked --no-sync python studies/09_range_xv_c2_confirmation/publish_web.py --revision 20261006T230936Z_web09 --check
```

These are saved-evidence presentation checks, not numerical research execution.
New exporter tests live in Sahadeva and operational guards under `scripts/tests/`.
Future stages require a structured ordinary numerical-test record; numerical
suite growth no longer changes sealing eligibility. Under separately authorized
research/sealing scope:

```sh
./scripts/check-workspace --check study-09
./scripts/uv run --locked --no-sync python scripts/record-numerical-tests.py --study 09_range_xv_c2_confirmation --stage work/09_range_xv_c2_confirmation/<new-run-id>
./scripts/uv run --locked --no-sync python scripts/record-numerical-tests.py --study 09_range_xv_c2_confirmation --stage work/09_range_xv_c2_confirmation/<new-run-id> --check
./scripts/uv run --locked --no-sync python studies/09_range_xv_c2_confirmation/seal.py --stage work/09_range_xv_c2_confirmation/<new-run-id>
```

Old log-only stages require `--legacy-test-log`; that path preserves the original
eight-test check and records that tested source is unbound. New-workflow adoption,
including incomplete/failed evidence, prevents legacy bypass. Chart and fourteen
ledger completeness checks remain unchanged. See
[future-stage evidence](../README.md#future-stage-evidence) for strict gates and
limits. Historical runs, logs, snapshots and revisions remain unchanged.
