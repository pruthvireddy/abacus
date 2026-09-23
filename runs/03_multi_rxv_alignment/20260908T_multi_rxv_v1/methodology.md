# Methodology: multi-Range-XV alignment study

## Design

This is a bar-event study of multiple ATAS Range XV transformations of the same underlying instrument. Agreement is evaluated as a filter, not as independent confirmation.

A small-chart reversal is known only at its completion proxy (the next small bar's start). The aligned larger state is the latest larger bar whose completion proxy is strictly earlier than the signal time. Exact timestamp matches are rejected, which prevents a larger bar completing in the same recorded second from leaking into the signal.

Primary results additionally require the small signal's completion proxy to occur in a later recorded second. Same-second small bars are retained only as sensitivity analysis.

## Frozen definitions

- **small reversal:** a non-doji small bar whose direction is opposite the immediately preceding non-doji bar in the same session.
- **pullback:** the small reversal follows one or two consecutive opposite-direction small bars.
- **aligned:** small reversal direction equals the latest strictly-prior completed larger-bar direction.
- **rolling trend:** sign of larger close minus larger close 10 completed larger bars earlier in the same session.
- **recent co reversal:** aligned signal occurring within 15 minutes after the first completed larger bar in its current directional run.
- **large confirmation:** first later larger-chart reversal in the small signal direction.
- **extended large run:** at least five consecutive completed larger bars in the current direction.
- **repeated countertrend attempt:** second or later small countertrend reversal during the same still-unreversed larger run.

Continuation `L` excludes the reversal bar itself and counts immediately following same-direction small bars. Session-censored horizons are excluded. Entries are represented by the next small bar's open.

Large-chart confirmation is an outcome, not a signal-time feature: it is the first strictly later completed larger reversal in the small signal direction. Early-entry advantage is positive when the small-chart next-bar open is better than the larger-confirmation next-bar open in the direction of the proposed trade.

## Inference

Rates and differences use 2,000 session-cluster bootstrap replicates. The chronological development, validation, and test partitions were fixed before outcome inspection. No independent-confirmation claim is made because each pair comes from the same trades.

## Timing limitations

The ATAS export omits `IndicatorCandle.LastTime`. Next-bar opening time is only a completion proxy at one-second resolution. Session-boundary bars and export-final bars have no proxy. The export timezone and configured ATAS session are not encoded; the supplied 18:00 session-date proxy is used consistently across paired files.

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
    "small_reversal_signals_with_completion_proxy": 118511,
    "strict_timing_signals": 113750,
    "same_second_signal_sensitivity_rows": 4761,
    "strict_signals_with_larger_state": 113712,
    "larger_state_exact_match_violations": 0
  },
  {
    "pair_id": "GC_6_10",
    "asset": "GC",
    "small_setting": 6,
    "large_setting": 10,
    "small_rows": 1254233,
    "large_rows": 571237,
    "small_reversal_signals_with_completion_proxy": 388621,
    "strict_timing_signals": 354909,
    "same_second_signal_sensitivity_rows": 33712,
    "strict_signals_with_larger_state": 354788,
    "larger_state_exact_match_violations": 0
  },
  {
    "pair_id": "GC_10_20",
    "asset": "GC",
    "small_setting": 10,
    "large_setting": 20,
    "small_rows": 571237,
    "large_rows": 174336,
    "small_reversal_signals_with_completion_proxy": 176508,
    "strict_timing_signals": 166437,
    "same_second_signal_sensitivity_rows": 10071,
    "strict_signals_with_larger_state": 166195,
    "larger_state_exact_match_violations": 0
  },
  {
    "pair_id": "NQ_10_20",
    "asset": "NQ",
    "small_setting": 10,
    "large_setting": 20,
    "small_rows": 2314301,
    "large_rows": 684982,
    "small_reversal_signals_with_completion_proxy": 713397,
    "strict_timing_signals": 656615,
    "same_second_signal_sensitivity_rows": 56782,
    "strict_signals_with_larger_state": 656555,
    "larger_state_exact_match_violations": 0
  }
]
```
