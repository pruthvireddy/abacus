# Candidate implementation corrections retained during Phase 4

The frozen candidate **control remains 3.0.0**: same bars, profiles, row grid,
thresholds, N1/E1 geometry, composite membership, PBT arithmetic and snapshot
cutoff. Implementation revisions below correct native compilation and contract
metadata. They do not fit thresholds or select a different construction to match
source labels. Original sources and earlier failure records remain unchanged.

Snapshot paths under `work/` are local retained evidence, outside a Git source
checkout. Restore the exact pinned file before comparing its bytes.

| Source | Implementation identity | SHA-256 |
|---|---|---|
| [Original Phase 3](../indicator/verniman_levels_phase3.pine) | 3.0.0 | `9cf9f9a56311496ea7414758d1dd51e6e9a7af5739cffa4438c35190b1f64504` |
| [Native compiler correction](../indicator/verniman_levels_phase3_3_0_1.pine) | 3.0.1 | `40b28d3a581edc1246582f9d2c4c7b127f24423885ba16d20c1cfb65f8b294cd` |
| [Contract-metadata correction](../indicator/verniman_levels_phase3_3_0_2.pine) | 3.0.2 | `034c3731f2ada4620aac9a80ca20261d0a06376bee044fa30e95529ad9e1954c` |
| Phase 4 implementation 4.0.0 snapshot (`work/29_verniman_level_reconstruction/phase4_20261031T010249Z/phase4-implementation-4.0.0-before-display-fix.pine`; local only) | Selection control 4.0.0, candidate implementation 3.0.2 | `0b86c709b646dda0318dd6428dbbf5b9a31b3dd7f11fed3f2c176f84461fa4b0` |
| [Current Phase 4 selector](../indicator/verniman_levels_phase4.pine) | Implementation 4.0.1, selection control 4.0.0, candidate implementation 3.0.2 | `1145834bfb240029f07342e52f98d805771ca4f2a39a646c19e80d3846794924` |

Exact native compile, private-save and Replay scope belongs in the
[verification record](verification.md). A local transformation or unchanged
mathematics does not itself establish successful native execution. The work
stage retains prior attempts, sources and observations separately.

## 3.0.1: native compiler corrections

Original native compilation identified two source issues:

- `f_p3Cell` used reserved parameter name `text`; rename it to `cellText` and
  update its body reference.
- Last-bar HVN drawing locals named `low` and `high` shadowed chart built-ins
  already used in that scope; rename them `zoneLow` and `zoneHigh` and update
  the drawing call.

These affect helper identifiers and presentation scope only. No profile method
return, arithmetic, threshold, tie, readiness or source window is changed.
The separately retained 3.0.1 source compiled natively; its observed date/step
coverage must be read from the exact native receipts, not inferred for every
training date.

## 3.0.2: separate contract from chart execution context

The retained native 3.0.1 October 1 cutoff capture
`work/29_verniman_level_reconstruction/phase4_20261031T010249Z/phase3-oct1-cutoff.png`
shows the contract field carrying a Replay-modified ticker identifier. In that
context, directly using `syminfo.tickerid` as a declared contract conflates the
instrument with dataset/execution modifiers. It can also make the unhashed
input fallback and derived candidate IDs depend on a particular Replay context.
A standard manual anchor contract would fail the old direct comparison against
that wrapped value. This diagnosis follows the retained native metadata and
literal comparison code; it is not a claim that causal PBT anchors were recovered.

TradingView's current official [chart-information documentation](https://www.tradingview.com/pine-script-docs/concepts/chart-information/)
explains that ticker IDs may include dataset modifiers and provides
`ticker.standard()` to obtain the identifier without those modifiers.
Implementation 3.0.2 therefore:

1. Defines `P3_CONTRACT = ticker.standard(syminfo.tickerid)`.
2. Uses that standard identifier for distribution contracts, the manual-anchor
   contract comparison and the explicitly **unhashed** chart-history fallback ID.
3. Freezes the original `syminfo.tickerid` separately as each distribution's
   `rawChartContext`, visible in the Contract/feed tooltip. Raw context is not
   included in semantic profile/candidate IDs.
4. Adds `P3_IMPLEMENTATION = "3.0.2"` separately from unchanged
   `P3_POLICY = "P3-3.0.0-N1E1-P1-P2"`. The default missing-external-hash code
   identity includes the implementation version. An entered external source hash
   remains explicit provenance, not something Pine independently verifies.
5. Identifies the implementation/control versions in its header/table and points
   native-verification status to the external exact-source record.

A local anchor now declares standard contract `CME_MINI:ESZ2026`; it must still
satisfy every original provenance, precision, observation/confirmation, independent
causal-support and cutoff condition. Normalization does not authorize mixing
contracts, infer exchange history or prove that the chart's adjustment/session
settings are correct. Raw chart context, observed configuration and coverage
remain separate metadata. The fallback string remains labeled unhashed; this
change does not invent a market-data checksum or historical source availability.

The same correction is present in Phase 4's embedded candidate backend. Phase 4
selection formulas, original candidate coordinates and target policy are
unchanged by it. Its prior source bytes are retained in the work-stage history.

## Preservation and renewed verification

Removing all marked Phase 4 blocks and the single descriptive header word
`backend`, then normalizing introduced blank lines, restores the complete 3.0.2
candidate source. The 3.0.1→3.0.2 diff is limited to the documented contract/raw-
context metadata, implementation identity and diagnostic text. All original
3.0.0 and 3.0.1 byte hashes above still match.

The old 3.0.1 captures remain observations of that exact implementation. Their
Replay-wrapped IDs must not be silently relabeled as 3.0.2 output. Capture the
new standard contract, preserved raw-context tooltip, same 19 baseline values,
new candidate identity version, cutoff/advance/restart invariance and actual
compiler/runtime outcome in fresh receipts. A changed raw context across a
restart is a diagnostic difference; equivalent standard contract and captured
input/code/settings identities must remain stable. Null historical source
availability remains null.

No still-unrevealed training answer, protected target or later reaction was used
to choose these corrections. They supply implementation prerequisites, not
empirical evidence that candidate construction or selection reproduces Vern's
method.

## Phase 4 implementation 4.0.1: bounded visible decision captions

The original 0b86 Phase 4 source compiled and passed the October 1/2/5 native
cutoff/advance/restart matrix. Its D1 branch-ledger decision captions included
full provenance IDs and expanded the table beyond the viewport. The retained
`phase4-oct5-D1-ledger-overflow-4.0.0.png` records this presentation failure.

Implementation 4.0.1 truncates only those visible captions after 48 characters,
with an ellipsis. Full decisions, originating IDs, duplicate members, intervals
and source details remain in tooltips and calculation arrays. Separate
`P4_IMPLEMENTATION="4.0.1"` appears in header/status/settings metadata while
`P4_POLICY="phase4-4.0.0"` remains unchanged. No pivot, destination eligibility,
ranking, price, fallback, abstention or timing calculation changes.

The current source was saved as a separate private indicator, read back exactly
after line-ending normalization, and checked again at cutoff/advance/restart on
October 1/2/5. Observed prices/counts equal the original 0b86 matrix. The ledger
fits the viewport, and an actual hovered decision retains full original IDs and
reason text. Exact receipts and limits are in [verification](verification.md).
Earlier 0b86 source/private output and the display-correction receipt remain
retained. Native three-date parity does not establish source-method fidelity or
maximum 6,000-row performance.
