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
