# Sahadeva — Research & Analysis

Use the [component instructions](AGENTS.md) for task routing and checks, and the
[repository map](../../ARCHITECTURE.md) for file placement and dependencies.

Sahadeva consumes explicitly versioned Bhishma publications. It owns research
methods, event/outcome definitions, statistics, execution assumptions, and
interpretation. Study definitions and saved evidence live in the workspace's
`studies/`, `runs/`, and `strategies/` directories.

The shared package provides fixed-bar cooldown selection, read-only VWAP input
diagnostics, and bounded saved-CSV presentation projection. Add shared methods when
authorized studies demonstrate reuse; signal rules, outcomes, parameters, and
interpretation remain study-local.
The three selected VWAP candidates are implemented and evaluated within
[study 05](../../studies/05_session_vwap/README.md); its methods remain local to that study.

## Current capabilities

| Capability | Module / API | Consumers and scope | Focused checks |
|---|---|---|---|
| Fixed-bar cooldown | [cooldown.py](src/abacus_sahadeva/cooldown.py): `accepted_bar_indices` | [Study 12](../../studies/12_gc_ema_band_excursions/README.md) mask adapter and [study 13](../../studies/13_gc_ema_band_filter_validation/README.md) absolute indices | [Shared tests](tests/test_cooldown.py), [study 12 tests](../../studies/12_gc_ema_band_excursions/tests/test_engine.py), [study 13 tests](../../studies/13_gc_ema_band_filter_validation/tests/test_engine.py) |
| Saved-CSV presentation projection | [saved_evidence.py](src/abacus_sahadeva/saved_evidence.py): `project_table` | Presentation exporters in studies [08](../../studies/08_countertrend_bar_continuation/README.md) and [09](../../studies/09_range_xv_c2_confirmation/README.md) only | [Projection tests](tests/test_saved_evidence.py), [exporter parity tests](tests/test_export_projection.py), [guard tests](tests/test_export_guards.py) |
| Prepared presentation revision writing | [presentation_revision.py](src/abacus_sahadeva/presentation_revision.py): `write_revision` | Study 08/09 only; prepared bytes, README and explicit producer sources, without claims or projection | [Writer tests](tests/test_presentation_export_writer.py) and existing exporter integration/guards |
| VWAP input-pin verification | [inputs.py](src/abacus_sahadeva/inputs.py): `verify_inputs` | `doctor`; supported VWAP locks, catalog/manifest identities and applicable audit/report hashes | [Input-pin tests](tests/test_input_pins.py) |
| Bounded VWAP sample read | [inputs.py](src/abacus_sahadeva/inputs.py): `read_samples` | `doctor --read-sample`; hash one selected partition and load one session per product/timeframe | [Input-pin tests](tests/test_input_pins.py); remaining partitions are not verified |
| CLI routing | [cli.py](src/abacus_sahadeva/cli.py): `main` | `doctor` with optional `--read-sample`; no study execution command | Root and doctor `--help` smoke checks; workspace gate |

`accepted_bar_indices(candidate_indices, cooldown_bars)` takes positions in the
original ordered chart-bar series, not ordinals within a filtered candidate list.
After accepting bar i, it suppresses i+1 through i+C; i+C+1 is eligible, and a
suppressed candidate does not restart the timer. Cooldown zero accepts every
candidate. Calls are independent and return an `int64` NumPy array, including
empty output. Negative cooldowns and duplicate/descending indices remain errors.

Study 12 retains `accepted_indices(candidates, cooldown)` as a mask adapter using
`np.flatnonzero(candidates)`. It accepts signals before evaluating future path
validity. Study 13 applies the causal filter before cooldown on the full historical
context, then selects outcome years. Do not restart cadence at year/session
boundaries or gaps, or use future outcome exclusions to alter acceptance.

## Saved-evidence presentation support

`project_table(path, *, columns, where, section, source)` returns `(rows, bindings)`
for one explicitly selected saved CSV. `columns` is the authored list of column
definitions and scales; `where` combines exact original-string membership
predicates with AND. `source` is the caller's workspace-relative source path and
`section` identifies the table. Original data rows remain numbered from 1 before
filtering; output rows start at 0 for each table.

The helper preserves blank cells as null, exact `True`/`False` strings as booleans,
identifier underscores, and explicit numeric formats/scales without rounding or
another percent conversion. It rejects nonfinite numbers, empty selections, and
tables over 100 rows. It does not calculate statistics, infer columns, discover
runs, resolve storage, or assemble publication metadata. Only studies 08/09 adopt
it here; their identities, authored claims, prose, ordering, and CLI remain local.

