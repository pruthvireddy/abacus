# GC lower-band long: two-year filter selection

Prepared 2026-09-25 in response to the user's request to improve the GC
outer-lower-band long excursion profile using the last two calendar years.
Only 2025 and 2026 YTD signal outcomes are in scope. Existing causal band
features retain their earlier warm-up history.

The [study 12 run](../../runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/report.md)
already showed both years' unfiltered results. Consequently 2026 is a
chronological check, **not an untouched holdout**. A better-looking 2025 rule
that fails in 2026 is a negative finding; no filter will be promoted merely
because its own training score is high.

## Question and fixed baseline

Can one simple condition known at an outer-lower-band signal close reduce
long-side adverse excursion without giving up most of the favorable excursion?
Retain the study 12 signal (`close <= lower_outer_3sigma`), next complete
five-minute unadjusted open, full-path exclusions, 10-bar cooldown, and 20-bar
future horizon as the **primary** comparison. Cooldown is reapplied **after**
each filter: a rejected candidate does not start the cooldown. The unfiltered
rule is evaluated on the same 2025 and 2026 data.

## Timing and feature candidates

All filters are computed from the signal candle or earlier bars. They are
applied only after the completed signal candle, before a hypothetical next-bar
entry. No future high, low, close, excursion, or path-validity status is used
to form or tune a feature.

The protocol freezes these single filters and two prespecified combinations:

1. First outer close: immediately previous chart bar closed above its then
   outer lower band, with a five-minute contiguous predecessor.
2. Bullish signal body: signal close exceeds its open.
3. Upper-half close: `(close-low)/(high-low) >= 0.5`, with positive bar range.
4. Shallow penetration: `(lower_outer-close)/signal_sigma <= 0.25`.
5. Less-falling EMA: `(EMA225[t]-EMA225[t-20])/sigma[t] >= -0.5`.
6. Nonexpanding sigma: `sigma[t]/sigma[t-20] <= 1.1`.
7. New York morning: signal close at or after 08:00 and before 13:00 NY time.
8. First outer close AND upper-half close.
9. Shallow penetration AND upper-half close.

No optimized threshold search is permitted in this run. Thresholds are simple
fixed chart units and were chosen after a feature-only support pilot, not after
candidate outcomes. All nine candidates must be retained in the report.

## Selection and validation

The primary score is mean `clip(MFE/sigma, 0, 10) - clip(MAE/sigma, 0, 10)`
on valid 20-bar paths. The cap limits the effect of extreme low-sigma events;
uncapped means and GC-point means remain reported. A 2025 candidate may be
selected only if it has at least 45 valid paths, 20 distinct signal sessions,
and 10 ISO weeks; mean normalized MAE is below the unfiltered baseline; and
mean normalized MFE is at least 90% of baseline. Among those, choose the
largest positive training-score increase, breaking exact ties by the listed order.
If no candidate qualifies, select no filter.

Apply the chosen rule unchanged to 2026 YTD. Mark it as a descriptive
improvement only if it has at least 30 valid paths, 15 sessions, 8 ISO weeks,
a positive score difference, lower mean normalized MAE, and at least 90% of
the baseline mean normalized MFE. Show approximate 95% ISO-week bootstrap
intervals for the score difference but do not treat them as corrected for
the nine-candidate search or the already-viewed 2026 outcomes. Secondary
cooldown/horizon grids are descriptive sensitivity checks, not a new search.

## Evidence

Pin the source bar and band manifests and the sealed study 12 run manifest.
Retain feature-only candidate context, candidate event decisions, all candidate
2025/2026 metrics, selected-rule sensitivity tables, code/config/input hashes,
exclusions, numerical verification, and an offline HTML report. Do not change
the completed study 12 run. Interpret filtering as conditional path selection,
not realized trading performance. No spread, slippage, fee, stop/target
ordering, or fill probability is modeled.
