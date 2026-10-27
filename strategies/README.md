# Strategy evidence cards

Each card records the current interpretation of an enduring idea. It links to exact studies and runs as evidence accumulates. Three VWAP candidates have original statistical price-path evidence from study 05, re-entry has partial exploratory evidence, and two candidates remain proposed.

[Sahadeva — Research & Analysis](../packages/sahadeva/AGENTS.md) owns this
interpretation. Find the underlying protocol through the [study agent guide](../studies/AGENTS.md)
and saved numerical evidence through the [run guide](../runs/README.md).
See the [repository map](../ARCHITECTURE.md) for their relationship to presentation exports.

Keep setup definitions, evidence supporting and opposing the idea, applicability, execution assumptions, evidence status, and dated decisions together. Current advice can change; preserve each run’s historical advice. Record `inconclusive`, `rejected`, or `superseded` ideas so later work can find them. `supported_on_held_out_data` requires identified evidence and does not alone establish positive net returns.

Add every card to `index.json` and run `python scripts/build-research-index.py`. See [the card template](../templates/strategy.md) and [research library](../reports/index.html).

An optional `evidence_refs` array in `index.json` pins exact saved CSV rows by
study/run, artifact SHA-256, original-string selectors and ordered columns.
See the [reference contract](../docs/evidence-contract.md). Validate metadata with
`./scripts/check-workspace --profile metadata`, and selected artifact bytes/rows
with `--profile evidence-references`, before regenerating/checking the index.
Cards without references remain valid; proposed ideas need no fabricated result.

Initial adoption covers the original VWAP primary scorecard and the GC 2026
selected-filter/unfiltered comparison. It does not cover every claim in either
card or promote evidence status. Preserve the GC previously inspected 2026
qualification, inconclusive intervals and untested options, and the VWAP
distinction between primary and later exploratory evidence. Saved tables remain
the value source; current card prose and dated conclusions are unchanged.

## Research priority

[research-priorities.json](research-priorities.json) is Sahadeva's current dated
editorial registry, separate from strategy-card status and
[index.json](index.json). Follow the [versioned rubric](research-priority-rubric.md)
before assessing a scoped candidate. Research priority asks how strongly saved
evidence justifies focused investigation toward a material actionable edge;
it is not a profitability probability, paper-quality rating or trading advice.
Not assessed, Needs review and Not applicable are nonnumeric states. Initial
AI-assisted reviews identify their reviewer and pending human approval.

Record supporting and contrary saved-section references, candidate-specific
materiality and baseline, execution/timing/dependence limits, the main blocker
and a next experiment with support/rejection criteria. Whole selected-report
coverage, scope and rubric bindings detect staleness. Keep local material paths
and review notes private. Four/five scores require the rubric's explicit
hash-pinned materiality, separated-evaluation and execution/cost evidence;
five additionally requires independent corroboration. Checks verify identities
and bytes, not the truth of the judgment.

From the workspace root, use the standard-library projector explicitly:

```sh
python3 scripts/project-research-priorities.py --check
python3 scripts/project-research-priorities.py --write
./scripts/check-workspace --profile research-priority
```

`--write` changes only generated priorities and their public rubric in Narada's
existing catalog. Do not edit both registry and projection. Ordinary app builds
read only app-owned inputs. For relevant unpublished findings or other changed
unprojected evidence, use `--mark-needs-review STUDY_ID --reason "..."`, then
`--write`; the old score/date remain historical context, excluded from active
numeric filtering. Manual reassessment requires rereading the evidence and a new
dated assessment ID. Commit approved judgments before replacement so repository
history preserves them; leave old run advice, sealed reports and release records
unchanged. `--check-reviewed-inputs` separately audits explicitly recorded local
material hashes; it is not the metadata profile or a Narada build prerequisite.
