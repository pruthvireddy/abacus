# Databento definition batch profile

## Summary

| Property | Value |
| --- | --- |
| Batch ID | `GLBX-20260920-QQQSGCKWES` |
| Dataset | `GLBX.MDP3` |
| Schema | `definition` |
| Input symbology | Parent |
| Output symbology | Instrument ID |
| Products | `ES.FUT`, `NQ.FUT`, `GC.FUT` |
| Requested interval | `[2010-06-06 00:00:00, 2026-09-20 00:00:00) UTC` |
| First and last delivered dates | 2010-06-06 and 2026-09-18 |
| Daily DBN files | 5,100 |
| Definition payload | 81,288,444 bytes |
| Manifest entries | 5,102 |
| Original ZIP | 85,380,559 bytes |
| ZIP SHA-256 | `f7b161f56e9a2db8617e8748b68d46992c6a2d270916ab20c0828fb363acc0e1` |

## Integrity checks

- The ZIP central directory contains 5,103 entries and passed a complete CRC test.
- All 5,102 files listed by Databento's `manifest.json` match their vendor-provided SHA-256 hashes.
- The manifest covers 5,100 daily definition files plus `condition.json` and `metadata.json`; the manifest does not list itself.
- The raw batch directory contains those 5,103 extracted vendor files plus the preserved source ZIP.
- DBN metadata spot checks on the first file, midpoint file, and final file all report dataset `GLBX.MDP3`, schema `definition`, parent-to-instrument-ID symbology, and the expected one-day UTC interval.

## Dataset conditions

Databento's condition report contains 5,142 dated entries: 5,110 are marked `available` and 32 are marked `degraded`. A degraded condition is a provider quality signal and must be carried into downstream validation; it does not by itself prove that every record on that date is unusable.

Degraded dates:

```text
2014-06-11  2014-06-12  2014-06-13  2014-06-15
2014-09-22  2014-09-23  2014-09-24  2014-09-25
2017-11-13  2018-10-21  2019-01-15  2019-02-22
2019-03-13  2019-03-26  2020-02-27  2020-02-28
2020-05-05  2020-06-30  2020-07-01  2021-12-05
2022-01-02  2024-09-18  2025-09-17  2025-09-24
2025-11-28  2026-01-31  2026-03-15  2026-03-16
2026-03-21  2026-04-10  2026-05-24  2026-08-29
```

## Storage

The immutable delivery is stored at:

```text
data/raw/databento/GLBX.MDP3/definition/GLBX-20260920-QQQSGCKWES/
```

The daily files remain Zstandard-compressed in the raw layer. Downstream processing should stream them directly and write filtered, rebuildable outputs to `staging/` or stable contract-reference tables to `curated/instruments/`.
