# Abacus architecture

This document describes the current repository and where new work belongs.
[README.md](README.md) provides setup; [AGENTS.md](AGENTS.md) routes tasks and checks.
The [original structure proposal](docs/repository-structure-proposal.md) records the
historical consolidation decision. It is not the current file-placement guide.

## Components and dependency direction

| Component | Responsibility | Entry point |
|---|---|---|
| **Bhishma — Data & Features** | Ingestion, calendars, contracts, aggregation, reusable features, validation, immutable publication, and public loaders | [Package guide](packages/bhishma/AGENTS.md) |
| **Sahadeva — Research & Analysis** | Questions, events/outcomes, statistics, execution assumptions, research reports, and interpretation | [Package guide](packages/sahadeva/AGENTS.md) and [study agent guide](studies/AGENTS.md) |
| **Narada — Publishing** | Validate explicitly selected saved report content, record provenance, render webpages, and export a static site | [App guide](apps/narada/AGENTS.md) |

The permitted flow is source data → Bhishma publication → Sahadeva study → saved
run evidence → selected publication content → Narada. Studies call Bhishma's public
loaders with pinned versions; shared research methods live in Sahadeva. Bhishma
must not depend on a strategy, study, or Narada. Narada consumes report bundles,
not Python modules, live calculations, private data paths, or whole run directories.
Its independent Node/npm environment builds without the Python environment.

A study needing a reusable feature sends a [dataset request](requests/README.md)
to Bhishma. Strategy-specific labels, entries, exits, and success criteria remain
research work. Forward-looking labels must be declared as such, never passed off
as features available at signal time.

Bhishma owns dataset and feature contracts; `catalog/` pins released copies.
Sahadeva owns metric meanings, denominators, units, and interpretation. Narada
owns the generic [report schema](apps/narada/contracts/report.schema.json) that
Sahadeva report producers consume. Keep each schema at its owning location and
reference it directly; do not maintain competing copies of the same contract.

## File placement and ownership

| Location | Owner and contents |
|---|---|
| `packages/bhishma/src/abacus_bhishma/` | Bhishma implementation and public loaders |
| `packages/bhishma/tests/` | Tests for Bhishma package behavior and contracts |
| `packages/sahadeva/src/abacus_sahadeva/` | Sahadeva shared research integration and methods with demonstrated reuse |
| `packages/sahadeva/tests/` | Tests for those shared methods and integration |
| `studies/<study-id>/` | Sahadeva study plan, settings, input lock, metadata, notes, and study-specific implementation/tests |
| `runs/<study-id>/<run-id>/` | Sahadeva immutable completed research evidence, including preserved imported runs |
| `strategies/` | Sahadeva dated current interpretations with exact links to evidence across runs |
| `apps/narada/` | Narada source, publication contracts/publisher, tests, selected public bundles, and independent npm lock |
| `apps/narada/content/studies.json` | Narada's explicitly authored public study identities, stable slugs and featured/related publication selections; validated against staged bundles, never discovered from research directories |
| `apps/narada/content/release-sources.json` | Private explicit sealed-run or presentation-revision locators for release provenance audits; never consumed by the website or uploaded |
| `apps/narada/releases/<release-id>/` | Durable Narada release identity, checksum/source-audit records and append-only deployment/verification events; no credentials or public research bundles |
| `apps/narada/.release-artifacts/<release-id>/` | Ignored local static deployment inputs and separate dirty-source reconstruction snapshot; retain or archive outside Git for kept releases |
| `catalog/` | Bhishma pinned dataset manifests, schemas, indicator definitions, and calendar contracts |
| `config/` | Workspace storage/settings conventions; ignored machine-specific path configuration |
| `config/workspace-checks.json` | Explicit versioned verification profiles, checks, owners and maintained guide/context paths; no numerical definitions |
| `requests/` | Reusable dataset requests and preserved delivery specifications |
| `templates/` | Human-authored research/report/strategy presentation conventions and templates |
| `reports/index.html`, `reports/index.md` | Generated local research navigation, owned by the index builder |
| `reports/quality/` | Preserved Bhishma publication quality records |
| `reports/exports/<study-id>/<run-id>/<revision-id>/` | Later presentation-only exports with their own provenance manifest |
| `scripts/` | Workspace setup, validation, migration, and navigation orchestration |
| `docs/evidence-contract.md` | Opt-in future research-bundle contract, exact strategy CSV-row references, and bounded task routing |
| `CONTRIBUTING.md`, `docs/verification.md`, `docs/github.md` | Contributor setup, check prerequisites, GitHub upload scope and later first-push instructions |
| `docs/github-bulk-artifacts.json` | Additive locators/checksums for bulk artifacts excluded during GitHub preparation; original sealed records stay unchanged |
| `.github/` | Source-only CI and contribution review templates; no research execution or automatic deployment |
| `docs/` | Current supporting workflow guidance and identified historical migration/proposal records |
| `legacy/` | Immutable historical source, settings, and report snapshots |
| `data/inbox/`, `data/raw/`, `data/staging/`, `data/curated/`, `data/features/` | Bhishma physical data layers, excluded from Git; preserve provider batches and published release identities |
| `data/curated/external_levels/source=<source>/version=<version>/` | Bhishma versioned external narrative levels; retain source text, captured revisions and availability qualifications, with raw captures and reproducible extracts in their respective data layers |
| `data/range_xv/` | Sahadeva historical ATAS inputs and export manifest, excluded from Git |
| `data/research/sahadeva/` | Sahadeva retained historical working evidence, excluded from Git and kept with checksums; not disposable scratch |
| `work/` | Sahadeva new execution staging and workspace disposable scratch/caches; retained historical evidence lives under `data/research/sahadeva/` |

