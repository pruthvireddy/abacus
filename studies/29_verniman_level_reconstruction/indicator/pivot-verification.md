# Verniman Pivot Levels — implementation verification

New user-authorized experimental scope, completed 2026-10-30 New York.
The Phase 1/Phase 2 records, baseline and existing Verniman Levels source remain unchanged.
This verifies implementation and timing, not recovery of Verniman's proprietary method.

## Delivered source and account state

- [Pine v6 source](verniman_pivot_levels.pine), SHA-256 `86fd73f7791b875ef8078d3035b2b8319bc1732c0c81273ed1c09289020b9b68`.
- Private TradingView indicator: **Verniman Pivot Levels**, saved revision 2.
- New layout: [Verniman Pivot Levels — Verification](https://www.tradingview.com/chart/isTi4G1i/).
- Final account reload retained layout name, ESZ2026, five-minute standard candles,
  electronic sessions, indicator attachment and every input setting. Copying the
  saved editor source after reload produced an exact byte match to the local file.
- All TradingView interaction used the authenticated in-app browser. The original
  layout and saved scripts were preserved; the new script was never published.
- Evidence: `work/29_verniman_level_reconstruction/20261030T235900Z_pivot_v1/`
  relative to the Abacus root. `browser-verification.json`, `frozen-selections.csv`,
  source readbacks, settings, screenshots, checks and checksums are retained there.

## Frozen contract and settings

The [specification](pivot-specification.md) was retained and hash-frozen before
market results. The additive [numerical correction](numerical-implementation-addendum.md)
records mathematically equivalent raw-mass threshold arithmetic, chosen from a
synthetic rounding counterexample before any successful native pivot observation.
N1 output also retains normalized masses. No date received different parameters.
Later edits only clarified diagnostic text and moved the table to expose line starts.

Verified actual contract: **CME_MINI:ESZ2026**, December 2026 E-mini S&P 500,
CME GLOBEX; minimum tick 0.25, standard five-minute candles, electronic sessions,
unadjusted dated prices. Row 16 ticks =4 points, zero grid, VA 70%, max 6,000 rows,
no smoothing; N1/E1 constants as frozen. Keep 30 daily lines; endpoint 16:00 NY;
strict suppression off, uncertainty shading off, acceptance and table on.

## Native results

| Date | YVAH / YPOC / YVAL | ONPOC / P | Pivot | Reason | RTH advance / restart |
|---|---|---|---|---|---|
| Oct 1 | 7776 / 7772 / 7752 | 7740 / 7729 | 7752 | Prior-value reclaim boundary | Equal / equal |
| Oct 2 | 7724 / 7688 / 7680 | 7760 / 7791.75 | 7788 | Hold higher auction | Equal / equal |
| Oct 5 | 7788 / 7772 / 7764 | 7768 / 7774 | 7764 | Overnight value shifted lower | Equal / equal |

For all three dates: prior RTH 78/78, overnight 185/185, tolerance 2 points,
status ready, no fallback, no capped or overlapping regions. RTH source dates
were Sep 30, Oct 1 and Oct 2 respectively. Before terminal confirmation, today's
pivot was na and no line appeared. Replay Select date 09:25 initially leaves the
terminal bar unconfirmed; one Forward step confirms 09:20–09:25. All snapshots
record that exact last included interval and09:25 cutoff, excluding 09:25–09:30.
The timestamp-based line starts 09:25; screenshots retain the visible start/label.

Eight more five-minute steps advanced into RTH without changing any frozen
price, reason, origin, fallback, confluence, cutoff or coverage. Each date was
then restarted at 09:25 and confirmed again; every displayed frozen field matched.
Acceptance alone could change: bearish on Oct 1, unresolved on Oct 2, bullish on Oct 5.
An additional full-page-reload Oct 5 reconstruction also matched.

Oct 2 selected **ON 2026-10-02 N1@1948 lower E1**, coordinate 7788 with uncertainty
[7786,7790]; it did not select the region peak. Oct 5 selected **RTH 2026-10-02 YVAL**
at 7764 and separately reported **ON 2026-10-05 N1@1942 lower E1** at 7764 as confluence.
Both identities and prices remain unchanged. Oct 1 had no nearby qualified E1.

## Local checks and failures retained

- Focused owning study gate: **95 passed, zero skips** (59 new pivot tests and
  36 unchanged Phase 1 tests), using the existing locked environment without sync.
- Independent optimization comparisons: 87,380 synthetic profiles; 174,760 directional
  minima checks; 4,776,848 region-growth intervals. Final-source hash bound in result.
- Documentation checker: 110 active guides, zero errors. New delivery links checked separately.
- No package/configuration/navigation changes were made, so no repository-wide
  numerical rerun or index regeneration was needed.
- First native compile failed 62:9 because the overflow flag and volume addition
  returned incompatible types. Explicit method return fixed it. Subsequent final
  source compiled and ran without compiler or runtime errors; failed screenshot retained.

The translated models and independent source review do not execute Pine. Native
compilation, Replay and save/reload checks above supply separate evidence.
No profitability study, public publication or sealed run
was created. The evidence remains in the requested work stage. Native CSV exports retain the
loaded input bars for all three dates. A separate translated calculation and the
native exported diagnostic series both match every screenshot input and pivot;
full model histograms and node ledgers are retained in `retained-replay-comparison.json`.
This is a same-feed calculation check, not independent provider validation.

## Limits and unfinished scope

All requested implementation, three-date Replay, private save, layout save and
account persistence actions completed. No unavailable input or fallback occurred
on these dates. Synthetic tests cover fallback and missing-data branches; these
branches were not forced through native market Replay by tuning dates/settings.

The profiles estimate volume from candles rather than observing trades at price.
Only the recorded ESZ2026 five-minute configuration was tested natively. No live
market cutoff was observed. Replay sets Pine's realtime flag during stepping;
the table therefore says live/Replay indistinguishable for observed confirmations
and separately labels historical reconstruction. External evidence identifies
these executions as Replay.

Coverage requires complete observed sessions. An observed shortened/partial RTH
invalidates it; no exchange holiday calendar is implemented, so a wholly absent
session cannot be distinguished from a closed holiday. The prior actual RTH date
is always disclosed. Identical retained data/settings/history reproduces the
selection, while feed corrections or changes can alter historical reconstruction.
Replay itself resets after a page reload; the saved source, settings and attachment
persist, and the authorized Oct 5 example was restored afterward.

No additional dated Verniman target sources, development answers or hidden-test
answers were inspected. The page reload restored the ordinary current chart
briefly for account-state checks; no additional source/target evidence was used.
