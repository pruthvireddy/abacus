# Autopivot Levels - Daily

Study 29 · experimental pivot indicator · Pine Script v6

Renamed from Verniman Pivot Levels. The latest [ranked-candidate update](ranked-candidates.md) adds frozen alternatives to the Data Window; the [future calibration proposal](future-calibration.md) and [simple feedback template](pivot-feedback-template.csv) prepare for user-supplied labels without fitting any target data. The latest [display and alternate-reference update](autopivot-display-update.md) records the new styling, secondary reference, private account name, and current verification. The original verification record below remains the historical v1 record.

[Autopivot Levels - Daily](verniman_pivot_levels.pine) selects one daily reference
using confirmed information through **09:25 America/New_York**. It combines the
unchanged Phase 1 candle-profile arithmetic with the authorized N1/E1 engineering
control and the separately frozen contextual selector. These rules are
hypotheses; they do not recover Verniman's proprietary method or establish
profitability.

This implementation is separate from **Verniman Levels**, the original baseline,
and the completed Phase 1 and Phase 2 records. Its controlling documents are the
[frozen pivot specification](pivot-specification.md) and the
[numerical implementation addendum](numerical-implementation-addendum.md).
The [verification record](pivot-verification.md) owns native TradingView results,
the final source hash, private-save status, layout URL, and retained evidence
location. The record confirms completed native verification and account persistence,
with the evidence limits stated separately.

## Chart and data requirements

Use **standard five-minute futures candles with extended electronic-session
data**. Other chart types, timeframes, and instruments show an unsupported status.
Calculations use the chart symbol and its minimum tick; they make no external
timeframe request. Verification uses the actual dated, unadjusted contract
**CME_MINI:ESZ2026**, with one settings set for October 1, 2, and 5, 2026.

Load enough history to include the preceding full RTH and the entire current
overnight prefix. The previous RTH reference is the latest actually observed
09:30–16:00 New York session, requiring 78 contiguous five-minute bars. Friday
normally supplies Monday's reference. An observed partial or shortened latest
RTH makes the reference unavailable; an older good session does not replace it.
There is no exchange-holiday calendar, so a wholly absent session cannot be
distinguished from a holiday closure. The source RTH date remains visible.

The overnight profile runs from the preceding 18:00 opening through 09:25,
requiring 185 contiguous bars. The terminal 09:20–09:25 bar must be present and
confirmed; 09:25–09:30 is excluded. Missing volume, a nonpositive profile total,
overflow, missing bars, or insufficient history produces an explicit unavailable
result. Individual zero-volume bars are permitted when total volume is positive.
No previous day's pivot is substituted. All boundaries use New York civil time,
including daylight-saving changes.

## Selection and display

The tolerance is `b = max(2 minimum ticks, half a profile row)`. Below previous
value by more than `b`, select YVAL. Above previous value by more than `b`, select
the qualified lower E1 boundary of the unique unambiguous overnight N1 region
containing price, provided that boundary is above YVAH plus `b`; otherwise use
the labeled YVAH fallback. Within or near previous value, compare ONPOC with
YPOC using the same tolerance: a lower shift selects YVAL, a higher shift selects
YVAH, and a balanced result uses the labeled YPOC fallback. Exact tolerance
boundaries follow the within-or-near branch.

N1 parents are full regions rather than renamed volume peaks. E1 boundaries
require sufficient parent width, an observed outside neighbor, and border
contrast. Cap omissions, competing overlaps, and incomplete edge evidence remain
visible and cannot silently decide a pivot. Nearby independent E1 boundaries are
reported as confluence with their original prices and identities; confluence
never moves the selected reference.

The price, reason, inputs, origin, and fallback status freeze at the terminal
confirmation. The main purple line and optional dotted black alternate start at **09:25** and
end at **16:00** by default. Both use width 1 with small plain-text labels at the
right endpoint; the main reason is retained in its tooltip. A main fallback is
still dashed. The alternate is a distinct prior-value fallback reference, frozen
at the same cutoff; it does not change the primary selection.
The diagnostic table shows readiness, source periods, frozen inputs, selection,
confluence, and edge uncertainty. Historical execution is a reconstruction;
TradingView may not distinguish live execution from Replay in its execution
flags. Reload reproduction requires identical settings, feed data, and sufficient
history. Feed corrections can change reconstructed history.