Place one study's entry point at `studies/<study-id>/run.py`, its local modules
under `studies/<study-id>/src/`, and its tests under `studies/<study-id>/tests/`.
Keep this code near the protocol it implements. Extract methods into Sahadeva only
when reuse is needed; study parameters and strategy rules remain local. There is
no universal `src/shared/` directory. Root scripts invoke owned code and orchestrate
checks; numerical implementations do not accumulate in `scripts/`.

Package tests stay beside their package; study-specific numerical tests stay with
the study; publication/UI tests stay under `apps/narada/tests/`. Synthetic fixtures
belong with the tests that consume them. Large input data and retained event tables
stay in configured storage with locators/checksums, not committed test fixtures.

Checks for workspace utilities belong in `scripts/tests/`. The documentation
checker's own tests run with
`python3 -m unittest discover -s scripts/tests -p 'test_check_agent_docs.py'`.
The [check registry](config/workspace-checks.json) supplies the explicit allowlist
to [workspace orchestration](scripts/workspace_checks.py) and the documentation
checker. A bounded filesystem inventory detects uncovered study/test directories;
it does not select arbitrary executable files. No second study-ID registry or
repository-wide Python test namespace belongs in the harness.

## Authoritative, generated, pinned, and historical files

Active package/app source and study definitions express current behavior. A study's
`plan.md`, `study.yaml`, `inputs.lock.json`, and decision notes define its protocol;
`study.json` supplies navigation metadata. Freeze the executed settings and identities
inside each completed run. A later edit to a study definition never changes what a
previous run tested.

Saved metrics/tables are the numerical evidence for report text, figures, and exports.
Generate displayed values from that evidence rather than manually maintaining parallel
numbers. A completed run's manifest records its exact execution and artifact identities.
Strategy cards hold the current synthesis, with dated decisions and precise run references;
older run advice remains a record of the interpretation made at that time.

