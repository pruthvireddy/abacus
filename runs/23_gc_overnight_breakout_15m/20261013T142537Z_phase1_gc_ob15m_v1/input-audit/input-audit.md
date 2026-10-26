# Phase 1 frozen input audit

The October 13, 2026 approval authorizes the fixed baseline. This audit was
completed before any strategy outcomes were calculated. It creates a study
consumer view of existing immutable inputs; no dataset was rebuilt or published.
The [market lock](phase1-inputs.lock.json) is separate from the retained Pine
[source lock](../../../../studies/23_gc_overnight_breakout_15m/inputs.lock.json).

The selected dataset is `volume_lead_unadjusted_v1`, algorithm version `1.0.0`,
methodology `volume_lead_v1`, manifest SHA-256 `00757f5fc8278e75744d7adfaddc688be588d619d82b1dc1811aa60f21b7e5d4`. Bhishma's explicitly
pinned public `open_continuous_dataset` loader verified the published GC bytes.
Selected UTC-year partitions 2017–2026 are individually pinned; 2017 is supporting
coverage for the requested fixed-UTC+3 broker start, with no observed selected
2017 minute. Published instrument master and roll schedule Parquet/CSV bytes are
pinned and independently reconciled to every selected minute.

Selected history starts at the first observed minute **2018-01-01 23:00 UTC**
(2018-01-02 02:00 broker time) and ends **2026-09-18 20:59 UTC**, with modeled
completion at 21:00 UTC. There are 3,046,589 observed minutes across 45 composite
contract identities. The first loaded broker day, January 2, 2018, is excluded.
The 2026 year is partial; retained coverage does not extend through October 13.

| Broker year | Causally eligible days | Valid complete ranges | Calendar dates covered |
| --- | ---: | ---: | --- |
| 2018 | 93 | 103 | 2018-01-01–2018-12-31 |
| 2019 | 117 | 127 | 2019-01-01–2019-12-31 |
| 2020 | 169 | 180 | 2020-01-01–2020-12-31 |
| 2021 | 102 | 114 | 2021-01-01–2021-12-31 |
| 2022 | 81 | 96 | 2022-01-01–2022-12-31 |
| 2023 | 57 | 69 | 2023-01-01–2023-12-31 |
| 2024 | 89 | 104 | 2024-01-01–2024-12-31 |
| 2025 | 178 | 195 | 2025-01-01–2025-12-31 |
| 2026 | 108 | 118 | 2026-01-01–2026-09-18 |

Valid ranges are distinct from eligible days: a complete range can still fall on
a weekend with no trading window or the first loaded day. The full roster retains
every broker calendar date. Eligibility is frozen using the range prefix known
at 07:00 and the conservative known calendar qualification. Later missing trading
minutes are saved separately and never remove an eligible day retrospectively.
The conservative complete-minute rule reduces support substantially: no-trade
minutes and unproven delivery gaps are both treated as unavailable evidence.

`ts_event` is the inclusive one-minute aggregation start, based on trade-message
receipt timing; it is not an observed tick fill time. [Databento's OHLCV schema](https://databento.com/docs/schemas-and-data-formats/ohlcv)
confirms this convention, the integer `1e-9` encoding, and omission of intervals
without trades. One-minute `available_at` is modeled as open plus one minute;
15-minute `available_at` is the exclusive completed-candle close. Actual vendor
publication/receipt latency and point-in-time receipt of leader mappings are
unavailable, so modeled close availability is qualified.

Quarter-hours in UTC and fixed GMT+3 align. Every observed 15-minute aggregation
was independently reconciled with integer NumPy first/open, max/high, min/low,
last/close, summed volume and minute count reductions: **205,578 observed candles,
1,233,468 compared cells, zero mismatches and zero tolerance**. Missing or partial
nominal slots retain observed prices as unusable; no source minute is filled.
Source OHLC, tick alignment, unique timestamps, mapping bounds and master/roll
identity passed for every selected minute, with zero failures.

The normal retained GC calendar is Sunday 18:00 through Friday 17:00 New York,
with daily [17:00,18:00) maintenance and no weekend trading. [CME filing 15-387](https://www.cmegroup.com/market-regulation/files/15-387.pdf)
establishes the 17:00 New York close from September 21, 2015, covering this study.
These scheduled closures fall inside the broker range: ordinary weekdays have
360 expected range minutes; Monday has 300 in winter and 360 in summer. DST
changes the New York offset, never the fixed broker decision time. A winter range
can span the preceding session's last hour and the next contract's opening;
mixed-contract ranges are excluded at the decision. Live observations must be
censored at a later contract transition before comparing the incoming price.

Annual historical holiday/early-close certification is unavailable. The pinned
calendar contract and holiday generator conservatively reject nominal sessions
for named holiday/early-close candidates, including mourning candidates. This is
a qualification exclusion, **not an assertion that every candidate was a full
exchange closure**. Their nominal missing slots remain separately labeled.
The audit records 41,537 missing qualified normal-schedule minutes, 51,398 missing
uncertified holiday nominal minutes, and 24 observed minutes outside the normal
schedule. Those 24 prints remain in the input audit with `scheduled=false` and
are not silently treated as regular trading evidence.

[CME COMEX rulebook Chapter 113](https://www.cmegroup.com/rulebook/COMEX/1a/113.pdf)
specifies 100 troy ounces and a $0.10-per-ounce minimum price change: $100 per
point, $10 per tick and one indivisible listed GC contract. Whole-contract minimum
and quantity step are 1. Every selected master tick is exact 0.1. The master
`contract_multiplier` value 2147483647 is an unavailable sentinel; it is never
used as a dollar multiplier. Verified CME economics supply 100 instead.

## Prerequisite recheck

Both previously recorded raw reconstruction failures persist. Read-only locked
commands without environment synchronization ran October 13:

- `test_continuous_phase1.py`: three tests ran successfully, with a mapping-class
  setup error because the declared volume-rank-zero mapping JSON is absent.
- `test_continuous_phase2.py`: eleven tests ran successfully, with a real-roll
  class setup error because ES roll 1 has no point-in-time definition pair in its
  ten-day search window.

The tests themselves report `FAILED (errors=1)` for each suite; no suite pass is
claimed. All seven raw-source locators declared in the original manifest are
absent at their recorded paths. These existence checks do not certify bytes or
prove that no alternate retained locator exists. Selected published GC input
bytes and the authoritative published roll/master bytes were nevertheless
verified. Original raw reconstruction, native TradingView replay, tick ordering,
annual holiday certification and off-device backup remain unverified.

Eight synthetic input tests passed: integer aggregation and availability,
missing-source slots, causal later-missing handling, missing range decisions,
normal closure/DST behavior, winter range rolls, explicit holiday qualification,
and first-loaded-day exclusion. Actual output and prerequisite logs are retained
under the run stage's `input-audit/`; no historical outcome was queried for this
audit. Later-year Phase 1 results create prior exposure for Phase 2.