Future exports from these two consumers retain their exact exporter, projector
and writer bytes as private `provenance/publish_web.py`,
`provenance/saved_evidence.py` and `provenance/presentation_revision.py`, with hashes
in `provenance/source-inventory.json`. The writer handles only an explicitly
supplied fresh revision and already-prepared payloads. All source reads, hash
checks and serialization finish before creating output; write failures preserve
diagnostic partials. Study identities, claims, ordering and assembly remain local.
The inventory identifies the producer implementation; it does not replace the
presentation manifest and completion checks in the [artifact workflow](../../templates/README.md#later-presentation-revisions).

## VWAP input diagnostic

From the workspace root after `scripts/bootstrap`:

```sh
scripts/uv run --locked --no-sync abacus-research doctor
scripts/uv run --locked --no-sync abacus-research doctor --read-sample
scripts/check-workspace
```

`doctor` diagnoses `session_anchored_vwap` inputs specifically. Its default lock
is `studies/05_session_vwap/inputs.lock.json`; an explicit `--inputs-lock` must
follow the supported VWAP lock contract, with schema version 1 and a supported
release version (currently `1.0.0`). Study 12/13 locks have different contracts.
It checks pinned release and catalog identities in the workspace and configured
publication root, plus applicable audit and quality-report hashes.

`--read-sample` hashes one selected partition and loads one session per
product/timeframe through Bhishma's public loader. The JSON field
`all_data_partitions_verified` remains false. This bounded diagnostic does not
verify every partition, reproduce features, execute a study, or certify
profitability. Both help commands work without configured data.

Storage resolution and environment overrides follow the
[path configuration](../../config/paths.example.toml) and
[architecture's storage guide](../../ARCHITECTURE.md#storage-and-data-access).
Preserve pinned and historical inputs under the [workspace rules](../../AGENTS.md#preserve-the-research-record).

To use the loader directly, pass the configured publication root and an explicit
version, as in `load_session_anchored_vwap(paths.publication_root, "ES", "2m",
version="1.0.0", start_date="2024-01-08", end_date="2024-01-09")`.

## Focused verification

Run these suites as separate processes; the study suites each import their own
`src.engine`:

```sh
./scripts/uv run --locked --no-sync python -m unittest discover -s packages/sahadeva/tests
./scripts/uv run --locked --no-sync python -O -m unittest discover -s packages/sahadeva/tests -p 'test_*export*.py'
./scripts/uv run --locked --no-sync python -m unittest discover -s studies/12_gc_ema_band_excursions/tests
./scripts/uv run --locked --no-sync python -m unittest discover -s studies/13_gc_ema_band_filter_validation/tests
./scripts/uv run --locked --no-sync abacus-research --help
./scripts/uv run --locked --no-sync abacus-research doctor --help
python3 scripts/check-agent-docs.py
./scripts/check-workspace
```

Synthetic method tests and the read-only workspace gate do not rerun historical
research or revalidate existing findings.

The [workspace harness](../../README.md#workspace-check-harness) registers this
suite as `sahadeva`, separate study processes, ordinary/optimized `guards`, and
command-help checks. Use `./scripts/check-workspace --context sahadeva` for exact
commands/cwd and prerequisites. Full discovery uses locked dependencies and
synthetic numerical, input and exporter fixtures; saved-output comparisons do not
revalidate historical findings. The workspace tooling profile uses only the
standard library. Harness execution uses the prepared locked environment
without sync and reports counts/skips from actual unittest results.

See the [study maintenance source map](../../studies/README.md#implementation-and-export-maintenance)
for rendering, exporter, and sealing ownership. Operational guards now include
the stage-bound numerical records and Study 12/13 phase provenance under
`--profile study-evidence`. Study 12 refuses optimized scientific verification;
ordinary/optimized guard passes do not certify analytical validity. The
[future-stage workflow](../../studies/README.md#future-stage-evidence) distinguishes
suite execution, recorded numerical evidence, scientific verification and sealing.

## Report content and publication

Sahadeva owns the statistical results, explanations, units, caveats, and strategy
interpretation that appear in reports. [Narada](../../apps/narada/README.md) owns
their selected web publication and presentation.

A future report producer can prepare `publication.json` with selected raster
figures in working storage, then include it in
`runs/<study-id>/<run-id>/` before the run is sealed. It follows
[Narada's generic report contract](../../apps/narada/contracts/report.schema.json).
The producer must declare the source run and supply the complete content to
publish. Narada validates and renders that content; it does not calculate
statistics, infer conclusions, or parse existing HTML or Markdown reports.

For an already completed run, save a new presentation revision under
`reports/exports/<study-id>/<run-id>/<revision-id>/`. Record source artifacts,
hashes, and rendering provenance using the [artifact guide](../../templates/README.md).
Changes to numerical methods or findings require a new analytical run.

The Sahadeva package does not yet generate this JSON. Existing run
artifacts remain unchanged. See the [publication workflow](../../docs/narada.md)
for the contract, explicit staging command, and immutable publication IDs.
