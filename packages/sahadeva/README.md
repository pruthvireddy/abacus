# Sahadeva research package

Sahadeva consumes explicitly versioned Bhishma publications. It owns research
methods, event/outcome definitions, statistics, execution assumptions, and
interpretation. Study definitions and saved evidence live in the workspace's
`studies/`, `runs/`, and `strategies/` directories.

This initial package provides read-only configuration and input-pin checks.
The planned VWAP strategies have not been implemented or evaluated.

From the workspace root after `scripts/bootstrap`:

```sh
scripts/uv run --locked abacus-research doctor
scripts/uv run --locked abacus-research doctor --read-sample
scripts/check-workspace
```

`doctor` checks pinned release and catalog identities in both the workspace and
the original publication root, plus the release audit and quality report.
`--read-sample` also checks one data partition's hash and loads one session per
product/timeframe through `abacus_bhishma.feature_loader`. It does not revalidate
all data partitions, run strategy calculations, or create results.

`config/paths.local.toml` resolves machine storage. Relative storage paths are
relative to the workspace root. Environment overrides are
`ABACUS_WORKSPACE_ROOT`, `ABACUS_PUBLICATION_ROOT`, and
`ABACUS_LEGACY_RESEARCH_ROOT`. The input lock retains portable relative paths;
historical absolute paths in immutable data manifests remain provenance.

To use the loader directly, pass the configured publication root and an explicit
version, as in `load_session_anchored_vwap(paths.publication_root, "ES", "2m",
version="1.0.0", start_date="2024-01-08", end_date="2024-01-09")`.
