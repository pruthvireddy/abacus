# Sahadeva — Research & Analysis

Start with the workspace [agent map](../../AGENTS.md), the current
[architecture](../../ARCHITECTURE.md), and the [package README](README.md).
Read the relevant study's plan and pinned inputs before analytical work.

## Read and write

- Shared numerical methods, input integration, statistical checks, and report
  content generation belong in `src/abacus_sahadeva/`; shared tests belong in
  `tests/`. The current package supplies fixed-bar cooldown, VWAP input
  diagnostics, and bounded saved-CSV presentation projection. It is not a
  universal study engine. Add methods only when authorized studies demonstrate reuse.
- One study's entry point, event definitions, configuration, and tests belong
  under `studies/<study-id>/`, following the [study guide](../../studies/README.md).
  Keep signal rules, outcomes, parameters, and interpretation local; extract
  methods into this package when reuse warrants a shared interface.
- Obtain data and features through Bhishma's loaders and explicit input locks.
  Request reusable feature changes through the [request workflow](../../requests/README.md).
  Respect feature availability and the study's observation/execution conventions.
- Resolve retained inputs and evidence through the
  [storage guide](../../ARCHITECTURE.md#storage-and-data-access) and
  [data layers](../../data/README.md). Follow the
  [workspace preservation and clock rules](../../AGENTS.md#preserve-the-research-record)
  for historical inputs and sealed records.
- Develop new outputs under `work/`; seal verified evidence under a unique
  `runs/<study-id>/<run-id>/`, following the [run guide](../../runs/README.md).
  Keep current, dated interpretation in [strategy cards](../../strategies/README.md).
- Own dated research-priority judgments in
  [research-priorities.json](../../strategies/research-priorities.json), following
  the [rubric](../../strategies/research-priority-rubric.md). Assess one named
  candidate against its baseline and practical costs; retain failed primaries,
  contrary evidence, timing limits and a proposed discriminating next test.
  Preserve prior judgments in repository history. Explicitly mark Needs review
  for relevant new unpublished findings; do not refresh hashes to imply review.
  Publish only through the root standard-library projector's `--write` action.
  Narada presents its bounded saved projection and owns no rating inference.
- Sahadeva owns estimates, units, denominators, uncertainty, and conclusions.
  Narada owns the [publication schema](../../apps/narada/contracts/report.schema.json)
  and webpage presentation. Use that schema directly; do not copy it into this
  package. Prepare optional publication content before sealing a run, or use
  the separately identified revision convention in the
  [artifact guide](../../templates/README.md).

## Existing shared interfaces

| Capability | Owner / API | Consumers and checks |
|---|---|---|
| Fixed-bar cooldown | [cooldown.py](src/abacus_sahadeva/cooldown.py): `accepted_bar_indices` | Studies [12](../../studies/12_gc_ema_band_excursions/README.md) and [13](../../studies/13_gc_ema_band_filter_validation/README.md); [shared tests](tests/test_cooldown.py) and each study's engine tests |
| Saved-CSV projection | [saved_evidence.py](src/abacus_sahadeva/saved_evidence.py): `project_table(path, *, columns, where, section, source)` → `(rows, bindings)` | Studies 08/09 exporters only; [projection](tests/test_saved_evidence.py), [parity](tests/test_export_projection.py), and [guard](tests/test_export_guards.py) tests |
| Prepared revision writing | [presentation_revision.py](src/abacus_sahadeva/presentation_revision.py): `write_revision` | Studies 08/09 only; [writer tests](tests/test_presentation_export_writer.py); prepared payloads and exact producer-byte inventory |
| VWAP input-pin verification | [inputs.py](src/abacus_sahadeva/inputs.py): `verify_inputs` | `doctor`; [input-pin tests](tests/test_input_pins.py) |
| Bounded VWAP sample read | [inputs.py](src/abacus_sahadeva/inputs.py): `read_samples` | `doctor --read-sample`; one selected partition hash and one session per product/timeframe, not every partition |
| CLI routing | [cli.py](src/abacus_sahadeva/cli.py): `main` | Root/doctor help smoke checks and the read-only workspace gate |

Cooldown units are original chart-bar positions. Study 12's mask adapter uses
`np.flatnonzero`; study 13 passes absolute indices after applying its causal
filter. Accepting i suppresses i+1 through i+C; i+C+1 is eligible. Suppressed
candidates do not rearm, and each call is independent. Preserve full-history
cadence before outcome-year subsetting. Do not move future-path exclusions
before acceptance or introduce resets at years, sessions, or gaps.

`doctor` supports VWAP schema-version-1 locks and explicit supported release
versions; its default is `studies/05_session_vwap/inputs.lock.json`. It does not
accept arbitrary study locks. Manifest/catalog identities and applicable
audit/quality-report hashes are checked; `all_data_partitions_verified` stays
false, including with `--read-sample`. It does not reproduce features, execute
studies, or certify profitability. See the [capability map](README.md#current-capabilities)
and [diagnostic contract](README.md#vwap-input-diagnostic).

Keep saved-evidence projection limited to explicit CSV paths, authored columns,
selectors, scales, and binding context. Original-string filters and original
source-row identities must survive transfer. Do not move study identities,
claims, publication assembly, or output ownership into the shared helper.
New 08/09 revisions snapshot exporter, projector and writer bytes and inventory their exact hashes;
historical exporter snapshots and finalizers remain unchanged. Completion records
still follow the [presentation workflow](../../templates/README.md#later-presentation-revisions).

See the [task/source/test map](../../studies/README.md#implementation-and-export-maintenance).
Keep exporter tests in this package, numerical tests with their study, and
orchestration/record guards under `scripts/tests/`. Future 08/09/10 numerical
gates use stage-bound records; literal eight/eight/six counts apply only to the
explicit legacy log path before adoption. Exporter checks do not revalidate
research. Study 12 refuses optimized verification; operational guard success
does not make analytical assertions safe under `python -O`. Read the
[future-stage workflow](../../studies/README.md#future-stage-evidence) for phase
provenance, required scientific checks and old-stage refusal.

## Verify

Run commands from the workspace root:

```sh
./scripts/uv run --locked --no-sync python -m unittest discover -s packages/sahadeva/tests
./scripts/uv run --locked --no-sync python -O -m unittest discover -s packages/sahadeva/tests -p 'test_*export*.py'
./scripts/uv run --locked --no-sync python -m unittest discover -s studies/12_gc_ema_band_excursions/tests
./scripts/uv run --locked --no-sync python -m unittest discover -s studies/13_gc_ema_band_filter_validation/tests
./scripts/uv run --locked --no-sync abacus-research --help
./scripts/uv run --locked --no-sync abacus-research doctor --help
./scripts/uv run --locked --no-sync abacus-research doctor --read-sample
```

Run study suites in separate processes because both use generic `src.engine`
imports. Run the affected study's documented tests for analytical changes. Check known
examples, units, exclusions, and ambiguous outcomes; do not use a full historical
rerun as the default test. Run `scripts/check-workspace` for shared package,
storage-path, dependency, or cross-component changes. Publication changes also
use [Narada's checks](../../apps/narada/AGENTS.md). Documentation-only changes use
`python3 scripts/check-agent-docs.py`.

The [workspace harness](../../README.md#workspace-check-harness) exposes
`./scripts/check-workspace --check sahadeva`, `--profile guards`, and individual
`study-12`/`study-13` checks from the root. Each selected suite gets a fresh locked
Python process without sync; context and planning use only the standard library.
Preserve historical logs and completed evidence; use `--profile study-evidence`
for exact ordinary/optimized record/provenance guards. Neither profiles nor generic
reports create stage-bound records or authorize execution/sealing.
Full package discovery uses locked dependencies and synthetic numerical, input
and exporter fixtures; saved-output comparisons do not revalidate historical findings.

Offline evidence/navigation maintenance uses workspace validators under `scripts/`,
not numerical package methods. Read the [contract/reference guide](../../docs/evidence-contract.md)
for future opt-in bundles, exact strategy rows and task routing. Select root
`--profile metadata` or `--profile evidence-references` according to the change;
validate future bundles with an explicit target. Historical evidence remains
unassessed under the new contract; integrity does not establish research validity.

For priority maintenance, run `python3 scripts/project-research-priorities.py --check`
or `./scripts/check-workspace --profile research-priority`, plus the focused
`scripts/tests/test_research_priorities.py` suite. Exact selected report/section
identity errors fail; changed authored scope, selected coverage or rubric produces
Needs review without upgrading the dated score. The separate explicit
`--check-reviewed-inputs` action checks recorded local material hashes and may need
retained files unavailable in a source-only clone. It is not the app's dependency
or a numerical validation gate.
