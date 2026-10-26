# Planning decisions

## 2026 October 1

The user requested an elaborate reversal/continuation study plan and a copyable
prompt for another agent. The requested outcomes are follow-through frequency
and candle count, MAE/MFE, average delta, the landing after three subsequent
candles, elapsed time, and conditioning on the preceding leg's candle count.
This turn is planning only; no reversal outcome extraction, numerical engine,
new research run, strategy update, or publication is authorized here.

Study 16 was unused at creation. The newly imported eight FX Range XV charts
are the proposed universe based on the immediate conversation. An optional
clarification was requested about universe and the meaning of delta; the
default is FX-only and signed price delta. “rangeXC” is interpreted as Range XV.
These defaults may be corrected by the user; they are not findings.

Existing studies 01/04/08/09 were inspected as methodological context. This
plan preserves the first-opposite-colour event and counts additional future
same-direction candles separately from R. It adds exact prior lengths, a
three-physical-bar price/time endpoint, quality/censoring diagnostics, and
source-specific tick regimes. Older data, reports, manifests, scripts, and
sealed runs are preserved and not reinterpreted or pooled.

Direction uses exact source-price comparisons. The candle-order cohort keeps
completed same-second sequences; the strict time/price cohort isolates
positive-duration completion proxies. Prior-run start censoring and future-run
end censoring must be distinguished. Fixed-horizon prices include immediate
continuation failures; conditioning on future successes is explicitly secondary.

“Three candles” means F1/F2/F3 after R, including dojis/opposite bars. The chart
reference enters at F1 open and exits at F4 open, after F3's proxy completion.
MAE/MFE include that exit mark to account for gaps and exclude R's own range.
Exact intrabar ordering and hit times remain unavailable from these exports.

Primary source verification found a material 6S tick change effective trade
date 2022-05-02. The plan uses constant 2026 outright tick equivalents plus
raw price units, with mandatory pre/post 6S tables and historical tick units
only as a separate event-date normalization. CME sources are linked in the
plan/settings. No inference is made that ATAS reconstructed old chart bars
with verified historical tick/contract/roll settings.

Only planning metadata and existing input manifests have been inspected for
this study. No new event frequencies, MAE/MFE, time distributions, parameter
selection, or profitable rule have been calculated. Protocol settings remain
proposed and `frozen_at_utc` is null. The receiving agent must freeze its
executable protocol after input/unit audits and before outcomes.

Planning verification: maintained documentation/link checks, metadata/input-pin
consistency, and generated research-index freshness. Numerical verification,
the event ledger, figures, report QA, evidence retention and run sealing are
assigned to the receiving agent by the handoff prompt.

## 2026 October 1 revised handoff

The user requested a complete rewrite after researching Range XV mechanics and
reported that the previous receiving agent sought screenshots and controlled
laptop applications to interpret candles. Proposed protocol 2.0.0 replaces the
earlier proposal and explicitly prohibits those workflows. OHLC comparisons
supply all primary direction/doji/reversal labels. Figures are derived report
outputs; programmatic report checks replace browser/GUI inspection.

New chart learning: Range XV uses price movement rather than equal time; runs
and compressed sideways activity reflect its construction. The exact algorithm
is private and need not be reconstructed. Opposite-price movement already in
R is not a post-entry gain. A high continuation rate and a predictive lead-up
are hypotheses to estimate, not assumed findings.

The revised scope adds causal-availability feature definitions for prior-leg
pace, distance, efficiency, overlap, recent chop/leg history and R geometry;
same-chart/direction baselines; incremental comparisons beyond R geometry;
chronological development/validation/later evaluation; limited logistic/ridge
models and at most three frozen interpretable conditions. It also adds failure
profiles, excursion reachability, cost assumptions and secondary stale
completed-close clock marks with explicit coverage. These are study proposals,
not computed evidence or tested execution rules.

Existing input identities are unchanged. Proposed settings remain unfrozen.
This revision turn prepares the plan/prompt and verifies documentation/metadata.
The copied handoff authorizes the receiving agent to implement, execute, verify
and seal a unique run; this authoring turn does not run study calculations.

## 2026 October 1 execution authorization and freeze

The user supplied the complete handoff and explicitly authorized implementation,
local execution, verification, reporting and sealing protocol 2.0.0 without routine
approval pauses. No external publication or GUI/browser/laptop interaction is
part of this run. Existing unrelated dirty work and historical evidence remain.

