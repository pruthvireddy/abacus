# Camarilla reversals with an EMA cloud in ES NQ and GC

Study 20_camarilla_ema_cloud_reversals · Draft protocol 0.3.0 · 2026-10-08.

## Study purpose and review scope

Determine how ES, NQ and GC behave after five-minute Camarilla rejections, whether
the 20/50 EMA cloud identifies better opportunities, and whether a specified
entry and exit policy can capture that behavior after assumed costs.

The user requests an elaborate plan and report proposal before coding. This
version authorizes documentation and a read-only inventory. Historical signal
calculation, research implementation and website changes await review. The
existing Pine indicator remains delivered and privately saved. Its chart-local
ES acceptance observations are exploratory and are not the study's historical
results. Preserve [the earlier protocol](reference/protocol_0.2.0.md) and
[settings](reference/settings_0.2.0.yaml).

The proposed design has two related questions:

1. **Price behavior:** among R3/S3 rejections, how does five-minute EMA alignment
   change average direction-normalized close delta at 15 bars, alongside MAE, MFE,
   favorable-close probability and opportunity coverage?
2. **Executable policy:** how does that alignment change net R per eligible
   instrument-session under next-open entry, a confirmation-candle stop and a
   fixed 3R target?

The first describes conditional associations. The second evaluates a specified
simulation. Neither establishes that the EMA causes the price movement.

## Inputs and observation periods

Use ordinary time bars: one-minute source observations, five-minute signals, and
daily HLC assembled over the prior electronic trading session. One-minute replay
provides finer stop/target ordering; it does not resolve ordering within a minute.
Range XV data cannot reconstruct the exact five-minute path.

The [data inventory](data-inventory.md) verifies retained one-minute ES/NQ/GC
coverage from the June 7, 2010 trading session through September 18, 2026. There is
also an existing five-minute OHLCV publication with approximately 1.14 million
rows per product. It is an adjusted analytical snapshot; use its aggregation and
lineage for cross-checks rather than treating those prices as fills.

| Period by trading-session date | Proposed role | Use |
| --- | --- | --- |
| 2018-01-01 through 2020-12-31 | Development | Fixtures, parity, diagnostics and bounded choices before freezing |
| 2021-01-01 through 2023-12-31 | Validation | Check frozen rules; a rule change consumes this sample |
| 2024-01-01 through 2025-12-31 | Final historical evaluation | Evaluate the locked main protocol once |
| 2026-01-01 through 2026-09-18 | Recent replication | Apply the same rules; report this as a partial year |
| 2010-06-07 through 2017-12-31 | Earlier historical robustness | Apply frozen rules separately, subject to calendar and coverage support |

These are calendar boundaries, not assertions that every date contains usable
data. Fetch earlier observations for warmup without scoring them. Do not choose
new dates after inspecting strategy outcomes.

The main period starts in 2018 because the existing publication audit reports a
sharp improvement in NQ bar completeness: partial nonempty five-minute buckets
fall from 21.082% in 2010–2017 to 0.246% in 2018 onward. ES and GC also improve.
This is a data-based choice. The old history remains useful, with its own coverage
and regime qualifications.

The 2026 ES chart panel was viewed during indicator acceptance. Historical prices
have also been used in other repository studies. Therefore describe 2024–2025 as
held out from this protocol's development, and 2026 as recent replication with
known ES exposure; do not claim all history is previously unseen. Prospective
paper trading remains a separate confirmation step.

Analyze the requested mini ES/NQ and full GC contracts directly. MES, MNQ and MGC
are outside this study; outcomes and fees cannot be presented as measured micro
execution performance.

## Data quality and causal availability

Primary candidate source: [volume_lead_unadjusted_v1](../../catalog/datasets/volume_lead_unadjusted_v1.json),
consumed through Bhishma's public continuous loader and workspace path configuration.
Pin selected manifests, schedules, condition records and partition hashes before
execution. No market dataset is yet in the executed input lock.