Future research bundles may explicitly adopt `abacus.evidence/v1`. The offline
validator checks declared local artifact/provenance bytes and reports external
declarations as unverified; heterogeneous historical manifests are unassessed.
This does not establish executed-code dependency completeness or scientific
validity. Current strategy metadata may hold optional hash-pinned `evidence_refs`
with exact saved CSV selectors/columns, without copying statistics or changing
the dated card's interpretation. See the [contract/reference guide](docs/evidence-contract.md).

Navigation metadata supports additive `content_kind: indicator_implementation`.
Its implementation links and qualifications are rendered separately from planned
or computed research. Harness owner kind remains independent of navigation kind.

`catalog/` contains pinned contracts and publication records, not machine configuration.
Existing copied catalog files remain byte-identical references to their releases. New
publication work requires an explicit new release and matching contracts; repository
maintenance does not authorize replacing pinned records. `config/paths.local.toml`
locates storage on a machine; changing a locator does not change a dataset identity.

The research indexes are generated from registered study/strategy metadata and saved
runs by [the index builder](scripts/build-research-index.py). Edit those inputs and
regenerate instead of hand-editing index output. Templates are authoring sources, not
computed findings. Narada's staged publication bundles are immutable versioned copies;
its `out/` and build caches are generated. Details are in [Narada's contract](docs/narada.md).

Narada may compact its generated static report JSON as a verified lossless
delivery transform. Canonical public bundles retain their original bytes and
content hashes; new release receipts separately pin canonical and delivered
file identities. This changes transport formatting without rewriting evidence
or creating new analytical findings.

`legacy/`, imported run contents, fulfilled request snapshots, and migration records
preserve historical context. Add provenance separately; do not modernize their paths or
rewrite old results. Historical commands may contain fixed output paths and must not be
rerun into those locations. A migration did not audit imported conclusions.

## Storage and data access

The configured `publication_root` is this workspace (`.`), which contains both
`catalog/` and `data/`. Bhishma's original `raw/`, `staging/`, `inbox/`, `curated/`,
and `features/` trees now live directly under `data/`, with their nesting preserved.
Sahadeva Range XV inputs live in `data/range_xv/`; its retained working evidence lives
in `data/research/sahadeva/` with the original study/run structure. These are real
copied files. The former external `data/bhishma` alias has been removed.

The configured `legacy_research_root` is `legacy/sahadeva`. Compatibility links
under `legacy/` resolve to data inside Abacus. The Range XV enhanced CSVs were
clock-normalized in place on 2026-09-24; their before/after hashes are in the
[migration record](docs/migration/range-xv-clock-normalization-20260924.json),
and sealed run artifacts remain unchanged. Resolve paths through [configuration](config/paths.example.toml) and
its documented overrides, not a package's installation directory. The original
project folders remain preserved, but active storage no longer depends on them.
Bulk data remains ignored by Git and needs its own backup.

See the [data layer guide](data/README.md), the
[storage relocation record](docs/migration/storage-relocation-20260922.md), and the
[read-only storage verifier](scripts/verify-storage.py). The relocation preserves
bytes and release identities; it does not rerun ingestion or research.

Pin release versions and manifest hashes independently of physical locations. Loaders
must respect feature `available_at`; executions/P&L use unadjusted prices. Report
retrospective day eligibility and keep undefined event flags distinct from false values.
See the [Bhishma README](packages/bhishma/README.md) for the actual loader/storage contract.

## Study, run, and publication lifecycle

A **strategy** is an enduring idea, a **study** defines an investigation, and a **run**
is one execution of frozen settings/code/inputs. Planning files alone do not authorize
implementation or computation. Follow the user's requested scope and preserve negative
and inconclusive results alongside positive findings.

1. Define the protocol and sample, pin inputs, and record exploratory variants.
2. Prepare an execution under `work/<study-id>/<run-id>/`. Calculate and verify results,
   then derive reports, figures, advice, and any intended `publication.json` source from
   the saved numerical evidence. Select its figures explicitly.
3. If web publication is planned, include its source and selected assets **before sealing** the completed run.
   Record settings, input hashes, code revision/dirty snapshot, environment lock,
   exclusions, exact commands, checks, and artifact hashes in the evidence bundle.
4. Seal the verified bundle at a unique `runs/<study-id>/<run-id>/`. Do not append,
   overwrite, or regenerate files in that completed directory. Keep large external
   evidence retained and identifiable through its locator/checksum manifest.
5. Publish selected source content through Narada's explicit publisher. Raw data and
   saved report content are not automatically public. Public bundles are downloadable;
   a workspace file's presence is not authorization to publish it or deploy a site.

For an already sealed run, a later **presentation-only** export belongs at
`reports/exports/<study-id>/<run-id>/<revision-id>/`. This can add a new layout or
format while preserving the saved results and their meaning. Include a small
`manifest.json` identifying source-artifact paths and hashes, renderer/version,
exact rendering command, and the changes made. This is a guidance convention;
there is no generic export generator implemented by this architecture document.

Changes to a run's numerical results, methods, or interpretation require a **new run**,
not an export revision or edits to old evidence. Current strategy-card advice may evolve
as a separately dated synthesis across cited runs. Every changed Narada publication uses
a new publication ID, including a presentation revision; previous public copies remain
unchanged. Never amend a completed run merely to fit a publication contract.

Narada's authored study catalog generates stable `/studies/<slug>/` pages and
study-oriented library navigation. Every publication keeps its immutable
`/reports/<id>/` route. Catalog selections assert source-run attribution and
distinguish another run, an exploratory supplement and a presentation revision.
Changing a featured selection does not change a research reference, evidence
status or old publication. The build reads only app-owned metadata and staged
bundles; study-specific saved-evidence exporters stay beside their owning study.

See [evidence bundles](runs/README.md), [artifact conventions](templates/README.md),
[report export locations](reports/README.md), and the
[publication workflow](docs/narada.md) for the owning documents.

## Verification follows ownership

| Change | Appropriate gate |
|---|---|
| Documentation only | `python3 scripts/check-agent-docs.py` — read-only, standard-library checks |
| Package/configuration or migration | `./scripts/check-workspace` plus focused tests for changed behavior |
| Study calculations | Focused numerical tests under the study or shared package and the study's declared checks |
| Navigation metadata | `./scripts/check-workspace --profile metadata`; regenerate after inputs change, then `--profile navigation` for freshness |
| Exact strategy evidence references | `./scripts/check-workspace --profile evidence-references`; only explicitly referenced saved artifacts are read |
| Future evidence bundle | `python3 scripts/check-evidence-bundle.py <explicit-bundle-or-manifest>`; opt-in declared artifacts, no run discovery |
| Narada publication/UI | From `apps/narada`: `npm run verify`, `npm test`, `npm run lint`, `npm run build`; browser verification when UI changes |

Documentation edits alone do not need numerical suites, data reads, or a site build.
The [documentation checker](scripts/check-agent-docs.py) validates its maintained
guide list and local Markdown link targets, including ordinary heading anchors.
It does not enforce dependency direction, execute the documented commands, or
lint all historical artifacts. Declare maintained guides in the check registry's owner records;
use ordinary Markdown links for concrete navigation and inline code for example
paths. Its command help documents the supported Markdown syntax.
The [harness guide](README.md#workspace-check-harness) distinguishes the unchanged
six-step default from tooling, study, configured-input, navigation and Node checks.
Each independently owned Python suite runs in a separate process. Execution uses
the prepared locked environment without sync; planning/context and workspace
tooling use the standard library. Results disclose counts/skips and fail-fast
unexecuted scope; zero discovery and an entirely skipped requested suite do not pass.
Live preview, retained private evidence and heavy storage checks stay explicit.
The runner never registers research, sealing, publishing or deployment actions.
Maintain current ownership guidance beside the component that owns the work; update
this document when boundaries or placement change. Keep historical proposals and
migration snapshots as records, with current guidance linked separately.
