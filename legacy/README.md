# Preserved historical material

`bhishma/` and `sahadeva/` preserve source, configuration, documentation, and report files from the original project folders. The original folders remain preserved. Original snapshot hashes and mappings are recorded in [source-files.json](../docs/migration/source-files.json).

Bulk storage has been copied into Abacus. Compatibility links resolve entirely
inside this workspace:

- `legacy/bhishma/data` → `data/`.
- `legacy/sahadeva/data/*.csv` → corresponding files in `data/range_xv/`.
- `legacy/sahadeva/work` → `data/research/sahadeva/`.

The last location retains the original study/run structure and is not disposable
scratch. The configured legacy research root is `legacy/sahadeva`; no active
storage reference requires an original project folder. The
[storage relocation record](../docs/migration/storage-relocation-20260922.md)
records these changes separately. Historical snapshot files, including
[Bhishma's original data README](bhishma/data-readme.md), remain unchanged.

These snapshots retain their original commands, dates, paths, and conclusions for provenance. Commands may assume historical dependencies or input names that are no longer present. In particular, the old studies 1 and 2 refer to short-window CSV filenames absent from the current data directory. Do not substitute the newer exports silently.

Run existing unit tests through `scripts/check-workspace`. Do not run archived full study scripts against their fixed historical output paths. New experiments belong under `studies/` and unique `runs/` directories.

`presentation-exports` holds the prior poster/PDF/Excel collection. Its source-run mapping remains unverified; the index labels that explicitly.
