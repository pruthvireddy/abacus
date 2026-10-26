# Range XV reversal study agent prompt

Copy the entire text below into an agent conversation in the Abacus workspace.
It replaces the earlier handoff and authorizes the receiving agent to complete
the local study. The [full plan](plan.md) and [settings](study.yaml) contain the
expanded method and acceptance requirements.

```text
Implement, execute, verify, report, and seal the Abacus study
16_range_xv_reversal_paths using its revised proposed protocol 2.0.0.
Workspace: /Users/ppanati/Documents/projects/abacus.

OBJECTIVE
Use the existing numeric OHLC exports to identify completed Range XV reversals,
measure their subsequent continuation and price paths, and test whether the
lead-up predicts how much follow-through occurs. Produce a complete reproducible
study with clear conclusions, including negative and inconclusive results.

A reversal has already incorporated an opposite price move before it is known.
The hypothesis is that continuation may be common and that some preceding-leg
contexts may add predictive value. Test this; do not assume it. Distinguish
ordinary persistence created by chart construction from incremental prediction,
and distinguish price-path evidence from executable trading profitability.

AUTHORIZATION AND WORKFLOW
I authorize implementation, local execution, verification, reporting and sealing
a new run. Continue through completion without routine approval pauses. Resolve
ordinary choices in writing before outcomes; ask only for a material missing
input or ambiguity that prevents valid research.

Read README.md, ARCHITECTURE.md, AGENTS.md, studies/AGENTS.md,
packages/sahadeva/AGENTS.md, runs/README.md and templates/README.md. Then read
studies/16_range_xv_reversal_paths/plan.md, study.yaml, inputs.lock.json,
notes.md and README.md. The revised full plan governs details in this prompt.
Preserve existing dirty work, input files, historical evidence and sealed runs.

DATA ONLY: DO NOT USE COMPUTER VISION OR LAPTOP CONTROL
Work from the pinned local CSVs using code. Do not open/control ATAS or other
laptop applications, capture/request screenshots, inspect the user's screen,
use OCR/image recognition, run browser automation, or visually classify candles.
Do not research candlestick pictures or pattern names. Exact close == open is
a doji; close > open is bullish; close < open is bearish. These numeric rules
are sufficient. Generate report charts from computed evidence and validate
reports/files programmatically; no GUI/browser inspection is required.

INPUTS AND NEW CHART LEARNINGS
Use only the eight pinned 6E/6B/6J/6S Range XV charts at settings 4 and 5 in
data/range_xv/fx_20170721_20261001/.
Verify all identities in inputs.lock.json, including the manifest/mirror hash:
ac74f7a9e26f41799f6a66501db6dae272f4a9a0fc7a51c419362377e2432e8d.
Keep every chart and bullish/bearish reversal direction separately visible.

Range XV organizes price movement rather than equal time. It can compress
sideways activity and display sustained moves as runs. Its exact algorithm is
proprietary. Use the observed bars rather than recreating it or inventing a
reversal threshold. The 4/5 settings are price-tick parameters, not minutes or
a guarantee about every body or high-low span. Measure actual candle geometry.
This is a reversal within exported Range XV bars, not ATAS's separate Reversal
chart type. No external lookup is necessary for the OHLC study.

There is no volume/order-flow delta in these files. Average delta means signed
price change. Enhanced timestamps already represent inferred New York wall
time; never convert them again. Completion is proxied by the next bar's start.
Exclude first session 2017-07-21 and partial final session 2026-10-01 from primary
estimates, while retaining audit records. Apply the declared 6S tick-era split.

EVENTS AND COUNTING
Use exact Decimal/fixed-point price comparisons without rounding or epsilon.
R is the first completed non-doji opposite-direction bar immediately after a
known maximal uninterrupted non-doji directional leg. L is that prior leg's
length and excludes R. Include L=1; dojis break legs and cannot be reversals.

B1/B2/B3/... mean successive PHYSICAL bars after R, whatever their colour.
F counts only consecutive completed bars AFTER R with R's direction. A completed
opposite/doji bar ends F. Never count R itself or skip an intervening bar.
Example: bull bull bull | R bear | bear bear bear bear | bull means L=3, F=4.
The new leg has five candles including R. An exact F requires an observed
breaker; a boundary after four followers gives F>=4, not a known exact F=4.

Do not cross sessions or quality barriers. Distinguish unknown prior-leg starts
from censored future ends. Keep null/unknown separate from false/zero. Retain
all original rows, flag repeated records and long gaps, and implement the plan's
primary/sensitivity policies. Same-second rows support order-based counts but
cannot prove distinct execution opportunities. Keep candle-order and strict
positive-duration price/time cohorts separate with explicit denominators.

CONTINUATION STUDY
Report P(F>=1/2/3/4/5/10), conditional progression, immediate opposite/doji
failure, and L-to-F counts/percentages with unresolved/censored columns.
Display L=1..10, 11-15,16+, retain exact lengths, and directly compare L=2 and L=3.
Give capped min(F,10) mean/median/mode/quantiles on the common ten-bar cohort,
separate exact-run summaries and censor bounds, and reconcile the capped mean
with the sum of continuation probabilities. Show common three-bar probabilities.

LEAD UP AND REVERSAL CONTEXT
Use only information available when R completes. Follow the plan's exact feature
dictionary: L; prior price distance/span/body totals; pace/duration; close-path
efficiency; overlap/wicks; previous three completed legs; prior 10/20-bar chop
and range context; R body/span/wicks/close location, opposing displacement and
formation duration; R relative to the prior leg and recent range; session/era.
Keep zero-duration and zero-denominator features undefined with explicit flags.

Determine whether an identical leg count behaves differently when fast/slow,
efficient/choppy, or followed by different R geometry. Freeze discovery-only
quartiles and limited interactions. Record feature availability and missingness.
Do not use subsequent F, later extremes, future duration or full-sample thresholds
as predictors. Do not silently lose short-history events from baseline results.

PRICE PATHS AND THREE BAR LANDING
Primary horizon: B1/B2/B3 regardless of colour, including reversals that fail.
Reference entry E = B1 open. Exit mark X3 = B4 open after B3 proxy completion.
Signed delta D3 = direction(R) * (X3 - E). R's completed move is not a profit
available at this entry. Do not enter at R open or include R's range in MAE/MFE.

Compute MAE/MFE from entry, highs/lows of B1..B3 and the exit-open mark, with
long/short symmetry and nonnegative magnitudes. Include gaps. Add horizons
1/2/5/10, separately labelled last-bar-close and structural close-to-close marks.
Report means/medians, quantiles, favourable/flat/adverse landing probabilities,
MAE/MFE tails and sample/date counts. Retain raw prices, constant tick-equivalent
units and declared known-at-decision range normalizations.

Show failures versus successes, including F>=3 with adverse D3 and early colour
breaks with favourable D3. Add the prespecified favourable/adverse excursion
attainment and fixed assumed cost sensitivities. Do not infer stop-versus-target
order or claim net execution performance from OHLC alone.

ELAPSED TIME
For h=3, elapsed time is B4 start minus B1 start, using timing proxies. Report
mean/median/quantiles and 1/5/15/30-minute completion shares. Give time-to-k
consecutive followers with attainment rates and censoring. Locate MAE/MFE in
physical bars and report possible hit-time intervals, not invented intrabar times.
Include the plan's separate 5/15/30-minute completed-close marks with coverage,
actual timestamp and staleness. Never present those as exact prices at T.

TEST WHETHER THE LEAD UP ADDS PREDICTIVE VALUE
Use the same-chart/direction ordinary reversal baseline, common eligible cohorts,
and declared session/era standardization. Report absolute lift, price-path
differences, uncertainty and support. Do not use a 50-percent coin flip as the
chart's assumed baseline or treat correlated 4/5 charts as independent evidence.

Use chronological development 2017-2019, validation 2020-2022, and later
evaluation 2023-2026, with synchronized session splits, purge/embargo and
training-only preprocessing. Record prior inspection and avoid claiming a
pristine holdout. Save final model/condition settings before reading later
outcome summaries. Never random-split bars.

Compare B0 constant training baseline; B1 context plus R geometry; M1 B1 plus
prior L; M2 M1 plus richer lead-up/history. This tests whether L helps beyond
what R itself already shows. Fit the plan's limited logistic/ridge models for
F>=3, supplementary F>=1, D3 and capped F. Save predictions and compare Brier,
log loss, calibration, regression errors and paired incremental improvements
on identical later event sets. Keep model choice/regularization search bounded.

Nominate at most three simple interpretable conditions from development and
validation only, freeze them, and evaluate every one later. Nominate none if
unsupported. Show coverage, counts/dates, continuation, delta, MAE/MFE, elapsed
time, stability and failures. Call a stable predictive association an association;
a verified executable trading edge requires evidence this dataset cannot supply.

UNCERTAINTY AND REPRODUCIBILITY
Use the declared synchronized session bootstrap: 2,000 replicates, seed 161001,
with paired comparisons and five-session block sensitivity. Show sparse cells,
missing support, censoring, yearly/session/6S-era panels and overlap sensitivity.
6S changed tick size on trade date 2022-05-02; retain raw prices and the plan's
constant equivalents, never round off-grid values or silently pool historical
changing tick units. Preserve negative/inconclusive results and all candidate
selection history. Freeze the executable protocol before extracting outcomes.

DELIVER AND VERIFY
Implement study-local src/, tests/, run.py and reproducible summary/verify/seal
entry points using the locked workspace environment. Stage a unique run under
work/16_range_xv_reversal_paths/. Save the event ledger, feature dictionary,
predictions, selection lock, all numerical tables, uncertainty, input/quality
and leakage audits, offline HTML/Markdown reports and clear computed charts.
Every displayed value must derive from saved evidence. No external publication.

Validate independently with synthetic long/short examples and real source-row
recounts: L=2/3, F=0/4, dojis, unknown starts/censored ends, same-second bars,
barriers, B4 exit indexing, gaps, excursions, features, split leakage, units,
clock staleness and denominator identities. Check report links/assets and values
programmatically. Run focused study tests and required documentation/index checks;
run broader workspace checks only for shared package/configuration changes.

Seal only after verification under a unique
runs/16_range_xv_reversal_paths/<run-id>/ with frozen settings, input hashes,
code/dirty snapshot, environment lock, exact commands, exclusions and artifact
hashes. Retain large event evidence with locators/checksums outside ordinary Git.
Update study notes/metadata and regenerate/check the research index.

Finish with direct answers: baseline follow-through frequency and typical count;
L=2 versus L=3 and other prior legs; whether richer lead-up improves later
prediction beyond R geometry; where price lands after three bars; average signed
delta and MAE/MFE/tail risk; how long it takes; and which conditions remain
supported, unsupported or inconclusive. Link the report and evidence. Do not
stop at a plan, pilot, partial metrics table or promise to continue.
```
