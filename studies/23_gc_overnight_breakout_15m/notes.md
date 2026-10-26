# GC- Overnight Breakout 15M planning decisions

## October 13 2026

The user requested study creation and a draft plan from two supplied Pine
scripts, followed by review before execution. The research question includes
baseline entry-to-exit profits and possible better entries when price returns
to the midpoint or within the overnight range, their success frequency, and
whether such behavior could support a filter.

- Created `23_gc_overnight_breakout_15m` as a proposed research study. The
  [plan](plan.md) and [settings](study.yaml) are drafts, not an executed protocol.
- Preserved both scripts byte for byte under `sources/`; the
  [source lock](inputs.lock.json) records hashes, sizes, and original locators.
  Neither source was edited or compiled.
- Documented original/indicator differences in [source-rules.md](source-rules.md).
  The midpoint is visual only in the indicator. Re-entry rules are new hypotheses.
- Proposed four symmetric confirmed return/reclaim levels: broken boundary,
  25%, 50% midpoint, and 75% inside the range. Limit-touch entries are a separate
  exploratory family. User review may narrow or change these choices.
- Separated replacement from additional entries and limited the latter to a
  fixed daily risk budget. A future retracement cannot filter a prior breakout.
- Proposed net trade profitability, recovery of the broken boundary, and 1R
  excursion as distinct success measures with explicit denominators.
- Kept source-style trade statistics separate from signal-close H10 excursions
  and the future GC execution model. Market data and numeric costs are pending.
- Proposed chronological development/validation/final/recent periods subject to
  coverage. Other GC research has inspected parts of this history; no pristine
  holdout claim is made.

Only documentation, source retention, registration, and local navigation are
in scope. No research engine, market-data run, sealed evidence, strategy card,
publication bundle, or deployment was created. Documentation, registry and
metadata checks establish their own bounded scope, not scientific validity.

Before execution, incorporate the user's review, pin market inputs, settle costs
and availability/calendar conventions, freeze the approved protocol and settings,
then obtain execution scope. Record subsequent protocol changes here without
rewriting any future completed run.

## Planning verification

Documentation checks passed for 76 maintained guides. Navigation metadata passed
for 23 studies; the regenerated local index passed its freshness check. The
focused standard-library registry suite passed all 26 tests. Both retained
scripts matched their original attachment bytes and locked SHA-256 identities.

The compatibility gate was attempted with
`UV_CACHE_DIR=/private/tmp/abacus-study23-uv-cache ./scripts/check-workspace`
using the existing locked environment without synchronization. Documentation
passed; Bhishma ran 226 tests and failed on two existing raw-input prerequisites:
an absent continuous volume-rank roll-map JSON and an unavailable point-in-time
ES definition pair. Fail-fast left Sahadeva, legacy studies 01/02, and VWAP doctor
unexecuted. An earlier attempt failed before checks because the default uv cache
was outside writable sandbox storage; the explicit temporary cache resolved it.
These are workspace-check results, not this study's market-data analysis.

## October 13 2026 publication and reporting amendment

The user requested eventual publication on the existing Vercel-hosted site, with
the study name as its library navigation entry and smaller tabs for conditions.
The supplied chart screenshot is a visual guide for the later page-building
stage. The user also requested year-wise performance and statistics identifying
Asia, London, or New York entries. Current scope remains planning, with no coding
or analysis before review.

- Updated the draft to `0.1.1` with planned study/condition navigation, a common
  results-reading sequence, visual diagrams, selected saved-data controls, and
  publication acceptance criteria. Publication is an intended later deliverable;
  it is not authorized for execution in this turn.
- Retained the screenshot unchanged under `sources/` and appended its bytes/hash
  to the source lock. It supplies appearance cues only. Its missing axes/settings
  and unexplained markings are not interpreted as trade or performance evidence.
- Required annual, entry-session and year-by-entry-session results for each
  condition, plus entry-hour distributions and breakout-to-later-entry session
  transitions. Trade grouping uses actual fill time; paired comparisons retain
  the common original-breakout cohort.
- Proposed New York reporting windows: Asia [20:00, 02:00 next day), London
  [02:00, 09:00), New York [09:30, 16:00), with all other hours retained. These
  are analytical windows for review, not an exchange calendar or eligibility
  filter. Missing and partial cohorts remain explicit.
