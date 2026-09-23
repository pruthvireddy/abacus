# Repository structure for repeatable Abacus research

Prepared September 22, 2026. **Proposal only.** This document records the recommended organization; it does not initialize Git, migrate files, move publications, or implement research infrastructure.

## Recommendation

Combine Abacus Bhishma and Abacus Sahadeva into one Git repository before implementing the VWAP studies. Keep their names and responsibilities as separate Python packages. Use one research index, one convention for studies and run artifacts, and a common dependency lock where the packages' requirements are compatible.

The benefit is a single history connecting data-processing code, study definitions, statistical methods, and research conclusions. Published datasets retain their own version and checksum identities. Sharing a repository does not make a new feature release an automatic input to an old study.

Consolidate source code and research records first. Keep the current published data at its existing location through a configured publication root. Physical data migration is a separate operation with its own checksum and path checks.

## Current organization

Both project roots were checked with Git and are currently ordinary directories, not initialized Git repositories. Sahadeva's earlier run manifests also record a null Git revision. There is therefore no visible local Git history to reconcile in a consolidation, although the original directories should still be retained as migration snapshots.

| Project/location | Present purpose | Approximate local size |
|---|---|---:|
| Bhishma `src/`, `tests/`, `scripts/` | Ingestion, continuous contracts, features, loaders, validation | Under 1 MB combined |
| Bhishma `catalog/` | Dataset manifests, schemas, indicator definitions | 336 KB |
| Bhishma `data/` | Raw, curated, and published feature data | 4.0 GB |
| Bhishma `reports/`, `requests/` | Quality reports and data requests | 136 KB combined |
| Sahadeva `analysis/` | Four implemented studies and an export transformation | 1.0 MB |
| Sahadeva `plans/`, `prompts/` | Study plans and execution prompts | Under 100 KB |
| Sahadeva `data/` | ATAS Range XV exports and input metadata | 729 MB |
| Sahadeva `work/` | Event records, normalized data, and diagnostics | 3.6 GB |
| Sahadeva `reports/` | Versioned Markdown/HTML reports, CSV tables, charts, manifests | 14 MB |
| Sahadeva `New Folder With Items/` | PDF/PNG posters and an Excel summary | 4.1 MB |

The existing structure already has useful separation between source inputs, analysis code, intermediate results, and reports. Studies 1–2 have Python package definitions, configuration files, and tests. Studies 3–4 are standalone scripts with JSON configuration and fixed run identifiers. Report content and provenance depth vary across studies. Some outputs are organized by study/run, while the poster collection has no similarly discoverable place in the research index.

The main gaps are consistent version control, a shared environment and research library, a uniform artifact contract, a central index, and persistent strategy summaries tied to specific evidence. No strategy results were recomputed to assess the layout.

## Why consolidate now

1. **The projects form one workflow.** Bhishma publishes features; Sahadeva immediately consumes them to answer research questions. A single change can record a loader update and the corresponding consumer update together.
2. **The next analysis establishes reusable conventions.** The six VWAP candidates need common event timing, excursion measurements, clustered uncertainty, and report generation. This is a good point to make those conventions consistent before more standalone scripts accumulate.
3. **A code revision can identify the whole research implementation.** The run still pins input data independently, so old results remain tied to their original publication.
4. **Shared documentation and navigation become easier.** One entry point can lead from a strategy idea to its studies, runs, tables, figures, and current interpretation.
5. **Consolidation is comparatively small today.** Source code and curated reports are small, and neither directory has a visible Git history. The large files can stay in place.

The cost is some initial path and environment work, plus the need to preserve the data/research boundary explicitly. Bhishma's current README describes downstream repositories; a consolidation would revise that organizational statement while preserving the published-data contract.

Separate repositories would become preferable if the projects had different access permissions, independent teams, or external consumers needing distinct delivery cycles. None of those needs is evident in the inspected workspace. Separate package identities leave that option open later.

