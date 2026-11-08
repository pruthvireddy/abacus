# Phase 3 private installation and Replay

The [derivative](../indicator/verniman_levels_phase3.pine) has indicator title
**Verniman Levels**. Its header/table identify Phase 3. Installation instructions
are not proof of compilation; [verification](verification.md) records actual status.

## Safe separate layout

TradingView security rejected this task's **Manage layouts → Make a copy →
Make copy** submission. The original remains at
[the Phase 1 layout](https://www.tradingview.com/chart/mtK3TbRP/).
Do not bypass that rejection with alternate browser surfaces, hidden commands or
another route to the same copy action. A user-created separate study layout and
normal permitted access are prerequisites for resuming native work.

Once available, preserve Phase 1's private script/settings. Create a separate
indicator, paste the whole derivative, save it privately and add it to the
separate Phase 3 layout. Do not publish it. Record the exact source hash, private
revision, native compiler/runtime messages and layout URL. Pine cannot load the
local settings or anchor JSON; enter its supported inputs explicitly.

## Fixed chart and profiles

Use `CME_MINI:ESZ2026`, CME GLOBEX, individual unadjusted December contract,
standard five-minute candles, electronic trading hours, 16-tick rows, 70% VA
and 09:25 America/New_York. Load a complete previous week plus current week and
the three prior RTH sessions. Inspect actual contract/feed/adjustment/history;
continuous prices or missing data are not interchangeable inputs.

The five profile families have separate identities/readiness. Use the family
toggles and selected-profile table pages to inspect rows, candidates/rejections,
composite membership, omissions and raw evidence. Node/edge caps affect display;
they do not select a scenario divider or targets. Keep drawings readable by
showing one expanded family at a time. The [Pine interface](pine-implementation.md)
explains exact controls and extraction limits.

## Manual PBT anchors

Keep a local provenance ledger with stable anchor IDs, price intervals, reading
precision, reference period/measurement, contract, observed/confirmed timestamps,
evidence and selection reason, source/analyst status and independent causal
support. Default first-pass anchors are empty. An entered timestamp or checkbox
attestation is a recorded claim, not independent proof.

Enter the corresponding Pine strings manually using the format in
[pine-implementation.md](pine-implementation.md). The [local encoder](anchor_inputs.py) prints strings from the
[empty first-pass ledger](anchors.json); it never sends or installs them into
TradingView. For example, from the repository root:

```sh
python3 studies/29_verniman_level_reconstruction/phase3/anchor_inputs.py studies/29_verniman_level_reconstruction/phase3/anchors.json --cutoff 2026-10-01T09:25:00-04:00
```

The 13 fields include reading precision. The ledger uses `explicit_source` or
`analyst_proposed`; the encoder serializes the Pine hyphenated equivalents.
Do not invent defaults or solve backward from a PBT price. Later-confirmed or
unsupported anchors remain unavailable. Known full-range midpoint reflection
must be identified as the opposite existing boundary. Retain retrospective
illustrations separately from the causal pre-open map.

## Cutoff, advance and restart

1. First verify October 1, 2 and 5. For each date choose Replay 09:25; in the
   previous verified configuration one Forward step was needed to confirm the
   09:20–09:25 bar. The recorded included boundary is authoritative.
2. Capture all 19 baseline fields and five identified distributions; compare
   the baseline with the attributed Phase 1 record. Investigate any difference.
   Capture regions, LVNs, E1 evidence, composite members, missing anchors or PBT
   outputs, readiness, rejected/omitted IDs/counts, code/settings/input hashes.
3. Advance into RTH. Confirm frozen values, source/profile/anchor IDs and last
   included bar remain identical. Later developing data can change separately.
4. Restart at the same cutoff/settings/history and compare the complete saved map.
   Include a synthetic later-confirmed manual-anchor check; it must not appear
   in the earlier map. Record actual runtime, timeouts and drawing behavior.
5. Save and hash **all seven** October 6, 7, 8, 9, 12, 13 and 14 maps before
   opening any of their target sources. A failure record is not a completed map
   and does not unlock source reveal. Keep all first-pass settings unchanged.

October 15–20 development and October 21–27 hidden-test target sources and Replay
navigation remain forbidden. These ten dates are training observations, not an
out-of-sample test. Only after the seven-map gate passes, apply the
[comparison contract](comparison-specification.md). No profitability testing,
selection automation, Narada publication or deployment is part of this phase.
