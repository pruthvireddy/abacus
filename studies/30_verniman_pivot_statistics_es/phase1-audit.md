# Phase 1 — source and input audit

## Ranked extension coverage audit — 2026-10-31

Before new event outcomes, the pinned release contained 1,753 retained session
records. Source-independent quality/readiness checks found 1,308 VWAP-only RTH
sessions and 1,292 full-Globex sessions. The existing 875 pivot-matched baseline
sessions remain a separately selected population. The fresh execution repeats
and freezes this coverage audit, preserving every excluded requested date and
its reasons. No feature release was rebuilt and no data was acquired.
The retained pre-outcome audit is
`work/30_verniman_pivot_statistics_es/20261031_ranked_coverage_v1/coverage.json`.
Its earlier internal `vwap_only_globex` key names the full-Globex population;
the new event evidence uses explicit `vwap_only_full_globex` membership.

Study `30_verniman_pivot_statistics_es` · 2026-10-31

Requested sessions are 2020-01-01–2026-10-30 inclusive. The initial retained
inventory is `work/30_verniman_pivot_statistics_es/20261031_phase1_repo_inventory_v1/`.
Its read-only verifier passed 27 retained artifact hashes, outlook/level/calendar
accounting and CSV/JSON projections. It is an input inventory, not a sealed
numerical research run.

| Inventory | Count |
|---|---:|
| Requested calendar dates | 2,495 |
| Canonical outlooks in requested interval | 1,606 |
| Shared single-price trigger shapes | 1,536 |
| Shared zones / separate thresholds | 13 / 13 |
| One-sided / no-trigger outlooks | 27 / 17 |
| Dates with multiple canonical outlooks | 23 |
| In-range outlooks with null historical availability | 1,606 |
| Separate user image/recollection observations, full release | 5 / 14 |

## Source-only semantic review

Most legacy extractions omit `trigger_interpretation`. A new study-local,
versioned source-only rule checks both original scenario strings: an explicit
“If market moves/remains/trades/stays above” bullish condition and corresponding
“below” bearish condition, whose first literal price equals the saved shared
single-price trigger. It rejects contrary roles, ranges, mismatched first prices
and ambiguous source wording. Exact source-string hashes and decision reasons
are retained; no published source row is changed and no market outcome is used.
Additional source internals/delta conditions are unmodeled qualifications.

This resolves paired-threshold semantics for 1,525 outlooks. After all independent
source checks, 1,157 outlooks are retrospective source candidates. Remaining
exclusions include duplicate revisions, weekday/date conflicts, partial/failed
extraction, incompatible shapes, missing contracts and other retained source
issues. These counts precede exact-contract and feature eligibility.

## Repository-only input decision and feature audit

The user explicitly selected retained repository data and prebuilt OHLC rather
than external acquisition. October 30 remains the requested reporting cutoff;
retained ES source bars end September 18. Missing dates, delivery mismatches and
quality failures remain exclusions; no quote, purchase or download is needed.

The new [ES indicator delivery](../../catalog/datasets/es_contract_session_indicators__1.0.0.json)
reuses existing native OHLC and cloud values. Its independent audit at
`work/30_verniman_pivot_statistics_es/feature-audit-v1/receipt.json` passed:

- Exact source OHLC/identity parity for 2,373,137 minute rows.
- Exact reuse of 804,440 three-minute and 482,664 five-minute OHLC/EMA rows.
- EMA6 recurrence/readiness parity from 1,160,250 full-history native observations.
- Completed cloud joins, anchor VWAP and 10,280 independently aggregated native
  bars across 14 deterministic January/July sessions.

The [fulfilled request](../../requests/fulfilled/es_contract_session_indicators__1.0.0.yaml)
records the input-only delivery. Complete minute rosters and checked feature
values do not certify original vendor reconstruction, native chart parity,
historical pre-open availability, or scientific profitability.
