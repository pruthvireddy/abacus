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
