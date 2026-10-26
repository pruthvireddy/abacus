# Storage relocation — 2026-09-22

The user authorized consolidating the remaining original Bhishma and Sahadeva
storage into Abacus. All three trees were copied and checked with SHA-256 before
switching configuration. The originals were retained. No datasets were rebuilt
and no strategy calculations were run.

This record supersedes the **storage locations** in the
[initial migration record](README.md) and [initial inventory](storage-locations.json).
Those records, pinned dataset manifests, imported runs, and historical source
snapshots remain unchanged.

## Current storage map

Paths below are relative to the Abacus workspace root.

| Original location | Current location | Files | Bytes |
|---|---|---:|---:|
| `abacus-bhishma/data/` | `data/` (original README preserved separately) | 5,323 | 4,247,985,295 |
| `abacus-sahadeva/data/` | `data/range_xv/` | 9 | 763,996,105 |
| `abacus-sahadeva/work/` | `data/research/sahadeva/` | 154 | 3,829,648,668 |
| **Total** | | **5,486** | **8,841,630,068** |

```text
data/
  inbox/databento/        # vendor landing zone
  raw/databento/          # original provider batches, compressed DBN and metadata
  staging/databento/      # decoded/extracted intermediate files
  curated/
    instruments/         # contracts and symbology
    bars/                # contract bars
    continuous/          # versioned continuous series
  features/
    bars/                # versioned bar/feature releases, including VWAP
    audits/              # retained eligibility and release audits
  range_xv/              # original ATAS exports, README and export manifest
  research/sahadeva/     # retained historical study/run working evidence
```

Bhishma's provider, schema, product, interval, version, and year partitions are
unchanged. Its original data README remains byte-identical at
[legacy/bhishma/data-readme.md](../../legacy/bhishma/data-readme.md); the current
[data guide](../../data/README.md) explains the consolidated layout.
The inventory includes filesystem metadata files such as `.DS_Store` to account
for the full source trees. Counts reflect the copy-time inventory, which is more
recent than the initial consolidation inventory.

`data/research/sahadeva/` retains the original study and run directory names.
These files are retained evidence, not disposable caches. New execution scratch
continues to belong under `work/`. Completed run artifacts stay under `runs/`;
their historical manifests are not rewritten merely to change physical storage.

## Configuration and compatibility

The local and example configurations now use:

```toml
[paths]
publication_root = "."
legacy_research_root = "legacy/sahadeva"
```

The publication root contains both `catalog/` and `data/`. Existing dataset IDs,
release versions, and hashes are unchanged. Historical absolute paths in manifests
remain provenance; current loaders resolve the pinned relative file paths from
the configured root.

Internal relative links preserve existing local access:

- `legacy/bhishma/data` → `../../data`
- `legacy/sahadeva/work` → `../../data/research/sahadeva`
- Seven `legacy/sahadeva/data/*.csv` links → `../../../data/range_xv/<filename>`

The former external `data/bhishma` alias was removed. `data/range_xv` is now a
real directory. Active storage configuration and these compatibility links no
longer depend on either original project folder. Archived scripts may contain
historical absolute commands; read them as historical records and do not rerun
them into their fixed old output paths.

## Verification and retention

[The complete storage inventory](storage-files-20260922.json) records each source,
destination, size, SHA-256, directory, and compatibility link. Copy verification
checked source stability and separate destination files, rather than hard links.
[The nonbulk audit](nonbulk-audit-20260922.json) accounts for 421 current meaningful
source/code/report files, all already preserved by hash in Abacus. It found no
root or nested Git repositories to transfer. Environments and caches are excluded;
Abacus uses its own locked Python environment.

Recheck the copied storage independently of the originals:

```sh
python3 scripts/verify-storage.py
./scripts/uv run python scripts/verify-migration.py --publication-root .
./scripts/check-workspace
```

`verify-storage.py --verify-sources` additionally compares original files while
those folders exist. Routine verification does not require them. Verification
results are recorded in [the acceptance summary](storage-acceptance-20260922.json):

- [Storage verification](storage-verification-20260922.json): 5,486 file hashes,
  8,841,630,068 bytes, 320 directories, and nine internal links passed without
  reading original source roots.
- [Publication verification](storage-publication-verification-20260922.json):
  757 preserved-copy checks and all 46 VWAP partitions passed at the new root.
- [Workspace log](storage-workspace-check-20260922.log): 84 tests and six loader
  samples passed using Abacus storage. All 16 utility tests also passed, including
  missing/corrupt-file and external-link cases for the new verifier.
- All 19 active navigation guides passed; the research index remains current.

The preserved-copy verifier now checks the original request guide at
`legacy/bhishma/requests/README.md`, because the active `requests/README.md`
contains current workflow guidance. Its recorded historical SHA-256 remains
mandatory; the original inventory was not altered.

Bulk files remain ignored by Git. Back up the actual `data/` tree and its checksum
inventory together; cloning the repository alone will not restore the datasets.
Also retain or recreate the nine ignored compatibility links listed in the inventory
when restoring this workspace on another machine.
The source folders remain available as the immediate fallback after this copy.
The prior missing short-window exports described in the initial migration record
remain missing; this relocation preserves all files currently available and does
not reconstruct those old inputs.
