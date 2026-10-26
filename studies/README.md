# Research studies

A study is a defined question and protocol. A run is one execution; a strategy is an enduring idea that can collect evidence from multiple studies.

Start with the [study agent guide](AGENTS.md), which points to
[Sahadeva's instructions](../packages/sahadeva/AGENTS.md). Use the current
[repository map](../ARCHITECTURE.md) to place code and evidence.

`study.json` provides the portable index metadata: unique `study_id`, `title`, `summary`, `status`, `topic`, `products`, `data_summary`, `evidence_status`, and `strategy_ids`. Optional `reference_run` is an explicit reviewed selection, never inferred from recency. Historical code remains under `legacy/sahadeva/analysis/`; `05_session_vwap` is the first new executed statistical study.

[Study 19](19_value_area_fade_tracker/README.md) documents an external trade
tracker and registers a proposed first-touch value-area fade strategy. Its source
review is complete; independent empirical analysis remains planned. Keep reported
external evidence distinct from Abacus's own calculations and holdout findings.

[Study 27](27_verniman_method_knowledge/README.md) maintains the selected
Verniman-method source-review protocol and points to its frozen Markdown
knowledge base. It distinguishes Vern's own statements, curated third-party
lessons and Abacus synthesis; transcript/chart coverage and unresolved rules
are explicit. This qualitative owner has no numerical suite or tested strategy.

[Study 28](28_globex_ema_crossings/README.md) measures completed-bar EMA6 crossings
of Globex-anchored VWAP across ES, NQ and GC, now using 3-minute closes,
annual/monthly breakdowns, prior available ATR14% regimes and retrospective
session-range/ATR expansion bins. Its [protocol](28_globex_ema_crossings/protocol-1.1.0.md)
preserves published input eligibility, continuous EMA history and explicit
zero/undefined counts; this is descriptive crossing research without trade returns.

[Study 22](22_es_range_xv_focused/README.md) contains focused ES Range XV trend-length and reversal research.
Every future statistic must include yearly and seven named New York session-window
breakdowns. Its first completed analysis measures directional candle-run lengths for all
three settings, with independently verified saved statistics and separate web tabs.

[Study 23](23_gc_overnight_breakout_15m/README.md) implements the approved Phase 1 fixed GC overnight breakout baseline. Its [frozen protocol](23_gc_overnight_breakout_15m/protocol-phase1.md) separates one-contract execution, source-account sizing, causal data quality and ordering/cost sensitivities. It preserves both Pine scripts. Midpoint/reclaim/interior entries, re-entry, additional trades and filters remain unexecuted Phase 2 proposals.

Use the [study template](../templates/study.md). Record the proposal in `plan.md`, freeze an executed versioned protocol before examining outcomes, and keep machine-readable settings in `study.yaml`, input identities in `inputs.lock.json`, and decisions in `notes.md`. Add executable study code only when implementation is authorized. Regenerate the [research library](../reports/index.html) with `python scripts/build-research-index.py`.

## Study-specific implementation

Use `run.py` as a thin entry point, `src/` for local definitions and calculations,
and `tests/` for that study's checks. Keep strategy rules and parameters with the
protocol. Shared methods with demonstrated reuse belong in
`packages/sahadeva/src/abacus_sahadeva/`, with tests in the package.

Document the exact run and test commands in the study README. Use the workspace
environment; do not add a separate environment for each new study. Historical
snapshots keep their original environments and paths.

## Implementation and export maintenance

| Task | Owner file | Focused test | Preservation boundary |
|---|---|---|---|
| Project saved CSV cells | [Sahadeva saved_evidence.py](../packages/sahadeva/src/abacus_sahadeva/saved_evidence.py); exporters [08](08_countertrend_bar_continuation/publish_web.py) and [09](09_range_xv_c2_confirmation/publish_web.py) | [Projection](../packages/sahadeva/tests/test_saved_evidence.py) and [export parity](../packages/sahadeva/tests/test_export_projection.py) | Saved values, original source rows, authored prose and existing revision bytes |
| Enforce exporter integrity | Active `studies/*/publish_web.py` (16 files) | [Exporter guards](../packages/sahadeva/tests/test_export_guards.py), ordinary and optimized Python | Prepare/hash checks before output creation; read-only `--check`; no overwrite |
| Change study 05 presentation | [report_rendering.py](05_session_vwap/src/report_rendering.py), via [reporting.py](05_session_vwap/src/reporting.py) | [Synthetic rendering tests](05_session_vwap/tests/test_report_rendering.py) | Numerical/table functions, report meaning, SVG/PNG/JSON outputs and callers |
| Enforce study 15 pre-seal gates | [sealing.py](15_vwap_excursion_response/src/sealing.py) | [Synthetic sealing tests](15_vwap_excursion_response/tests/test_sealing.py), ordinary and optimized Python | Frozen executable, staged/retained hashes and completed-run identities |
| Record owned numerical tests | [numerical_test_record.py](../scripts/numerical_test_record.py), via [record-numerical-tests.py](../scripts/record-numerical-tests.py); sealers 08/09/10/12/13 | [Record guards](../scripts/tests/test_numerical_test_record.py): `numerical-record-guards` and `numerical-record-guards-optimized` | Actual child result, selected source/test bytes, stage identity, lock and log; explicit legacy boundary |
| Capture execution and verify a stage | [study_provenance.py](../scripts/study_provenance.py); run/render/verify/seal in studies 12/13 | [Phase guards](../scripts/tests/study_provenance_guards.py): `study-execution-guards` and `study-execution-guards-optimized` | Pre-execution retained bytes, unchanged scientific conditions, verified artifact identities and preflight |
| Write prepared presentation revisions | [presentation_revision.py](../packages/sahadeva/src/abacus_sahadeva/presentation_revision.py); exporters 08/09 only | Sahadeva export parity/guard tests | Exact prepared JSON bytes and three retained producer sources; no projection or claim changes |

The shared projection helper serves only studies 08/09; other exporters retain
their local projection code. Its private source inventory records exact producer
bytes/hashes, not a complete presentation manifest. Follow the
[presentation workflow](../templates/README.md#later-presentation-revisions) for
source maps, completion records, new revision identities, and publication checks.
Historical snapshots/finalizers stay unchanged.

Keep exporter integration tests in Sahadeva's package and operational record
guards under `scripts/tests/`. Existing numerical suite contents are preserved;
future structured records permit test growth. Run study suites in separate processes because
several use generic `src` imports. Synthetic fixtures and read-only saved-output
comparisons do not rerun historical research or revalidate findings.

The [workspace harness](../README.md#workspace-check-harness) exposes every active
test directory through explicit `study-05` through `study-16`, `study-18` and
`study-20` through `study-23`, `study-25`, `study-26` and `study-28` checks. From the root, use `./scripts/check-workspace --context study-12`
for prerequisites/read-first paths and `--check study-12` to execute its suite.
`--profile studies` selects those independent processes; it does not run study
entry points, sealers or report generators. Studies 01/02 route to their legacy
numerical suites; 03/04 are historical adapters without standalone suites.
Studies 17/19 have no current local Python suite. Study 18's navigation metadata
registers an indicator implementation with synthetic validation only. Test
coverage comes from explicit owner records and does not require `study.json`.

Navigation preserves existing status vocabulary. An optional `content_kind`
defaults to research; `indicator_implementation` links its actual implementation
files and states validation limits without inventing outcomes or a reference run.
Use `--profile metadata` before regenerating the index, then `--profile navigation`
for freshness. See the [contract/reference guide](../docs/evidence-contract.md).

Full study 06 discovery reads real 2023 product data. Study 11 combines synthetic
core tests with retained Pine exporter/evidence checks. Scalar Pine tests cover
selected translated semantics, not TradingView compilation or replay. Check
prerequisites and skipped scope before interpreting a successful process.
The registry's `guards` profile selects ordinary/optimized exporter, study 15
sealing, numerical-record and study 12/13 provenance guards. The narrower
`study-evidence` profile selects the latter two. Optimized guards test refusal
enforcement, not analytical validity. Generic harness summaries remain distinct
from the stage-bound evidence below.

## Future-stage evidence

Ordinary suite execution and recording evidence are separate operations. Under
separately authorized research scope, an existing explicit stage can record its
owned suite through the bounded recorder:

```sh
./scripts/check-workspace --check study-08
./scripts/uv run --locked --no-sync python scripts/record-numerical-tests.py --study 08_countertrend_bar_continuation --stage work/08_countertrend_bar_continuation/<new-run-id>
./scripts/uv run --locked --no-sync python scripts/record-numerical-tests.py --study 08_countertrend_bar_continuation --stage work/08_countertrend_bar_continuation/<new-run-id> --check
./scripts/check-workspace --profile study-evidence
```

The recorder supports only the existing owned checks for studies 08/09/10/12/13.
It creates `numerical-tests/` exclusively and runs the registry suite in a fresh
locked process without synchronization. `record.json` uses
`abacus.numerical-test-record/v1`, with exact study/stage/check/selection, actual
argv/cwd and exit, runtime/optimization, timestamps, retained log/lock/source
identities and the existing unittest child's actual result. The declared source
scope includes selected tests and relevant local helpers and is compared before
and after execution and at validation. A lock records bytes; it does not prove
the installed environment matched them.

Numerical sealing requires ordinary, nonempty, fully executed success with no
failures, errors, unexpected successes, skips or expected failures. Counts must
have valid integer types and be consistent; no literal suite length is required.
These stricter rules do not change the generic harness's mixed pass/skip policy.
Records with wrong identities, changed source/log/lock bytes, failed discovery or
incomplete execution fail. A generic harness report is insufficient.

Studies 08/09/10 accept old log-only stages only with `--legacy-test-log`.
That path retains their original eight/eight/six count checks and labels the
evidence as legacy and unbound to tested source. Any `numerical-tests/` adoption,
including a failed or incomplete attempt, prevents that bypass. An invalid new
record never falls back to apparently successful logs. Completed historical
runs, logs and snapshots remain unchanged.

Studies 12/13 capture execution source/settings/input-lock and environment-lock
bytes before data loading. Separate `provenance/` phase records retain execution,
rendering, numerical verification and sealing observations. Source changes during
execution prevent a successful completion record; failure leaves an incomplete
stage for diagnosis. Rendering consumes saved evidence. Verification receipts
bind the study/stage, actual verifier command and runtime, retained verifier
source, and checked artifact hashes. Sealing rechecks those identities, requires
the actual owning numerical-test record, and preserves scientific cardinalities
(595 statistic cells for 12; 70 baseline cells for 13) before creating completed
destinations. Study 12 refuses optimized verification because its analytical
assertions require ordinary Python. Never reconstruct missing execution records
from today's source files.

Under separately authorized execution/sealing scope, validate and seal separately:

```sh
./scripts/uv run --locked --no-sync python scripts/check-study-provenance.py --study 12_gc_ema_band_excursions --stage work/12_gc_ema_band_excursions/<new-run-id> --phase execution
./scripts/uv run --locked --no-sync python scripts/check-study-provenance.py --study 12_gc_ema_band_excursions --stage work/12_gc_ema_band_excursions/<new-run-id>
./scripts/uv run --locked --no-sync python studies/12_gc_ema_band_excursions/seal.py --stage work/12_gc_ema_band_excursions/<new-run-id>
```

The phase validator reads an explicitly selected stage; it does not execute the
scientific verifier or seal it. Required scientific/numerical gates are distinct
from integrity. Supplementary checks not executed are recorded `not_run` with a
reason. Study 12/13 keep their existing manifest families; complete
`abacus.evidence/v1` adoption is deferred. Declared retained scope does not prove
dependency closure or historical execution. These checks do not lock writers or
provide a crash-safe transaction across artifacts; preserve partial evidence for
inspection. Sealing provenance records successful preparation before the final
move, not a completed move that has not yet occurred. A failed move leaves
diagnostic evidence; completed runs are never edited to add a post-move record.

Stage outputs in `work/<study-id>/<run-id>/`; save verified evidence using the
[run lifecycle](../runs/README.md). Editing a study's current settings does not
alter the frozen configuration in an existing run.

[Study 26](26_es_opening_pivot_cloud/README.md) tests ES opening pivot/cloud rejection and mirrored support, with frozen retrospective input eligibility, paired early/confirmed entries, four EMA masks and two exits. Its [protocol](26_es_opening_pivot_cloud/protocol-1.0.0.md) preserves unverified source availability, matching-contract prices and published readiness. Hosted deployment is separate from local preview.
