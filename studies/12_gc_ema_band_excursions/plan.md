# GC outer lower EMA band: long excursion study

Prepared 2026-09-25. The user requested implementation, execution, a year-by-year
report, and a reusable data path. This is an exploratory descriptive study, not
a tested trading strategy or an optimizer.

## Question

For a five-minute GC bar that **closes at or below** the indicator's outer
lower band, what subsequent long-side MAE and MFE occur over 5, 10, 15, 20,
30, 50, and 100 complete five-minute bars? Compare signal lockouts of 0, 5,
10, 20, and 30 *following* bars and break results out by New York calendar
year. The zero case is a reference, not a proposed trading cadence.

The pasted indicator's band is EMA(close,225) minus three times the population
standard deviation of the last 225 signed close-minus-EMA residuals. Its
separate inner-band re-entry setup, flat-EMA filter, and marker-only minute
cooldown are not part of this question. The plotted outer band's current close
participates in its calculation; the signal only exists after the bar closes.

## Event and measurement

At signal bar close, take the next contiguous, complete five-minute bar's
unadjusted open as a hypothetical entry. A cooldown of C bars suppresses bars
i+1 through i+C after accepted bar i; a suppressed candidate does not restart
the timer. Each C is a separate cohort. For horizon H, use the next H complete
five-minute bars from entry bar through bar H; include their high and low.
MAE=max(0, entry minus minimum future low), MFE=max(0, maximum future high
minus entry), in GC price points. Terminal move is bar H close minus entry.
Record means, medians, 90th percentiles, counts, and terminal-positive rate.
MAE and MFE are separate extrema; their order within a bar is unknown and they
must not be combined into a realized trade result.

Require five-minute timestamp continuity, full source-bar counts, one raw
contract, one price adjustment, and no roll or mixed-contract bar from signal
through horizon. Subtract the pinned adjustment from the adjusted OHLC to obtain
unadjusted selected-contract prices. Exclude incomplete horizons and partial,
cross-roll, or gap paths explicitly; do not replace missing bars. The adjusted
indicator series is a final retrospective snapshot, not point-in-time
certified. Count year by the signal close in America/New_York. 2026 is YTD.

## Reasoning and limitations

The outer band identifies unusually negative residuals relative to a recent
rolling distribution. A subsequent bounce could create favorable movement,
but an expanding downtrend can also produce further adverse movement. MAE/MFE
across horizons shows path scale and asymmetry without choosing a profit target
or stop from the same data. Cooldown changes sample composition and dependence;
it is not an independent profitability comparison. There is no slippage,
commission, spread, fill probability, exit policy, or trade-overlap model.
Multiple years and 35 parameter cells are exploratory, with no pristine
holdout. Yearly counts and exclusions matter as much as averages.

## Evidence and checks

Pin the source bar and new band feature manifests. Save a per-signal ledger,
all cooldown/horizon/year statistics, exclusions, a saved report, exact settings
and input/code hashes in a unique run. Unit tests cover the band formula,
cooldown edge, entry-bar inclusion, time gaps, rolls, and incomplete horizons.
The HTML report is rendered from saved statistics, not a fresh data pass.
