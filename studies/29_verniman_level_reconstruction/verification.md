# Phase 1 verification

Study `29_verniman_level_reconstruction` · 2026-10-30 · implementation checks,
not a market-data research run or a recovered Verniman algorithm.

The [script](indicator/verniman_levels.pine), [specification](specification.md),
[plan](plan.md) and [changes](changes.md) describe the candidate baseline.
Fresh evidence is staged under
`work/29_verniman_level_reconstruction/phase1_20261030/`. No run is sealed.

## Verification layers

| Layer | Status |
|---|---|
| Source review | Supplied attachment read; exact baseline retained with SHA-256 `aaa95a7e639b027637c6eb6ab0c9e5c8fa096f16b069f5e1a9a418f65c08094b` |
| Independent synthetic specification model | 36 tests passed in the locked environment without sync; covers arithmetic, DST, rollover, gaps, warm-up, resets and snapshot timing |
| Native Pine v6 compilation | Passed in the logged-in TradingView in-app browser; saved private revision 3 attached to the separate study layout |
| Actual browser replay | Final revision, October 1, 2 and 5: 19/19 references, unchanged after advancing into RTH, equal after restarting at cutoff |
| Repository checks | Study suite, registry/tooling, documentation, metadata and navigation passed; default gate stopped at unrelated configured-input errors, detailed below |

The Python model is an independent specification oracle, not a Pine interpreter.
Its passing tests do not establish TradingView compilation or replay behavior.

## Browser configuration

