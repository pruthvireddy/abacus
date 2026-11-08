# Statistics catalog — Verniman Pivot Statistics — ES

This is a definition catalog, not a results report. The authorized descriptive
workflow uses repository-retained pivots and data only; no external acquisition.
Requested coverage ends 2026-10-30 and actual retained market data currently
ends 2026-09-18. These measurements must be retained with the actual executable
protocol/input freeze before market outcomes are calculated.
The [protocol](protocol-1.0.0.md) owns event timing and boundary rules.

## Ranked extension

The [2.0.0 protocol](protocol-2.0.0.md) and
[20-row implementation matrix](implementation-matrix.md) extend these definitions
to actual price/EMA6–VWAP transitions, independent RTH and full-Globex populations,
EMA-reference recrosses, pivot/VWAP sequences, opening configuration and fixed
separation bands. S01–S20 are stable statistic IDs. Existing `ema_events` and
`ema_vwap_aligned` retain their original meanings. Recent20/60/120 comparisons
use disjoint preceding histories. The full private tall summary preserves units,
numerators, valid denominators, supporting days, missing/censored counts and dates;
bounded public projections select saved values only.

## Units, record levels and information time

All price distances and excursions use unadjusted same-contract **ES points**;
context basis points are `10000 * distance / pivot`; return/excursion basis
points use the event reference close as denominator. A nonpositive or missing
reference makes the basis-point value undefined. Any tick display declares its
tick size. Rates are ratios, durations are minutes,
and timestamps carry America/New_York semantics plus an unambiguous stored
instant. No distance or reach is labeled trading profit.

| Record | Key and retained content | Denominator role |
|---|---|---|
| Source/calendar audit | Session date, canonical outlook/source revision, exact contract, pivot shape/interpretation, availability, missing/conflict reasons | Requested calendar and source-candidate coverage, not assumed eligible days |
| Daily | Eligible session date and contract, opening/pre-open states, daily counts, occupancy, closing states, quality/exclusions | One row per explicitly eligible day, including actual zero-event days |
| Section | Date plus one of the three fixed section IDs, start/end states, counts and endpoints | Eligible observed day-sections, including zero events |
| Price event/episode | Stable date/contract/bar/direction identity, time-zero states, confirmation and return timestamps, future path and censoring | Events; distinct days accompany every event count |
| EMA event/retest | Actual EMA6 crossing identity, state at crossing, first post-cross pivot touch and closing classification | Actual EMA crossings with a fully observed relevant horizon |

Store the information time of each condition separately from the time its
outcome becomes known. Opening cloud/EMA/VWAP state is known from completed
values by 09:30. Subsequent confirmation, episode return, full-day behavior and
closing location are future labels. Historical pivot source availability and
retrospective full-day data-quality selection remain separate qualifications.

## Opening and reference context

At 09:25 and 09:30 save price, pivot, VWAP, EMA6, EMA20, EMA50 and their source
observation/availability times. The opening-price value is the actual 09:30
open; the pre-open value is the last completed one-minute close.

- `price_minus_pivot`, `ema6_minus_pivot`, `vwap_minus_pivot`, cloud lower/upper
  minus pivot, and price minus VWAP/cloud/EMA6: signed ES-point distances.
- Price/EMA6/VWAP strict side relative to pivot: above/below/equal, with unknown
  separate. Price and pivot cloud location: below/inside/above; touching either
  boundary belongs to inside. A zero-width cloud is a line and retains its
  explicit flat ordering.
- Cloud signed spread/width and EMA20/EMA50 ordering, plus 15-minute changes of
  EMA6, EMA20, EMA50 and VWAP. Keep continuous values as well as positive/zero/
  negative categories; do not fit slope thresholds after observing outcomes.
- Cloud width change is current absolute width minus width 15 minutes earlier.
  Opening gap is actual 09:30 open minus the preceding applicable RTH close of
  the same delivery contract; missing prior-session evidence stays undefined.
- Opening price, EMA6, cloud and VWAP agreement/disagreement panels use these
  time-zero measurements. Missing one feature makes that condition unknown,
  not bearish, flat or false.

Denominators are eligible days with the particular snapshot/feature available.
Display missing-feature counts and the overall eligible-day count alongside
conditional denominators.

