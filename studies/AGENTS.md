# Study agent guide — Sahadeva

Sahadeva owns this directory. Follow the [Sahadeva instructions](../packages/sahadeva/AGENTS.md)
and [study conventions](README.md); use the [repository map](../ARCHITECTURE.md#file-placement-and-ownership)
for file placement. Before working on a study, read its README, plan, settings,
input lock, and decision notes when present, and follow the user's authorized scope.
Keep study-specific code and tests with that study; put reusable methods in
Sahadeva's package. Use the study's declared checks and the [run lifecycle](../runs/README.md)
for staged output and completed evidence.

For source maintenance, use the [task/source/test map](README.md#implementation-and-export-maintenance)
to distinguish numerical ownership, presentation exporters, and sealing gates.
Keep exporter tests in Sahadeva and orchestration/record guards under
`scripts/tests/`; keep numerical tests with their studies. Future 08/09/10 stages
use structured numerical-test evidence, with literal counts only in the explicit
legacy path. Read [future-stage evidence](README.md#future-stage-evidence) before
changing provenance or sealing; saved-output comparisons do not revalidate findings.

From the root, use `./scripts/check-workspace --context study-12` (or the relevant
owner) for bounded read-first paths and focused checks. Select
`./scripts/check-workspace --check study-12` or `--profile studies`; the
[harness](../README.md#workspace-check-harness) runs each suite in its own locked
Python process. Inspect declared prerequisites before selecting retained-input
or external-tool checks. A test profile is not authorization for a research run.

For navigation-only edits, read the [contract/reference guide](../docs/evidence-contract.md)
and use `--profile metadata`, then regenerate/check the index after inputs change.
Content kinds describe navigation; they do not change harness study ownership or
authorize market-data calculations. Exact evidence references require their
separate byte/row check.
