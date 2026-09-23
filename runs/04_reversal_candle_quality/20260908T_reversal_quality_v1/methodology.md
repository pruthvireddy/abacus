# Methodology: reversal-candle quality

## Signal and timing

A reversal is a completed non-doji small-chart bar whose direction is opposite the immediately preceding non-doji bar in the same inferred session. The signal becomes observable at its completion proxy, which is the next small bar's opening timestamp.

The larger-chart state is the latest larger bar with a completion proxy strictly earlier than the small signal. Exact timestamp matches are rejected. Primary results exclude small bars whose opening and completion proxies share the same recorded second.

## Frozen geometry

- Body fraction is `abs(close-open)/(high-low)`.
- Favorable close fraction is `(close-low)/(high-low)` for bullish bars and `(high-close)/(high-low)` for bearish bars.
- Close-side wick is the distance from the close to the high for bullish bars and to the low for bearish bars.
- Adverse wick is the opening-side wick: open-to-low for bullish bars and high-to-open for bearish bars.
- Directional opening gap is positive when the reversal opens favorably relative to the preceding close.
- Previous-extreme break means the reversal trades above the preceding high when bullish or below the preceding low when bearish. The strict version requires the close to pass that extreme.
- Prior-run break applies the same rule to the full immediately preceding opposite-direction run.
- Full preceding-body retracement means a bullish reversal closes at or above the preceding open, or a bearish reversal closes at or below it.

The primary strong-close threshold is 0.80. The primary structure-break feature combines that threshold with a previous-extreme break. The strict version requires a close beyond the previous extreme. The quality stack also requires body fraction of at least 0.70.
A dedicated one-bar-snapback contrast separates reversals after a one-bar opposite run from reversals after runs of two or more bars. This guards against interpreting a prior-run break as independent candle quality when it is largely determined by prior-run length.

## Outcomes and inference

Continuation `L` excludes the reversal bar and counts immediately following same-direction small bars. Entry geometry uses the next small-bar open. Larger confirmation is the first strictly later completed larger reversal in the signal direction.

Differences compare feature-present with feature-absent signals inside the same chart, context, split, and timing sample. Confidence intervals use 2,000 session-cluster bootstrap replicates. Secondary features are diagnostic and are not multiplicity-adjusted entry rules.

The chronological partitions match the previous multi-RXV study. Because the exhaustion context was motivated by earlier inspection of the same overall dataset, exhaustion interactions should be treated as follow-up historical evidence rather than a fully pristine independent test.

## Limits

The exact ATAS last-trade/completion time, timezone, and configured trading session are absent. Completion remains a one-second next-bar-start proxy. OHLC cannot reconstruct intrabar path, volume, delta, or order flow.

## Pair audit

```json
[
  {
    "pair_id": "ES_5_6",
    "asset": "ES",
    "small_setting": 5,
    "large_setting": 6,
    "small_rows": 375442,
    "large_rows": 274479,
    "reversal_signals_with_completion_proxy": 118511,
    "strict_timing_signals": 113750,
    "same_second_sensitivity_signals": 4761,
    "strict_signals_with_larger_state": 113712,
    "larger_state_exact_match_violations": 0,
    "future_confirmation_order_violations": 0
  },
  {
    "pair_id": "GC_6_10",
    "asset": "GC",
    "small_setting": 6,
    "large_setting": 10,
    "small_rows": 1254233,
    "large_rows": 571237,
    "reversal_signals_with_completion_proxy": 388621,
    "strict_timing_signals": 354909,
    "same_second_sensitivity_signals": 33712,
    "strict_signals_with_larger_state": 354788,
    "larger_state_exact_match_violations": 0,
    "future_confirmation_order_violations": 0
  },
  {
    "pair_id": "GC_10_20",
    "asset": "GC",
    "small_setting": 10,
    "large_setting": 20,
    "small_rows": 571237,
    "large_rows": 174336,
    "reversal_signals_with_completion_proxy": 176508,
    "strict_timing_signals": 166437,
    "same_second_sensitivity_signals": 10071,
    "strict_signals_with_larger_state": 166195,
    "larger_state_exact_match_violations": 0,
    "future_confirmation_order_violations": 0
  },
  {
    "pair_id": "NQ_10_20",
    "asset": "NQ",
    "small_setting": 10,
    "large_setting": 20,
    "small_rows": 2314301,
    "large_rows": 684982,
    "reversal_signals_with_completion_proxy": 713397,
    "strict_timing_signals": 656615,
    "same_second_sensitivity_signals": 56782,
    "strict_signals_with_larger_state": 656555,
    "larger_state_exact_match_violations": 0,
    "future_confirmation_order_violations": 0
  }
]
```
