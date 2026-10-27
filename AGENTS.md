# Abacus agent guide

Start with [README.md](README.md) for setup and [ARCHITECTURE.md](ARCHITECTURE.md)
for current ownership, file placement, dependency boundaries, and artifact lifecycle.
Read the relevant component guide and study plan before editing or running research.
The user's current scope determines whether a planned study may be implemented or run.

## Route the task

Use this table to choose the owner, then read its linked guide before editing.
Paths are relative to the workspace root. [Architecture](ARCHITECTURE.md#file-placement-and-ownership)
is the authoritative placement map; the preservation rules below apply to every row.

| Task | Read first | Find or place files | Verify |
|---|---|---|---|
| **Bhishma — Data & Features**: ingestion, reusable bars/features, schemas | [Bhishma guide](packages/bhishma/AGENTS.md), [data layers](data/README.md) | Code/tests: `packages/bhishma/`. Contracts/manifests: `catalog/`. Data: `data/inbox/`, `data/raw/`, `data/staging/`, `data/curated/`, `data/features/`. New publication work follows the release contract. | Focused package tests; workspace checks for package/configuration changes; release checks for new publications |
| **Sahadeva — Research & Analysis**: study logic and shared methods | [Study agent guide](studies/AGENTS.md), [Sahadeva guide](packages/sahadeva/AGENTS.md), relevant study plan | One study's protocol/code/tests: `studies/<id>/`. Methods with demonstrated reuse: `packages/sahadeva/`. | Focused numerical tests and the study's declared checks |
| **Sahadeva — Evidence & Advice**: results, reports, interpretation | [Sahadeva guide](packages/sahadeva/AGENTS.md), [run guide](runs/README.md), [artifact conventions](templates/README.md) | Stage new output: `work/`. Seal completed evidence/reports: new `runs/<study>/<run>/`. Current advice: `strategies/`. Later presentation exports: `reports/exports/`. | Relevant study checks; index freshness when navigation inputs change |
| **Sahadeva — Research priority**: dated editorial triage and reassessment | [Priority rubric](strategies/research-priority-rubric.md), [strategy guide](strategies/README.md) | Current assessments: `strategies/research-priorities.json`; explicit standard-library projection: `scripts/project-research-priorities.py`; bounded saved presentation in Narada's existing catalog | Focused projector tests and `--profile research-priority`; app checks for projected UI changes; local reviewed-input hashing is separate |
| **Sahadeva — Historical Inputs & Evidence**: find retained files | [Sahadeva guide](packages/sahadeva/AGENTS.md), [data layers](data/README.md) | ATAS exports: `data/range_xv/`. Retained historical working evidence: `data/research/sahadeva/`. Preserve these files; stage new experiments in `work/`. | Recorded hashes for integrity checks; the consuming study's input checks |
| **Narada — Publishing**: webpage components and selected report publication | [Narada guide](apps/narada/AGENTS.md), [publication contract](docs/narada.md) | Renderer, components, publisher, and generated public bundles: `apps/narada/`. Source report content belongs to Sahadeva's run or presentation export. | App verify/test/lint/build; browser verification for UI changes |
| Documentation and navigation | [Architecture](ARCHITECTURE.md), nearest component guide | Current guidance at its owner; generated research index under `reports/` via its script | Documentation checker; index check only for navigation changes |
| GitHub preparation | [Upload and restoration guide](docs/github.md), [contribution guide](CONTRIBUTING.md) | Upload audit in `scripts/`; additive bulk locators in `docs/github-bulk-artifacts.json`; source-only CI in `.github/` | Read-only GitHub audit, synthetic tooling tests, clean-clone checks; do not rewrite sealed artifacts or push internal refs |
| Evidence integrity and exact references | [Contract/reference guide](docs/evidence-contract.md), [run guide](runs/README.md), [strategy guide](strategies/README.md) | Standard-library validators in `scripts/`; mutable references in `strategies/index.json`; opt-in manifests in new staged bundles only | Separate metadata, reference-byte and explicit future-bundle checks; index freshness after navigation inputs change |
| Workspace verification harness | [Harness guide](README.md#workspace-check-harness), [registry](config/workspace-checks.json) | Explicit owner/check records in `config/`; standard-library orchestration and synthetic tests in `scripts/` | Focused harness tests, documentation and tooling profiles; preserve the default gate |
| Reusable data request | [Request workflow](requests/README.md) | A new request under `requests/inbox/` | Request completeness and relevant publication checks at delivery |

## Preserve the research record

- Published datasets are immutable. Pin dataset IDs, versions, and manifest hashes.
  Never rebuild or overwrite a release during research or repository maintenance.
- Keep existing catalog snapshots, legacy snapshots, and imported run artifacts
  unchanged. Add migration metadata separately. Never rerun archived scripts into
  their fixed historical output locations.
- Range XV enhanced CSVs were clock-normalized at their existing paths on
  2026-09-24. Use their derived timestamps as inferred New York wall time;
  `source_timestamp` retains the raw export clock. The
  [clock migration record](docs/migration/range-xv-clock-normalization-20260924.json)
  maps historical and current hashes. Do not reinterpret sealed runs as having
  used the corrected files.
- Resolve storage through [path configuration](config/paths.example.toml) and its
  documented environment overrides. The publication root is this workspace (`.`),
  containing both `catalog/` and `data/`; it is not a package directory. The legacy
  research root is `legacy/sahadeva`, whose data/work links resolve inside Abacus.
  Retained historical working evidence lives in `data/research/sahadeva/`; it is
  not disposable scratch. See the [storage relocation record](docs/migration/storage-relocation-20260922.md).
- Stage new work outside completed runs; seal evidence under a unique run ID with
  frozen settings, code revision/dirty snapshot, environment lock, input hashes,
  exclusions, exact commands, and artifact hashes. Retain large evidence with
  locators and checksums outside ordinary Git history.
- Preserve `available_at` timing. Use unadjusted execution/P&L prices and disclose
  retrospective day eligibility. Distinguish null/undefined events from false.
- Planned strategies are not tested findings. Cite specific runs and metric/table
  references in strategy cards; retain negative and inconclusive results.
- Prepare any publication source before sealing its run. Later presentation-only
  exports use a separate revision directory as defined in [Architecture](ARCHITECTURE.md).
  Changes to a run's numbers, methods, or interpretation require a new run.
- Narada consumes explicit saved report bundles. It must not import research code,
  calculate statistics, or discover and expose arbitrary workspace artifacts.
  Its Node environment remains independent of the Python workspace. Publication
  and deployment follow the user's scope; workspace presence is not public consent.

## Choose the narrow verification gate

For documentation-only work, run `python3 scripts/check-agent-docs.py`.
Do not run numerical suites or rebuild Narada for prose-only changes.

For package/configuration or migration changes, run `./scripts/check-workspace`.
For study calculations, run focused tests beside the owning study or shared method
and the checks required by that study's protocol.

The default is the compatibility six-step gate, not complete repository coverage.
Use `./scripts/check-workspace --list` and explicit profiles/checks to select more;
use `--context study-12` (or another registered owner) before reading deeper context.
Planning commands use system Python's standard library and must remain read-only.
Tooling tests need no locked environment; package/study execution uses the existing
locked environment without sync. Preserve separate study processes and local
legacy `PYTHONPATH` overrides. Report skips, missing prerequisites and unexecuted
checks honestly; do not interpret integrity checks as research revalidation.
When adding an owner, suite or maintained guide, update the one
[registry](config/workspace-checks.json) and its bounded coverage tests.

For navigation inputs, select `--profile metadata`; for adopted exact saved rows,
select `--profile evidence-references`. Validate a future evidence bundle only
with an explicit target using the [contract guide](docs/evidence-contract.md).
Research-priority changes use the separate `--profile research-priority` check;
it validates the registry and public projection, not scientific validity.
`--check-reviewed-inputs` on the priority projector is an explicit local hash audit,
never an implicit metadata or Narada build requirement. Follow the
[rubric's reassessment workflow](strategies/research-priority-rubric.md#reassess-when-evidence-or-scope-changes)
when scope, evidence or relevant unpublished findings change.
Keep metadata validity, verified bytes, recorded checks and scientific validity
distinct. Initial structured references do not cover every strategy-card claim.

For navigation metadata changes, run `python3 scripts/build-research-index.py --check`;
regenerate with `python3 scripts/build-research-index.py` only when its inputs changed.

From `apps/narada`, publication/UI changes require `npm run verify`, `npm test`,
`npm run lint`, and `npm run build`; inspect the static preview when UI changes.
Use its [README](apps/narada/README.md) for setup and commands.

Update the nearest guidance when responsibility or file placement changes.
[The original proposal](docs/repository-structure-proposal.md) is historical context;
[ARCHITECTURE.md](ARCHITECTURE.md) is the current architecture reference.
