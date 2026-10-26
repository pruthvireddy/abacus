# Historical futures data for the Camarilla study

Inventory date: 2026-10-08. This is a read-only input inventory for the proposed
ES, NQ and GC study. Bar counts describe retained datasets; they are not signal
counts or performance findings.

## Available history

The retained Databento GLBX.MDP3 publications cover all three products from
2010-06-06 at 22:00 UTC through 2026-09-18 at 20:59 UTC. The opening timestamp is
Sunday evening in New York, belonging to the June 7 trading session. The last
minute opens at 16:59 New York and completes at 17:00. September 18 is the
available end date; there are no published intraday observations through October 8
in these releases.

| Product | Unadjusted one-minute rows | Existing five-minute rows | Five-minute session labels | Complete five-minute bars | Partial five-minute bars |
| --- | ---: | ---: | ---: | ---: | ---: |
| ES | 5,694,142 | 1,145,369 | 4,195 | 1,120,171 | 25,198 |
| NQ | 5,520,074 | 1,143,458 | 4,195 | 1,030,514 | 112,944 |
| GC | 5,651,836 | 1,149,486 | 4,191 | 1,093,135 | 56,351 |

The five-minute counts come from the
[OHLCV delivery manifest](../../catalog/datasets/tv_indicators__dridr_ohlcv_5m__v1.json).
The delivery contains OHLCV and lineage, despite its DR/IDR name; it contains no
DR/IDR signals or outcomes. Its prices use a final additive back-adjustment
snapshot. The [quality report](../../reports/quality/tv_indicators__dridr_ohlcv_5m__v1.md)
documents aggregation, completeness and limitations.

## Why the main period begins in 2018

The published audit separates nonempty buckets containing all five source minutes
from buckets with fewer than five. A partial bucket is an observation-quality flag,
not proof of lost data: Databento omits intervals with no trades.

| Product | 2010–2017 observed five-minute bars | Partial share | 2018–2026 observed five-minute bars | Partial share |
| --- | ---: | ---: | ---: | ---: |
| ES | 530,324 | 4.295% | 615,045 | 0.393% |
| NQ | 528,564 | 21.082% | 614,894 | 0.246% |
| GC | 534,597 | 7.897% | 614,889 | 2.299% |

These shares are arithmetic summaries of the manifest's product/year quality
records across the entire electronic session. They do not establish morning-window
coverage or the number of eligible events. The proposed main period is calendar
2018 through September 18, 2026, with 2010–2017 reported separately. Exact eligible
session and event counts require the approved data audit.

## Proposed input roles

| Input | Role | Material limitation |
| --- | --- | --- |
| [Unadjusted one-minute continuous release](../../catalog/datasets/volume_lead_unadjusted_v1.json) | Primary observed prices; build five-minute signals and daily HLC; replay trade barriers at one minute | Contract switches and historical session changes require explicit handling; vendor mapping availability must be checked |
| [Existing five-minute OHLCV release](../../catalog/datasets/tv_indicators__dridr_ohlcv_5m__v1.json) | Aggregation and lineage cross-check; completeness flags and coverage inventory | Final adjusted prices are synthetic and are not direct fills or a certified live signal history |
| [Back-adjusted one-minute release](../../catalog/datasets/volume_lead_back_adjusted_v1.json) | Optional analytical parity and additive-shift checks | Uses later roll information; pin the snapshot and do not use it for execution prices |
| [Session VWAP release](../../catalog/datasets/session_anchored_vwap__1.0.0.release.json) | Secondary VWAP confluence on its declared subset | Retrospective whole-day eligibility leaves only 1,037 ES, 1,177 NQ and 825 GC sessions over its own coverage |
| [TradingView daily context](../../catalog/datasets/tradingview_daily_context__1.0.0.json) | Optional prior-available daily regime context and chart parity checks | External continuous-contract and daily-close conventions differ; do not substitute it silently for the primary intraday-built pivots |
| [GC deviation bands](../../catalog/datasets/gc_ema_deviation_bands__1.0.0.json) | Retained related research input | GC-only specialized bands are not the requested five-minute 20/50 cloud |
| [Range XV exports](../../data/range_xv/README.md) | Optional later visual or order-flow context | Price-range bars cannot reconstruct an exact time-bar OHLC path; their inferred clock is a separate input convention |

The primary study will not inherit the VWAP release's day selection. Requiring a
complete current day would also use information unavailable at a morning signal.
Use the primary source independently and disclose any later outcome censoring.

## Session and price conventions

The continuous release labels sessions using a recurring New York 18:00–17:00
boundary, while retaining historical observations outside that nominal schedule.
The existing [calendar](../../catalog/calendars/cme_fixed_clock_session_v1.json)
recognizes two historical changes: GC's close moved from 17:15 to 17:00 New York
for trade date September 21, 2015; the ES/NQ 16:15–16:30 pause ended for trade date
June 28, 2021. Its unsupported flags belong to the earlier VWAP specification,
including its two-minute alignment requirement. They do not automatically exclude
those years from a five-minute study.

The earlier GC interval can have misleading inherited session labels for
17:00–17:15 observations. A study using that interval must certify a historical
calendar and reassign observation sessions in a derived layer. Keep the source
release unchanged. Annual holidays and early closes also need explicit support.

The current source contains no official settlement input selected for this study.
Primary pivots therefore use observed prior electronic-session HLC with a
last-trade close. TradingView daily-based futures pivots can use settlement closes,
so agreement with a chart cannot be presumed.

## Inventory verification and identities

For each of the three main releases, all 51 product/year Parquet partitions are
present. File sizes match the manifest and Parquet footer row totals reconcile with
the published counts. This inspection read no strategy outcomes and did not
recompute data releases. Full partition SHA-256 verification, source-condition
checks and the study's calendar/availability audit remain execution prerequisites.

| Manifest | Observed SHA-256 |
| --- | --- |
| volume_lead_unadjusted_v1.json | 00757f5fc8278e75744d7adfaddc688be588d619d82b1dc1811aa60f21b7e5d4 |
| volume_lead_back_adjusted_v1.json | 5500ac1e472c48b0f31b11c6586354dc700e4ba2ef526ebef5fa05582b228ce8 |
| tv_indicators__dridr_ohlcv_5m__v1.json | d5044c605c4b13249b0f51118fccbd4d86b6811b17821f339cdd25ffb578c5d7 |
| tradingview_daily_context__1.0.0.json | b7395d6ec2a3263e6f17b2ed95d22ea235d543a01e5b7f850eff81604ba6ce8f |

These are candidate identities observed during planning, not an executed input
lock. Resolve storage through the workspace path configuration and use Bhishma's
public loader. Pin selected manifests, schedules, conditions and consumed
partitions before analysis.

## Primary references

- [Databento OHLCV conventions](https://databento.com/docs/schemas-and-data-formats/ohlcv)
  explain bar-open timestamps, omitted no-trade intervals and aggregation from one
  minute to five minutes.
- [CME 2021 equity pause removal](https://www.cmegroup.com/notices/electronic-trading/2021/06/20210621.html)
  establishes the equity-session regime boundary.
- [CME COMEX closing-time change](https://www.cmegroup.com/market-regulation/files/15-387.pdf)
  establishes the September 2015 metals boundary.
- [TradingView pivot inputs](https://www.tradingview.com/support/solutions/43000521824-pivot-points-standard/)
  explain daily-based futures settlement and session differences.
