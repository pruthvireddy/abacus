# Methodology

## Question and numbering

The reversal candle is sequence position 1. Its immediately following candle is follow-through position 1 and sequence position 2—the “second green/red candle” in this study. The primary cohort contains every reversal for which that next candle exists in the same valid segment and closes with the same `sign(close-open)` direction as the reversal.

The example of three red candles followed by a green reversal is covered by the prespecified `prior_opposite_run >= 3` sensitivity. The primary result retains every reversal with at least one preceding opposite non-doji candle.

## Primary adverse movement

For the same-direction follow-through candle:

```text
green/long: follow_open - follow_low
red/short: follow_high - follow_open
```

This is the candle's adverse wick/range from its own open. It is nonnegative and uses only that candle's OHLC. The sensitivity reference uses the reversal close instead:

```text
green/long: max(0, reversal_close - follow_low)
red/short: max(0, follow_high - reversal_close)
```

Directional open gap, favorable movement from the follow-through open, and directional close progress are reported for context. These values describe bar geometry, not executable entries or profits.

## Events, boundaries, and units

A reversal is an adjacent non-doji candle whose close-minus-open direction opposes the preceding non-doji candle. Dojis and provisional export-date boundaries break adjacency. The final row of each export is omitted because completion is unverified. A missing next candle is excluded, not treated as a failure. All arithmetic uses integer CME ticks, then translates to native price and gross dollars per standard contract.

The full-period result includes all 72 export dates. Development/validation/test labels from Analysis 01 are reused only as chronological stability slices; no setting is selected or optimized in this analysis. Mean confidence intervals use 2,000 export-date block bootstrap replicates with seed 20260906.

## Time-of-day extension

Time-of-day results use fixed 30-minute raw export-clock intervals, with the start included and the end excluded. No timezone conversion is made because the files do not identify a timezone. The exports also do not establish whether timestamps denote bar opens, closes, or another platform convention.

The signal-time table assigns events to the reversal candle timestamp and supplies the denominator needed for follow-through probability. The confirmation-time table assigns successful events to the next candle timestamp, when membership in the same-direction cohort becomes known. Rankings require at least 200 conditioned events and 10 active export dates in a window.

## Post-confirmation hold-time extension

The primary hold target requires the two bars immediately after the confirmation candle to both close in the existing reversal direction. Exact bar distance is therefore two additional bars. The raw timestamp-difference proxy runs from the confirmation candle timestamp to the second additional bar timestamp and is summarized only when the target succeeds. The success probability uses every event with two complete subsequent bars in the same provisional export-date segment.

A separate eventual-pair sensitivity searches the next 20 complete bars for the first pair of consecutive bars in the established direction and allows intervening opposite/doji bars. It requires the full search horizon so truncated boundaries are not counted as failures. Time-of-day attribution uses the confirmation candle's raw export-clock window.

## Limitations

The files remain provisionally identified by their filenames as Range XV. Timezone, timestamp meaning, exact ATAS settings, bar completion metadata, data-feed provenance, and contract-adjustment history remain unresolved. GC6 is analyzed explicitly because this study covers all seven available exports; it is not called GC20 and does not resolve the missing-GC20 limitation in Analysis 01.
