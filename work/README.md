# Working storage

New disposable scratch/cache output and staged executions belong here and are
ignored by Git. Seal completed evidence under a unique run ID following the
[run guide](../runs/README.md); retain large event-level files with artifact
locators, checksums, and a deliberate backup policy.

The original Sahadeva working tree has been copied into
`data/research/sahadeva/`, preserving all study/run directories and file bytes.
It is retained historical evidence and is not disposable scratch.
`legacy/sahadeva/work` is an internal compatibility link to that location.
The original project folder remains preserved but is no longer needed for
active storage access. See the [data layer guide](../data/README.md) and
[storage relocation record](../docs/migration/storage-relocation-20260922.md).
