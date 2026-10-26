# Contributing to Abacus

Start with the [README](README.md), [architecture](ARCHITECTURE.md), and
[task map](AGENTS.md). The architecture defines ownership and file placement;
the nearest component guide defines its workflow and checks. Read a study's
plan, settings, input lock, and notes before changing its implementation.

## Choose a development scope

A Git clone contains source, contracts, documentation, and the research artifacts
selected for version control. It does not restore ignored market data, retained
working evidence, local configuration, or development environments.

| Work | Required local resources |
|---|---|
| Documentation and workspace utility maintenance | System Python 3; no research environment or market data for the documentation and tooling profiles |
| Narada website maintenance | Node 24, npm, and dependencies installed from the app's lockfile; ordinary verify/test/lint/build use app-owned saved content |
| Python package or study maintenance | Python 3.11 and the prepared locked workspace environment; some checks also require retained data, Ruby, or `clang++` |
| Research execution or full input verification | The exact pinned input releases and retained evidence declared by the study, restored separately |

Inspect prerequisites before choosing a check. A source-only clone cannot be
expected to pass configured-input or retained-evidence checks. Report missing
resources and unexecuted checks explicitly; a smaller passing check does not
establish that the full research workspace is available.

## Set up the Python workspace

From the repository root:

```sh
./scripts/bootstrap
./scripts/check-workspace --list
```

`bootstrap` synchronizes [uv.lock](uv.lock) for all workspace packages. It uses
an available uv installation or installs uv 0.12.18 in the ignored `.tools/uv`
directory. [.python-version](.python-version) selects Python 3.11. Installation
may need network access. Keep dependency changes explicit and update package
metadata and the lockfile together when dependencies change.

After setup, use the locked environment without implicit synchronization:

```sh
./scripts/uv run --locked --no-sync abacus-research --help
./scripts/check-workspace --context study-12
```

The harness uses the same locked/no-sync convention for package and study
execution. Run independently owned study suites in separate processes; some
studies intentionally use local `src` imports. Preserve the harness's local
legacy `PYTHONPATH` overrides rather than combining all studies in root pytest.

For data-backed work, restore the required input bytes from their separate
backup. The default publication root is the workspace containing `catalog/`
and `data/`; the legacy research root is `legacy/sahadeva`. When needed, copy
[paths.example.toml](config/paths.example.toml) to the ignored
`config/paths.local.toml`. Relative paths resolve from the workspace root;
the example documents supported environment overrides. See the
[data guide](data/README.md) and [input diagnostic](packages/sahadeva/README.md#vwap-input-diagnostic).
Do not rebuild a published dataset to compensate for missing local files.

## Set up Narada

Narada has an independent Node/npm environment. From `apps/narada`:

```sh
npm ci
npm run verify
npm test
npm run lint
npm run build
npm run preview
```

The preview serves the static export at `http://127.0.0.1:4173`. Follow the
[Narada README](apps/narada/README.md) for HTTP smoke checks and browser
inspection. A local build uses explicitly selected saved bundles; it does not
calculate research statistics. Publishing a report or deploying a release is
a separate action governed by the [publication contract](docs/narada.md) and
[release workflow](apps/narada/releases/README.md).

## Place changes with their owner

- Put reusable ingestion, calendars, features, contracts, and loaders in
  [Bhishma](packages/bhishma/AGENTS.md); request new reusable datasets through
  [requests](requests/README.md).
- Put one study's definitions, execution code, and numerical tests under its
  `studies/<study-id>/` directory. Shared methods with demonstrated reuse belong
  in [Sahadeva](packages/sahadeva/AGENTS.md).
- Put website rendering, publication validation, and UI tests in
  [Narada](apps/narada/AGENTS.md). Keep research calculations outside the app.
- Put setup, navigation, and integrity orchestration in `scripts/`; numerical
  implementations remain with their package or study.

Update the nearest guide when responsibilities or placement change. Declare a
new maintained guide, owner, or suite in the single
[check registry](config/workspace-checks.json) and update its bounded coverage
tests. Avoid a second ownership or study-ID registry.

## Preserve the research record

Published data, pinned catalog snapshots, imported evidence, and completed runs
are immutable. Keep existing release IDs, manifest hashes, and historical paths.
Retained evidence under `data/research/sahadeva/` needs a separate backup and is
not disposable scratch. Do not rerun archived scripts into fixed historical
output directories or rewrite sealed results during source cleanup.

Stage new execution under `work/`. A new completed run needs a unique ID and
frozen settings, code revision/dirty snapshot, environment lock, input hashes,
exclusions, exact commands, checks, and artifact hashes. Prepare intended
publication source before sealing. Later presentation-only changes use a new
revision under `reports/exports/`; changed numbers, methods, or interpretation
require a new run. Follow the [run guide](runs/README.md) and
[artifact conventions](templates/README.md).

Preserve feature `available_at` timing, use unadjusted execution/P&L prices,
disclose retrospective eligibility, and keep undefined events distinct from
false. Proposed studies are not tested findings. Cite exact runs and saved
metrics or table rows, including negative and inconclusive outcomes.

## Verify the affected scope

Use the narrow gate required by the change:

| Change | Check |
|---|---|
| Documentation only | `python3 scripts/check-agent-docs.py` |
| Standard-library workspace utilities | `./scripts/check-workspace --profile tooling` |
| Package, configuration, or migration | Focused owner tests and `./scripts/check-workspace` |
| Study calculations | The affected study's numerical tests and declared protocol checks |
| Navigation metadata | `./scripts/check-workspace --profile metadata` |
| Adopted exact saved-row references | `./scripts/check-workspace --profile evidence-references` |
| Narada publication/UI | App verify/test/lint/build; inspect the browser for UI changes |

Inspect selections before execution with `--list`, `--dry-run`, or
`--context <owner>`. These planning commands use system Python's standard
library and do not run checks or read private data. The no-argument gate is the
compatibility six-step gate, including configured inputs; it is not complete
repository coverage. See the [harness guide](README.md#workspace-check-harness).

When navigation inputs change, regenerate with
`python3 scripts/build-research-index.py`, then check freshness with
`python3 scripts/build-research-index.py --check`. Do not edit generated indexes
by hand or regenerate them for unrelated prose changes.

Validate a future evidence bundle only with an explicit bundle or manifest
target as described in the [evidence contract](docs/evidence-contract.md).
Metadata validity, byte integrity, recorded tests, and scientific validity are
different claims. Integrity checks do not revalidate research conclusions.

## Prepare a review

Review `git status` and the full diff before staging. Keep credentials, local
path settings, environments, dependency folders, bulk data, caches, and scratch
output out of commits. Do not use `git add -f` to bypass ignore rules for these
files. A GitHub upload can expose every tracked file and its history; check the
actual upload scope rather than assuming `.gitignore` removes existing history.

Describe the concrete problem, resulting behavior, affected owner, and checks
run. Disclose skipped or unexecuted checks and missing prerequisites. For
research changes, identify the protocol, pinned inputs, and new run or revision
without implying that ordinary code tests reproduce the findings. Keep source
maintenance and publication/deployment decisions explicit.
