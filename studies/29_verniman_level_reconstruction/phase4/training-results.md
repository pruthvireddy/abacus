# Phase 4 training results

**Ten full candidate maps and frozen predictions were retained before the seven new answers were opened.** All five profiles are ready in each local map. Native verification and the exact-source scope are in [verification](verification.md). Source comparisons below read the saved predictions; no detector or selector was rerun on answers.

The [assessed source ledger](source-role-ledger-assessed.json) and [candidate-choice index](candidate-choice-ledger.json) retain all 303 occurrences. The original [303-row source input](source-role-ledger.json) remains unchanged at its pinned hash; older pending comparison fields there are historical input metadata. The separate assessed index is authoritative for current comparison status.

Canonical role data has 72 occurrences: 20 branch triggers, 29 bullish destinations and 23 bearish destinations across 10 plan class/revision strata on 9 dates. October 6 lacks a dated canonical plan. October 7 has two independent plans at 7848 (YHOD) and 7852 (HVE); neither is chosen or averaged into a single pivot answer. Thirty-six user-recollection occurrences stay separate from canonical truth; 29 have recalled/reported selected roles. Closing structural references and execution annotations do not supply missing scenario labels.

| Date | P0 pivot / reason | D1 bullish targets | D1 bearish targets | Source suitability |
|---|---|---|---|---|
| 2026-10-01 | 7752 / P0_BELOW_VALUE_RECLAIM | 7776, 7782, 7828 | 7709.25, 7705.5 | Common divider; exact window unresolved |
| 2026-10-02 | 7788 / P0_HIGHER_AUCTION_LOWER_E1 | 7796, 7802.75, 7828 | 7767.75, 7741.25, 7723.25 | Common divider; exact window unresolved |
| 2026-10-05 | 7764 / P0_ON_VALUE_SHIFT_LOWER | 7788, 7793, 7810.25 | 7760.25, 7754, 7723.25 | Common divider; exact window unresolved |
| 2026-10-06 | 7856 / P0_HIGHER_AUCTION_LOWER_E1 | 7864, 7867.75 | 7847.5, 7829, 7778.25 | No canonical plan |
| 2026-10-07 | 7868 / P0_BELOW_VALUE_RECLAIM | 7884, 7897.5 | 7860.25, 7832.5, 7829 | Two plans; no single divider |
| 2026-10-08 | 7824 / P0_ON_VALUE_SHIFT_LOWER | 7856, 7858.25, 7884.5 | 7815.75, 7802.75, 7792 | Common divider; exact window unresolved |
| 2026-10-09 | 7836 / P0_HIGHER_AUCTION_LOWER_E1 | 7852, 7858.25, 7872 | 7817, 7783, 7780 | Common divider; exact window unresolved |
| 2026-10-12 | 7864 / P0_ON_VALUE_SHIFT_HIGHER | 7870.5, 7887 | 7840, 7826.75, 7817 | Common divider; exact window unresolved |
| 2026-10-13 | 7848 / P0_ON_VALUE_SHIFT_LOWER | 7856, 7864, 7870 | 7836, 7832, 7820 | Common divider; exact window unresolved |
| 2026-10-14 | 7844 / P0_BELOW_VALUE_RECLAIM | 7856, 7863.25, 7879.75 | 7834.5, 7821.25, 7812 | Common divider; exact window unresolved |

P0 and the current translated Autopivot comparator choose the same primary price on all 10 complete inputs. This is same-input implementation agreement, not source-method validation. The comparator uses latest observed RTH; P0 uses expected prior weekday. The eligibility difference did not activate on these complete sessions. Its alternate is never a target.

## Pivot placement diagnostics

Eight dates have one common functional source divider. October 6 has no canonical source; October 7 retains two revision-specific dividers without a pooled single-answer error. Opposite branch triggers are not independent pivot observations.

| Policy | Eligible geometry dates | Mean absolute point/boundary error | Median error | Within 1 point | Interval-gap within 1 point |
|---|---|---|---|---|---|
| P0 | 8 | 3.875 | 3 | 0/8 | 2/8 |
| B0 | 8 | 24.375 | 17 | 0/8 | 0/8 |
| B1 | 8 | 11.625 | 5 | 0/8 | 0/8 |

These are descriptive training errors, not family/window coverage or learned validation. P0 has no exact point/boundary within one point. Its two interval-gap coincidences reflect E1 uncertainty, not exact boundary agreement. Source availability remains null.

