# Bhishma data package

Bhishma owns ingestion, calendars, continuous contracts, reusable features,
validation, and immutable data publication. Sahadeva consumes its public loaders.

Moving this package into `packages/bhishma` did not create a data release. The
existing versioned data remains at the configured publication project root,
which contains the original `catalog/`, `data/`, `reports/`, and `requests/`.

Set `paths.publication_root` in the workspace's `config/paths.local.toml`, or
`ABACUS_PUBLICATION_ROOT`. Explicit CLI `--root` or `--project-root` arguments
take precedence. An explicit `--output` on the Databento CLI takes precedence
over its default destination. Paths are resolved at command execution; they are
never inferred from this installed package's directory. `--help` requires no
data configuration or network access.

The existing loaders retain their public interfaces and require an explicit
publication root. The feature loader also requires an explicit release version.
Use the read-only `abacus-research doctor --read-sample` from the workspace root
to check access to the pinned VWAP publication. Build/download commands remain
separate operations and must not be used as workspace verification.

Tests use synthetic examples plus the configured historical publication for
existing integration checks. Integration checks skip when no publication root
is configured; they fail if a configured root is invalid. Run
`scripts/check-workspace` from the workspace root for the full migration checks.
