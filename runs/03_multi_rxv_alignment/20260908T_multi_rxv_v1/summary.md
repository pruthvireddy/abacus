# Multi-Range-XV alignment analysis

## Executive conclusion

The larger Range XV chart is useful mainly as a **short-horizon timing filter** and as context for **large-run exhaustion**. It is not a second independent confirmation and it does not consistently predict a long continuation run.

- ES 5→6 and GC 6→10 show the most useful alignment behavior. Alignment raised the held-out probability of at least one additional same-direction small bar by 3.19 and 1.84 percentage points, respectively.
- NQ 10→20 gained only 0.65 percentage points on the next bar and no benefit over three or five bars.
- GC 6→10 had the strongest three-bar evidence: the difference was positive in all three periods, with development and validation intervals above zero, although the held-out interval for the small effect touches zero. ES also had positive point estimates in all three periods, but every interval included zero.
- A long run on the larger chart is a much stronger reversal-context feature than repeated small-chart countertrend attempts. The probability of a larger-chart reversal within 15 minutes was materially higher after 8+ large bars than after 1–2 large bars in every pair and every chronological split.
- Small-chart countertrend reversals usually preceded a same-direction larger-chart reversal, but these high confirmation rates are partly mechanical because both charts transform the same trades. They are not win rates or evidence of positive net expectancy.

## Data and no-look-ahead controls

The study uses the 540-day export window from 2024-08-14 through 2026-09-08, containing 534–535 inferred session dates per file. The primary pairs are ES 5→6, GC 6→10, and NQ 10→20. GC 10→20 is included as a secondary comparison. The new data does not contain ES 4 RXV, so ES 4→5 and ES 4→6 could not be tested.

The primary timing sample uses the completion proxy of the small reversal bar as the signal time. It attaches only the latest larger bar whose completion proxy is **strictly earlier** than that signal. Exact-second matches are rejected. Small bars whose start and completion proxies share the same recorded second are excluded from the primary sample and retained only for sensitivity analysis.

Across 1,291,250 strict-timing reversal signals with an available larger state, the audit found zero larger-state exact-match or future-bar violations. The same-second sensitivity sample produced materially similar conclusions.

Results use fixed chronological partitions:

- Development: 2024-08-14 to 2025-11-10
- Validation: 2025-11-11 to 2026-04-10
- Test: 2026-04-13 to 2026-09-08

Confidence intervals are 95% session-cluster bootstrap intervals with 2,000 replicates.

## 1. Small-chart pullback continuation

A pullback signal is a small-chart reversal after one or two opposite-direction small bars. `P(L>=1)` means at least one more small bar continues in the reversal direction. `P(L>=3)` and `P(L>=5)` require at least three or five more bars.

### Held-out test results, both directions

| Pair | Aligned P(L>=1) | Countertrend P(L>=1) | Difference, percentage points (95% CI) | P(L>=3) difference, pp (95% CI) | Interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| ES 5→6 | 79.34% | 76.15% | +3.19 (+1.62, +4.70) | +1.02 (-0.66, +2.73) | Clear next-bar benefit; little evidence of a durable run benefit |
| GC 6→10 | 78.31% | 76.47% | +1.84 (+1.15, +2.54) | +0.99 (-0.02, +1.91) | Repeatable short-horizon filter; three-bar effect is small |
| GC 10→20 | 77.91% | 76.87% | +1.04 (-0.07, +2.22) | +0.86 (-0.47, +2.13) | Directionally positive but inconclusive |
| NQ 10→20 | 78.24% | 77.59% | +0.65 (+0.10, +1.18) | -0.08 (-0.65, +0.48) | Very small next-bar effect and no sustained benefit |

No pair showed a reliable aligned advantage at `P(L>=5)`. The rolling ten-large-bar trend and a larger-chart reversal within the prior 15 minutes added little beyond the latest larger-bar direction.

An exploratory direction split found that ES bullish alignment had a +3.08 percentage-point held-out advantage at `P(L>=3)`, while ES bearish alignment did not. That asymmetry was not established in the development period and should remain exploratory.

