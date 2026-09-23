# Consolidation record — September 22, 2026

Destination: `/Users/ppanati/Documents/projects/abacus`. The user approved creating a new combined repository based on the saved structure proposal.

## What was consolidated

- Bhishma's active Python source and tests moved into `packages/bhishma`, with root discovery adapted for the installed workspace layout. The original source is preserved under `legacy/bhishma`.
- A small Sahadeva package supplies configured publication access and a read-only input verification command. Strategy calculations were not implemented by the migration.
- The catalog and fulfilled data requests were copied without changing their bytes. Data-quality reports appear under `reports/quality`.
- Four historical studies and 12 historical run folders were registered. Their existing report/table/figure/manifest bytes remain unchanged. Run copies are under `runs`; original historical snapshots also remain under `legacy/sahadeva`.
- The six-candidate VWAP plan is registered as study `05_session_vwap`, with a pinned input lock and explicitly proposed strategy cards.
- The PDF/PNG poster collection and workbook were preserved under `legacy/sahadeva/presentation-exports`. Their source-run correspondence is marked unresolved rather than inferred from filenames.
- Static HTML/Markdown indexes, artifact templates, package checks, and a migration verifier provide a common starting point for later studies.

## What remains at the original locations

- `/Users/ppanati/Documents/projects/abacus-bhishma/data`: original raw, curated, audit, and feature data; approximately 4.0 GB.
- `/Users/ppanati/Documents/projects/abacus-sahadeva/data`: original ATAS exports and metadata; approximately 729 MB.
- `/Users/ppanati/Documents/projects/abacus-sahadeva/work`: historical event records and intermediates; approximately 3.6 GB.

Both complete original project directories remain in place. The new local configuration references them. Ignored access links expose those data locations from this workspace; these links are not independent copies or backups. Do not delete or rename the original roots without migrating storage and updating the locators deliberately.

## Preservation evidence

`source-files.json` records each original path, mapped destination, size, and SHA-256 before active-code adaptation. It includes 773 copies from 424 unique source files. Active `packages/` copies are allowed to change for workspace integration; their exact historical counterparts remain under `legacy/`.

`verify-migration.py` checks the remaining 757 preserved copies against their recorded hashes. With `--verify-sources`, it also checks the 424 original files. With `--publication-root`, it checks all 46 published 2m/5m VWAP Parquet partitions and the eligibility audit against the unchanged publication manifests. `verification.json` records the results.

The copied catalog remains a pinned record of the existing publication. Its absolute paths are historical provenance. Runtime location is provided explicitly through local configuration; no dataset identity or version was silently replaced.

## Historical input limitation

Studies 1 and 2 include configurations naming earlier short-window exports such as `ESU6_rangexv5_0614_0904.csv`. Those files are not present in the current source `data/` directory, which contains newer 2024–2026 exports. The migration preserves the old configurations and conclusions without claiming a full rerun is currently possible.

The archived numerical tests can still run on their fixtures. Studies 3 and 4 refer to exports that are currently present; ingestion of an available ES export is checked separately against its saved audit count. This verifies migration compatibility, not a new assessment of strategy evidence.

## Working conventions after consolidation

Use the new workspace for future changes. Treat legacy source and imported result files as snapshots. Add new studies and unique run bundles, with explicit input locks and dated strategy interpretations. The latest run is not automatically a recommended or validated run.

No source repository was deleted, no published dataset was rebuilt, and no new strategy results were computed. Git was initialized locally for the combined workspace; no remote publication is part of this consolidation.
