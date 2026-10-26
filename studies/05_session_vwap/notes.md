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

## 2026-09-22/23 — A/C exploratory context study

The user authorized implementation and computation of A and C segmentation, specifically adding NY first 30 minutes and first hour for 2σ exits. [Protocol 1.1.0](protocol-1.1.0.md) was frozen before inspecting new context-conditioned outcomes. The parent A/C event ledger and outcomes were not changed. The new `20260923T035300Z_ac_context` run verifies the parent and pinned Bhishma input hashes, extracts prior-only ATR, opening balance, completed-bar path context, and re-entry, then links the context to parent event IDs. An ES 2021 extraction smoke test and 14 focused study tests passed; after full extraction the independent context audit reconciled 90,938 A, 138,674 C, 394,070 A controls, and 38,529 C near controls across 23 product-year partitions. NY-local first-half-hour A count was structurally zero under the existing warm-up.

The aggregate context tables were inspected after extraction and audit. The proposed early-NY weakness failed at the primary half-sigma barrier for Globex VWAP: first hour 48.7%, later 42.4%; a fixed 8-tick barrier reversed the clock ordering. NY-local minute 30–59 and later primary rates were near equal. C's 2σ+ pre-touch peak group had a lower primary bounce rate than the 1.5–2σ group (45.6% versus 47.8%); fixed 8-tick rates clustered near 40–41%. A faster return from a 2σ+ peak looked better at the primary barrier but reversed slightly at 8 ticks. Re-entry conversion was 98.4% of original A episodes, but its later-signal conditional rate is not a paired immediate-versus-wait policy result. The report and dated advice preserve negative and inconclusive results, with no execution promotion.

After inspecting results, reporting prose was expanded to state the barrier reversals and structural NY warm-up limit explicitly. The context extraction, event identity, barrier outcomes, bin thresholds, and matching strata did not change. The daily ATR helper was refactored without a change to its prior-day definition. Reporting was rerun from unchanged event context to produce final tables and source content. A local Narada publication source is prepared but no public bundle or deployment is authorized by this research request.

## 2026-10-06 — local web presentation pilot

Phase 2 presents the unchanged registered reference run `20260923T015900Z_vwap3`
in [export revision 20261006T210008Z_web05](../../reports/exports/05_session_vwap/20260923T015900Z_vwap3/20261006T210008Z_web05/README.md),
with [source](../../reports/exports/05_session_vwap/20260923T015900Z_vwap3/20261006T210008Z_web05/publication.json)
and [manifest](../../reports/exports/05_session_vwap/20260923T015900Z_vwap3/20261006T210008Z_web05/manifest.json).
Publication `session-vwap-vwap3-20261006-web05` is staged through Narada for local
static preview. The exploratory context run remains separate. Saved values,
findings, evidence status and reference selection are unchanged; no research
rerun or hosted deployment was performed.

## 2026-10-06 — Phase 3 local publication navigation

Featured presentation: [20261006T210008Z_web05](../../reports/exports/05_session_vwap/20260923T015900Z_vwap3/20261006T210008Z_web05/publication.json) · [manifest](../../reports/exports/05_session_vwap/20260923T015900Z_vwap3/20261006T210008Z_web05/manifest.json). Stable local study route: `/studies/session-vwap/`; immutable report route: `/reports/session-vwap-vwap3-20261006-web05/`.

Registered reference retained: `20260923T015900Z_vwap3`. Catalog navigation is maintained in [Narada](../../apps/narada/content/studies.json). Saved findings, evidence status and research-reference metadata are unchanged. This is local static publication; no deployment or research execution.
