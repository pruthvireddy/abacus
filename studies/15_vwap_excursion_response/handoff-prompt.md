# Coding agent prompt for the anchored VWAP study

Copy the following prompt into an agent working in Abacus. The detailed plan
and proposed settings are already saved in this study directory.

```text
Implement, execute, verify and report a fresh anchored-VWAP research study in
/Users/ppanati/Documents/projects/abacus.

Use studies/15_vwap_excursion_response/ as the owner. Read its README.md,
plan.md, study.yaml, inputs.lock.json and notes.md completely. The plan is the
detailed specification. Freeze an executable protocol before inspecting new
outcomes. This prompt authorizes coding, local research execution, verification,
local report generation and sealing a new run. Do not stop at another plan.
Do not implement a Pine indicator, publish externally, deploy or place orders.

First read AGENTS.md, README.md, ARCHITECTURE.md, studies/AGENTS.md,
studies/README.md, packages/sahadeva/AGENTS.md, packages/sahadeva/README.md,
packages/bhishma/AGENTS.md, packages/bhishma/README.md, data/README.md,
runs/README.md, templates/README.md and requests/README.md. Respect applicable
additional guides. Preserve unrelated dirty/untracked work. Preserve all old
VWAP studies, indicators, catalog snapshots and sealed runs unchanged. Reuse
the pinned data, not old result tables, probabilities or outcome-tuned rules.

Implement three modules on completed two-minute candles for ES, NQ and GC:

1. Following the first fresh close beyond 2, 2.5 and 3 sigma in an excursion,
   calculate full-horizon MAE, MFE and terminal price delta for both continuation
   and fade directions at 5, 10, 20 and 50 candles, plus 15 candles. Entry is the
   next two-minute open. Report means, medians, tails, points/ticks/signal-sigma
   units, average close and centered close change, close above entry open, and
   final candle close above its own open as separate metrics. Preserve ties.
2. From the same signals, calculate cumulative VWAP-touch probabilities and
   first-touch timing at those horizons. Causally evolving VWAP is primary;
   departure-frozen VWAP is secondary. A touch uses a tick-rounded +/-1-tick
   zone against one-minute price ranges with only the VWAP available before
   each minute. Gaps and reference overtakes are not invented traded contacts.
3. After each parent excursion's first valid return touch, confirm the containing
   two-minute candle and measure from the next two-minute open. Report bounce
   toward the original excursion side and continuation through VWAP separately,
   with MAE/MFE and terminal delta at the same horizons. Also report symmetric
   0.5-touch-sigma first-move outcomes: bounce first, through first, neither and
   same-minute ambiguous. Do not credit touch-candle movement to a later entry.

Follow the plan's causal episode/rearming rules: one first signal per threshold
per parent excursion and one first-touch event per parent. Keep upper/lower
sides and nested threshold cohorts identifiable. Do not count every outside
candle as a new event. Use valid early-anchor data; explicitly report anchor
age and the specified 30-minute-minimum sensitivity instead of silently
retaining the old study's warm-up rule.

Use four separate New York-clock windows and their matching anchors:
Asia 20:00–03:00, London 03:00–09:00, NY 09:30–16:00, Globex 18:00–17:00.
Keep main horizons within their originating window, with per-horizon exclusions
and a common complete-50-candle cohort. Use DST-aware timestamps. Preserve
missing/undefined outcomes separately from false; never fill missing minutes.

Data locations and APIs:
- Resolve roots through abacus_bhishma.paths.load_workspace_paths and
  config/paths.local.toml or the documented ABACUS_* overrides. Publication
  root is the workspace containing catalog/ and data/, not a package directory.
- Use abacus_bhishma.feature_loader.load_session_anchored_vwap with
  version='1.0.0', timeframe='2m' and the study input lock. Physical feature
  files are under data/features/bars/2m/feature_set=session_anchored_vwap/
  version=1.0.0/product=<ES|NQ|GC>/year=<YYYY>/part-000.parquet.
- Use abacus_bhishma.continuous_loader.open_continuous_dataset with
  variant='unadjusted' for matched one-minute source paths, under
  data/curated/continuous/1m/product=<product>/roll=volume_lead_v1/
  variant=unadjusted/year=<YYYY>/part-000.parquet.
- Verify manifest and every consumed partition hash. Honor available_at,
  contract IDs and fixed-point units; convert adjusted feature levels to the
  matching raw contract coordinates before measuring paths. Derive 2.5-sigma
  bands locally from published VWAP/sigma. Never rebuild a published release.
- The feature release ends 2026-09-18 with sparse complete-day eligibility.
  Disclose retrospective selection and product-specific coverage. Do not
  silently extend the feature history using the older one-minute source.

Use price change as the working meaning of delta unless the user clarifies
otherwise. True aggressive buy-minus-sell volume delta is absent from the pinned
OHLCV inputs. Never fabricate it from candle direction or volume. If requested,
create a properly specified Bhishma request in requests/inbox/, document the
gap and continue the price-based work. Measure both bounce and through responses
unless the user explicitly narrows this scope.

Keep run.py thin, study code in src/ and numerical tests in tests/ under this
study. Use the existing locked workspace environment. Complete a causal
feature/coverage pilot and synthetic tests, freeze protocol-1.0.0.md plus its
machine-readable companion, then compute outcomes. Do not tune definitions
using outcomes. Use the plan's shared-week bootstrap, counts/support flags,
year and chronological stability summaries; history is exploratory, not unseen.

Stage in work/15_vwap_excursion_response/<unique-UTC-run-id>/. Produce event,
threshold, touch and horizon ledgers; exclusions; metrics; CSV/Parquet tables;
figures; a master HTML/Markdown report and separate Asia, London, NY and Globex
HTML/Markdown reports. Keep products separate inside each session report.
Explain denominators, directions, horizon units, target definitions and limits.
All displayed values must come from saved tables. Include negative findings.

Verify causal timing, horizon arithmetic, side symmetry, episode deduplication,
touch/reference/gap handling, ambiguous barriers, session/DST/roll boundaries,
missingness and denominator reconciliation. Independently recount actual paths
from the raw one-minute source and visually inspect reports/figures. Preserve
full-horizon MAE/MFE even after a touch or barrier resolves.

Seal only verified evidence into a new runs/15_vwap_excursion_response/<run-id>/
with exact commands, frozen config/protocol/input lock, code revision and dirty
snapshot, environment lock, source and artifact hashes, checks and advice.
Keep large evidence outside ordinary Git with retained locators/checksums and
documented retention; do not leave its only copy as disposable work/ output.
Never append to or overwrite any completed run. Update this study's README,
notes and study metadata; document any explicit reference-run selection.

Run focused study tests and audits, python3 scripts/check-agent-docs.py, and
regenerate the research index followed by --check when metadata changes.
Run ./scripts/check-workspace if shared package/configuration changes require
it. Do not rebuild Narada for research-only changes. Do not run archived scripts
into historical locations. Conclude with links to the new reports, exact
verification results, meaningful findings and any remaining data limitation.
```
