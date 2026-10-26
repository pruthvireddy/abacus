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