- Planned to use Narada's saved-report navigation and figure/schematic support.
  Future conditions from different runs may need a generic navigation extension;
  no application/catalog/schema or release files changed now.

## October 13 2026 Phase 1 approval

The user reviewed and approved the plan, then explicitly authorized complete Phase 1 baseline implementation, causal input preparation, verification, research execution, saved evidence and report preparation, publication and production deployment on the existing Narada website. This supersedes the earlier documentation-only flags for Phase 1. Fixed GMT+3, 00:00–07:00 range, 07:00–20:00 trading, 1% stops and one accepted breakout per broker day remain fixed. Costs are explicitly assumed scenarios, not user broker charges. Phase 2 midpoint/reclaim/interior entries, re-entry, extra trades and new filters remain unexecuted. Annual baseline exposure removes any future claim that these years are untouched Phase 2 holdouts.

## October 13 2026 protected boundary planning amendment

The user requested adding protected-low break frequency, possible recovery/new
entries, and their statistics to the plan and a revised Phase 2 coding-agent
prompt. The user explicitly clarified that protected low means the overnight
range low, the opposite boundary after an upper breakout, rather than a swing low.

The plan now includes touch, one-tick breach, close-confirmed break and later
reclaim events; same-session and remaining-broker-window horizons; three separate
touch/hold, failed-break continuation and confirmed reversal hypotheses; and
price recovery versus actual financial loss recovery. Upper-first/protected-low
results remain prominent, with a protected-high mirror. All branches require
annual/session statistics, causal availability, exact denominators, uncertainty,
paired baseline comparisons, and distinct website views. The existing four
primary inward-reclaim policies and their multiplicity family are unchanged.

This turn updates planning documents and the handoff prompt only. It does not
execute Phase 2, change the Phase 1 protocol/settings, or modify saved evidence.
The coding agent must freeze dedicated Phase 2 settings before any outcomes.

## October 13 2026 Phase 3 EMA cloud planning amendment

The user requested a Phase 3 plan and copyable coding-agent prompt using the
five-minute EMA20/50 cloud to build trend confidence, add to an open position
at cloud support, cut losses earlier, and test other bounded uses. The user
explicitly permits the in-app browser for future testing.

The plan now distinguishes causal trend-context statistics, two entry gates,
EMA20/EMA50 support add-ons, two early-exit rules, and secondary EMA50 trailing,
overextension/compression, range confluence and retest diagnostics. It keeps
original parent decisions, five-minute EMA availability, risk reservation,
whole-contract feasibility and annual/session cohort meanings explicit.

The retained Study 21 user source defines a five-minute close-based EMA20/50
cloud; its touch signals are disabled for EMA timeframe below chart timeframe.
Phase 3 therefore requires dedicated confirmed five-minute decisions, not an
end-of-fifteen-minute sampled cloud used retrospectively. Existing feature
release 1.1.0 is a candidate matching the Phase 1 source manifest; its exact
selected bytes/mapping must be verified and pinned before execution. Earlier
EMA-cloud studies' outcomes are not transferred as evidence for this strategy.

This turn edits planning prose and the handoff only. No EMA calculation, Phase 3
backtest, app implementation, publication or deployment is performed here, and
no prior protocol, input lock, run or release is rewritten. Dedicated Phase 3
settings and any combined policy must be frozen before their outcomes.

## Phase 1 research completion

Completed and sealed `20261013T142537Z_phase1_gc_ob15m_v1` under protocol `1.0.0`, with frozen inputs/costs before outcomes. Nine fixed baseline executions cover primary one-tick, zero-cost, zero/two-tick net scenarios, high/low ordering, native observed 1m, source 15m OHLC and original whole-contract source-account sizing. H10 and all alternative-entry outcomes remain uncomputed. The scientific receipt passed 592,328 comparisons, exact-decimal stops passed 19,362 cells, publication transfer passed 13,168 displayed and 9,165 CSV cells, and the final owned suite passed 95 tests without skips. Prior verifier-format and diagram attempts remain retained; no executed analytical source or settings changed after scoring. The research seal has 165 inventoried local files and 124 externally retained declarations with an actual local retained-byte check. Native replay/raw reconstruction and annual holiday certification remain unavailable. The existing default gate still has two Bhishma raw prerequisite failures and leaves its remaining four checks unexecuted.

