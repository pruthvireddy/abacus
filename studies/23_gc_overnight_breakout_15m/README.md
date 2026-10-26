# GC- Overnight Breakout 15M

Study `23_gc_overnight_breakout_15m` · Phases 1 and 2 approved October 13, 2026 · Phase 1 protocol `1.0.0`; Phase 2 protocol `2.0.0`.

Phase 1 measures the fixed baseline overnight breakout, one executable GC contract per accepted broker day. Phase 2 completed implementation, numerical verification, chronological execution and sealing. Its frozen policies cover four confirmed inward reclaims, three exploratory passive limits, protected overnight-boundary occurrences and three replacement continuation/reversal rules, plus separate whole-contract account experiments. Protected low means the frozen overnight range low after an upper-first breakout, with an explicit protected-high mirror. Phase 3 EMA/cloud backtests and verified same-study production publication are now authorized; its dedicated implementation and synthetic verification are in progress before historical scoring. Additional filter searches remain unexecuted.

Read the [frozen Phase 1 protocol](protocol-phase1.md), [settings](config-phase1.json), [input audit](phase1-input-audit.md) and [market lock](phase1-inputs.lock.json), then the dedicated [Phase 2 protocol](protocol-phase2.md) and [settings](config-phase2.json). The [research plan](plan.md) preserves the approved proposals and later Phase 3 planning. The current Phase 2 authorization supersedes its earlier documentation-only scope for these frozen policies. Published baseline years are exposed and cannot be called untouched Phase 2 holdouts.

The baseline uses fixed GMT+3, range [00:00,07:00), trading [07:00,20:00), boundary stop touches, OCA cancellation and one accepted trade per broker day. Regular 15-minute candles govern submission and stop updates; observed unadjusted one-minute candles resolve fills approximately. Initial 1% stops are boundary anchored; only a surviving entry candle resets from actual fill at its close. The evening close is queued for the next opening. Native standing-order semantics and the explicit causal quality overlay remain distinct from the indicator's missing-bar fallback.

Immutable `volume_lead_unadjusted_v1` version `1.0.0` supplies 3,046,589 source minutes across 45 contracts, from January 1, 2018 23:00 UTC through September 18, 2026 20:59 UTC (completion at 21:00). The 2026 year is partial. The frozen audit identifies 994 causally eligible broker days and 1,106 valid complete ranges. Missing range minutes, uncertified holiday candidates, roll barriers and the first loaded day reduce support. Later missing execution evidence censors accepted trades instead of excluding their signals. GC economics are 0.1 tick, $100 per point and whole contracts; the source account's $10,000 capital, 1% risk and 10x leverage cap is a separate view.

Prespecified assumed costs are $2.50 per contract per side plus one adverse tick/fill, with zero-cost and zero/one/two-tick executions. These are scenarios, not the user's broker charges. Reporting uses actual estimated entry fill in America/New_York with approved Asia/London/New York/outside windows. Within-minute fill times retain bounds, and native TradingView compilation/replay remains unverified.

## Retained sources