## Proposed destination

The name `abacus/` below is a suggested new root, not a directory created by this proposal.

```text
abacus/
  README.md                         # Entry point: setup, research index, boundaries
  AGENTS.md                         # Data immutability and research conventions
  pyproject.toml                    # Workspace configuration
  uv.lock                           # Tested dependency resolution
  .gitignore
  config/
    paths.example.toml              # Documented publication/storage aliases
    paths.local.toml                # Machine-specific locations; ignored

  packages/
    bhishma/
      pyproject.toml
      src/abacus_bhishma/            # Data ingestion, features, published loaders
      tests/
    sahadeva/
      pyproject.toml
      src/abacus_sahadeva/           # Shared statistics, events, execution, reporting
      tests/

  catalog/                          # Data contracts and pinned manifest records
  docs/                             # Architecture decisions and research methodology
  requests/                         # Requests for new reusable data/features

  studies/
    05_session_vwap/
      README.md                     # Question, status, links to accepted runs
      plan.md                       # Hypotheses and prespecified comparisons
      study.yaml                    # Products, events, horizons, costs, splits
      inputs.lock.json              # Dataset versions and manifest checksums
      run.py                        # Thin study-specific entry point, when implemented
      notes.md                      # Decisions, variants tried, interpretation changes
      notebooks/                    # Optional exploration

  runs/
    05_session_vwap/
      <unique_run_id>/              # One immutable completed evidence bundle
        manifest.json
        config.json
        inputs.lock.json
        metrics.json
        tables/
        figures/
        report.html
        report.md
        advice.md
        events.manifest.json        # Location and hashes of larger event records

  strategies/
    vwap_extreme_fade.md            # Current interpretation with exact evidence links
    vwap_reentry_fade.md
    ...

  reports/
    index.html                      # Generated visual research library
    index.md                        # Portable index readable in Git

  templates/                        # Shared report, chart, and strategy-card styling
  legacy/                           # Historical code/report snapshots and migration map
  data/                             # Optional local data location; bulk files ignored
  work/                             # Rebuildable scratch/cache; ignored
```

This is the target organization, not a requirement to create every folder immediately. Small studies should remain a configuration plus a thin entry point, using shared functions when there is genuine reuse. Extract recurring functionality from the first implementation; avoid building a general-purpose backtesting framework in advance.