This reference run is the fixed Phase 2 baseline handoff, not a strategy promotion. All annual baseline outcomes are now exposed. Publication and production release events are subsequent records; completed run bytes remain immutable.

## Phase 1 production publication

Published and verified October 13, 2026 at [GC- Overnight Breakout 15M](https://abacus-narada.vercel.app/studies/gc-overnight-breakout-15m/), with publication `gc-overnight-breakout-15m-phase1-20261013-v1` and release `20261013T172420Z_c9cd5748`. The existing brew-vee/abacus-narada project was verified before hosted changes. Protected preview and staged production matched all 1,004 static files and five hard 404s; the staged production deployment `dpl_DipGeCPi9mnfquhRqevqNpQLk3LG` was promoted only after the actual browser gate. Anonymous public production matched all 1,004 files, 126 CSVs and five hard 404s without cookies or bypass credentials.

Actual browser review covered desktop/mobile layout, library/study/report and contents navigation, saved year/session/side rows, unavailable cohorts, pagination, keyboard table scrolling, all eight new raster loads, provenance/download links and retained quantitative, qualitative, historical, table-heavy and enriched layouts. The native local browser CSV download completed and matched the sealed selected bytes; no fresh native hosted/production download completion is claimed. Initial in-app preview access reached Vercel login, and automatic approval review rejected a temporary share-link attempt. Existing normal authenticated Chrome access resolved protected browser review without changing protection; signed-out in-app browsing verified public production. Preparation's first Node 26 attempt failed before a release was created, then pinned Node 24/npm 11/CLI 62.7 preparation passed. Failed attempts remain retained separately from passed gates.

The release outcome and append-only events preserve actual verification scope and the previous verified production `20261013T035220Z_b4759d0f` / `dpl_CxsD7ZNDXY6PHu7zzWLmqFMekSq5` as rollback. All 212 previously selected public files, existing study/catalog entries and previous release mappings remain unchanged. Final independent integrity review matched the sealed manifest, 165 local artifacts, 124 actual private external files, all selected input/source pins and the exact release payload. The default six-step compatibility gate is unchanged. Phase 2 and Phase 3 research outcomes remain uncomputed; later-year baseline exposure is retained in the handoff.

## October 13 2026 Phase 2 execution authorization and freeze

The current user instruction authorizes implementation, testing, research execution, evidence/report preparation, appropriate navigation changes, publication and production deployment through verified public production within the existing study page. Protected low is explicitly the frozen overnight range low after an upper-first breakout; the protected-high mirror is separate. This supersedes earlier planning-only Phase 2 flags. Phase 3 EMA/cloud management and new filter searches remain unexecuted.

Protocol `2.0.0`, `config-phase2.json` and `protocol-phase2.md` were prepared before any historical alternative-policy outcomes. The new stage is `work/23_gc_overnight_breakout_15m/20261013T180939Z_phase2_gc_ob15m_v1`. The baseline pin independently verified completed Phase 1 run `20261013T142537Z_phase1_gc_ob15m_v1`, manifest `d2f93832610ca6e6284838ce22ca9547b8c848a1b0f06a740a345df39d94c027`, all 165 local and 124 retained external artifacts, selected input/source hashes, scenario ledgers and public baseline files. Phase 1 bytes and settings remain immutable.

Development/validation policies will execute first; their saved selection and settings hashes must precede later assessment. Published baseline years remain exposed. Primary one-contract comparisons use unchanged Phase 1 costs and execution conventions. Actual two-leg experiments separately freeze the source account at $10,000, 1% start-of-day risk split equally, 10x leverage and 5% margin with whole contracts; null execution/capital states remain distinct from known quantity skips. Current production Phase 1 release `20261013T172420Z_c9cd5748` remains the verified rollback until a separately gated Phase 2 release succeeds.

The first frozen implementation attempt (`20261013T180939Z_phase2_gc_ob15m_v1`) executed development/validation but was retired before opening its outcomes, independent historical verification, later assessment or summaries. A source-schema review found the summary adapter used three wrong price-path field names. Its freeze, ledgers and logs are preserved unchanged. Corrected adapter tests now verify non-null saved MFE/MAE/depth fields, and the diagnostic 1R reference is explicit. Policy rules, selection criteria and input identities are unchanged. Fresh authoritative run `20261013T190208Z_phase2_gc_ob15m_v2` freezes the corrected producers before execution. No v1 policy outcomes or selection were inspected.

Before sealing Phase 2, the requested recovery-delay diagnostic received its own source/input freeze (`additional/time-recovery/measurement-freeze.json`) after policy execution and before the derived measurements. It measures first known protected one-tick breach to first known recovery, with source-OHLC estimates and conservative time bounds, on the existing frozen raw event ledgers. No policy, order, P&L, mask or selection changes. The initial recovery tables measure elapsed time from original breakout; that distinct anchor remains unchanged. Independent first-side audit found no original fill minute visiting both overnight boundaries across all 880 accepted episodes. Unknown/censoring and price-path versus trade versus financial-recovery distinctions remain explicit.


## October 13, 2026 Phase 2 research and production completion

Completed and sealed `20261013T190208Z_phase2_gc_ob15m_v2`, protocol `2.0.0`, manifest `ffe43f2403520d9ba058720908ad711b88e665b0d8d3928bdaa5342ad7cb3c4a`. The completed bundle has 1,874 local artifacts and 1,148 external declarations; a separate post-copy audit verifies actual locally retained external bytes. The immutable Phase 1 manifest, all 165 local/124 retained external records, selected market/source pins and original retained release static bytes remain unchanged. No off-device backup or new scientific revalidation is inferred from byte integrity.

Development and validation of 550 episodes preceded the hashed selection; independent verification passed before the later 330 episodes executed. The frozen selection is null: all four validation paired mean differences are negative, on 207 common pairs from 213 validation episodes. Later assessment retains the unchanged Phase 1 baseline without retuning. Passive/protected rules and their mirrors remain exploratory rather than newly selected strategies. All 880 original episodes remain in the roster, including 17 censored baseline fills; known no-fill contributes zero only on a known path. Unknown first setup/fill, event time, loss eligibility and account capital remain null.

Final locked/no-sync numerical recording observed 336 tests, 353 success callbacks and no skips. Independent replay reconciled all policy/event paths, all 16 saved tables and aligned confidence intervals, seven fixed sensitivities, actual account/capacity ledgers and 80 earliest selected examples. All 23 publication sources passed exact saved-cell/download/SVG geometry/final-inventory checks; 852 synthesis cells passed. The saved occurrence table records 132 protected-low one-tick breaches among 442 known upper-first histories over the remaining broker window, with one unknown history; the original entry session records 27 among 440 known histories, with three unknown. Different horizon exposure and observation after baseline exits limit interpretation; these are price-event counts, not financial recovery probabilities.

Actual whole-contract historical account ledgers have no known financed original or later fills; nonzero executed two-leg accounting is supported by separate synthetic fixtures, never by substituting standardized hypothetical profits. Missing-equity and possible hidden first-setup states remain unavailable.

The requested breach-origin supplement is explicitly a post-policy-execution measurement declaration. Its source/input freeze precedes only these derived measurements, not the historical policy outcomes. It uses unchanged canonical event rows and changes no order, P&L, mask or selection. Conditional known recovery delays retain conservative bounds and risk/unknown denominators; breakout-origin elapsed metrics are separate. Canonical ledgers preserve 23 censored-only observed holding metadata values omitted by first-row CSV projection. Exact raw/reference float inequality can set `gap_entry` from binary noise; it is not an economic one-tick-gap count. Independent original-minute audit found zero unresolved dual-boundary first-side minutes across 880 originals. Failed verifier and presentation attempts, the unopened abandoned v1 analytical attempt and losslessly verified prior draft archives remain retained.

Manual direct raster review observed all 88 unique hashes across 89 final PNG paths. Production and browser completion is recorded in release `20261013T211202Z_4c5b1446` and deployment `dpl_CtfrwaVuh82zqVWDuaPDSRVzSzKC`, with scope `anonymous_exact_bytes_and_actual_browser_passed`. The prior verified Phase 1 release `20261013T172420Z_c9cd5748` and its references remain retained. Partial 2026, exposed baseline years, uncertified holiday exclusions, missing data, native TradingView/tick replay and live mapping timing qualifications persist. The final broad default workspace attempt again failed at the same two Bhishma prerequisites (226 tests/2 errors), leaving its four subsequent default processes unexecuted; the default six-step registry remains unchanged. Phase 3 EMA/cloud management, source H10 and new filter searches remain uncomputed.

## Post-seal transition presentation revisions

Two separately verified presentation-only revisions complete the session-transition coverage from the unchanged sealed tables: [comparison sessions](../../reports/exports/23_gc_overnight_breakout_15m/20261013T190208Z_phase2_gc_ob15m_v2/20261013T204013Z_comparison_sessions_r1/manifest.json) and [protected entries](../../reports/exports/23_gc_overnight_breakout_15m/20261013T190208Z_phase2_gc_ob15m_v2/20261013T204013Z_protected_entry_r1/manifest.json). Their publication IDs are `gc-overnight-breakout-15m-phase2-session-transitions-20261013-r1` and `gc-overnight-breakout-15m-phase2-protected-entry-20261013-r1`. The original 23 run publications remain unchanged; production selects 25 Phase 2 sources when these revisions are included.

Ten original-breakout-to-candidate-entry matrices cover every policy; protected-entry tables also expose the three breach-to-candidate matrices and breach-to-price-reclaim. Two ordered, full-column downloads partition all 22 transition kinds and 16,500 saved rows into disjoint 7,500-row and 9,000-row sets under the unchanged native download bounds. All 1,800 timing cohorts retain both horizons, all three levels, event types, bounds, denominators and unknown support. Protected entry performance displays 12 declared fields and downloads 24; a privately retained exact 450-row/61-column copied source preserves the full saved schema. Executable fills remain bound to their original field and are not substituted from a legacy accepted-breakout label.

These revisions recompute no research outcome or statistic and change no selection, policy, cost, source manifest or prior publication. The original 336-test numerical receipt remains unchanged. A separate seven-test presentation checker suite and exact saved-cell/final-inventory receipts cover the new exports. Manifest hashes are `85d8e590677f8b00d55781361c59db128dee3b4cb9f577c409a969dd1f9e89dc` and `bc40312a1897fb3f4ad0d92b8d2944e2ac92d14f2e53ee1a61c7a412a49bc34a`.

The production release preserves eight analysis groups and 26 study tabs. Protected preview, staged production and anonymous public production each matched all 1,418 prepared files, all 201 selected CSV attachment/media headers and five hard 404s. Actual browser checks covered all 26 report/run attributions, saved row controls and unavailable cohorts, desktop/mobile layout, protected-low figures and session transitions; representative retained layouts were checked on the exact preview artifact. Narada verify, 160 app tests without skips, lint, build and the 87-publication private source audit passed. Project protection is unchanged. The verified Phase 1 release `20261013T172420Z_c9cd5748`, deployment `dpl_DipGeCPi9mnfquhRqevqNpQLk3LG`, is the explicit rollback reference. No fresh native hosted CSV-download completion or off-device backup is inferred from served-byte verification.


## October 13 2026 Phase 3 execution authorization

The user explicitly authorized implementation, confirmed five-minute EMA20/50 input integration, backtests, meaningful tests, independent reconciliation, selected evidence/report preparation and publication through verified public production on the existing Narada study. The in-app browser is permitted. This supersedes the prior Phase3 planning-only scope; earlier completion notes remain historical records. Dedicated [Phase3 settings](config-phase3.json) and [protocol](protocol-phase3.md) govern the new run, frozen before historical scoring. Phase1 is the primary trading parent. The already frozen Phase2 selection is null, so Phase2 contributes descriptive event context only. No combined cloud policy, fitted probability model or all-history threshold optimization is authorized by implication.

The read-only input audit verifies the Phase1 manifest and source/runtime bytes and the same-contract cloud release's exact minute-source match, selected five-minute bytes, raw prices/contracts/calendar and full-history EMA/ATR recurrence. It preserves release inputs, prior runs/publications and unrelated dirty workspace changes. Statistical, artifact-integrity, publication-transfer and browser gates have separate scopes.
