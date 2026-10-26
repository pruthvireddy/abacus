# Protocol 1.1.0 — Three-minute EMA6 / Globex VWAP crossing counts

User-requested timeframe correction after the original 5m/2m results were viewed.
Freeze this revision before examining 3m crossing outcomes. This is descriptive
retrospective research, with no parameter search, causal prediction claim or
profitability test. The original protocol and sealed run remain historical records.

## Inputs and population

Pin `session_anchored_vwap` 1.0.0 and its published whole-product-day eligibility
audit, the release's `volume_lead_back_adjusted_v1` one-minute source, and
`tradingview_daily_context` 1.0.0 for ES/NQ/GC. Current analysis uses only **3m**.
The released 5m/2m manifests remain pinned for the unchanged audit and selected
min-tick/lineage reference, not as a claimed 3m publication. Verify
selected manifest and partition bytes. Use every published eligible session;
retain explicit exclusions and year/month coverage, including periods with no
sample. Main comparable calendar: 2021-06-28 through 2026-09-18 inclusive.
Additional cohorts: all available history, and the intersection of eligible
session dates across all three products within that common calendar. These are
selected retrospective samples; especially GC is not representative of all days.

## EMA and crossings

EMA6 is on completed chart-bar closes, alpha = 2/7, first observed close seed,
recursive adjust=False. Independently aggregate one-minute closes to each output
interval on fixed New York clock boundaries, across all observed source history.
The close is the last observed minute; never synthesize missing minutes/bars.
Carry EMA through sessions and rolls on the pinned adjusted continuous series.
Require at least 250 preceding observed chart bars before any evaluated session.
Check every evaluated chart close against the independent full-history 3m close
aggregation, and reconcile all selected 3m OHLCV against the source minutes.
Adjustment uses later roll information; no absolute price is an execution price.

Independently aggregate each complete eligible source session to 460 three-minute
OHLCV bars. Use Bhishma's existing `aggregate_session` and `output_schema` helpers
in memory, select the required numerical fields, and discard their publication
metadata. Save only study evidence; never invoke a publisher or claim this is a
released 3m dataset. Validate the complete 1,380-minute roster, one contract and
one adjustment per session. Derive matching 3m Globex VWAP (three-minute bar-HLC3
weighted by three-minute volume), resetting at 18:00 New York and ending 17:00
next day. Verify against an independent cumulative weighted calculation. It is
interval-specific and is not exact trade-price VWAP. A crossing requires two consecutive
bars within the same Globex session: above if d[t] > 0 and d[t-1] <= 0, below if
d[t] < 0 and d[t-1] >= 0, where d = EMA6 - contemporaneous VWAP. Equality uses
floating-point comparisons with no tick tolerance. Touching zero alone is not a
cross; leaving zero to a strict side is a cross, including a return to the same
side. First session bar has undefined event, never a false/no-cross observation.
Do not count the VWAP anchor reset as a cross. Count each direction and their sum;
both moving lines contribute. No intrabar inference.

Windows use current bar OPEN in America/New_York and events become observable at
bar close. `globex` = full [18:00 D-1,17:00 D), `us_cash` = [09:30,16:00), common
comparison window for all products (not GC's exchange-specific RTH), and GC-only
`gc_day` = [08:20,13:30). A cross in the first window bar may compare with the
preceding bar in the same session. The 3m US cash window contains 130 bars, 09:30–15:57 opens. GC's 08:20 boundary
does not align: bar-open membership selects 08:21–13:27 (103 complete bars,
309 minutes), excluding the 08:18–08:21 bar. Its first counted comparison can
use that previous same-session bar. Do not split or synthesize boundary bars.
Sensitivity `globex_after_30_bars` drops the first 30 chart bars and the transition
into that window, to assess opening/seed/pre-session-history dependence. Main
EMA is continuous, including across year boundaries; this sensitivity is not a
second fitted EMA. At 3m the first counted sensitivity-bar open is 19:33 New York
(positions 0–29 form the first 90 minutes; position 30 transition is also omitted).

## Volatility

Use the last confirmed daily ATR(14) available at/before 18:00 session open, with
maximum age seven calendar days. Daily context contains Wilder ATR copied from
the source chart; do not recompute ATR from sparse eligible research days. Rank
the selected ATR-percent value against the immediately preceding 252 daily ATR%
observations for that product, excluding that selected observation; require 252
valid observations. Midrank percentile = (less + 0.5*equal)/252. Low < 1/3,
normal [1/3,2/3), high >= 2/3. Save ATR points, percent, source day, available_at,
percentile and bin. No future daily row may affect an earlier session's bin.
This as-of alignment is temporal, not proof of a point-in-time provider snapshot.

Separately label realized session range / pre-session ATR: quiet < 0.75,
normal [0.75,1.25), active >= 1.25. Full-session high-low uses the derived three-minute
bars; range is invariant to their session-constant adjustment. This classification
is retrospective and cannot be used at the open. These fixed ratios measure
realized expansion relative to background volatility, a different question from
high versus low ATR regime. Missing/old/nonpositive ATR is `unknown`, not quiet.

## Saved statistics and checks

Save per-cross event ledger, per-session/window counts (including true zero),
coverage/audit exclusions, overall, annual, calendar-year/month, month-of-year
and count-frequency tables. Segment each by both volatility classifications,
including unclassified days. Summaries include sessions, total/up/down crosses,
mean, median, 25th/75th/90th percentiles, zero-cross fraction, exposure and rate
per observed hour. Flag cells with fewer than 30 sessions. Calendar month missing
observations is absent evidence, never zero crossings. Session-date determines
year/month, including the preceding evening. Partial 2021 and 2026 are explicit.

Overall means receive descriptive 95% circular moving-block bootstrap intervals:
2,000 replicates, blocks of five chronologically ordered observed sessions,
resample entire product/timeframe/window/cohort panel with labels intact before
selecting bins; seed 20261023. This preserves short-run dependence among observed
sessions but not omitted calendar days. No multiple-testing significance claims.
Annual/monthly cells show distribution/support, not formal inference.

Verify EMA hand recursion, cross equality/reset and windows, time availability,
future-data invariance, thresholds, no-sample versus zero, and aggregation. A
separate reviewer reconstructs counts/statistics from saved evidence and samples
EMA from source. Save actual commands/results and environment versions. Rendering
uses saved tables only. Seal only after passed checks and an artifact inventory.
No Narada publication, deployment or strategy-card recommendation is requested.

## Revision comparability

Preserve previous run `20261023T202400Z_ema6_v1` unchanged. A fresh run contains
only 3m results. Reconcile product/date coverage, session ranges, ATR points, ATR
percentile and both volatility labels against its retained per-day evidence;
these should be identical for the same product/date. Historical 5m/2m outcomes
are not recomputed or selected for favorable performance. Keep full Globex,
US cash, GC-day and 30-bar sensitivity windows, annual/monthly segmentation,
all-history/common-calendar/matched-date cohorts, and fixed bootstrap settings.