The [Phase 3 plan](plan.md#phase-3-five-minute-ema20-and-ema50-cloud) adds the
user's five-minute EMA20/50 cloud for trend context, support add-ons, earlier
exits and bounded confluence/extension diagnostics. It requires causal five-
minute decisions, fair risk controls, and annual/session result tabs on the same
study page. The EMA-management rules remain planning and a coding-agent handoff;
the current authorization supersedes that earlier planning-only scope. Read the dedicated [Phase3 protocol](protocol-phase3.md) and [settings](config-phase3.json); historical outcomes have not yet been scored.

- [Original strategy](sources/original-strategy.pine), by WillyAlgoTrader.
- [Indicator adaptation](sources/indicator-adaptation.pine).
- [Source differences](source-rules.md) and [source-byte lock](inputs.lock.json).
- [Screenshot](sources/indicator-chart-reference.png), appearance reference only; no market-data evidence or inferred meanings for unlabeled marks.

The midpoint is visual in the supplied scripts. Indicator H10 signal-close diagnostics are omitted from this Phase 1 execution and are distinct from trade results.

## Ownership and checks

Study implementation, aggregation, exporter and tests belong here. Bhishma owns immutable data and public loaders; Narada renders explicitly selected saved report cells. Stage new output under `work/23_gc_overnight_breakout_15m/<run-id>/`; seal only verified evidence under a unique `runs/23_gc_overnight_breakout_15m/<run-id>/`. Retain large event/input evidence under `data/research/sahadeva/` with hashes and locators. Preserve completed runs and all earlier publication routes. Follow the [study guide](../AGENTS.md), [architecture](../../ARCHITECTURE.md) and [evidence contract](../../docs/evidence-contract.md).

```sh
UV_CACHE_DIR=/private/tmp/abacus-study23-uv-cache ./scripts/check-workspace --check study-23
python3 scripts/check-agent-docs.py
./scripts/check-workspace --profile metadata
python3 scripts/build-research-index.py --check
```

Numerical tests use the existing locked environment without sync. The broader default gate's missing raw roll-map and unavailable ES definition prerequisites are recorded separately; they do not establish failure of the selected GC release bytes or excuse required study verification. Run records identify the executed checks and their limits.

## Verified Phase 1 evidence

Phase 1 is published at the [verified production study](https://abacus-narada.vercel.app/studies/gc-overnight-breakout-15m/). Immutable publication `gc-overnight-breakout-15m-phase1-20261013-v1` is selected by release `20261013T172420Z_c9cd5748`, deployment `dpl_DipGeCPi9mnfquhRqevqNpQLk3LG`. The [release outcome](../../apps/narada/releases/20261013T172420Z_c9cd5748/outcome.json) and append-only events retain protected preview/staged checks, actual browser reviews and anonymous public production verification. All 1,004 selected static files, 126 CSVs and five hard 404s passed the final anonymous gate; earlier studies and publications remain retained. Project protection is unchanged. The previous verified release `20261013T035220Z_b4759d0f` remains the rollback reference.

Research run [20261013T142537Z_phase1_gc_ob15m_v1](../../runs/23_gc_overnight_breakout_15m/20261013T142537Z_phase1_gc_ob15m_v1/report.md) executed protocol `1.0.0` with the frozen settings and input lock. The [manifest](../../runs/23_gc_overnight_breakout_15m/20261013T142537Z_phase1_gc_ob15m_v1/manifest.json) declares 165 local artifacts and 124 private external artifacts; actual local external bytes were separately checked before sealing. General evidence integrity independently leaves external declarations unverified.

The primary saved ledger has 880 estimated fills, 863 completed trades and 17 censored trades. There are 28 known no-trade days and 86 unobserved first-fill opportunities. Completed-trade net P&L is $201,045 under the assumed primary costs; 2019 and 2023 are negative, and partial 2026 contributes $117,305. The original $10,000 account submits no whole-GC orders. These are descriptive authored-fill results, not native TradingView or live execution validation.

The owned suite passed 95 tests without skips. Independent numerical verification passed 592,328 comparisons plus 19,362 exact-decimal stop checks. Every selected publication cell, CSV cell and figure source was independently checked. The run preserves failed preliminary formatting/diagram attempts and final passed receipts. Subsequent browser and hosted checks are recorded in the separate Narada release. Phase 2 was uncomputed at the Phase 1 seal; its later completion is recorded below.

## Verified Phase 2 evidence

Research run [20261013T190208Z_phase2_gc_ob15m_v2](../../runs/23_gc_overnight_breakout_15m/20261013T190208Z_phase2_gc_ob15m_v2/report.md) executes Phase 2 protocol `2.0.0` using the unchanged Phase 1 input and baseline pins. Its [manifest](../../runs/23_gc_overnight_breakout_15m/20261013T190208Z_phase2_gc_ob15m_v2/manifest.json), SHA-256 `ffe43f2403520d9ba058720908ad711b88e665b0d8d3928bdaa5342ad7cb3c4a`, inventories 1,874 local artifacts and 1,148 retained external declarations. A separate read-only audit verified the actual retained external bytes after sealing; the general evidence-contract assessment alone does not verify external bytes or backup availability.

All 880 original accepted episodes remain in the roster, including 17 censored baseline fills. Four confirmed inward-reclaim replacements use one common complete-pair mask. Development/validation (2018–2023) executed and passed independent verification before selection was frozen; 2024–2025 and qualified available 2026 evaluation followed without retuning. The [saved selection](../../runs/23_gc_overnight_breakout_15m/20261013T190208Z_phase2_gc_ob15m_v2/selection.json) remains null: all four validation mean paired differences were negative. Validation has 213 original episodes and 207 common complete pairs. The shallower two policies met the 100-completed-fill threshold; the other two did not. The [later assessment](../../runs/23_gc_overnight_breakout_15m/20261013T190208Z_phase2_gc_ob15m_v2/assessment.json) retains the fixed Phase 1 baseline. Published baseline years were previously exposed and are not pristine holdouts.

| Rule | Validation completed fills | Mean paired difference (USD) | Qualified |
| --- | --- | --- | --- |
| reclaim-q000 | 161 | -125.31 | No |
| reclaim-q025 | 127 | -117.05 | No |
| reclaim-q050 | 96 | -173.74 | No |
| reclaim-q075 | 76 | -181.76 | No |

Protected-low occurrence, touch/hold, failed-break continuation and reversal are separate exploratory evidence, with an explicit protected-high mirror. Their price recovery diagnostics are distinct from executed trade P&L and financial loss recovery. Actual-entry performance uses candidate fill cohorts; paired comparisons and occurrence summaries use original-breakout cohorts. Known no-fill is zero on a known path; unknown execution, first-event timing and censored outcomes remain unavailable. Annual/session, side, event-transition and first-touch-level results retain empty and partial support.

The [saved occurrence table](../../runs/23_gc_overnight_breakout_15m/20261013T190208Z_phase2_gc_ob15m_v2/tables/occurrence.csv) records protected-low one-tick breaches in 132 of 442 known upper-first histories over the remaining broker window, with one unknown history. Within the original entry session, it records 27 of 440 known histories, with three unknown. The horizons have unequal exposure, and price observation continues after the baseline trade exits; these counts do not establish live probabilities or financial recovery.

Historical whole-contract account ledgers contain no known financed original or later fills under the frozen $10,000 capital, 1% daily risk, 10x leverage and 5% margin assumptions. Unknown possible setups, fills, loss eligibility and capital propagate as null rather than false or zero. Standardized one-contract outcomes are not source-account returns; executed two-leg arithmetic is verified with separate synthetic fixtures.

The requested [breach-origin recovery-delay supplement](../../runs/23_gc_overnight_breakout_15m/20261013T190208Z_phase2_gc_ob15m_v2/additional/time-recovery/time-recovery.csv) froze its source/input hashes after policy execution and before its derived measurements. It reports first known protected one-tick breach to first known recovery, conditional on known timings, with conservative minute bounds and explicit risk/unknown denominators. It changes no order, P&L, mask or selection and is not a survival probability. Original-breakout elapsed time remains a separate saved metric. Canonical ledgers retain censored-only observed holding metadata omitted from the common trade CSV; raw `gap_entry` float inequality may reflect binary price noise and is not a one-tick gap certificate.

The final stage-bound numerical suite passed 336 tests with 353 success callbacks and no skips. Independent scientific reconstruction verified every accepted episode, all 16 saved tables, aligned 10,000-draw intervals, seven fixed cost/order/resolution sensitivities, actual account constraints and 80 selected examples. Publication transfer verified all 23 sources, 626,751 displayed cells, 493,491 CSV download cells and 89 figures. Exact synthesis transfer verified 852 cells. Manual raster review and production/browser checks have separate scopes and receipts; failed and superseded attempts remain retained. Partial 2026 ends September 18, 2026. Native TradingView/tick replay, annual holiday certification and live mapping receipt timing remain unverified. The unchanged default compatibility gate still fails on two Bhishma raw-input prerequisites (226 tests, two errors), leaving four later default checks unexecuted. Phase 3 EMA/cloud management, H10 and new filter searches remain uncomputed.

Phase 2 is published at the [existing study page](https://abacus-narada.vercel.app/studies/gc-overnight-breakout-15m/) through release `20261013T211202Z_4c5b1446` and deployment `dpl_CtfrwaVuh82zqVWDuaPDSRVzSzKC`. The [verified release outcome](../../apps/narada/releases/20261013T211202Z_4c5b1446/outcome.json) records `anonymous_exact_bytes_and_actual_browser_passed`. Phase 1 run, publication and release bytes and their original references remain retained.

## Post-seal transition presentation revisions

Two separately verified presentation-only revisions complete the session-transition coverage from the unchanged sealed tables: [comparison sessions](../../reports/exports/23_gc_overnight_breakout_15m/20261013T190208Z_phase2_gc_ob15m_v2/20261013T204013Z_comparison_sessions_r1/manifest.json) and [protected entries](../../reports/exports/23_gc_overnight_breakout_15m/20261013T190208Z_phase2_gc_ob15m_v2/20261013T204013Z_protected_entry_r1/manifest.json). Their publication IDs are `gc-overnight-breakout-15m-phase2-session-transitions-20261013-r1` and `gc-overnight-breakout-15m-phase2-protected-entry-20261013-r1`. The original 23 run publications remain unchanged; production selects 25 Phase 2 sources when these revisions are included.

Ten original-breakout-to-candidate-entry matrices cover every policy; protected-entry tables also expose the three breach-to-candidate matrices and breach-to-price-reclaim. Two ordered, full-column downloads partition all 22 transition kinds and 16,500 saved rows into disjoint 7,500-row and 9,000-row sets under the unchanged native download bounds. All 1,800 timing cohorts retain both horizons, all three levels, event types, bounds, denominators and unknown support. Protected entry performance displays 12 declared fields and downloads 24; a privately retained exact 450-row/61-column copied source preserves the full saved schema. Executable fills remain bound to their original field and are not substituted from a legacy accepted-breakout label.

These revisions recompute no research outcome or statistic and change no selection, policy, cost, source manifest or prior publication. The original 336-test numerical receipt remains unchanged. A separate seven-test presentation checker suite and exact saved-cell/final-inventory receipts cover the new exports. Manifest hashes are `85d8e590677f8b00d55781361c59db128dee3b4cb9f577c409a969dd1f9e89dc` and `bc40312a1897fb3f4ad0d92b8d2944e2ac92d14f2e53ee1a61c7a412a49bc34a`.

The production release preserves eight analysis groups and 26 study tabs. Protected preview, staged production and anonymous public production each matched all 1,418 prepared files, all 201 selected CSV attachment/media headers and five hard 404s. Actual browser checks covered all 26 report/run attributions, saved row controls and unavailable cohorts, desktop/mobile layout, protected-low figures and session transitions; representative retained layouts were checked on the exact preview artifact. Narada verify, 160 app tests without skips, lint, build and the 87-publication private source audit passed. Project protection is unchanged. The verified Phase 1 release `20261013T172420Z_c9cd5748`, deployment `dpl_DipGeCPi9mnfquhRqevqNpQLk3LG`, is the explicit rollback reference. No fresh native hosted CSV-download completion or off-device backup is inferred from served-byte verification.