## Recurrence, episodes and sampled occupancy

| Metric family | Definition | Denominator / support |
|---|---|---|
| Price crosses | All strict three-minute close side changes; counts up/down/total; daily and section distributions | Eligible days/sections, retaining zero counts |
| EMA6 crosses | Actual strict line-side transitions on completed three-minute closes, with opening seed excluded | Eligible days/sections and actual EMA event counts |
| Crossings per observed hour | Per-day/section crosses divided by valid native three-minute price or ready-EMA observations × 3/60 hours | Corresponding observed-hour exposure; zero exposure is undefined, while a valid zero-cross rate is zero |
| Touches | Completed three-minute bars whose low/high contain the exact pivot | Eligible three-minute bars; bars, not distinct tick touches |
| First/last cross | First/last observed crossing time, direction and assigned section | Days/sections with a cross; no-cross support shown separately |
| Recrosses | Each subsequent reverse price cross and the preceding episode's elapsed duration | Price episodes with observed reverse endpoint; censored count separate |
| Occupancy | Count/share of completed three-minute closes above/below/equal to pivot | Valid sampled closes, with expected/observed support; not exact minutes on a side |
| Longest same-side run | Longest consecutive strict same-side three-minute closing observations; equality, opposite side and unknown break a run | Eligible days/sections, measured in native bars |
| Episode penetration | Maximum directional distance from pivot during the active post-cross episode | Episodes with complete observed path through return/end; censored status retained |
| Episode duration | Cross-close to reverse-close; end-of-day duration is right-censored | Returned episodes for completed-duration distribution; total/censored support shown |
| Closing location | RTH close relative to pivot, opening price, EMA6/cloud and VWAP | Eligible days with corresponding closing features |

No opening side is counted as a crossing. Equality retains remembered strict
side but remains an observed equal close in occupancy. Touch, cross and
recross measure different objects and may not share a denominator implicitly.

## Price breaks and EMA6 crossing

The central panels retain both event-time state and later path:

| Panel | Membership becomes known | Interpretation |
|---|---|---|
| Same-close EMA crossing | Price-event close | Actual EMA6 cross in the same direction at that close |
| Already aligned | Price-event close | EMA6 on the price-break side without a same-close actual cross |
| Opposite/equal/unknown | Price-event close | Explicit raw side, remembered side and availability fields |
| Delayed EMA crossing | Actual confirmation close before episode reverse | Lag in minutes and price movement before confirmation; subsequent outcomes start here |
| Returned without new EMA cross | Reverse price close | Retrospective path label; separate already-aligned-at-start cases |
| Unfinished episode | 16:00 with no reverse | Censored return/confirmation observation, not an automatic shallow failure |

Save confirmation lag, distance from pivot at confirmation, episode penetration
before return/confirmation, and direction-specific outcomes. The phrase
“shallow break” is descriptive: show the measured penetration of returned
unconfirmed episodes without optimizing a numerical shallow/deep cutoff.
Do not group an initially aligned EMA6 with an initially opposite EMA6 merely
because neither produced a new crossing before the return.

All-event recurrence remains a principal descriptive view. Parallel
first-price-event-per-day and first-price-event-per-section panels reduce
repetition and reveal whether later events drive a pattern. Keep their
populations labeled; first events are not a replacement for all raw crossings.

## Followthrough and retest outcomes

For direction d equal to +1 for upward and -1 for downward events, reference
price R is the unadjusted close when the event becomes observable. At endpoint
T, signed displacement is `d * (close[T] - R)`. Favorable excursion is the
maximum nonnegative directional distance from R on the subsequent one-minute
path; adverse excursion is the maximum nonnegative opposite distance. Use
endpoint-close displacement distributions, mean/median/quantiles, positive/
zero/negative shares and favorable/adverse excursion distributions.

- Fixed horizons: 15, **30 primary**, 60 minutes. Each requires the full path
  ending by 16:00. A missing or too-late horizon is null with a reason.
- Endpoint context: assigned-section end and 16:00, with elapsed minutes.
  Zero elapsed time is not applicable for followthrough.
- Reach: favorable/adverse touch of 5, 10 or 20 ES points within the declared
  horizon. Both sides can be reached; no intraminute ordering or fill is inferred.
