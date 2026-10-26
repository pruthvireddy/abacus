# Evidence bundles

[Sahadeva — Research & Analysis](../packages/sahadeva/AGENTS.md) owns completed
run evidence. Find protocols and executable study code through the
[study agent guide](../studies/AGENTS.md); use the [repository map](../ARCHITECTURE.md#file-placement-and-ownership)
for related storage and publication locations.

Imported historical runs preserve their original study IDs, run IDs, reports, tables, figures, and run manifests. Additive `import_manifest.json` files explain migration provenance; an imported result has not been re-evaluated or promoted to a validated strategy.

For a new completed run, save frozen config/input lock, metrics and tables,
figures, HTML/Markdown report, dated advice, and a manifest with code/environment/
input identities and artifact checksums. Stage under `work/<study-id>/<run-id>/`
and seal at `runs/<study-id>/<run-id>/` only after verification. Never append to
or overwrite a completed run. See the [artifact convention](../templates/README.md)
and current [repository map](../ARCHITECTURE.md).

Include optional Narada source content and selected figures before sealing the
run. A later presentation-only revision belongs under
`reports/exports/<study-id>/<run-id>/<revision-id>/`, with its source hashes and
rendering provenance. New numerical methods or findings require a new run.
Current interpretation across runs belongs in a dated [strategy card](../strategies/README.md).

Use sortable UTC timestamps plus a unique suffix for new run IDs, for example
`20260922T153000Z_a1b2`. Preserve all imported study and run IDs as they are.

Future research bundles can opt in to `contract: "abacus.evidence/v1"`, documented
in the [contract/reference guide](../docs/evidence-contract.md). Run
`python3 scripts/check-evidence-bundle.py <explicit-bundle-or-manifest>` from the
workspace root. It verifies inventoried local bytes and retained provenance;
external declarations remain unverified. It never scans runs or executes commands.
Existing manifests are unassessed under this contract, including manifests with
generic `schema_version: 1`; historical runs and logs remain unchanged.

Future studies 08/09/10 require stage-bound numerical-test records, with log-only
compatibility available only through an explicit legacy option before adoption.
Future 12/13 stages additionally retain execution bytes before calculation and
artifact-bound scientific verification receipts; old stages without those
records are refused rather than reconstructed. Their existing manifest families
remain separate from `abacus.evidence/v1`. See the
[study evidence workflow](../studies/README.md#future-stage-evidence) for separate
suite, recording, validation and sealing commands. Integrity cannot substitute
for the owning study's required scientific/numerical pass gates.
