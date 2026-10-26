# Abacus

<img src="docs/assets/abacus-logo-readme.png" alt="Abacus logo: an abacus-shaped A with a gold bead beside the Abacus wordmark" width="520" />

A research workspace for trusted market data, reproducible studies, and selected
web reports. Abacus keeps data preparation, research evidence, and publication
separate so that every result can be traced to its inputs and saved run.

**[Explore the live research journal ↗](https://abacus-narada.vercel.app/)** ·
[GitHub repository](https://github.com/pruthvireddy/abacus) ·
[Architecture](ARCHITECTURE.md) · [Contributing](CONTRIBUTING.md) ·
[Documentation](docs/README.md)

## Explore the research

The [Narada website](https://abacus-narada.vercel.app/) presents selected studies,
figures, evidence qualifications, and summary downloads. Examples include
[session-anchored VWAP](https://abacus-narada.vercel.app/studies/session-vwap/),
[GC overnight breakout](https://abacus-narada.vercel.app/studies/gc-overnight-breakout-15m/),
and [Forex News across six futures](https://abacus-narada.vercel.app/studies/forex-news-ema/).

For the broader workspace, browse the [Markdown research index](reports/index.md)
or open `reports/index.html` locally. GitHub displays HTML source rather than the
interactive library. Some local report links require separately retained evidence.
The deployed collection can differ from current local publication selections.

Research includes negative and inconclusive results. Proposed strategies,
descriptive price paths, and assumed-fill simulations have different evidence
limits; the linked reports retain those qualifications. Repository checks do not
establish profitability or reproduce every historical calculation.

## How the workspace fits together

Abacus has three components: **Bhishma prepares dependable inputs, Sahadeva
investigates research questions, and Narada publishes selected saved findings.**

| Component and code | What it does | What it produces |
|---|---|---|
| **[Bhishma — Data & Features](packages/bhishma/README.md)** · `packages/bhishma/` | Ingests source data, validates quality, applies calendar and bar-building rules, and prepares reusable features. | Versioned datasets and features, schemas, catalog manifests and checksums, accessed through public loaders. |
| **[Sahadeva — Research & Analysis](packages/sahadeva/README.md)** · `packages/sahadeva/` and `studies/` | Defines study protocols, pins inputs, calculates events/outcomes and statistics, and interprets results. Study-specific logic lives beside its protocol; shared methods live in the package. | Saved metrics, tables and figures; frozen run evidence; dated strategy cards; explicitly selected report content for publication. |
| **[Narada — Publishing](apps/narada/README.md)** · `apps/narada/` | Validates selected report content and asset hashes, stages immutable public bundles, and renders study/report pages in its independent Node environment. | Downloadable report bundles and a static research website, released to Vercel through the [release workflow](apps/narada/releases/README.md). |

### Who passes what to whom

```mermaid
flowchart TD
    Inputs["Market data and source exports"]
    Bhishma["Bhishma<br/>Data and Features"]
    Sahadeva["Sahadeva<br/>Research and Analysis"]
    Evidence["Sealed research evidence<br/>runs/"]
    Strategies["Dated strategy cards<br/>strategies/"]
    Reports["Selected saved publication source<br/>Report JSON, figures, CSVs and provenance"]
    Narada["Narada<br/>Publishing"]
    Website["Research journal on Vercel"]

    Inputs -->|"Raw source inputs"| Bhishma
    Bhishma -->|"Versioned bars and features<br/>Schemas, manifests and hashes via public loaders"| Sahadeva
    Sahadeva -.->|"Reusable dataset or feature request"| Bhishma
    Sahadeva -->|"Frozen inputs, settings, code and results"| Evidence
    Evidence -->|"Exact evidence references"| Strategies
    Sahadeva -->|"Explicitly choose saved content and assets"| Reports
    Reports -->|"publication.json and declared assets"| Narada
    Narada -->|"Verified static output<br/>Separate authorized release"| Website
```

The main handoffs are:

1. **Bhishma → Sahadeva:** a pinned data/feature release with its manifest and
   hashes. A study uses Bhishma's loaders and records the exact input identities.
   New reusable inputs start as a [dataset request](requests/README.md) from
   Sahadeva to Bhishma.
2. **Sahadeva → Narada:** an explicitly selected `publication.json`, declared
   raster figures and summary CSVs, with source provenance. Sahadeva follows
   Narada's [report contract](docs/narada.md) when preparing that handoff.
   Prepare publication source before sealing a new run; later presentation-only
   revisions use `reports/exports/` with their own provenance.
3. **Narada → the website:** validated public bundles and verified static pages,
   deployed through a separately authorized release. Narada builds from those
   saved inputs independently of Python research execution.

Alongside publication, Sahadeva retains completed evidence in [runs/](runs/README.md)
and maintains current interpretations in [strategies/](strategies/README.md),
with exact links back to that evidence. The [architecture](ARCHITECTURE.md)
defines the authoritative ownership map and artifact lifecycle; the
[agent task map](AGENTS.md) routes maintenance.

## Quick start

A clone contains source, contracts, documentation, selected reports, and retained
small evidence. Market data, bulk ledgers, local configuration, environments, and
release payloads are excluded. GitHub is not a backup of the complete research
workspace; see [storage and restoration](docs/github.md#what-belongs-in-git).

### Documentation and workspace tooling

These checks use system Python's standard library and do not need market data:

```sh
python3 scripts/check-agent-docs.py
./scripts/check-workspace --profile tooling --profile metadata
```

### Website

Use Node 24 and npm. Narada has its own lockfile and needs no Python setup:

```sh
cd apps/narada
npm ci
npm run verify
npm test
npm run lint
npm run build
npm run preview
```

Open `http://127.0.0.1:4173`. See the [app guide](apps/narada/README.md) for preview
smoke checks and browser verification. Hosting uses the existing
[static release workflow](apps/narada/releases/README.md); pushing to GitHub does
not deploy the site or connect Vercel to this repository.

### Python research workspace

Use Python 3.11 and the committed uv lockfile:

```sh
./scripts/bootstrap
./scripts/check-workspace --list
./scripts/check-workspace --context study-12
```

`bootstrap` uses an installed uv or installs uv 0.12.18 under ignored `.tools/`,
then synchronizes the locked environment. Later package/study commands use
`./scripts/uv run --locked --no-sync ...`.

Restore exact pinned data separately before running data-backed checks or studies.
The default storage roots are `.` for publication and `legacy/sahadeva` for legacy
research. Copy [the path example](config/paths.example.toml) to
`config/paths.local.toml` only for machine-specific overrides. See
[Contributing](CONTRIBUTING.md) for setup and owner-specific prerequisites.

## Repository map

| Path | Contents |
|---|---|
| `packages/` | Bhishma and Sahadeva Python packages and their tests |
| `studies/` | Study protocols, settings, input pins, local code and tests |
| `runs/` | Immutable completed evidence; bulk artifacts may be retained separately |
| `strategies/` | Dated interpretations linked to specific saved evidence |
| `apps/narada/` | Independent website source, contracts, selected bundles and release receipts |
| `catalog/`, `requests/` | Pinned data contracts, manifests and reusable dataset requests |
| `reports/` | Generated local research index, quality records and presentation revisions |
| `scripts/`, `config/` | Setup, verification, navigation and workspace configuration |
| `docs/`, `templates/` | Current workflow references and artifact conventions |
| `legacy/` | Preserved historical source and compatibility links |
| `data/`, `work/` | Separately retained data/evidence and new execution staging |

## Data and preservation

Published datasets, catalog snapshots, sealed runs, and historical migration
records are immutable. Stage new work under `work/`; seal verified evidence under
a unique run ID. Changes to numbers, methods, or interpretation require a new run.
Later presentation revisions belong under `reports/exports/`.

The VWAP `session_anchored_vwap` release remains pinned to version `1.0.0`.
Range XV derived timestamps were
[normalized to inferred New York wall time](docs/migration/range-xv-clock-normalization-20260924.json)
on September 24, 2026; old sealed runs retain their original input identities.
Do not rebuild releases or rerun archived scripts into historical output locations.

Read the [data guide](data/README.md), [run guide](runs/README.md),
[artifact conventions](templates/README.md), and
[storage relocation record](docs/migration/storage-relocation-20260922.md)
before restoring data or executing research. Bulk files and ignored release
reconstruction snapshots need a separate backup.

## Reproducibility checks

Choose the narrow gate for the affected owner. Documentation uses
`python3 scripts/check-agent-docs.py`; study calculations use their declared
numerical tests; Narada changes use its four app gates and browser checks when
the UI changes. The [verification reference](docs/verification.md) explains each
check's actual scope and prerequisites.

## Workspace check harness

The [single registry](config/workspace-checks.json) owns check selection.
`./scripts/check-workspace` preserves the compatibility six-step gate:
documentation, Bhishma, Sahadeva, legacy studies 01 and 02, then VWAP input doctor.
It requires the prepared environment and configured inputs and is not complete
repository coverage. Planning with `--list`, `--dry-run`, and `--context` is read-only.

The [GitHub workflow](.github/workflows/ci.yml) runs source-only documentation,
tooling and metadata checks plus independent Narada checks. It does not run
data-backed research or deploy. See [detailed harness behavior](docs/verification.md#workspace-check-harness).

## Evidence and navigation checks

[Evidence contracts](docs/evidence-contract.md) distinguish metadata validity,
exact saved-row references, declared artifact integrity, and research validity.
Use explicit bundle targets and retain negative and inconclusive outcomes.
Regenerate research navigation only when its inputs change; freshness also
depends on which optional local artifacts are restored.
See [verification commands and limits](docs/verification.md#evidence-and-navigation-checks).

## GitHub repository

Source and selected saved artifacts are hosted at
[pruthvireddy/abacus](https://github.com/pruthvireddy/abacus). The
[GitHub guide](docs/github.md) records upload scope, the repeatable readiness
audit, clean-clone checks, and recovery of the previous repository contents.
The repository has no blanket reuse license. Vercel hosting follows its separate
static release workflow.