- Delayed confirmation: use its own reference time/price and complete forward
  horizons. Outcomes from the earlier price cross conditioned on eventual
  confirmation are descriptive future-conditioned paths, never an entry-time
  filter or proof of incremental prediction.
- Retest: first subsequent completed three-minute bar containing the exact
  pivot within 30 minutes after an actual EMA6 crossing, with the full rule in
  the protocol. Report touch incidence, three-minute-resolution time to touch,
  and touch-bar close `hold` / `failed` / `equal`. A touch already observed can
  be reported under a shorter observed window; absence is false only when the
  full declared window is observed, otherwise censored/unknown.

Forward paths begin at event-close time and exclude the signal bar's earlier
high/low. Horizon support varies by event time. Never average truncated paths
with full horizons under the same label or silently discard late-event counts.

## Conditional, temporal and aggregate tables

Precompute curated panels by direction, section, opening state, price-event
EMA6 state, cloud ordering/location/15-minute change and VWAP relationship.
Keep whole-sample baselines beside conditional counts. Avoid an uncontrolled
full Cartesian product of small cells. Continuous values remain in the ledger
for later explicitly identified exploratory variants.

Three declared reference-time combinations retain alignment and crossing as
different objects. `ema_cloud_aligned` requires EMA6 strictly on the event side,
cloud ordering in that direction and both EMA20/50 15-minute changes strictly
in that direction. `ema_vwap_aligned` requires EMA6 on the event side and price
on that side of VWAP. `ema_cloud_vwap_aligned` requires both combinations.
Missing required states/slopes yield unknown. Already-aligned EMA6 can satisfy
these conditions; `actual_ema_cross_at_reference` separately identifies a new
cross. Later confirmation references use their own contemporaneous states.

The primary returned-break comparison starts with initially unconfirmed price
events (opposite/equal/uninitialized EMA6), retaining already-aligned events as
a separate cohort. The return-before-EMA denominator is resolved actual EMA
confirmation or reverse price close before confirmation; unresolved censored
events are not failures. All selected events and censored support remain shown.

Save the whole requested sample, each calendar year and calendar-year/month,
and trailing 20/60/120 eligible observed sessions at the fixed 2026-10-30 cutoff.
Recent windows report requested cutoff, latest usable date, actual observed
start/end and number of sessions. No eligible days in a calendar month means
no sample, not a zero event rate. Full-day labels may explain recurrence but
cannot be used as opening-time predictors.

Section transition panels count observed changes of closing price-side and
cloud ordering from Opening range to New York AM and from New York AM to New
York PM. Their denominator is eligible observed source-state days for that
transition; missing endpoints remain unknown, not an unchanged state.

Every aggregate row identifies metric, cohort, event panel, period, direction,
section, condition, horizon and units. Save numerator, valid denominator,
distinct eligible days, total candidates and excluded/unknown/censored counts.
For daily frequencies include mean, median, 25th/75th/90th percentiles and
zero-event fraction. Conditional event outcomes include event count and day
count; zero displacement is distinct from negative displacement.

Uncertainty uses 2,000 moving-block bootstrap replicates of five chronological
observed sessions, seed 20261031, preserving each resampled day's full panel
before selecting conditions. Flag cells below 30 distinct days. Report
descriptive 95% intervals where defined; a zero denominator or unsupported
estimate is null. Calendar subdivision and many conditional panels are
exploratory, not independent confirmations or multiple-testing-adjusted claims.
Intervals are undefined with five or fewer total observed sessions or fewer
than two contributing days; sparse cells otherwise remain labeled.

## Saved interfaces and presentation

The future run retains audit, daily, section, price/EMA event and summary tables
with stable IDs, schema/units, hashes and metric-source bindings. Raw evidence
may be retained externally with locators/checksums. Narada receives explicit
bounded saved summaries and selected figures; it never recomputes denominators,
combines populations, loads full private ledgers or discovers research files.
Year/month/recent and condition controls select saved rows. Any future generic
chart/interface extension is a separately reviewed presentation change.

An exported number or figure must reconcile to saved evidence with the exact
cohort and horizon. Preserve null/false/zero, censored observations, sparse
support and retrospective availability qualifications in presentation and
downloads. These behavioral statistics do not establish executable profitability.
