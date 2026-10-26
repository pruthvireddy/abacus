# Per-future news: descriptive statistics protocol

Protocol `per-future-descriptive-2` · authorized October 17, 2026.

The user's follow-up authorizes six contract tabs and expanded event-type, weekly,
monthly and related descriptive statistics from the improved per-future study,
plus publication on the existing Abacus Vercel site. This extends the original
import-only scope. Preserve the original run and its publication unchanged.

## Frozen observations and timing

Use the saved `per_future_news/study/horizons.csv` and `events.csv`, alongside
original aggregate tables, source calendars, indicator code and validation receipts.
Do not regenerate historical prices, calendar signals or TradingView exports.
The study interval is [2025-10-17 00:00, 2026-10-17 00:00) America/New_York.
Retain original source bytes before calculations; record every input hash and
source-project revision/dirty identity. Freeze execution source bytes before deriving
new tables. Existing locked Python is used without environment synchronization.

One observation is `(symbol, mode, event_epoch, horizon_bars)`; require uniqueness.
Contracts: 6E, 6B, 6J, 6A, 6C, 6S. Modes: combined, us_only, local_only.
Horizons: 5, 10, 15, 50, 100 actual chart candles. Use the existing confirmed
15-minute pre-release close/EMA20 versus EMA50 direction and frozen side.
The candle opening at release is first measured. Earlier entry-candle extremes
are excluded. Retain completion flags; incomplete outcomes do not enter averages.

Modes remain separate and are not added together. Mixed type 13 is an exclusive
bucket for simultaneous selected categories; never assign its outcome to each
component independently. Event counts differ by contract. These expanded domestic
samples are not the previous common-64 cross-contract comparison.

## Prespecified descriptive summaries

Group by contract, mode and horizon, with separate tables for overall, news type,
month, ISO week, news type × month, news type × week, entry side, news type × side,
weekday, release hour, year and quarter. All period labels use America/Chicago,
matching the source monthly table. ISO weeks start Monday and use ISO week-years.
Empty periods are absent rather than imputed as zero. Coverage/exclusion tables
separately show declared categories without eligible observations. Calendar groups
at sample boundaries can be partial; never label them full annual performance.

For each group retain signals, completed/pending counts, long/short counts;
mean and median MFE, MAE and signed close in original price units, outright ticks
and entry-normalized percentage points; favorable/adverse/flat close counts and
rates; MFE-above-MAE frequency; ratio of average MFE to average MAE; 10th, 25th,
75th and 90th percentiles of MFE, MAE and close ticks; min/max signed close ticks;
and mean/median/max elapsed calendar minutes. Favorable means close > 0, adverse
< 0 and flat exactly 0. MFE-above-MAE follows the original source tolerance:
`mfe_price - mae_price > 1e-10 * max(1, mfe_price, mae_price)`.

Means use finite completed observations and fsum/n; medians use the middle sorted
observation or mean of the central pair. Quantiles interpolate linearly at index
`(n-1)*p`. Empty outcome groups and zero MAE denominators yield null, not zero or
infinity. A small-sample label uses n < 10 only as a descriptive reading aid;
it is not a significance test or a selection rule. No confidence intervals,
multiple-comparison inference, prespecified holdout or profitable policy is claimed.
Preserve all negative and inconclusive values. Never pool overlapping modes or
currency shock observations into independent-trial uncertainty calculations.

## Verification and publication

Before real-ledger calculation, freeze this protocol, settings, input hashes,
producer/statistical source snapshots, Python lock, exact commands and exclusions.
Run meaningful synthetic numerical tests. Independently reconstruct every new
aggregate from the retained ledger and compare existing overall/type/monthly
summaries within 1e-10 relative/absolute tolerance. Check group partitions,
completion denominators, UTC/Chicago period labels, Mixed attribution and excluded
candidate categories. A second implementation must verify the new values without
calling the production aggregate function.

Prepare six standard Narada 1.1 saved reports before sealing the new unique run.
Each publication uses bounded saved-row tables, three charts and four selected
summary CSVs, with complete transfer mappings and checks. No research runs in the
web app. Preserve the original report as a related earlier run. Validate source
contract and private source audit, metadata/index, Node24 verify/test/lint/build,
static preview/browser behavior, then the separate Vercel release gates.

The 4,968 imported native checks mean eight fields across 621 native observations,
including H5 excursions; they do not revalidate every full-year outcome or horizon.
The full-year prices are reconstructed/back-adjusted history, calendars include
later corrections, event windows overlap, and sample availability is retrospective.
No executable fills, stops, targets, transaction costs, portfolio sizing, net P&L,
profit factor, Sharpe ratio or causality is inferred from these path observations.