A Python workspace using uv is a reasonable implementation choice: its workspace members keep individual package definitions and share a lockfile. Dependency compatibility must be checked first; packages with incompatible requirements can keep separate environments even in the same Git repository. Existing historical environment records should remain available rather than being overwritten by the new lock. [Official uv workspace documentation](https://docs.astral.sh/uv/concepts/projects/workspaces/).

## Responsibilities and dependency direction

Bhishma owns source ingestion, calendars, eligibility, contract mapping, aggregation, reusable features, schemas, quality validation, and immutable publication releases.

Sahadeva owns hypotheses, strategy-specific events, outcome labels, forward returns, MFE/MAE, statistical comparisons, execution assumptions, train/validation/test design, and interpretation. Strategy outcomes belong in research run artifacts. A reusable feature becomes part of Bhishma only through an explicit feature publication with its own contract and version.

Studies depend on Sahadeva and Bhishma's public loaders. Bhishma must not depend on a particular strategy or study. Reusable numerical methods and reporting live in Sahadeva; individual study definitions live under `studies/`.

The current feature loader accepts a **publication project root**, then appends `data/features/...`. Moving the Python package must not silently reinterpret that argument as the package directory or new Git root. During initial consolidation, configure the existing `/Users/ppanati/Documents/projects/abacus-bhishma` as the publication root. Treat copied catalog records as byte-identical pinned references to that publication, not a new dataset release. Retain the original publication catalog as part of that publication's identity.

Store dataset ID, release version, manifest hash, and portable partition paths in `inputs.lock.json`. Resolve physical roots from local configuration. A manifest's original absolute path remains provenance; do not rewrite an immutable manifest merely to suit a new machine. A later locator change should be explicit and validated against the same content hashes.

## Strategy, study, and run are different identities

| Identity | Meaning | Example |
|---|---|---|
| Strategy | A durable idea that may accumulate evidence across studies | `vwap_extreme_fade` |
| Study | A defined research question and protocol | `05_session_vwap` |
| Run | One execution of a particular configuration, code, environment, and input set | A UTC timestamp plus unique suffix |

The six VWAP candidates can share one study and input population. They do not need six packages or copies of the feature dataset. A later execution-cost study may reference the same strategy IDs while having a different protocol and new runs.

Protocol changes should receive a recorded version or new study identity when the question materially changes. Each attempted configuration belongs in the study's experiment history, including negative and inconclusive results. This preserves knowledge about how many variants have already been inspected.

## The artifact bundle for every completed run

Every run should produce both readable conclusions and the values supporting them:

| Artifact | Content |
|---|---|
| `report.html` | Main presentation: concise findings, charts, comparison tables, expandable detail, links to evidence |
| `report.md` | Durable narrative with definitions, findings, limitations, and reproduction instructions |
| `metrics.json` and `tables/` | Exact statistical results in JSON/CSV/Parquet, with denominators, units, intervals, sample/split labels, and stable metric identifiers |
| `figures/` | Exportable SVG/PNG charts; interactive HTML where interaction improves inspection |
| `advice.md` | Dated research interpretation, applicability, evidence strength, and next action |
| `manifest.json` | Run identity, code and configuration identity, dependency lock, data hashes, validation outcomes, artifact checksums, and exact command |
| `events.manifest.json` | Location, schema, row counts, checksums, and retention status of event-level evidence too large for Git |

Generate report tables, charts, and displayed headline numbers from the saved numerical results. Keep a shared visual template so later studies look related without manually copying old figures or percentages. Rendering a new format should not recompute the statistics. Record the report/template version alongside the run; a corrected published report receives a new revision linked to the original rather than silently replacing it.

HTML is the primary visual artifact because it supports readable narrative, interactive exploration when useful, and links to underlying tables. Keep its assets local for offline use. PDF is an optional shareable snapshot; Excel is an optional review export. These formats should all point to the same study/run and data evidence.

Use a temporary work directory during execution. Publish a completed run under a unique ID only when its required artifacts and checks are present. Never overwrite an existing completed bundle. The manifest should record the Git revision and any uncommitted source snapshot needed to reproduce the run; a commit hash alone is insufficient when the working tree is dirty.

## Strategy advice that stays useful months later

Maintain one strategy card under `strategies/` for each enduring idea. It should answer:

- What exactly is the setup, and when is its information available?
- Which products, anchors, sessions, and timeframes were studied?
- What evidence supports it, what contradicts it, and how uncertain are the estimates?
- What are the exact supporting run IDs and table/metric references?
- Were costs modeled, and was evaluation exploratory, on validation data, or on a protected test period?
- Where does it fail or remain untested?
- What is the current research action: investigate further, retain as a filter, test execution, or reject?

Use explicit statuses such as proposed, exploratory, supported on held-out data, inconclusive, rejected, or superseded. A supported behavioral effect and a strategy with positive modeled net returns are different evidence claims and should be labeled precisely.

The card represents the current synthesis across runs. Each run's `advice.md` preserves what was concluded at that time. Update the strategy card through dated decisions with evidence links; do not rewrite old run advice to match today's view. Rejected hypotheses remain searchable so future analyses do not unknowingly repeat them.

## A browsable research library

The generated `reports/index.html` should list studies and strategy cards with product, topic, status, data release, latest completed run, and designated reference run. The newest run may be a debugging run or failed candidate, so “latest” must not automatically mean “recommended.”

For this user, useful navigation is: **VWAP → outside-2σ fade → ES/NY/5m → reference run → statistics and charts → current strategy interpretation**. The corresponding Markdown index keeps the same links available without a custom application.

Begin with a static local library and consistent run artifacts. A service, database, or hosted dashboard can be added if actual collaboration or interactive querying requires it. The statistics remain portable files regardless of the eventual interface.

## Storage and preservation

The inspected projects already contain roughly 8 GB of source/feature data and intermediate work. “Saved within the project” and “committed to Git history” need distinct policies:

- Commit source code, study protocols, environment locks, schemas, manifests, strategy cards, report sources, compact summary tables, and selected small presentation artifacts.
- Keep raw/curated/feature datasets, large event tables, environments, and disposable caches outside ordinary Git history, even when physically located under the project directory.
- Back up irreplaceable inputs and accepted run evidence separately. Git-ignore status is not a backup policy.
- Distinguish rebuildable scratch files from retained event-level evidence. Do not delete existing `work/` just because the new layout calls future scratch output disposable.
- Give each externally stored artifact a stable identifier, checksum, location, and retention status. A small manifest does not preserve the data unless the referenced content is retained or recoverable.

GitHub's documented large-file constraints are another reason to establish these boundaries before an initial commit. [GitHub large-file guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

## A staged consolidation

1. Inventory and snapshot the existing directories and their manifests. Record the old-to-new path map and classify historical inputs, scratch, accepted evidence, and presentation exports.
2. Create the new Git root with exclusions in place before adding files. Bring in code, documentation, contracts, and curated research artifacts while preserving original snapshots.
3. Set up the two package identities and a tested dependency configuration. Replace machine-specific runtime assumptions with explicit local path configuration for new studies.
4. Keep published Bhishma data at its existing root. Verify that the installed loader still opens the pinned release and that its manifest hashes remain unchanged.
5. Establish the small standard study/run bundle and shared presentation template. Use the planned VWAP study as the first new study following the convention.
6. Register old studies and reports in the index without recalculating results or rewriting historical manifests. Keep old study IDs and run IDs. Relocated historical reports get a migration record; preserve original locations or compatibility paths where needed for old commands and links.
7. Place the existing posters and workbook into the index as historical presentation artifacts, with verified source-run links where available and provenance marked unresolved otherwise.
8. Consider physical data relocation only afterward, using byte-for-byte checks and an explicit root-locator change. Repository cleanup alone does not justify republishing or modifying VWAP 1.0.0.

Acceptance for the future migration should include reading the pinned release through the new package, running existing relevant tests in the resolved environment, opening representative old reports, verifying evidence links and checksums, and reproducing at least one small historical case where its inputs remain available. Any missing historical input is a documented limitation rather than something silently substituted.

If consolidation is deferred, adopt the same `studies/`, immutable run bundle, strategy-card, index, and data-root conventions in Sahadeva now. That reduces future migration to packaging and paths rather than redesigning the research records. The preferred timing remains before substantial new VWAP implementation.

## Inspected references

- [Bhishma README](/Users/ppanati/Documents/projects/abacus-bhishma/README.md)
- [Bhishma package definition](/Users/ppanati/Documents/projects/abacus-bhishma/pyproject.toml)
- [Pinned feature loader](/Users/ppanati/Documents/projects/abacus-bhishma/src/abacus_bhishma/feature_loader.py)
- [Existing detailed run manifest](/Users/ppanati/Documents/projects/abacus-sahadeva/reports/01_reversal_follow_through/20260906T_full_v3/run_manifest.json)
- [Existing HTML report](/Users/ppanati/Documents/projects/abacus-sahadeva/reports/01_reversal_follow_through/20260906T_full_v3/report.html)
- [Existing study configuration](/Users/ppanati/Documents/projects/abacus-sahadeva/analysis/04_reversal_candle_quality/config.json)
- [Planned VWAP candidates](/Users/ppanati/Documents/projects/abacus-sahadeva/plans/05_potential_vwap_strategies.md)
