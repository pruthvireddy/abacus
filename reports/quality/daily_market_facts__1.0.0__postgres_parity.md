# Daily Facts 1.0.0 local Postgres parity

**Passed on November 8, 2026 New York time.** The committed local projection
matched every field of the pinned release for 4,095 ES, NQ and GC asset sessions
from June 28, 2021 through September 18, 2026. The check compared 872,235 field
values across 213 typed columns and verified all 24,570 window keys. The
initial import and both committed readbacks found zero mismatches.

| Asset | Sessions | Globex | Overnight | RTH | OR15 | First60 | Last60 |
|---|---:|---:|---:|---:|---:|---:|---:|
| ES | 1,365 | 1,365 | 1,365 | 1,365 | 1,365 | 1,365 | 1,365 |
| NQ | 1,365 | 1,365 | 1,365 | 1,365 | 1,365 | 1,365 | 1,365 |
| GC | 1,365 | 1,365 | 1,365 | 1,365 | 1,365 | 1,365 | 1,365 |
| **Total** | **4,095** | **4,095** | **4,095** | **4,095** | **4,095** | **4,095** | **4,095** |

These are matched roster counts and include incomplete and calendar-excluded
windows. Their values, nulls, quality flags and availability timestamps matched
the source. The intermediate Globex-to-RTH-close VWAP quality fields were also
compared in the wide view. For research eligibility counts, see the
[release quality record](daily_market_facts__1.0.0.md).

## Inputs and comparison

- The importer verified the [release manifest](../../catalog/datasets/daily_market_facts__1.0.0.json)
  against SHA-256 `ba5a1b8fb15d7e2ddb4de167122a2930f45868358f66549fb748037c95d60fb2`
  and verified the sizes and SHA-256 hashes of all three Parquet partitions.
- It read the typed `daily_facts.daily_facts_v1` view and matched each row to
  Arrow by release, asset and session date. Prices matched at nine decimal
  places, integer values matched exactly, and float64 values matched bit for
  bit. Dates, timestamps, booleans, text arrays and nulls matched field by field.
  It separately checked the normalized window table for missing, extra or
  duplicate keys. This is storage parity with the released values.
- The initial transaction passed parity before commit. Separate connections ran
  the importer again and verified the committed release without rewriting rows.
  In a disposable database, adding one to the staged ES `first60_volume` for
  June 28, 2021 triggered the expected mismatch. A separate connection verified
  the projection schema was absent after rollback.

## Local database

The `daily_facts` database runs on PostgreSQL 18.6 from the verified
[Postgres.app release](https://github.com/PostgresApp/PostgresApp/releases/tag/v2.9.6).
The cluster lives under `work/daily-facts-v1/postgres/cluster/` and accepts
connections through the private `work/daily-facts-v1/pgsock/` Unix socket with
port number `55434`. The five projection tables and their indexes occupied
10.3–11.2 MiB across the checks. Follow the
[local query and rerun instructions](../../packages/bhishma/README.md#daily-facts-local-postgres).

[Machine-readable parity evidence](daily_market_facts__1.0.0__postgres_parity.json)