| Date | P0 signed error | B0 signed error | B1 signed error |
|---|---|---|---|
| 2026-10-01 | 5.00 | 25.00 | 5.00 |
| 2026-10-02 | 3.00 | -97.00 | -61.00 |
| 2026-10-05 | -3.00 | 5.00 | 5.00 |
| 2026-10-06 | Not estimable | Not estimable | Not estimable |
| 2026-10-07 | Not estimable | Not estimable | Not estimable |
| 2026-10-08 | -3.00 | 25.00 | -3.00 |
| 2026-10-09 | 3.00 | -25.00 | -5.00 |
| 2026-10-12 | -3.00 | -7.00 | -3.00 |
| 2026-10-13 | -2.00 | 2.00 | -2.00 |
| 2026-10-14 | 9.00 | 9.00 | 9.00 |

## Target choices and retained misses

The table reports coordinate-only one-to-one pair counts within each branch/class/revision stratum. It ignores construction identity and is **not reproduction coverage**. Revisions remain separate; no pooled target success rate is reported. All source targets remain in their denominators, including four October 1 bullish destinations despite the executable cap of three.

| Date / source stratum | Branch | Source targets | D0 coordinate pairs | D1 coordinate pairs | Complete coordinate ladder D0 / D1 |
|---|---|---|---|---|---|
| 2026-10-01 | bullish | 4 | 1 | 1 | False / False |
| 2026-10-01 | bearish | 3 | 0 | 1 | False / False |
| 2026-10-02 | bullish | 2 | 2 | 2 | False / False |
| 2026-10-02 | bearish | 2 | 0 | 0 | False / False |
| 2026-10-05 | bullish | 2 | 0 | 0 | False / False |
| 2026-10-05 | bearish | 2 | 1 | 0 | False / False |
| 2026-10-06 / no canonical labels | bullish | Unavailable | Not assessed | Not assessed | Not assessed |
| 2026-10-06 / no canonical labels | bearish | Unavailable | Not assessed | Not assessed | Not assessed |
| 2026-10-07 / 8669f26717dd | bullish | 5 | 0 | 0 | False / False |
| 2026-10-07 / 9034180c5397 | bullish | 3 | 0 | 0 | False / False |
| 2026-10-07 / 8669f26717dd | bearish | 2 | 0 | 1 | False / False |
| 2026-10-07 / 9034180c5397 | bearish | 2 | 0 | 1 | False / False |
| 2026-10-08 | bullish | 3 | 0 | 2 | False / False |
| 2026-10-08 | bearish | 2 | 0 | 0 | False / False |
| 2026-10-09 | bullish | 2 | 0 | 1 | False / False |
| 2026-10-09 | bearish | 2 | 1 | 0 | False / False |
| 2026-10-12 | bullish | 3 | 1 | 1 | False / False |
| 2026-10-12 | bearish | 3 | 1 | 1 | False / False |
| 2026-10-13 | bullish | 3 | 1 | 2 | False / False |
| 2026-10-13 | bearish | 3 | 1 | 2 | False / False |
| 2026-10-14 | bullish | 2 | 1 | 1 | False / False |
| 2026-10-14 | bearish | 2 | 1 | 2 | False / False |

No complete canonical branch ladder is reproduced even by coordinate-only matching. Extra selections, rank shifts, unmatched source references and competing/equal-optimum assignments are retained in each saved comparison. In particular, October 2 matches two bullish coordinates only at target ranks 2/3 rather than source ranks 1/2, while carrying an extra nearer target. GAP and PBT components remain unsupported/unidentified; nearby HVE or extrema are not relabeled as those constructions.

## Availability, abstention and scope

All 10 P0 pivots are ready/nonfallback. D1 bullish ladders are partial on October 6, 7, 12; the October 1 bearish ladder is partial. There are no causal PBT targets because first-pass anchors are empty. Synthetic tests exercise fallback/abstention branches; their absence in these 10 sessions does not remove the policy. B0/B1 and D0/D1 complete saved outputs and rejected alternatives remain in the map artifacts.

All exact source construction/window identities remain unresolved. Primary family/window coverage, conditional strict selection accuracy and end-to-end source-method reproduction are therefore **not estimable**, not zero percent. The choice index marks structural and recollected roles explicitly rather than silently dropping them. Source-assisted explanations remain diagnostics; no source price enters generated candidates.

The gate/chronology and every immutable map/comparator hash are in the [JSON result](training-results.json). Original Phase 3 failure records, earlier partial three-date reconstructions and the full pre-reveal attempt remain unchanged. These are 10 training sessions, not out-of-sample results.

A parallel readiness review accidentally encountered protected hidden-date answer snippets in a mutable guide after the rules and predictions were frozen. They were not used to change Phase 4 rules or outputs. The exposed hidden period is not pristine for the current team; a fresh unexposed evaluator or separately authorized replacement holdout is required for Phase 6. Development October 15–20 was not opened; Phase 5 needs separate authorization.

See the [rulebook](rulebook.md), [verification](verification.md), [assessed source ledger](source-role-ledger-assessed.json), [candidate-choice index](candidate-choice-ledger.json) and [Phase 5 handoff](phase5-handoff.md).