**Practical reading:** larger-chart alignment can help decide whether to take the immediate continuation after a small reversal, especially for ES 5→6 and GC 6→10. It should not be treated as evidence that a long same-direction run will follow.

## 2. Multi-scale reversal

For every small-chart countertrend reversal, the study found the first strictly later larger-chart reversal in the same direction. The larger confirmation is an outcome, not information available to the early entry.

### Held-out test results, strict timing

| Pair | Larger reversal within 15 min | Within 30 min | Median delay among 30-min confirmations | Median early-entry price advantage | Early entry had better price |
| --- | ---: | ---: | ---: | ---: | ---: |
| ES 5→6 | 87.76% | 93.89% | 1.12 min | 3 ticks | 71.78% |
| GC 6→10 | 97.02% | 99.31% | 1.03 min | 7 ticks | 67.74% |
| GC 10→20 | 80.86% | 92.10% | 3.34 min | 16 ticks | 69.18% |
| NQ 10→20 | 98.20% | 99.53% | 0.55 min | 15 ticks | 65.57% |

The price advantage compares entry at the next small-bar open with entry at the next large-bar open after confirmation, and only among signals that confirmed inside the stated window.

These rates changed materially over time, especially for GC 10→20. More importantly, the calculation does not charge early entries for signals that never confirm, adverse movement before confirmation, overlapping signals, fees, or slippage. The result supports studying staged entry, but it does not yet establish that early entry is better than waiting.

## 3. Larger-chart trend exhaustion

The cleanest exhaustion result is the current larger-chart run length. The table compares countertrend small reversals occurring after 8+ completed large bars with those occurring after only 1–2 large bars.

### Held-out probability of a larger reversal within 15 minutes

| Pair | Large run 1–2 | Large run 8+ | 8+ minus 1–2, pp (95% CI) |
| --- | ---: | ---: | ---: |
| ES 5→6 | 85.74% | 92.59% | +6.85 (+4.42, +9.48) |
| GC 6→10 | 96.22% | 98.77% | +2.55 (+1.97, +3.16) |
| GC 10→20 | 76.26% | 93.87% | +17.61 (+14.96, +20.08) |
| NQ 10→20 | 97.75% | 99.18% | +1.42 (+0.99, +1.93) |

The positive 8+-bar difference persisted in development, validation, and test for all four comparisons. The absolute increase is smaller for GC 6→10 and NQ because their short-run confirmation rates are already close to saturation.

Repeated small countertrend attempts did not provide a stable general filter. In the held-out test, repeated minus first-attempt effects at 15 minutes were +0.09 pp for ES, -0.34 pp for GC 6→10, +2.74 pp for GC 10→20, and -0.05 pp for NQ. The GC 10→20 effect reversed sign in validation. High results for the combined “extended run plus repeated attempt” cohort therefore appear to come mainly from run length, not repetition.

**Practical reading:** track the completed larger-chart run length. Treat 8+ bars as a meaningful exhaustion context. Do not require repeated failed continuations as a universal rule.

## Recommended use in future analysis

1. Use larger-chart direction as a near-term entry filter, with ES 5→6 and GC 6→10 as the lead candidates.
2. Use larger run length as the primary early-warning feature for a larger reversal. Test thresholds around 5–7 and 8+ rather than assuming one universal cutoff.
3. Keep repeated countertrend attempts as an exploratory interaction, particularly for GC 10→20, rather than a standalone condition.
4. Evaluate early-versus-confirmed entry with explicit stops, targets, maximum holding time, costs, and all nonconfirming signals. Cluster results by session and by larger-chart run to handle overlapping signals.
5. Add ES 4 RXV before drawing conclusions about the intended ES 4→5 and 4→6 relationships.

## Limits

- ATAS does not export the exact bar completion timestamp here. Completion is proxied by the next bar's start at one-second resolution.
- Session-final and export-final bars cannot receive a completion proxy.
- The export timezone and the configured ATAS trading session are not embedded in the files; the same 18:00 session-date proxy is applied consistently to every pair.
- The study evaluates bar-event behavior, not a fully specified trading strategy or net profitability.
- Multiple Range XV settings are transformations of the same trade stream, so agreement is a correlated filter rather than independent confirmation.
