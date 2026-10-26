# Decision and experiment history

## 2026-09-22 — repository consolidation

The previous research plan was copied unchanged. Six proposed strategy cards and shared configuration metadata were registered. No outcomes were computed. The release and dataset manifest hashes are pinned; inputs remain at the configured publication root.

Before implementation, record the initial product/window scope, confirm which evaluation outcomes have previously been viewed, and freeze the primary comparison family. Before profitability analysis, fix order type, costs, latency, size, exits, ambiguous-bar handling, and overlap policy. Preserve the plan’s distinction between frozen and evolving VWAP, and begin post-touch outcomes only when the touch is observable.

Record each inspected configuration here with its run ID, reason, outcome status, and decision. Include abandoned, negative, and inconclusive variants. An unexecuted plan is not an experiment result.

## 2026-09-22 — three-candidate statistical execution

The user authorized implementation and computation for `vwap_return_after_departure`, `vwap_extreme_fade`, and `vwap_first_retest_bounce` only. The other three ideas remain proposals. [Protocol 1.0.0](protocol-1.0.0.md) was written before strategy outcome tables were inspected. It fixes definitions, primary comparisons, matching bins, chronological splits, and sensitivity variants. The primary extraction ID is `20260923T015900Z_vwap3`; its execution was started under the frozen 30-minute warm-up and 0.5σ barrier settings.

During extraction, development-period ES 2021 outputs were used to smoke-test the report code. A pandas `product` column/method collision in reporting was fixed before full tables were produced. Source-path enrichment and denominator audit code were added without altering the primary B/A/C event rules. The entry point later gained a `sensitivity_only` option for the prespecified 20- and 40-minute warm-up reruns; a fixed real session produced identical B/A/C events in full and sensitivity modes at 30 minutes. No threshold was selected from outcomes. Validation and final-period findings must not be called previously unseen.

The predeclared primary baseline family is retained, but the current reporting implementation labels comparisons exploratory unless a dependence-aware familywise interval is available. That restriction prevents an unsupported formal edge claim. Record completed warm-up run IDs, source audit results, conclusions, and any further changes below after their evidence is checked.

The prespecified single-factor warm-up extractions were started as `20260923T022000Z_warmup20` and `20260923T022830Z_warmup40`. Their sensitivity mode omits baseline controls and descriptive cycle detail while retaining the same B/A/C primary event logic. The primary run keeps the 30-minute warm-up. Barrier factors 0.25σ and 1σ and the 4/8/16/32-tick grid are recorded alongside the primary 0.5σ barrier on the same event populations.

Before inspecting aggregate validation/final outcome tables, source-audit enrichment was expanded to bound A's outward 3σ-before-return statistic when both extremes may occur in the same one-minute contact bar. Enrichment was rerun to add those fields. B/A/C primary event and barrier definitions, thresholds, and matching strata were unchanged; both bounds and adverse cases remain in the event ledger.

## 2026-09-22 — completed evidence and interpretation

Primary extraction, the 20- and 40-minute single-factor warm-up reruns, source reconciliation, and independent denominator audit completed. The audit found 3,039 eligible product-days, 42,546 correlated views, one B event in each of 42,487 departure views, and exhaustive A/C primary barrier classes. Full aggregate tables were inspected only after the second source enrichment. The primary B/A/C rates were 78.4% frozen return by window end, 46.8% A favorable-first, and 46.7% C favorable-first. The warm-up reruns changed B's deadline rate because the selected first departure shifted, while A/C primary rates were close across 20, 30, and 40 minutes. The 0.25σ and 1σ barrier results and fixed 4/8/16/32-tick grid remain visible in `tables/sensitivity.csv`.

The pre-full-run real-session smoke check compared primary and sensitivity extraction on a fixed session. After full extraction, all 42 deterministic example rows across nine product × strategy pairs were checked against their Parquet event IDs, reference-audit flags, and stored outcome classes. The prescribed full product/class example review was therefore completed after the full extraction rather than before it; no event rules were changed in response.

After viewing aggregate results, reporting text and metadata were revised to explain baselines and chronological stability. No event selection, barrier rule, baseline stratum, or data-extraction definition was changed. The pooled A 0.5σ matched contrast is exploratory and reverses under the common fixed 8-tick comparison; 2024 and final-period primary-barrier intervals include zero. C has no stable incremental lift over near approaches. The all-touch and confirmation-subset C results are similar. The resulting dated advice is retained inside the run, and the three selected strategy cards cite both supporting and opposing evidence. The three other cards remain proposals. No hosted publication or deployment was attempted.