## Defaults

| Setting | Default |
|---|---|
| Profile row width | 16 minimum ticks; configurable 1–1,000 |
| Grid origin / smoothing | Zero / none |
| Value area | 70%; configurable 1–100% |
| Maximum profile span | 6,000 rows |
| N1 height / prominence | At least 0.20 / 0.10 of global maximum |
| N1 region-growth threshold | Saddle plus 0.5 × prominence |
| N1 representative / ranking | Lowest plateau row; height, prominence, then ascending price |
| N1 minimum separation / region cap | Two rows / eight regions |
| LVN depth / cap | At most 0.25 of smaller parent peak / seven |
| E1 minimum parent width / contrast | Two rows / 0.10 of parent peak |
| E1 coordinates / uncertainty | Shared bin boundary / ± half a row |
| Maximum retained E1 edges | Sixteen |
| Cutoff / timezone | Fixed 09:25 / America/New_York |
| Historical lines | 30; configurable 1–100 |
| Line endpoint | 16:00 New York; configurable hour 10–23, minute 0–59 |
| Strict fallback suppression | Off |
| Selected-edge uncertainty shading | Off |
| Show diagnostic table | Off; can be enabled in Inputs; incompatible-chart warning remains visible |
| Show alternate / fallback level | On; suppressed by strict mode |
| Post-cutoff acceptance | On |
| Show ranked candidates in Data Window | On |
| Ranked candidates to show | 5; configurable 1–8 |
| Show candidate source details | Off |

Acceptance is a separate changing status: two consecutive completed post-cutoff
closes above `pivot + b` are bullish, two below `pivot - b` are bearish, otherwise
unresolved. Counters reset each trading day. Acceptance never revises the pivot;
this indicator contains no execution or trade-management logic.

The profile allocates each candle's volume uniformly across inclusive touched
rows, including a high exactly on a row boundary. POC ties choose the lowest
row; value-area adjacent ties expand upward. Value references use bin-base
coordinates. This estimates volume at price from candles and does not observe
trade-level volume at price.

## Local verification

The earlier display/alternate revision passed **116 tests**, including 21 alternate-reference
tests, 59 original pivot tests and 36 preserved Phase 1 tests. The new
[translated model](../src/pivot_model.py) and
[synthetic tests](../tests/test_pivot_indicator.py) cover selection branches and
fallbacks, exact boundaries, profile ties, N1/E1 controls, missing data, session
resets, New York daylight saving, and identical-prefix invariance under changed
post-cutoff bars. Independent bounded checks also compare optimized side minima
and region growth with direct specification algorithms.

From the repository root, the owning checks are:

```sh
./scripts/check-workspace --check study-29
python3 scripts/check-agent-docs.py
```

Translated-model tests and source checks do not compile or execute Pine. Consult
the [verification record](pivot-verification.md) for the separate native compile,
three-date Replay, private indicator save, layout save, and reload/readback
results. A failed or unfinished native action must remain explicit there.

## Ranked Data Window references

Inputs → **Show ranked candidates in Data Window** defaults on. Show 1–8
references (default 5); unused slots are unavailable rather than invented. The
existing alternate comes first. The remaining distinct qualified references are
ordered by distance from the frozen cutoff close, with deterministic ties. The
selected primary price is excluded. Candidate count, display omissions and N1
cap/overlap exclusions are visible. Prices and source identities freeze at 09:25.
These are engineering ranks, not learned confidence or additional chart lines.

Optional **Show candidate source details** adds numeric source codes, N1 parent
keys and confluence flags. The Inputs tooltip gives their legend; full names are
in the pivot label tooltip and optional diagnostic table. Hover a historical
post-cutoff bar in TradingView Data Window to inspect that day’s list. The bar
opening 09:20 carries its confirmed-close output only when it closes at 09:25.

The four affected synthetic suites pass 138 tests (36 baseline, 59 pivot,
21 alternate and 22 ranking). Native results and saved-source identity are
recorded in the ranked-candidate update. No target-label calibration was run.
