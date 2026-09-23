# Session-anchored VWAP 1.0.0 quality report

Status: **published and validated**.

The release applies whole-product-day eligibility retrospectively to the pinned one-minute source, then independently builds 2-minute and 5-minute bars. Eligibility is a research sample-selection rule known after the session ends; it is not present among predictive feature columns.

## Published coverage

| Interval | Product | Eligible days | Rows | UTC coverage |
|---|---|---:|---:|---|
| 2m | ES | 1,037 | 715,530 | 2021-06-27T22:00:00+00:00 – 2026-09-18T21:00:00+00:00 |
| 2m | NQ | 1,177 | 812,130 | 2021-06-27T22:00:00+00:00 – 2026-09-18T21:00:00+00:00 |
| 2m | GC | 825 | 569,250 | 2016-02-10T23:00:00+00:00 – 2026-09-18T21:00:00+00:00 |
| 5m | ES | 1,037 | 286,212 | 2021-06-27T22:00:00+00:00 – 2026-09-18T21:00:00+00:00 |
| 5m | NQ | 1,177 | 324,852 | 2021-06-27T22:00:00+00:00 – 2026-09-18T21:00:00+00:00 |
| 5m | GC | 825 | 227,700 | 2016-02-10T23:00:00+00:00 – 2026-09-18T21:00:00+00:00 |

## Eligibility

| Product | Candidate days | Included | Excluded (unique days) |
|---|---:|---:|---:|
| ES | 4,250 | 1,037 | 3,213 |
| NQ | 4,250 | 1,177 | 3,073 |
| GC | 4,250 | 825 | 3,425 |

Overlapping exclusion reason counts (a day can contribute to more than one reason):

| Reason | Product | Count |
|---|---|---:|
| `unsupported_historical_schedule_regime` | ES | 2,885 |
| `missing_expected_published_minute` | ES | 2,465 |
| `source_rows_outside_expected_schedule` | ES | 1,302 |
| `exchange_holiday_or_shortened_session` | ES | 185 |
| `no_source_rows` | ES | 56 |
| `source_condition_degraded` | ES | 39 |
| `unsupported_historical_schedule_regime` | NQ | 2,885 |
| `missing_expected_published_minute` | NQ | 2,424 |
| `source_rows_outside_expected_schedule` | NQ | 1,265 |
| `exchange_holiday_or_shortened_session` | NQ | 185 |
| `no_source_rows` | NQ | 56 |
| `source_condition_degraded` | NQ | 39 |
| `missing_expected_published_minute` | GC | 3,398 |
| `unsupported_historical_schedule_regime` | GC | 1,380 |
| `exchange_holiday_or_shortened_session` | GC | 176 |
| `no_source_rows` | GC | 60 |
| `source_condition_degraded` | GC | 39 |
| `source_rows_outside_expected_schedule` | GC | 29 |

Per-product/year overlapping reason counts are machine-readable in both manifests. The audit has one row for every candidate weekday and records expected/observed counts, missing/duplicate/invalid counts, observed bounds, all reasons, source condition, and calendar provenance.

## Calculation and causality

OHLCV bars are independently aggregated from one-minute data using fixed New York-clock `[start,end)` buckets. `ts_event` is the bar open; `bar_close_ts` and `available_at` are the exclusive end. VWAP uses each completed output bar's HLC3 and volume. Sigma is the weighted population standard deviation computed by stable Welford updates. Anchors accumulate independently to the same Globex close.

Close-based crossings use contemporaneous levels. Equality stays on the prior side for exits/crosses and counts as re-entry (`<= upper` from above; `>= lower` from below). Two same-anchor consecutive valid bars are required; band events also require positive sigma on both bars.

## Calendar coverage

CME notices establish the GC 17:15-to-17:00 close change effective 2015-09-21 and elimination of the ES/NQ 16:15–16:30 ET pause effective 2021-06-28. Earlier GC days do not match the fixed 17:00 specification; earlier ES/NQ days cannot form complete aligned 2-minute bars around the scheduled pause. They are explicitly audited and excluded rather than relabeled.

## Validation

The test suite covers unequal-volume hand fixtures, all anchors, zero volume/sigma, event equality/reset rules, aggregation and volume conservation, timestamp availability, DST/session assignment, holiday and missing-minute exclusion, roll/adjustment rules, product independence, shift invariance, truncation causality, deterministic replay, partition invariance, schema/order/key checks, and finite outputs. Full validation checks every published part checksum and every output product-day for complete bars and audit eligibility.

## Provenance and limitations

The back-adjusted source is appropriate for analytical features but its absolute historical prices use later roll information. Adding a session-constant adjustment shifts VWAP/bands with price while leaving sigma and point/tick distances invariant. Consumers should join the unadjusted continuous dataset by product/session/raw contract identity for executions and P&L.

Databento omits one-minute intervals with no trades. Therefore `missing_expected_published_minute` is a conservative exclusion label, not a claim of corruption. Live TradingView parity was not measured; formula comparison is limited to identical OHLCV inputs and matching anchor lifetime, with the Pine display-only first-two-bar suppression intentionally omitted.

## Rebuild and validation

```bash
./scripts/build-session-anchored-vwap
./scripts/validate-session-anchored-vwap
.venv/bin/python -m unittest discover -s tests -v
```
