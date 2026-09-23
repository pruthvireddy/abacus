# Analysis 01 — Reversal follow-through across ES, GC, and NQ range charts

Prepared: September 6, 2026. Status: research and implementation plan; the reversal analysis has not been run.

## 1. Objective and decisions this study should support

Determine which available range setting, **within each asset**, most reliably produces consecutive completed candles in the direction of a newly completed reversal candle. Compare ES 4/5/6, GC 10/20, and NQ 10/20, subject to verification of the files and chart settings below.

The primary question is: **After the reversal candle closes, what is the probability of at least three additional consecutive candles in its direction?** Accompany that probability with event counts, the full continuation distribution, adverse and favorable excursions, elapsed time where measurable, opportunity frequency, and uncertainty. Also report the probability of three candles **including** the reversal, because that is a different and potentially useful interpretation.

The final report must distinguish a strong estimate from a small or unstable sample, and allow the answer “no clear winner.” More candles per move can result from a smaller range setting. A high candle-count probability alone does not establish a profitable trading strategy.

This document covers the first analysis only. The second analysis has not yet been specified. The copy-paste execution prompt appears at the end and is also saved separately in `prompts/01_range_reversal_follow_through_prompt.md`.

## 2. What is already known about this project

The following is a preliminary inventory of the existing files, not a statistical finding about reversals. Paths below are relative to the project root.

| Asset | Requested range | Existing file in `data/` | Rows | Status |
|---|---:|---|---:|---|
| ES | 4 | `ESU6_rangexv4_0614_0904.csv` | 52,591 | Present; filename indicates Range XV |
| ES | 5 | `ESU6_rangexv5_0614_0904.csv` | 36,188 | Present; filename indicates Range XV |
| ES | 6 | `ESU6_rangexv6_0614_0904.csv` | 26,248 | Present; filename indicates Range XV |
| GC | 10 | `GCZ6_rangexv10_0614_0904.csv` | 67,164 | Present; filename indicates Range XV |
| GC | 20 | No matching file found | — | Requested dataset missing |
| NQ | 10 | `NQU6_rangexv10_0614_0904.csv` | 417,815 | Present; filename indicates Range XV |
| NQ | 20 | `NQU6_rangexv20_0614_0904.csv` | 125,793 | Present; filename indicates Range XV |
| GC | 6, outside requested comparison | `GCZ6_rangexv6_0614_0904.csv` | 152,418 | Inventory only unless the user confirms a correction |

All files are headerless, semicolon-delimited, with five fields consistent with `timestamp;open;high;low;close`. Preliminary checks found no timestamp regressions or impossible OHLC relationships under that interpretation. These checks must be rerun and recorded by the eventual pipeline.

The timestamp format appears to be **`%Y-%d-%m %H:%M:%S`**, not ordinary year-month-day. For example, `2026-14-06` means June 14, 2026. All files start at the exported timestamp June 14, 2026, 18:00:00 and finish on September 4, 2026, at different intraday times. End times are ES4 16:46:43, ES5 16:31:37, ES6 16:32:43, GC10 16:54:49, GC6 16:47:52, NQ10 16:59:44, and NQ20 16:38:28. These are unlocalized export times.

The exports contain no headers confirming field meanings, timezone, open-versus-close timestamp semantics, completed-bar flags, chart settings, volume, bid/ask, or underlying trades. Timestamps repeat, sometimes for dozens of bars. Original row order is therefore essential.

### Unresolved items and working defaults

| Item | Default for implementation if still unresolved | Effect on conclusions |
|---|---|---|
| User said “Range XC”; filenames say `rangexv` | Study the existing bars under the provisional label “filename-labeled Range XV”; request clarification and log it | Do not call the results a verified Range XC study |
| GC requested 10/20; files labeled 6/10 | Analyze GC10 descriptively; keep GC20 marked missing; do not rename GC6 or substitute it | No GC10-versus-GC20 winner until both are available and verified |
| Range parameter units and settings | Preserve the numeric parameter as an opaque setting until confirmed | Do not assume parameter × tick size is the actual bar range |
| Reversal meaning | First opposite-colored completed bar, using the explicit rule in section 5 | This is a reproducible analytical convention, subject to user correction |
| Export timezone and timestamp meaning | Preserve raw times, run sequence-based work, and label any provisional date grouping | Exact timing and named market-session conclusions may remain unavailable |
| Contract/source and synthetic prices | Preserve filename contract identifiers and disclose unverified history/settings | Describe chart behavior; do not assert executable fills |

