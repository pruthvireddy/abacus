# Preserved historical material

`bhishma/` and `sahadeva/` preserve source, configuration, documentation, and report files from the original project folders. The original folders remain at their original paths. File hashes and mappings are recorded in `../docs/migration/source-files.json`.

These snapshots retain their original commands, dates, paths, and conclusions for provenance. Commands may assume historical dependencies or input names that are no longer present. In particular, the old studies 1 and 2 refer to short-window CSV filenames absent from the current data directory. Do not substitute the newer exports silently.

Run existing unit tests through `scripts/check-workspace`. Do not run archived full study scripts against their fixed historical output paths. New experiments belong under `studies/` and unique `runs/` directories.

`presentation-exports` holds the prior poster/PDF/Excel collection. Its source-run mapping remains unverified; the index labels that explicitly.
