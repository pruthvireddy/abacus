# Abacus workspace conventions

Read README.md and the relevant study plan before editing or running research.

- Bhishma owns data preparation, feature calculations, publication contracts, and quality checks. Sahadeva owns hypotheses, outcomes, statistics, execution assumptions, and interpretation.
- Published datasets are immutable. Pin dataset IDs, versions, and manifest hashes explicitly. Never rebuild or overwrite an existing release as part of research or repository maintenance.
- Resolve storage from config/paths.local.toml or documented environment overrides. A publication root is distinct from this repository root.
- Keep legacy snapshots and imported run artifacts unchanged. Add migration metadata separately. Never rerun archived scripts into their fixed historical output locations.
- Use unique run IDs and frozen configurations for new work. Record code revision/dirty snapshot, environment lock, source hashes, sample exclusions, and exact commands. Keep large input/event data out of Git and preserve its locator and checksum.
- All feature use must respect available_at. Use unadjusted prices for executions/P&L, and disclose retrospective day eligibility. Keep null/undefined events distinct from false events.
- A planned strategy is not a tested finding. Strategy cards cite specific run IDs and metric/table references; retain negative and inconclusive findings.
- Reuse shared methods where useful. Do not implement or run a study merely because a plan exists; follow the current user's requested scope.
- Run scripts/check-workspace after migration/configuration changes and focused numerical tests after analytical changes. Regenerate the research index with scripts/uv run python scripts/build-research-index.py when study/run metadata changes.