These issues should not stop work that the data supports. They must prevent unsupported labels, substituted datasets, fabricated timestamps, or overconfident recommendations. A later explicit user correction takes precedence over these defaults and should be recorded in the run manifest.

## 3. Understand the ATAS chart before analyzing it

### Documented facts

ATAS describes range charts as price-movement-based charts, rather than fixed-time bars. Its current help page lists RangeX, RangeXV, RangeUS, and RangeZ variations and says their exact construction algorithms are not disclosed. The page does not identify a variation named Range XC. This absence does not prove that the user’s label is invalid. [ATAS: Chart Periods and Types](https://help.atas.net/en/support/solutions/articles/72000602350)

ATAS’s Range XV article describes successive same-direction candles during directional movement and opposite-colored candles when counteraction appears; it also states that the construction method is closed. This supports investigating continuation empirically, but does not supply a reproducible bar-building algorithm. [ATAS: The nuances and benefits of using Range XV](https://atas.net/blog/specific-of-the-range-xv-chart/)

### Verification work

1. Record the exact platform/version, chart type, every chart parameter, price increment, source contract, continuous-contract or adjustment settings, export settings, and timezone where available.
2. Confirm the five-column schema against the export configuration or a known chart example.
3. Inspect representative consecutive candles, including reversals, wicks, gaps between adjacent closes and opens, dojis, session boundaries, and unusually large bars. Determine whether exported prices or timestamps may be synthetic or reconstructed.
4. Compare distributions of `high-low`, `abs(close-open)`, `open-next/previous-close` gaps, and close-to-close changes in ticks. Use this to describe observed geometry, not to claim discovery of the proprietary algorithm.
5. Verify candle color against `sign(close-open)` where a reference chart is available. Keep close-to-close direction as a separately labeled sensitivity, never a silent replacement.
6. Use the exported bars as the source of truth for the chart study. Do not rebuild Range XV from ordinary OHLC, and do not synthesize a missing range-20 export by aggregating smaller bars.

Separate platform-documented facts, user-confirmed metadata, empirical observations, and unresolved assumptions in `methodology.md`.

## 4. Project organization and reproducibility

Keep original inputs, executable code, intermediate products, and final reports separate:

```text
abacus-sahadeva/
├── data/                                      # Existing source exports; never modify
├── plans/
│   └── 01_range_reversal_follow_through_plan.md
├── prompts/
│   └── 01_range_reversal_follow_through_prompt.md
├── analysis/
│   └── 01_reversal_follow_through/
│       ├── README.md                          # Setup, commands, definitions
│       ├── pyproject.toml                     # Dependency specification
│       ├── configs/study.yaml                 # Frozen settings and metadata
│       ├── src/reversal_study/
│       │   ├── ingest.py
│       │   ├── validate.py
│       │   ├── events.py
│       │   ├── excursions.py
│       │   ├── timing.py
│       │   ├── statistics.py
│       │   ├── comparisons.py
│       │   ├── reporting.py
│       │   └── cli.py
│       └── tests/                            # Meaningful numerical/edge-case tests
├── work/
│   └── 01_reversal_follow_through/<run_id>/
│       ├── normalized/                       # Derived bars, never raw replacements
│       ├── events/                           # Event-level Parquet/CSV
│       └── diagnostics/                      # Logs, exclusions, intermediate QA
└── reports/
    └── 01_reversal_follow_through/<run_id>/
        ├── report.md
        ├── report.html
        ├── methodology.md
        ├── data_quality.md
        ├── tables/                           # Machine-readable CSV results
        ├── figures/                          # PNG/SVG charts
        └── run_manifest.json
```

Only the plan and prompt are being delivered now. Create the implementation folders when executing the study. A future second study should have its own `02_...` directories and may reuse read-only inputs.

Use a small Python package and command-line workflow, with dataframes/arrays, Parquet support, numerical statistics, and standard plotting libraries as needed. Notebooks may supplement, but must not be required to reproduce results. Record dependency versions, source hashes, file sizes, row counts, configuration hash, code revision or source hashes, random seed, dates/sessions used, exclusions, and run time. Use unique run IDs; preserve previous reports. Cache only by input and configuration identity.

Proposed interface to implement:

```bash
python -m reversal_study.cli audit --config configs/study.yaml
python -m reversal_study.cli run --config configs/study.yaml
python -m reversal_study.cli report --run-id <run_id>
```

The README must supply actual working setup and invocation instructions from a clean environment.

## 5. Freeze the event definitions before inspecting performance

### Candle direction and reversal

For completed candle `i`, define `d_i = sign(C_i - O_i)` using validated integer-tick prices. Bullish is `+1`, bearish is `-1`, and a doji is `0`.

The primary reversal occurs when `d_i` and `d_(i-1)` are nonzero and `d_i = -d_(i-1)`, within the same valid sequence segment. Candle `i` is the signal. Its direction and attributes become available only when it closes. No future high, low, close, or eventual swing point may enter the signal definition.

Count the immediately preceding run of opposite-direction candles as a signal-time attribute. Primary eligibility requires at least one such candle. Prespecified secondary cohorts require at least two or at least three. Do not select the preferred lookback after inspecting the final test set. Long and short reversals must be reported separately and combined.

Dojis break both runs and event adjacency under the primary definition: a reversal requires two immediately adjacent non-doji candles. Do not skip over a doji or missing row to manufacture a reversal. Exclude an unconfirmed final live candle. If completion cannot be established, conservatively omit the final row and record that choice.

### Consecutive follow-through

Let `L_i` be the number of immediately following completed candles that retain the signal direction, stopping at the first opposite-colored candle or doji. **The reversal candle itself is excluded.** Let `T_i = 1 + L_i` include it.

Example: `down, down, UP(signal), up, up, down` has `L=2`, `T=3`. It satisfies “three candles including the reversal,” but not “three additional follow-through candles.”

Report:

- `P(L≥1)`, `P(L≥2)`, **`P(L≥3)`**, `P(L≥4)`, `P(L≥5)`, and `P(L≥10)`.
- `P(T≥3) = P(L≥2)` alongside the primary result.
- Exact completed-run counts for `L=0,1,2,3,4,5–9,10+`, with censored runs shown separately.
- Mean, median, p75, p90, p95, and maximum completed `L`, explicitly labeled as completed-run summaries. Supply sample counts and do not present the maximum as typical.
- A complete-window restricted mean `E[min(L,10) | ten valid future bars available]`, and a common-cohort continuation curve on that same cohort.
- Conditional continuation `P(L≥k+1 | L≥k)` on a common eligible cohort, so later-stage persistence is visible without changing denominators silently.

### Eligibility, boundaries, and censoring

For each fixed threshold `k`, require `k` valid subsequent bars in the same permitted segment, regardless of whether a break occurs earlier. Then `N_k` is all qualifying reversals, `S_k` is those whose next `k` bars all match the signal, and the estimate is `S_k/N_k`. This estimates continuation **among events with a complete k-bar observation window**, not unconditionally among all reversals. Excluded boundary events are reported separately, not treated as failures or omitted without explanation. The headline `P(L≥3)` uses `N_3` and must carry that complete-window qualification.

Future bar availability can itself select a different cohort for fast- and slow-forming charts. Show exclusion shares for every candidate and horizon, including fixed-horizon excursions. When timestamps permit, check sensitivity using the same prespecified signal-time cutoff for all sizes, such as omitting signals in the last hour before the verified session close. Freeze that cutoff before examining outcomes and retain the remaining censoring disclosure; it does not guarantee that every event has a complete future window.

Use a common `N_10` cohort for a monotone continuation curve and distribution comparisons; also publish threshold-specific results with their individual denominators. A natural run cut off before its terminating bar is observed is right-censored, not a completed run of the currently observed length. Describe the observed lower bound and censor reason. Do not estimate the unrestricted mean run length by averaging lower bounds.

Segments end at verified missing/corrupt data, contract transitions, the chosen session boundary, or the end of an export. An ordinary long gap in a price-based chart is not automatically missing data. Investigate gaps against metadata and other exports before classifying them. If invalid rows are removed, preserve a break marker; do not connect their neighbors as though no gap existed.

The primary intraday study stops labels at verified exchange-session boundaries. Until timezone/calendar metadata is established, sequence results may use explicitly provisional export-date segments with a boundary-sensitivity comparison. Do not call those dates verified trading sessions. There is no reversal across a segment boundary without valid within-segment history.

## 6. MAE and MFE: exact definitions and useful summaries

**MAE means maximum adverse excursion per event; MFE means maximum favorable excursion per event.** The study will report the **mean and median of those per-event maxima**, answering the request for average adverse and favorable excursions.

The primary price reference is the completed signal close `E=C_i`. This is a chart reference, not an asserted execution price. For a fixed horizon `H`, use only bars `i+1` through `i+H`; exclude all signal-bar highs and lows because they occurred before the signal was known.

```text
Long signal:
  MFE_H = max(0, max(future highs) - E)
  MAE_H = max(0, E - min(future lows))
  terminal_move_H = C_(i+H) - E

Short signal:
  MFE_H = max(0, E - min(future lows))
  MAE_H = max(0, max(future highs) - E)
  terminal_move_H = E - C_(i+H)
```

Use horizons **1, 3, 5, 10, and 20 future candles**. Every horizon uses all eligible reversals, including immediate failures; require a complete horizon within the segment. MAE and MFE are nonnegative magnitudes; terminal movement is signed. Record sample size, incomplete-horizon exclusions, mean, median, p75, p90, and p95. Show distributions, not only ratios of averages.

Provide three distinct excursion views:

1. **Fixed future-bar horizons:** the primary reproducible excursion tables, independent of how long the run eventually lasts.
2. **Through the first break:** include the entire first opposite/doji bar and reference an exit at its close. This measures the path until failure is confirmed. Censor if that bar is unavailable. It remains descriptive and assumes no verified fills.
3. **During the same-direction run only:** exclude the terminating bar and explicitly label the result as hindsight-conditioned “potential during the observed run.” It is not a realizable exit rule. For an observed `L=0`, the empty post-signal run has excursion zero by convention; unknown/censored values stay missing.

Keep winner-only or `L≥3` excursion tables secondary; show them beside the full-event table to avoid hiding the adverse paths of failed reversals.

### Price units and cross-asset interpretation

Store calculations in integer exchange ticks, then display native price units, ticks, and gross dollars for one standard futures contract. Current reference specifications are:

| Asset | Minimum tick in quoted price | Dollar value per tick | Dollar value per 1.0 price unit |
|---|---:|---:|---:|
| ES | 0.25 index point | $12.50 | $50 |
| NQ | 0.25 index point | $5 | $20 |
| GC | $0.10 per troy ounce | $10 | $100 |

Sources: [CME futures guide, ES tick example](https://www.cmegroup.com/education/files/a-traders-guide-to-futures.pdf), [CME E-mini Nasdaq-100 specifications](https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.contractSpecs.html), and [CME Gold contract fact card](https://www.cmegroup.com/trading/metals/files/fact-card-gold-futures-options.pdf). Recheck specifications when executing, and retain the sources in the manifest.

Normalize by the configured nominal range only after its units are confirmed; label that normalization as nominal, because actual XV high-low ranges may differ. Add a past-only volatility-normalized view if a common time-based price source is available. Do not compare raw ES, NQ, and GC points as if they represent equal distance or risk.

No realized P&L, win rate at a stop/target, or executable expectancy is required for this study. If added later, it needs its own entry/exit, fees, spread, slippage, and position-overlap specification. OHLC alone cannot determine which barrier was touched first when both occur inside a bar. Do not reconstruct an intrabar path or count MFE as captured profit.

## 7. Time and opportunity statistics

Measure time from **signal confirmation**, not from the signal’s opening. Where the timestamp semantics permit it, report:

- Mean, median, p75, and p90 time to complete follow-through candle 1, 2, 3, 5, and 10, with success counts and success-conditional labeling.
- Time to the last same-direction candle, and separately time to confirmation of the first breaking candle.
- The future-bar index containing the first positive MAE and MFE extreme at each fixed horizon; resolve equal positive extremes using the earliest bar. If an excursion is zero, use index `0` for the signal-close reference instant and mark a future extreme time inapplicable, rather than assigning an arbitrary future bar. Exact intrabar extreme time is unavailable without underlying trades.
- Distribution of candle durations, and count of tied/zero-resolution timestamps.
- Eligible reversals per session and per active hour where verified, successful three-bar runs per session, and their variability across dates. Include valid zero-event sessions in rate denominators.

If exported timestamps are bar-open times, the next bar’s opening timestamp may be used as a **close-time proxy only after checking the export semantics and continuity**. If they are close times, use them directly after verification. Without such evidence, provide sequence-based bar counts and mark elapsed seconds/minutes unavailable, or place explicit timestamp-difference proxies in a separate provisional table. Never invent precision or evenly distribute tied timestamps.

An extreme located in a known bar can be assigned a containing-bar time interval, not an exact touch time. A fixed clock horizon falling inside a bar cannot use the entire bar’s high/low without looking beyond the horizon. Common clock-window excursions require underlying trades or a clearly bounded method that discloses interval uncertainty.

Report completion times among successes beside the overall success probability; fast successful cases alone can hide many failures. Bars waiting beyond a valid study boundary are censored. Distinguish wall-clock elapsed time from active-market time if both are supplied.

## 8. Compare range settings fairly

### Primary comparisons

Compare ES4/5/6 on the same verified dates, sessions, contract history, and observation windows; compare NQ10/20 similarly. Compare GC10/20 only when both requested datasets are available. A GC6 supplementary comparison requires user confirmation. Report full available coverage separately from the common-window comparison.

Use the intersection of valid coverage, accounting for different first/last complete bars and missing intervals, not just matching filenames or calendar endpoints. Apply the same definitions and data-quality exclusions to every candidate. Retain zero-event dates when computing opportunity rates.

Range-specific events need not occur at the same timestamps; they should not be forcibly paired as though they were identical signals. Pair **dates or session blocks** for uncertainty on differences. Each candidate’s denominator remains its own eligible reversal count.

### What “best” means

Predeclare `P(L≥3)` as the primary ranking metric. Rank within each asset using development data. Use validation for prespecified checks of the selected candidate's sample support, direction of differences, and temporal stability; record whether the choice is supported or remains preliminary. Do not search for replacement filters or a new winner on validation. Freeze the candidate and reporting decisions before evaluating untouched chronological test data. Present the test estimates for all prespecified candidates as a comparison, with multiple-comparison uncertainty, but do not retune the selected candidate using that test set.

The recommendation must show the following side by side:

1. Probability and count of at least three additional same-direction bars.
2. Typical and upper-tail follow-through length.
3. Fixed-horizon mean/median MFE and MAE, including adverse tails.
4. Time needed, when supported.
5. Number of usable opportunities per comparable session.
6. Stability by direction and chronological subperiod, and uncertainty in differences.

Do not hide these tradeoffs in a weighted score chosen after seeing results. If the highest probability setting has few events, slow formation, or wide uncertainty, say so. If differences are not distinguishable, report a tie/no clear winner, with the practical tradeoffs.

### Guard against the smaller-bar advantage

Three smaller bars can represent less price travel than three larger bars. Alongside candle counts, report net directional price movement and excursion magnitudes in ticks, and distributions of price movement when each continuation milestone completes.

When timing is validated and data resolution supports it, add common 1-, 5-, and 15-minute post-signal windows and common within-asset price thresholds. Prespecify thresholds independently of outcomes, for example 1×/2×/3× the largest candidate’s verified nominal tick setting. Do not infer intrabar barrier ordering. If required precision is unavailable, disclose that a fair clock-based comparison is unavailable and restrict the “best” claim to the candle-count objective.

The cross-asset summary should display each asset’s best-supported setting and normalized tradeoffs. A pooled average dominated by NQ’s much larger bar count must not determine the answer. If an overall summary is added, weight assets equally and explain that the events and economic risk differ.

## 9. Statistical credibility and exploratory scope

### Chronological validation

After auditing coverage, freeze common date/session boundaries and split them chronologically: first 60% for development, next 20% for validation, final 20% for untouched testing. Use identical boundaries across a given asset’s range settings; prefer aligned dates across assets when available. Never randomly shuffle bars into train and test.

Purge events whose required future outcomes cross a split. Use an embargo of at least one full valid session between splits, extending it if any permitted outcome horizon can span farther. Keep all configuration choices, definitions, exclusions, and exploratory variants in an experiment ledger. Use expanding-window checks inside the development/validation period when enough dates exist.

### Uncertainty and dependence

Reversal events and horizons overlap, and market behavior is serially dependent. Use a session-block bootstrap (at least 2,000 replicates, fixed recorded seed) for primary 95% confidence intervals; resample the same session blocks across range candidates when estimating probability differences. Include a short multi-session-block sensitivity to assess dependence across dates. If only provisional export dates are available, disclose that limitation in the clustering unit.

Recalculate pooled numerators and denominators in each replicate rather than averaging event percentages incorrectly. Event-weighted probabilities and equally weighted session-average rates are different quantities; label and report both where useful. Do not silently drop empty-event days from the latter’s opportunity denominator. Handle replicates with undefined denominators explicitly.

Wilson intervals may accompany counts as an elementary reference, but they do not replace dependence-aware intervals. For the prespecified pairwise range comparisons, control the familywise error rate across the requested study comparisons with a suitable simultaneous block-bootstrap procedure or valid block-based tests with Holm adjustment. Clearly label additional slices as exploratory.

### Sample adequacy and stability

Record the number of distinct sessions as well as event counts. As an initial reporting rule, flag any held-out estimate with fewer than 200 eligible reversals or fewer than 10 valid sessions as low-support; these thresholds are reporting conventions, not guarantees of adequate power. Always show interval width. If the final test period is too small, retain it and report preliminary evidence rather than borrowing it for tuning.

Break down by long/short, prior opposite run length 1/2/3+, calendar month or chronological block, and verified session/time-of-day. Use a shared 09:30–16:00 America/New_York window only when localization is known; call it a common US daytime window rather than implying it is every asset’s official regular session. Define official asset sessions from verified calendars if those are used.

Volatility or trend regimes are secondary and must use information known at the signal, with cutoffs learned on development data only. The available OHLC exports do not support volume, delta, footprint, or order-flow filters. Avoid a large filter search that turns the test set into an optimization target.

Add a descriptive same-chart baseline: continuation probabilities after ordinary directional bars using the same eligibility rules, with direction/date/time composition standardized where feasible. Compare reversal-conditioned continuation against that baseline using block uncertainty. It is context for chart persistence, not independent evidence of tradable alpha.

## 10. Required tables and visual outputs

All tables must state chart identity status, asset, contract, range setting, direction/cohort, date window, split, denominator, horizon, units, and timing status. Missing/unavailable is distinct from zero.

### A. Headline continuation table

Use one row per asset/range/direction/split and include a combined-direction view. Compact example schema; values below are deliberately not populated:

| Asset | Range | Eligible N₃ | Successful L≥3 | P(L≥3), 95% CI | P(T≥3) | Mean capped L₁₀ | Signals/session | Status |
|---|---:|---:|---:|---|---|---:|---:|---|
| ES | 4 | pending | pending | pending | pending | pending | pending | Awaiting analysis |
| ES | 5 | pending | pending | pending | pending | pending | pending | Awaiting analysis |
| ES | 6 | pending | pending | pending | pending | pending | pending | Awaiting analysis |
| GC | 10 | pending | pending | pending | pending | pending | pending | Awaiting analysis |
| GC | 20 | — | — | — | — | — | — | Dataset missing |
| NQ | 10 | pending | pending | pending | pending | pending | pending | Awaiting analysis |
| NQ | 20 | pending | pending | pending | pending | pending | pending | Awaiting analysis |

Include a companion threshold table with `k`, total reversals, `N_k`, `S_k`, failures, boundary exclusions, probability, and confidence interval. The `P(T≥3)` column must carry its own denominator or use an explicitly shared eligible cohort.

### B. Excursion table

| Asset/range | Side | Horizon | N | Mean MAE | Median MAE | p90 MAE | Mean MFE | Median MFE | p90 MFE | Median terminal move | Unit |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| one row per configuration | long/short/all | 1/3/5/10/20 bars | … | … | … | … | … | … | … | … | ticks |

Supply price-unit and one-contract-dollar versions, plus separate through-break and run-only tables. Never combine these horizons without labels.

### C. Run-length and timing tables

Provide exact run bins, threshold probabilities, completed/censored counts, mean/median/p90 run length, time-to-k among successes with denominators, bar index to extreme, and timing-resolution flags. Pair opportunity counts with active dates/hours. Include paired range differences with confidence intervals and a stability table by chronological block.

### D. Figures

- Common-cohort `P(L≥k)` curves, with confidence intervals, one panel per asset.
- Run-length distributions and MAE/MFE median/p90 profiles by fixed horizon.
- Probability-versus-opportunities-per-session plot with uncertainty.
- Probability-versus-adverse-excursion comparison to make tradeoffs visible.
- Time-to-three distributions where timing is supportable.
- Chronological stability plots and a data coverage/gap chart.
- A small deterministic or seeded sample of annotated successful and failed reversal sequences, with signal, future bars, reference price, and excursions. Select examples by documented rules; do not present only attractive trades.

Use standalone PNG/SVG figures and a readable HTML report with links to CSVs. The Markdown report must remain useful without the HTML.

## 11. Implementation phases and completion criteria

1. **Audit and metadata:** inventory and hash inputs, confirm schema/date parsing, record chart and GC discrepancies, inspect synthetic-price/timing limitations, and write data-quality findings. Resolve what can be resolved without editing source data.
2. **Freeze specification:** write the configuration, event rules, units, boundaries, chronological splits, primary metric, comparison family, and assumption ledger before evaluating reversal outcomes.
3. **Normalize and detect events:** preserve source file and original row number, construct validated bars, break markers, signal attributes, future labels, and event-level audit records.
4. **Measure outcomes:** compute threshold eligibility, consecutive runs, all fixed-horizon excursions, through-break/run-only summaries, timing where valid, and opportunity rates.
5. **Validate numerical correctness:** use hand-computable synthetic examples for long/short symmetry, immediate failures, long runs, dojis, ties, invalid-row boundaries, session boundaries, incomplete horizons, split leakage, integer ticks, zero-excursion reference indices, and exclusion of signal-bar extremes. Confirm monotonic continuation on a common cohort and nonnegative MAE/MFE. Spot-check real sequences against reported events.
6. **Compare and quantify uncertainty:** run the frozen comparisons, block intervals, baseline, limited sensitivity analyses, and held-out evaluation. Use a small independent brute-force check on sampled events to validate optimized calculations.
7. **Produce and reconcile reports:** generate every available table and chart, reconcile event rows to aggregate counts, include source links and manifest, and state which requested conclusions remain unsupported and why.

Required event records include source hash/file/row, event ID, asset/contract/chart/range, segment and split, signal direction and prior run length, raw and interpreted time/status, reference price, eligibility and success for every threshold, observed run length and censor flag/reason, horizon-specific MAE/MFE and signed terminal move, extreme-bar indices, and valid timing/proxy fields. This provides a traceable answer to “which candles produced this statistic?”

The study is complete when the code reruns from preserved inputs, numerical checks pass, counts reconcile, all supported requested comparisons and outputs exist, and the report gives a supported recommendation or a clear no-winner/insufficient-data conclusion for each asset. GC20’s absence permits completion of available-data work, but does **not** count as completion of the requested GC10/20 comparison.

The final narrative should directly answer: Which setting has the strongest supported three-bar continuation probability? How many observations support it? What typically happens to price against and in favor of the signal? How many candles and how much time are involved? How often do opportunities occur? Does the result persist outside the period used to choose it?

## 12. Copy-paste execution prompt

The following prompt is also available as a standalone file for easy reuse.

<!-- EXECUTION_PROMPT_START -->
You are working in `/Users/ppanati/Documents/projects/abacus-sahadeva`.

Implement and execute Analysis 01: a thorough, reproducible study of reversal-candle follow-through across ES, GC, and NQ range-chart exports. Read `plans/01_range_reversal_follow_through_plan.md` first and use it as the detailed specification. This request authorizes the local implementation, validation, analysis, and report generation. Complete the supported work; do not stop after proposing another plan.

The requested comparisons are ES ranges 4/5/6, GC 10/20, and NQ 10/20. Inspect the current `data/` inventory again. At planning time the files were labeled Range XV, although I initially said Range XC, and GC had files labeled 6 and 10 rather than 10 and 20. Honor any corrections I have supplied since then. Otherwise record these discrepancies, provisionally analyze the filename-labeled XV exports, keep GC20 marked missing, and do not silently substitute GC6 or claim a verified XC result. Continue unaffected work and ask only for metadata that materially affects unresolved conclusions.

Preserve `data/` exactly. Keep all implementation, configuration, dependency information, and tests under `analysis/01_reversal_follow_through/`; derived bars and event-level working data under `work/01_reversal_follow_through/<run_id>/`; and final Markdown/HTML reports, CSV tables, figures, methodology, data-quality findings, and manifest under `reports/01_reversal_follow_through/<run_id>/`. Preserve earlier runs and document a reproducible command.

Begin by verifying ATAS chart terminology and available settings against official ATAS documentation and the exports. Distinguish documented facts, observed behavior, and assumptions. Do not invent ATAS's proprietary bar-construction algorithm or manufacture a missing chart from other OHLC bars. Verify contract tick sizes and dollar values against CME sources. Audit the data before computing performance. The existing exports appeared headerless and semicolon-delimited, with timestamp/open/high/low/close, and used `%Y-%d-%m %H:%M:%S`. Validate this explicitly; preserve original row order and repeated timestamps. Establish timezone, timestamp meaning, bar completion, contract history, and coverage where possible. Leave unsupported metadata unresolved rather than guessing.

Freeze definitions, parameters, exclusions, and chronological splits before reviewing reversal outcomes. Unless I specify otherwise, define a reversal as the first completed non-doji bar whose close-minus-open direction opposes the immediately preceding completed non-doji bar, within a valid segment. Require at least one prior opposite candle; use at least two and at least three as prespecified sensitivities. Dojis break runs. Do not use future data in signal selection.

Let L count consecutive same-direction candles AFTER the reversal, excluding it, and T=1+L include it. The primary comparison is P(L≥3). Also report P(T≥3)=P(L≥2), probabilities for L≥1/2/3/4/5/10, exact completed-run bins, censored counts, run-length summaries, and the restricted mean min(L,10). Use complete threshold-specific horizons with explicit denominators and a shared eligible cohort for continuation curves. Label these estimates as conditional on complete future-window availability, report exclusions, and check the shared signal-time-cutoff sensitivity where supported. Do not count incomplete future observations as failed continuations.

Compute maximum adverse and maximum favorable excursion per event, then their means, medians, and tails, from the signal-close reference using ONLY subsequent bars. Use fixed horizons 1/3/5/10/20 bars for all eligible signals, with correct long/short symmetry, and show signed terminal movement. Keep through-first-break excursions, including the break bar, separate from hindsight-conditioned run-only potential. Present ticks, native price units, and gross dollars per standard contract; do not describe these as executable profits. Show long, short, and combined results, with sample sizes and exclusions.

Report time to follow-through milestones, time to failure confirmation, bars containing MAE/MFE, and opportunities per session/hour when the data supports those measurements. Signal time must mean confirmation time. If timestamps cannot support elapsed-time claims, supply bar counts, explicit timing limitations, and separately labeled proxies where defensible. Never invent intrabar ordering or exact extreme times from OHLC, or invent subsecond durations for tied timestamps. Common clock-window comparisons must not use information from beyond their horizon.

Compare range sizes on matched valid date/session coverage within each asset. Keep an overall cross-asset table, but do not let NQ's larger event count dominate an aggregate or treat raw points as comparable. Show probability, count, follow-through length, MAE/MFE, speed, and opportunity frequency together. Explain the mechanical smaller-bar advantage; add common price/clock comparisons only where supported. A higher continuation probability is not itself evidence of profitability.

Use the plan's chronological 60/20/20 development/validation/test approach, purging crossing labels and applying the embargo. Select a candidate on development data, use validation for the prespecified stability checks, and freeze the candidate and reporting decisions before evaluating the final test period. Account for serial dependence and overlapping observations with paired session-block resampling, at least 2,000 bootstrap replicates with a recorded seed, and multiplicity control for prespecified range comparisons. Show interval widths, sample support, a same-chart persistence baseline, and limited stability checks by direction, prior run length, and time period. Mark exploratory findings and permit “no clear winner.”

Write meaningful numerical and boundary-case tests, manually reconcile a sample of real events, and cross-check an optimized calculation against a simple independent implementation on a sample. Make every table traceable to event records and input/configuration hashes. Generate the full supported table and figure set in the plan, including a headline probability/count table, horizon-specific MAE/MFE tables, run-length and timing tables, paired comparisons, coverage and stability findings, and annotated success/failure examples.

Finish with a clear report of the best-supported range setting for each asset, or why there is no reliable winner, explaining probability, count, adverse/favorable excursion, candle count, elapsed time, opportunity rate, and held-out stability. State missing inputs and unsupported conclusions precisely. In your final response, link to the main report, key comparison table, and implementation README, and summarize the most important findings. Do not place trades or develop the unspecified second study.
<!-- EXECUTION_PROMPT_END -->
