# Dataset requests

Sahadeva studies and other consumers request reusable bars, indicators, or
metadata from **Bhishma — Data & Features** by copying and completing:

```text
requests/templates/feature-dataset-request.yaml
```

Save the completed request under `requests/inbox/` with a unique request ID and
link it from the requesting study's notes. A task working on Bhishma can then use
that specification. Do not edit the shared template in place. See the current
[repository map](../ARCHITECTURE.md) and [Bhishma instructions](../packages/bhishma/AGENTS.md).

Bhishma owns market-data selection, session-aware aggregation, reusable feature
calculation, validation, and versioned dataset publication. Study-specific entries,
exits, success criteria, and statistics remain with Sahadeva and the study.
Forward-looking research labels must be explicitly declared so they cannot be
confused with causal features.

A completed delivery follows Bhishma's configured dataset project root:
`data/curated/` or `data/features/`, lineage and checksums under `catalog/datasets/`,
and quality reports under `reports/quality/` relative to that root. Return stable
dataset identities, paths, and manifest checksums. The current publication root
is this workspace (`.`), with physical data under `data/`. Creating a request
does not authorize rebuilding an existing release. The
[storage relocation](../docs/migration/storage-relocation-20260922.md) preserved
release identities and bytes. Pin delivered records for the consuming study.

Fulfilled specifications are preserved under `requests/fulfilled/` so the agreed
delivery remains identifiable as the consuming study evolves. Keep existing
snapshots unchanged; create a new request for changed requirements.
