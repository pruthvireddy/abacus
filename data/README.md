# Local data access

Bulk data is excluded from Git. On the migrated machine, `bhishma` and `range_xv` are ignored symlinks to the original published data and ATAS exports. These are access paths, not copied or newly published datasets.

The configured publication root remains `/Users/ppanati/Documents/projects/abacus-bhishma`; loaders need that root, not this data directory. Configure other machines through `config/paths.local.toml` or the documented environment override. Keep the original data folders and backups. Git alone does not preserve these datasets.

See `docs/migration/README.md` and the pinned study input lock for identities and verification.