- Separate layout: [Verniman Levels Phase 1](https://www.tradingview.com/chart/mtK3TbRP/).
- Contract/feed: `CME_MINI:ESZ2026`, E-mini S&P 500 Futures (Dec 2026), CME GLOBEX.
- Standard candles, 5-minute bars, electronic trading hours. Actual contract,
  so continuous-series back adjustment does not apply; original chart had B-ADJ off.
- Chart clock UTC-4 on the allowed dates; all indicator clocks use the IANA New
  York timezone independently. 16-tick rows, 70% VA; 09:25 NY cutoff.
- All families on, optional live lines off, developing RTH on. Expanded candidate
  table enabled for evidence; compact status is the script default.
- Previous-week and current-week readiness observed in Replay; full history
  coverage is assessed by the script, not by an independent provider audit.

## Native replay observations

The staged `browser-verification.json` records the script hash, settings,
source dates and values. `frozen-candidates.csv` transcribes all 57 candidate
prices from browser screenshots; it is an observation record, not a numerical
research result. Each date has cutoff, advanced and restart screenshots.
All 19 frozen prices and displayed reference dates were compared visually.
Verified Pine SHA-256:
`5bbc40075cefb19feacb1a676c67ee5770cb5ef7023b9dd76781f2927a243f73`.
The final revision adds the missing-terminal-RTH display gate and effective
coverage/live-source status; all three replay dates were checked again after
that change. Earlier revision-2 observations are retained separately in the stage.

| Trading date | Full/RTH source date | Previous-week start | Cutoff | Advance / restart |
|---|---|---|---|---|
| 2026-10-01 | 2026-09-30 | 2026-09-20 18:00 NY | 19/19, 09:20–09:25 bar | Equal / equal |
| 2026-10-02 | 2026-10-01 | 2026-09-20 18:00 NY | 19/19, 09:20–09:25 bar | Equal / equal |
| 2026-10-05 | 2026-10-02 | 2026-09-27 18:00 NY | 19/19, 09:20–09:25 bar | Equal / equal |

In this account, selecting 09:25 in Replay initially left the last bar
unconfirmed. One Forward step exposed its confirmed closing update and produced
the snapshot. Use the table's recorded 09:20–09:25 interval as the authoritative
included boundary. Eight further 5-minute steps advanced into RTH; frozen prices
and source dates did not change while live references could change. Each restart
used Select date 09:25 and the same one-step completion. No date substitution
was needed and no hidden-test date was navigated to.

## Current official documentation reviewed

Reviewed on 2026-10-30: TradingView's [bar-state semantics](https://www.tradingview.com/pine-script-docs/concepts/bar-states/),
[session/bar alignment](https://www.tradingview.com/pine-script-docs/concepts/sessions/),
[IANA timezone behavior](https://www.tradingview.com/pine-script-docs/concepts/time/)
and [Replay data availability](https://www.tradingview.com/support/solutions/43000692816-how-much-data-is-available-for-bar-replay/).
These support using confirmed bars, aligned session boundaries and a New York
IANA clock. Account-specific script execution and history were checked in the
actual browser, independently of plan-dependent documentation.

## Holdout and incidental exposure log

No protected intake, observation contents, daily-level release rows or dated
target charts were opened. No hidden-test date was selected in Replay.
When Pine Editor first opened, TradingView automatically restored an unrelated
existing script, `Verns Pivots - ESZ2026`. Its automatically displayed excerpt
included its title, explanatory header, source-date bounds September 15 through
October 20, 2026, and input declarations. No target prices or daily rows were
visible/read. The editor was switched to a new blank indicator without scrolling
or inspecting that source. This incidental metadata exposure is recorded; no
October 21–27 target-answer exposure is known. Existing layout names were also
visible in the layout menu; their contents were not opened.

## Local commands and limits

The first direct locked test command could not read the default UV cache. The
same command passed using the writable cache override, without installing or
synchronizing dependencies:

```sh
UV_CACHE_DIR=/private/tmp/abacus-study29-uv-cache ./scripts/uv run --locked --no-sync python -m unittest discover -s studies/29_verniman_level_reconstruction/tests -v
```

One automatic approval review initially rejected the private TradingView save
as unauthorized disclosure. The attached user request was checked: lines
201–207 explicitly authorize Pine editing and saving the derivative privately
to this TradingView account. Retrying with that established authorization
succeeded. The script was never publicly published.

Final registered execution also passed using the same cache override:

```sh
UV_CACHE_DIR=/private/tmp/abacus-study29-uv-cache ./scripts/check-workspace --check study-29 --report work/29_verniman_level_reconstruction/phase1_20261030/study29-checks.json
```

Other recorded checks: 34 registry tests passed; tooling 228 tests passed with
zero skips; documentation checked 102 guides with zero errors; metadata validated
29 studies, 10 strategy cards and 3 evidence references. Regenerated navigation
is current. These checks cover metadata/tooling, not scientific validity.

The required default six-step gate ran documentation successfully, then stopped
at Bhishma: 983 discovered / 976 run, 2 errors, zero skips. The missing input was
`data/raw/databento/GLBX.MDP3/symbology/continuous/volume-rank-0/2010-06-06_2026-09-20.json`;
another configured-input check had no point-in-time ES roll-1 definition pair
within its 10-day window. These unrelated inputs were not repaired or rebuilt.
Sahadeva, legacy-01, legacy-02 and vwap-doctor were unexecuted after fail-fast.
The staged default/tooling/metadata/navigation JSON reports and logs retain the
commands and exact outcomes. A full workspace pass is **not** claimed.

## Remaining boundaries

Native browser checks apply to the inspected ESZ2026 5-minute configuration.
1-minute charts and MES/NQ/MNQ are supported by the declared implementation but
have not yet been verified in the browser. Holidays, early closes and incomplete
history are withheld by strict coverage, not interpreted through an exchange
calendar. Feed changes or changed history/settings can change a recomputed map.
The VP remains uniform chart-bar volume allocation, not exact volume at price.
Native built-in volume-profile chart tools are not a dependency and have not
been tested in Replay. No profitability, HVE/PBT/LIS reconstruction or pivot/
target selection has been tested. Next: a separately authorized training-example
study to define HVN/HVE candidates and PBT constructions.
