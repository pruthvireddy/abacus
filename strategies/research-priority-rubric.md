# Research priority rubric

Sahadeva owns the dated editorial judgments in
[research-priorities.json](research-priorities.json). Narada presents their bounded
public projection. Rubric version **1.0** asks:

> How strongly does the saved evidence justify further focused investigation
> toward an actionable, material edge?

This is research triage, not a probability of profitability, a paper-quality
rating, or a trading recommendation. The registry's five band definitions are
authoritative: 1 Pause; 2 Define and test; 3 Targeted follow-up; 4 Strong candidate;
5 Highest priority. Not assessed, Needs review and Not applicable are nonnumeric
states, never zero stars. There is no required score distribution.

## Review an explicitly scoped candidate

Read the study's guide, protocol, decisions and relevant saved reports before
assessing it. Name the product/model/question being prioritized; one attractive
exploratory cell cannot promote an entire multi-analysis study. Record practical
materiality in the candidate's own units and relative to its baseline, including
costs, fills, availability, missing outcomes, uncertainty, validation history,
multiple testing and dependent populations. Preserve failed primaries and
separate subsequent exploration. Record both supporting and contrary evidence,
the main blocker, and a next experiment with support and rejection criteria.
Propose that experiment; this workflow does not execute it.

External claims without independent verification and descriptive associations
without resolved execution/costs cannot justify four or five. Four requires a
material effect in credible separated evaluation with explicit execution/cost
assumptions and bounded remaining work. Five additionally requires independently
corroborated material evidence. Such scores require explicit hash-pinned
`highPriorityEvidence` for material effect, separated evaluation and execution/
costs; five also requires independent corroboration. A cheap experiment is not
supporting evidence. Reference checks verify declarations and bytes, not the
scientific truth of those judgments.

Initial reviews identify **Codex (AI-assisted editorial review; human approval
pending)** as reviewer. They are local editorial proposals, not an independent
human sign-off, new statistical validation or permission to publish.

## One current registry and an explicit publication boundary

Each registry assessment has a stable ID/study ID, state/optional integer score,
review date/reviewer, rubric version/hash, scope/rationale/materiality, supporting
and contrary saved-section references, blocker and next test. `reviewedMaterials`
retains the actually read protocol/report paths and byte hashes locally. These
paths and review notes are never projected into Narada. `reviewedPublications`
pins the entire selected report set by run/content identity and canonical bundle
bytes; `reviewedStudySha256` binds authored question/scope and selection order.
The scope hash binds the full authored study, including findings, limitations and
statistic selectors/context. It excludes generated priorities and resolved values;
file modification dates are never freshness evidence.

Use system Python's standard library from the workspace root:

```sh
python3 scripts/project-research-priorities.py --check
python3 scripts/project-research-priorities.py --write
python3 scripts/project-research-priorities.py --check-reviewed-inputs
```

`--check` is read-only. It validates the authoritative registry, exact public
report/bundle/section identities and the generated catalog fields. `--write`
updates only the generated `researchPriority` fields and the public rubric in
Narada's existing catalog. Authored studies, report selections and reading paths
remain unchanged. Do not edit a rating in both places. Ordinary Narada
verify/build reads only its catalog and selected app-owned bundles; it never
imports this registry, Python, private locators or research directories.

`--check-reviewed-inputs` separately hashes the explicitly recorded local review
materials. Missing or changed inputs are reported for editorial reassessment,
not silently substituted or called scientifically invalid. A source-only clone
may lack retained materials. This separate check is not the app's build gate.

## Reassess when evidence or scope changes

A bad/missing publication, section, run or content identity is an error. It is
not disguised as a low score or Needs review. A still-valid historical assessment
whose authored scope, selected evidence set or rubric changed becomes **Needs
review**. Its dated previous score remains context; it is excluded from active
numeric filtering/sorting. New evidence never automatically upgrades a score.

Hashes cannot prove that later contrary findings were considered. When new
unpublished findings, relevant decisions, changed protocols or other unprojected
evidence may alter the judgment, the owner must explicitly mark it:

```sh
python3 scripts/project-research-priorities.py --mark-needs-review 05_session_vwap --reason "New contrary findings require editorial review."
python3 scripts/project-research-priorities.py --write
```

The flag preserves the original assessment and score. Re-read supporting and
contrary evidence, including later work; make a new dated assessment ID and
refresh its scope, rubric and evidence bindings only after that review. Remove
the flag only after completing the reassessment. Preserve previous assessments
in repository history: commit an approved assessment before replacing it, and
use its prior ID/date/revision to retrieve the historical judgment. Never edit
sealed runs, old advice, original report content or historical release records.

Changing the rubric guide bytes or registry band definitions, meaning or disclaimer
conservatively makes earlier assessments need review, even if the version was not
bumped. The assessment rubric hash binds both the guide bytes and the canonical
public definitions. Update the rubric version for a
substantive definition change and republish its projection. Assessments are not
made fresh merely by changing a publication date or copying newer hashes.

## Verification and scope

Run focused standard-library projector tests, the projection check, documentation
and metadata checks, and Narada's verify/test/lint/build plus static-preview
smoke and browser inspection. Keep editorial assessment, verified reference
bytes, recorded execution checks and scientific validity distinct. Completed
studies outside the explicit public catalog are inventoried separately; they
are not projected or published by this workflow.
