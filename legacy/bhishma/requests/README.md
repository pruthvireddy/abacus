# Dataset requests

Downstream repositories should request reusable bars, indicators, or meta columns by copying and completing:

```text
requests/templates/feature-dataset-request.yaml
```

The completed request can be pasted into a Codex task working in Abacus Bhishma or saved under `requests/inbox/` with a unique request ID. Do not edit the shared template in place.

Abacus Bhishma owns market-data selection, session-aware aggregation, reusable feature calculation, validation, and versioned publication. Strategy-specific entries, exits, success criteria, and performance statistics normally remain in the requesting repository. Forward-looking research labels must be explicitly declared so they cannot be confused with causal features.

A completed delivery should publish data under `data/curated/` or `data/features/`, record lineage and checksums under `catalog/datasets/`, create a report under `reports/quality/`, and return a delivery receipt containing stable paths and the manifest checksum.

Fulfilled request specifications are snapshotted under `requests/fulfilled/` so a delivery remains reproducible even if the requesting repository later changes its copy.
