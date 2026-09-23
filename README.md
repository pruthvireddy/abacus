# Abacus

A single workspace for trusted market data, reproducible strategy research, and a browsable research library.

**Start with the [research library](reports/index.html)** or its [Markdown index](reports/index.md). The [six VWAP candidates](studies/05_session_vwap/plan.md) are planned research; the repository consolidation did not run them.

## Responsibilities

- **Bhishma** (`packages/bhishma`) prepares and validates historical data and publishes reusable, immutable feature releases.
- **Sahadeva** (`packages/sahadeva`) consumes pinned releases and provides research integration, with shared statistical and reporting methods added as studies require them.
- **Studies** specify hypotheses and configurations. **Runs** preserve execution evidence. **Strategy cards** accumulate dated interpretations with links to that evidence.

## Setup

The migrated local workspace already has `config/paths.local.toml`. On another machine, copy `config/paths.example.toml` to that filename and configure the publication and historical-research roots.

```sh
./scripts/bootstrap
./scripts/check-workspace
```

`bootstrap` uses uv if available or installs uv 0.12.18 into the ignored `.tools/uv` directory, then synchronizes the locked environment. Python 3.11 is selected by `.python-version`. It does not install packages into either original project's environment.

Verify input identities and optionally read a small feature slice:

```sh
./scripts/uv run abacus-research doctor --workspace-root . --inputs-lock studies/05_session_vwap/inputs.lock.json --read-sample
```

Rebuild navigation after adding study/run metadata:

```sh
./scripts/uv run python scripts/build-research-index.py
```

Open `reports/index.html` directly in a browser for the offline library. Existing reports, figures, tables, and presentation exports are linked there. No web service is required to use it.

## Layout

| Directory | Purpose |
|---|---|
| `packages/bhishma/` | Data preparation, feature publication, loaders, and their tests |
| `packages/sahadeva/` | Research integration and shared research utilities |
| `catalog/` | Byte-identical pinned dataset manifests, schemas, and indicator contracts |
| `studies/` | Questions, protocols, configurations, input locks, and study notes |
| `runs/` | Immutable completed evidence bundles, including imported historical runs |
| `strategies/` | Current strategy interpretation with explicit evidence status |
| `reports/` | Research index and data-quality reports |
| `templates/` | Study, report, and strategy-card conventions |
| `docs/` | Architecture and migration records |
| `legacy/` | Exact historical source/config/report snapshots |
| `data/`, `work/` | Ignored bulk data access and working storage |

## Data and preservation

The original `abacus-bhishma` and `abacus-sahadeva` directories are preserved. Large data and historical event files remain there; local configuration and ignored links connect this workspace to them. **Keep those original directories while these storage references are in use.** The new Git repository includes code, metadata, and curated artifacts; Git does not back up the external datasets.

The published VWAP release remains explicitly pinned to `session_anchored_vwap` version `1.0.0`. Copying its catalog into this workspace does not create a new release or permit a rebuild of the old one. Input manifests remain unchanged, including their original provenance paths.

Historical study IDs, run IDs, reports, and manifests are preserved. Imported findings have not been re-evaluated by the migration. Some old short-window input filenames are absent from today's exports; see the [migration record](docs/migration/README.md). Avoid running archived scripts into their fixed historical output paths.

## Reproducibility checks

`./scripts/check-workspace` checks configured input identity, reads a small feature sample, and runs the active package and archived numerical test suites. To check the historical copies and all 46 VWAP partitions explicitly:

```sh
./scripts/uv run python scripts/verify-migration.py --verify-sources --publication-root /Users/ppanati/Documents/projects/abacus-bhishma
```

See [verification results](docs/migration/verification.json), [source mappings and hashes](docs/migration/source-files.json), and the [approved architecture proposal](docs/repository-structure-proposal.md).