Build five-minute first/max/min/last/sum OHLCV over fixed New York :00/:05 buckets,
with explicit open, close and available-at timestamps. Retain source-minute counts,
contract identity and quality flags. Do not fill prices or synthesize zero-volume
minutes. Databento does not print no-trade intervals, so an absent minute is not
automatically corruption. See [its OHLCV contract](https://databento.com/docs/schemas-and-data-formats/ohlcv).
For derived bars, available-at is a modeled completion time, not a measured vendor
delivery timestamp. The next-open simulation assumes the completed signal can be
acted on at that boundary. Record that latency assumption and test a one-minute
entry delay in the policy section before inferring executable performance.

Proposed primary quality rules, to approve before the data audit:

- Require all five published minutes in the confirmation candle, an observed
  preceding approach candle, valid OHLC and a positive ATR.
- Prior-session pivots require at least 99% of the calendar's expected source
  minutes, observed first/last five-minute buckets with all five minutes, no
  unexplained run of more than five missing minutes, and unchanged contract
  identity. Label these as high-coverage observed HLC, not certified settlement
  data. Also report a stricter 100%-coverage subset.
- EMA/ATR history uses actual nonempty bars, including flagged partial buckets.
  Require at least 250 preceding five-minute observations since the contract
  reset, at least 99% source-minute coverage over the seed window, and no
  unexplained absence longer than five minutes. No-trade absences and partial
  bars remain disclosed. A longer unknown gap resets the seed.
- A known scheduled closure is not a missing-data gap. Carry the EMA over such a
  closure without inserting candles or updating it on synthetic prices.
- Source-condition degradation, unresolved calendar cases and retrospective
  removals receive separate reason codes. Vendor condition reports and complete
  future-day audits are sample-selection information, not live morning gates.
- The current day is not required to be complete before accepting a morning
  signal. Track future interruptions as outcome censoring.

A source-bar absence at the intended entry open cancels the observable entry.
Do not use the eventual completeness of that entry candle to pretend the signal
could have been rejected in real time. Later missing/partial path bars censor the
relevant outcome; an entered position remains recorded as entered.

The first approved data audit will tabulate coverage by year, product and time
window, plus the number of valid prior-session HLC and warmup windows. If the
proposed rules leave sparse support, report it and revise the protocol before
viewing outcomes. Do not relax quality thresholds after seeing returns.

## Sessions and contract rolls

The main prior-session period is the electronic session, normally 18:00 on the
preceding calendar day through 17:00 on its trading-session date in New York.
Close is the last observed trade, not an official settlement. Levels remain fixed
through the current session. Use the immediately preceding scheduled trading
session; if its inputs fail the quality gate, exclude the current pivot setup.
Do not reach back to an older valid session to replace a missing prior day.

Before June 28, 2021, ES/NQ had a scheduled 16:15–16:30 New York pause. Before
September 21, 2015, GC closed at 17:15. Certify these historical regimes and annual
holidays in a versioned calendar; do not mutate the existing release calendar.
The old GC observation session assignment needs special care around 17:00–17:15.
Unsupported early history remains excluded with an explicit reason if that
calendar cannot be certified.
[CME equity notice](https://www.cmegroup.com/notices/electronic-trading/2021/06/20210621.html);
[CME COMEX filing](https://www.cmegroup.com/market-regulation/files/15-387.pdf).

Keep pivots, EMAs, ATR, signals and execution prices on the same unadjusted
contract price basis. Restart EMA/ATR state at each selected-contract switch;
exclude the roll session and require valid incoming-contract warmup and a valid
prior session on that same contract before admitting signals. Never calculate
today's level from the outgoing contract's close. This avoids needing a final
back-adjusted history as the primary live signal model.

The retained volume-lead mapping selects contracts at session opens. Verify what
information determined that mapping and when it was available. If historical
mapping choice is retrospective, label selection accordingly and specify a causal
roll-policy sensitivity before making execution claims. If verification fails,
the result remains historical descriptive evidence; a causal executable branch
requires an approved derived input. Do not rebuild existing publications.

An optional adjusted-price parity branch can be compared away from rolls after
proving additive-shift invariance and translating levels to the same price basis.
Never mix an adjusted pivot with an unadjusted candle. Settlement-based TradingView
parity is a separate branch requiring a suitably timed settlement input.
[TradingView explains these daily/intraday futures differences](https://www.tradingview.com/support/solutions/43000521824-pivot-points-standard/).

## Levels and setup families

Let C, H and L be the prior eligible session's observed close, high and low.
Use the exact formulas in the supplied combined indicator:

| Level pair | Formula | Study role |
| --- | --- | --- |
| R2/H2 and S2/L2 | C plus/minus 1.1 × (H−L) / 6 | Secondary shallow reversals |
| R3/H3 and S3/L3 | C plus/minus 1.1 × (H−L) / 4 | Primary reversal family |
| R4/H4 and S4/L4 | C plus/minus 1.1 × (H−L) / 2 | Secondary extreme reversals |

R and H identify the same resistance; S and L identify the same support. Use R/S
in reports consistently. The original short HPotter snippet rounded R2/S2 to
0.183 of range; the supplied larger indicator uses the exact fraction. Freeze the
exact fraction for this study. The coefficients are supported by
[TradingView's Camarilla definition](https://www.tradingview.com/support/solutions/43000521824-pivot-points-standard/).

Do not make R1/S1, R5/S5, all midlines, CPR or weekly pivots part of the primary
grid. R2/S2 adds a nearer comparator and R4/S4 tests deeper reversals, giving a
readable three-pair design. R4/S4 breakouts are a different setup family and appear
only in the bounded extension section.

A completed one-candle rejection must satisfy:

| Direction | Approach | Contact and reclaim | Candle body |
| --- | --- | --- | --- |
| Long at support S | Previous close > S; open ≥ S | Low ≤ S and close > S | Close > open |
| Short at resistance R | Previous close < R; open ≤ R | High ≥ R and close < R | Close < open |

Use zero contact tolerance in the baseline. The previous candle belongs to the
same session and contract. Skip a candle touching both sides of the studied pair.
Opening beyond a level and reclaiming it is a separately tagged delayed/reclaim
family, not quietly admitted into the primary rejection definition.

Use the first technical rejection in each contact episode before applying an
EMA filter. A later full candle strictly on the approach side without touching
the level rearms it. Reset episodes when the session or levels change. An EMA
failure consumes this first-event opportunity in every branch; do not wait for a
later cloud flip in the filtered branch.

Record all contacted levels. If a candle rejects several same-side levels, keep
each level's stand-alone study cohort but do not count them as independent
portfolio entries. A combined level policy, if added, selects the deepest
qualifying level, S4 before S3 before S2 or R4 before R3 before R2, and uses one
shared position per product. No pooled level result is implied by parallel cohorts.

## EMA cloud and other confluences

Compute close-based EMA20 and EMA50 over the observed full electronic-session
five-minute stream. They do not reset at 09:30. Decide the filter at the completed
confirmation close; the next candle's final EMA is unavailable at entry.

| Branch | Long criterion | Short criterion | Priority |
| --- | --- | --- | --- |
| No EMA filter | Rejection alone | Rejection alone | Required baseline |
| Cloud alignment | EMA20 > EMA50 | EMA20 < EMA50 | Primary proposed confluence |
| Price outside cloud | Close > both EMAs | Close < both EMAs | Secondary |
| Alignment and outside cloud | Both preceding long conditions | Both preceding short conditions | Secondary |

Equality fails a strict criterion. Undefined feature values exclude the event
from comparisons needing that feature; they are not classified as false. Do not
silently add the author's daily 21 EMA filter to the cloud.

Retain contemporaneous context rather than optimizing a large Cartesian grid:
EMA separation in ATR, five-bar EMA slopes, distance to cloud, rejection wick/body
ratio, prior-close distance from level, penetration in ATR, prior session range
relative to its trailing 20-session median, opening position relative to R3/S3,
and confirmation volume divided by the previous 20 bars' mean volume.
These are context tags; the primary signal does not require them.

Bounded secondary confluence tests apply one change at a time to R3/S3 alignment:

| Change | Proposed fixed comparison |
| --- | --- |
| EMA slope | Both EMAs rising over five bars for longs, falling for shorts |
| Wick strength | Rejection-side wick at least the nonzero body size |
| Relative volume | Confirmation volume at least 1.0 × mean of the prior 20 bars |
| Approach distance | Previous close at least 0.5 frozen ATR from the level |
| Contact tolerance | One tick instead of zero |
| Duplicate rule | Current Pine's ten-bar shared cooldown instead of contact episodes |

These are exploratory. Do not combine the best-looking pieces after observing the
final sample. No EMA-length optimization is planned; 20/50 is fixed.

VWAP, CPR and prior-day high/low can be descriptive context. A VWAP gate belongs
to a clearly labeled secondary subset because the current feature release has
retrospective whole-day exclusions. A daily 21 EMA comparator requires a causal
daily price/roll history and should not be assumed available just because a
TradingView snapshot exists. News exclusions require a pinned historical release
calendar with original availability timing; no ad hoc exclusion of losing news days.

## Entry timing and holding horizons

Primary next-open entries are permitted at 09:30 ≤ New York time < 11:30, Monday
through Friday, excluding declared holiday/shortened-session sample cases.
This shared window supports cross-product comparison and follows the original
first-two-U.S.-hours idea; it is a study choice, not a claim about GC's cash open.

Accept a rejection only after its five-minute candle closes. Queue the immediately
following scheduled five-minute open on the same contract and session. The first
source minute must start at that open. No chasing a delayed bar and no same-candle
entry. The confirmation candle's extremes do not enter forward MAE/MFE.

Main path horizons: 5, 10, 15, 30 and 50 five-minute bars. The entry candle is bar 1.
These cover 25, 50, 75, 150 and 250 uninterrupted minutes. A terminal current-session
16:00 close is a separate outcome, not another fixed-length horizon. Keep independent
event paths even when they overlap; dependence is handled in uncertainty estimates.
Paths and positions do not cross development, validation or final-evaluation
boundaries. Earlier observations may seed features, but later outcomes cannot
complete a prior split's event.

Cancel only unfinished horizon outcomes at unexpected missing or partial path bars,
contract switches or the declared end boundary. Preserve any shorter completed
outcomes. Record accepted, entered, completed, interrupted and end-of-sample counts
separately; cancellation is not a loss or a zero return.

The earlier Pine table includes 100 bars, or 500 minutes. That cannot complete
inside a 09:30-to-16:00 day. The main report therefore uses 30 bars in its place.
A separately labeled 100-trading-bar extension may cross the electronic-session
close and count only scheduled open-market bars. It requires an explicit overnight
policy, reports elapsed clock time, and censors unknown gaps. Do not silently
compare it with the intraday trade policy.

Session sensitivities are limited to ES/NQ 09:30–16:00 entries and GC 08:20–10:20
entries. Their exits retain the same 16:00 deadline. Report them independently
rather than selecting a best clock window per product.

## Excursion and close statistics

For each entered event, freeze five-minute ATR14 at confirmation close. Use
Wilder's true-range smoothing, a declared seed and the same valid historical
stream as the EMA. Require ATR > 0. Do not recompute the normalization at later
horizons.

With entry reference E, terminal close C_h, direction d = +1 for long and −1 for
short, and frozen A = ATR:

- Signed close delta is d × (C_h − E) / A.
- Long MFE is max(0, highest future high − E) / A; long MAE is
  max(0, E − lowest future low) / A.
- Short MFE is max(0, E − lowest future low) / A; short MAE is
  max(0, highest future high − E) / A.
- Favorable close is signed delta > 0; MFE greater than MAE is a strict comparison.
  Ties remain in the completed denominator.
- Literal close-above-entry and close-on-defended-side-of-pivot are separate
  indicators. A short's favorable close is below entry.

Normalize each event before averaging. MFE/MAE are nonnegative magnitudes; average
delta is signed. Add raw points and ticks in supporting tables and use R in the
trade-policy tables. Never average unnormalized ES, NQ and GC price moves together.

Report mean and median, MFE/MAE 75th and 90th percentiles, favorable-close share,
MFE > MAE share, distinct contributing sessions, counts and uncertainty. Publish
both event-weighted summaries and session-balanced summaries so a highly active
day does not dominate unnoticed.

At one-minute resolution, measure favorable thresholds 0.5, 1 and 2 ATR against
an adverse 1 ATR threshold, before each horizon. Keep neither-hit, missing and
same-minute ambiguous categories. Record the first minute interval containing
MFE/MAE attainment; ties use the earliest interval and zero excursion has no
attainment time. These are interval times, not precise tick timestamps.

A missing path yields an undefined full-horizon statistic. Binary outcomes can
show worst/best bounds over all entered events; unbounded continuous-price means
cannot receive invented worst-case prices. Report their completed-case population,
partial-path lower bounds where useful, and missingness by product, year and branch.

## Trade simulation and exit alternatives

Path analysis has no stop or target. Simulate a separate one-position-per-product,
per-level-branch policy with no pyramiding, trailing stops or partial exits.
Separate cohorts and policy returns because position occupancy changes later
available trades.

Primary stop is one tick beyond the completed confirmation candle's low for a
long or high for a short. The original excerpt's “entry candle” extreme is unknown
at entry; using the confirmation extreme is a declared executable interpretation.
If the next open is already beyond the stop, record an invalid-risk cancellation.

Enter at the observed next-open price plus declared adverse market slippage.
Initial R is absolute entry-fill-to-stop distance. Require positive risk and valid
tick prices. Target is 3R from the entry fill, rounded outward to the instrument
tick. Orders activate after the entry fill and replay one-minute bars in order.
Exit remaining positions at the observed one-minute open at 16:00 New York plus
adverse market slippage; the primary sample excludes known shortened days.
The path section's 16:00 terminal close uses the last minute ending at that time,
so the two reference prices are explicitly different. A gap at the required exit
leaves the policy outcome unresolved rather than receiving a fabricated close.

A stop gap fills at the worse minute open with adverse slippage. A target limit
has no favorable gap improvement. Require one tick of trade-through for assumed
limit fills in the reference simulation, with touch-fill as a sensitivity. When
both barriers occur within the same finest available minute and ordering is
unresolved, retain stop-first and target-first bounds. Do not delete the event or
use a favorable OHLC ordering.

Proposed assumed-cost reference: USD 10 round trip in fees, one adverse tick on
entry and on market/stop exits, no adverse target-limit slippage. Report fee
scenarios USD 5/10/15 and market/stop slippage 0/1/2 ticks as nine explicitly
declared scenarios, keeping the zero-slippage scenario labeled as diagnostic.
These are assumptions, not broker quotes or observed historical spread costs.
Before execution, replace or supplement the reference with the user's verified
contract-specific fees, recording the choice before outcomes.

In the one-minute latency sensitivity, enter at the source-minute open one minute
after the intended five-minute open, provided it is still in the entry window.
Activate barriers only after that fill and exclude all pre-entry extrema. Keep the
same 16:00 time exit. This is a separate trade-policy run; do not splice its fills
into the baseline fixed-horizon path table.

Tick units are ES/NQ 0.25 and GC 0.10; per-contract tick values are ES USD 12.50,
NQ USD 5 and GC USD 10. Report one-contract dollar outcomes and R separately.
[CME ES tick reference](https://www.cmegroup.com/trading/equity-index/eminifaq.html);
[CME NQ contract reference](https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.html);
[CME GC contract reference](https://www.cmegroup.com/education/courses/event-contracts-underlying-markets/product-gold).

Secondary exits retain the same stop and deadline:

- Fixed 2R, compared with the primary 3R target.
- Opposite same-number pivot for level-2/level-3 rejections: S2→R2, R2→S2,
  S3→R3 and R3→S3. The target must be favorable relative to entry.
- Inner level for extreme rejections: S4→S3 and R4→R3.
- Confirmation-to-entry opening gaps and inadequate target space are recorded;
  any minimum target-space gate is a later declared sensitivity.

Measure return to the prior-session close and relevant pivot reach in the path
section as well. A level-hit percentage is not the policy's win rate.

Report net R per eligible session as the primary policy endpoint, assigning zero
to valid no-trade sessions. Identify the common eligibility roster from prior
session HLC and pre-window feature availability. A later unknown gap in the signal
window cannot establish that there were no opportunities: mark that session's
policy summary unresolved rather than zero. Disclose the roster, scorable
denominator and retrospective audit exclusions separately.
Also report mean/median net R per trade, total trades,
target/stop/timeout/unresolved counts, profit factor, net dollars, drawdown and
holding time. Unresolved policy outcomes carry bounds or missing status, never zero.
Do not claim a portfolio return from adding overlapping ES/NQ/GC stand-alone results.

## Comparisons and statistical reliability

The core grid has 3 products × 3 level pairs × 4 EMA branches, with long/short
components and a combined-direction view. It is a declared descriptive grid,
not a search for its best cell.

Six primary contrasts: the alignment-minus-no-filter difference for (a) 15-bar
mean signed delta and (b) 3R net R per eligible session, separately for ES, NQ
and GC, using R3/S3 and both sides. The policy contrast uses the frozen reference
cost assumption and reports alternative costs separately.

For conditional path means, show alignment-passing and alignment-failing outcomes
from the same technical-event ledger, their coverage, and the no-filter aggregate.
This makes the changed population visible. For policy comparisons, pair results
by the same eligible instrument-session roster rather than pretend branches have
identical trade lists.

Propose 10,000 paired bootstrap resamples of contiguous four-New-York-week blocks,
with seed 20261008. Resample the same calendar blocks across instruments and EMA
branches, retaining overlapping paths, zero-trade eligible days and contemporaneous
ES/NQ dependence. Clip blocks to the evaluated split and exclude censored policy
values from completed-case estimates while retaining their reported counts.
Report pointwise 95% intervals. For the six primary contrasts,
also report Bonferroni familywise intervals at 99.1667% marginal coverage; label
all other grid intervals descriptive. Check sensitivity to one- and eight-week
blocks. If support is inadequate for an interval, retain an undefined result.

Flag a descriptive cell as sparse below 100 completed events or 30 contributing
sessions; these are display rules, not guarantees of precision. Report interval
width and effective calendar support. A small favorable percentage with a wide
interval remains inconclusive.

After approval, use development for debugging and bounded choice confirmation.
Freeze the main rules before validation. Any validation-driven revision needs a
new version and leaves only the reserved final period for evaluation. Evaluate
2024–2025 once, then recent 2026 replication without retuning. The old historical
extension applies those same frozen settings. Do not choose exits by maximizing
realized MFE or silently remove extreme losing observations.

Stability panels use year, NY week, long/short, entry time bins 09:30–10:00,
10:00–10:30, 10:30–11:00 and 11:00–11:30, and prior-known range/volatility tertiles.
Learn tertile boundaries only on development observations; do not classify using
that day's eventual range or future volatility.

## Bounded extensions and controls

After the core definitions are frozen, retain these as explicitly exploratory:

1. The one-change confluence and session sensitivities above.
2. Strict 100%-coverage prior-session/seed subset, longer 500-bar warmup, and the
   current Pine episode/cooldown convention for comparability.
3. R4/S4 continuation: previous close on the inner side, completed close beyond
   the boundary, directional body and cloud alignment in the breakout direction;
   next-open entry and the same stop/3R/deadline policy. Keep it separate from fades.
4. Nonstandard symmetric prior-close/range levels at coefficients 0.225 and 0.325,
   bracketing the R3/S3 coefficient 0.275, as location controls. Apply identical
   rules to test whether the exact Camarilla placement differs from nearby levels;
   do not search for a new optimum.
5. A daily-21 or settlement-parity branch only after its causal inputs are approved.
   VWAP confluence remains restricted to its disclosed eligible subset.

A later combined policy or additional EMA lengths needs its own protocol change.
Retain unfavorable and null extension results. More tests do not create more
independent evidence, particularly for correlated ES and NQ.

## Report and Abacus publication

The [report proposal](report-proposal.md) defines the reading order, horizon/weekly
tables, additional statistics, figures, selected downloads and publication scope.
The report separates observed path behavior, assumed-cost policy outcomes, and
prospective execution evidence.

Sahadeva will produce the full saved report and selected Narada contract-1.1
content from the same frozen numerical tables before sealing the analytical run.
Narada will validate and display explicit saved content; it will not calculate
statistics or expose arbitrary private artifacts. Keep large event evidence in
retained storage with checksums and locators.

Use a unique staged work directory and seal only verified outputs into a new run.
Save exact protocol/config, input hashes, calendar/roll rules, available-at
assumptions, code revision plus dirty-source snapshot, environment lock, exact
commands, exclusions, checks, metrics, tables, figures, report, advice and artifact
hashes. Record metric/table IDs in conclusions, including negative findings.

After approved execution, create an immutable report publication and an authored
study entry at the proposed stable slug camarilla-ema-reversals. Preserve prior
publications. Validate app verify/test/lint/build and static preview, then follow
the verified Narada release workflow for hosted publication. Website deployment
belongs to that later reviewed delivery.

## Proposed acceptance gates

| Gate | Evidence required before proceeding |
| --- | --- |
| Review the proposal | Confirm level grid, cloud branches, session, period allocation, quality rules and management choices |
| Audit approved inputs | Partition hashes, calendar/roll availability, coverage roster and known exposure; no return-based exclusions |
| Implement and verify | Numerical fixtures, prefix invariance, availability, missing/partial paths, roll/DST cases and one-minute ambiguity bounds |
| Freeze main evaluation | Versioned definitions, final dates, cost scenario, input lock, analysis/report IDs and documented development changes |
| Interpret findings | Coverage and uncertainty alongside effects; no unsupported edge if plausible costs or ambiguity overturn it |
| Seal and publish | Complete reproducible run, source-value transfer checks, explicit selected public bundle and hosted verification |
| Confirm prospectively | Log real opportunities/fills under fixed rules before treating simulated returns as live execution evidence |

No empirical study engine, historical signal run, sealed analytical result or
website publication is created by this proposal. The next coding stage begins
after the user reviews this plan.