Study-local run.py, src/ and synthetic tests implement the protocol in the locked
workspace environment. NumPy/pandas/Arrow are available; sklearn/scipy/plotting
libraries are absent, so the bounded local Newton logistic/ridge implementation
and computed SVG renderer require no dependency or shared-package changes.
The executable-protocol.md supplement fixes ordinary choices, feature dictionary,
solver normalization, candidate pool/support rules and synchronized bootstrap.

All pinned manifest/mirror/source/enhanced/supporting hashes, source rows/prices,
completion proxies and quality flags passed before event extraction. The initial
input-only preparation attempt encountered a NumPy string-array assembly error;
it produced no event outcomes. The corrected input audit is staged under the
unique run ID 20261002T010500Z_ohlc200_161001. Its original bytes and attempt remain
in work; no historical output was rerun or overwritten.

The executable freeze precedes real event extraction and follows 39 passing
synthetic checks, including a complete synthetic model/summary pipeline. Later
features/rules are selected only from development/validation; later outcome
summaries remain unread until selection.lock.json exists. Independent verification
and report refinements do not change the frozen feature, target, model or condition
settings. An additional include-original-barrier sensitivity test accompanies the
final checks. No pristine-holdout claim will be made.

Unit audit: all prices fit constant quote-equivalent grids. 6S setting 5 has 4,083
pre-change rows off the historical 0.0001 grid; they remain unrounded with raw and
constant units, and historical conversions are secondary diagnostics. Mandatory
pre/post 6S panels retain this provenance limit. Long gaps use strictly >3,600
seconds as the plan specifies. Raw input evidence is retained, including excluded
edge sessions and unknown starts. Reports are validated from saved evidence with
numeric provenance, local links and SVG parsing, without GUI inspection.

## 2026 October 1 verified completion and sealing

Run 20261002T010500Z_ohlc200_161001 completed the full frozen protocol, including
all thresholds/horizons, bounded development/validation model selection, every
nominated later condition, synchronized and five-session uncertainty, quality,
common-window, nonoverlap and feature-history sensitivities. Later outcomes were
read only after the selection lock; no feature, penalty, model or condition was
revised after that inspection. The seven frozen numerical module identities
remain unchanged from pre-outcome freeze.

Final checks pass: 40 synthetic tests, 556 source-row recounts across every chart
and direction (20 anomaly cases absent), all later predictions reconstructed from
saved preprocessing/coefficients, loss reconciliation and 64 independently
recomputed paired bootstrap intervals. Offline HTML/Markdown values, local links
and computed SVG assets are validated programmatically. The first verifier
attempt stopped at a pandas GroupBy `observed` property/column collision; explicit
column indexing repaired the auditor. Research code, labels, predictions and
numerical results were unchanged. Both attempt logs are retained.

The CLI now restricts mutable stages to work and offers read-only verify-sealed;
verify-report rechecks a presentation refresh against already-verified frozen
numerics. These interface/auditor refinements do not change research methods.
The final report adds explicit strict-cohort, progression, within-L quartile,
yearly, prediction-stability and candidate denominator/difference audit tables.
Those audits apply the prespecified cohorts/cutpoints and never select a new rule.

Results and interpretations are in the run report and named CSV tables, including
continuation, price-paths, L2-L3-direct/adjustment/yearly, model-paired-improvements
and candidate-support-summary. The primary incremental-prediction hypothesis is
not supported by the later prespecified models; negative/inconclusive scores are
retained. The surviving L-only colour association is separate from its negative
three-bar price mean. No executable strategy, pristine holdout, causal effect or
independent-confirmation claim is selected. The efficiency clause in the nominated
L=2 condition uses a collapsed discovery cut and adds no distinct efficient/choppy
population. No R-geometry condition met nomination requirements.

Every headline uses raw price or constant q. Historical tick fields outside 6S
individual era panels mix event-date units and are diagnostics only. No off-grid
price was rounded. Large raw-bar/event/prediction/bootstrap evidence is retained
under configured Sahadeva storage, with checksum locators. No off-device backup
was performed. Existing inputs and historical runs remain preserved. Nothing is
published externally. Navigation is regenerated and checked after sealing.
