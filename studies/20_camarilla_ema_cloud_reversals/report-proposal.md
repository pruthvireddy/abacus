# Camarilla futures study report proposal

Draft for review, 2026-10-08. Proposed title: **Camarilla Reversals and the EMA
Cloud in ES NQ and GC**.

The report will answer which pivot levels produce favorable subsequent price
behavior, what the EMA cloud adds, and which effects survive a specified exit
policy, costs and later evaluation periods. The opening will state the strongest
supported finding and its limits, even if the finding is negative or inconclusive.
The [protocol](plan.md) supplies the definitions and the
[data inventory](data-inventory.md) supplies the candidate input coverage.

## Reading order

| Section | Reader's question | Proposed evidence |
| --- | --- | --- |
| Findings and applicability | What did we learn and where does it apply? | Three instrument summaries; main comparison, uncertainty and execution qualification |
| Data and sample | Which history actually contributes? | Calendar coverage, exclusions, prior-session quality, rolls, accepted/entered/completed counts |
| Signal definitions | What is an R3 or S3 rejection in this study? | Rule table, EMA modes and fixed examples of accepted and rejected signals |
| Main horizon results | What happens after entry? | MAE/MFE/delta tables for ES, NQ and GC, with separate long and short views |
| Level and cloud comparisons | Is the cloud useful, and which levels differ? | R2/S2, R3/S3 and R4/S4 panels; pass/fail coverage and no-filter comparisons |
| Excursions and timing | How large are moves, and how soon do they occur? | Quantile curves, joint MAE/MFE distribution, adverse move before favorable threshold |
| Trade simulation | Can a specified policy capture the move? | Fixed 3R results, inner/opposite-pivot alternatives, timeout and cost scenarios |
| Stability | Does one period or a few events dominate? | Annual and weekly cohorts, time-of-day and prior-known volatility/range groups |
| Robustness and controls | Which assumptions change the conclusion? | Strict input subset, cooldown, contact tolerance, parity branch and bounded extensions |
| Interpretation and limitations | What is usable, uncertain or unsupported? | Instrument-specific conclusions, negative cases, sample selection and observed-history qualifications |
| Reproducibility and publication record | Can this exact finding be referenced again? | Frozen protocol, run ID, input/config/code identities, table IDs, checks and saved downloads |

The local report can include the complete declared grid. The public reading path
will show the main comparisons prominently and carry the full grid in selected
summary downloads and separately named supporting reports if necessary.

## Main horizon table

Use one instrument, level pair, EMA branch, side selection and chronological split
per clearly labeled panel. The main panel uses R3/S3, both directions and five-minute
20/50 alignment. Put the no-filter panel adjacent to it. Do not combine cells from
different entry definitions or data-quality branches.

**Columns:** bars, elapsed minutes, accepted events, completed N, average MFE in
ATR, average MAE in ATR, average signed close delta in ATR, favorable close
percentage, MFE greater than MAE percentage, and the 95% interval for mean delta.
Use 5, 10, 15, 30 and 50 bars, corresponding to 25, 50, 75, 150 and 250 minutes
when the path is uninterrupted.

Keep medians, 75th/90th percentiles and cancellation reasons in a second table.
The count alongside every statistic is its actual denominator. Undefined values
render as an em dash; measured zero remains zero. The report proposal contains no
sample performance numbers.

## What close above means

Three separate percentages prevent an ambiguous success label:

| Metric | Exact interpretation |
| --- | --- |
| Favorable close | Long closes above its entry; short closes below its entry |
| Close above entry | Literal terminal close greater than entry, for either direction |
| Close on the defended side of the pivot | Long closes above the touched support; short closes below the touched resistance |

Equality is a tie and does not count as favorable. It remains in completed N.
The defended-pivot statistic can be favorable while entry P&L is unfavorable,
so the two should appear in separate columns or tables.

## Level and confluence table

For each product, show all four EMA branches for each of the three level pairs.
The primary horizon is 15 bars. Columns will include branch, level pair, completed N,
contributing sessions, filter acceptance percentage, mean signed delta with its
interval, favorable-close percentage, median MAE and median MFE.

Add a separate comparison table for differences from the no-filter branch and
for cloud-passing versus cloud-failing events. State that these are conditional
associations: filtering changes the population. Actual one-position policy results
receive their own table because a skipped signal can free the instrument for a
later entry.

## Weekly and annual tables

The weekly table follows the user's screenshot:

**New York Monday week start | accepted | completed N at 15 bars | favorable close
at 15 bars | mean signed delta in ATR | missing/censored.**

Weekly membership follows the confirmation-close week, even if an outcome completes
later. Include observed eligible weeks with zero signals. The total row uses
event-weighted totals, not an unweighted mean of weekly percentages. First/last
partial weeks are labeled. The public page can show a declared recent set of weeks;
the selected weekly CSV preserves the complete summarized history within the
publisher's size limits.

Annual evidence shows completed N, distinct contributing sessions, delta and its
interval, median MAE/MFE, net R per eligible session, and exclusion share. Label
2026 as January 1 through September 18 rather than a full year. Annual summaries
will distinguish development, validation and final evaluation data.

## Figures that add useful information

1. **Horizon curves:** mean and median signed delta, MAE and MFE across holding
   horizons, with uncertainty and count annotations.
2. **Level and cloud comparison:** fixed panels by instrument and side, with the
   estimate and interval at 15 bars. Sparse cells remain visible.
3. **Joint excursion distribution:** show how many events experience both large
   favorable and large adverse moves. A ratio of average MFE to average MAE cannot
   describe this ordering.
4. **Time to threshold:** favorable threshold reached before an adverse threshold,
   neither reached, censored or ambiguous; supplemented by time to MFE and MAE.
5. **Annual stability:** identical axes within each metric, with evaluation periods
   labeled and data coverage alongside the estimates.
6. **Trade-policy outcomes and costs:** target/stop/timeout/ambiguous frequencies,
   daily cumulative net R and drawdown bounds under declared fill assumptions.

Figures will be rendered from saved evidence, with exact table/metric references.
Example price charts will come from a fixed selection rule that includes rejected,
losing, missing and ambiguous cases. Avoid selecting only attractive winners.

## Extra statistics worth retaining

| Statistic | Why it matters |
| --- | --- |
| Median and 90th-percentile MAE | Describes typical discomfort and the adverse tail that a mean can hide |
| Median MFE and favorable-threshold hit rate | Distinguishes broadly recurring movement from a few very large winners |
| Favorable threshold before adverse threshold | Tests path ordering relevant to stops and targets |
| Time to MFE and time to recovery | Helps distinguish quick rejection behavior from late unrelated movement |
| Filter coverage and opportunities per eligible session | Shows whether improved averages come with very few opportunities |
| Net R per eligible session and per trade | Measures opportunity loss as well as quality of retained trades |
| Cost budget before break-even | Shows how much all-in cost the observed gross result could absorb |
| One-minute entry-delay sensitivity | Checks whether assuming an immediate next-open fill drives the result |
| Largest-event and best-month contribution | Shows whether a small tail dominates the result; any removal is diagnostic, not a replacement headline |
| Weekly/monthly consistency with intervals | Describes stability without pretending each event is independent |
| Censoring and ambiguity rates | Reveals how missing paths or unresolved barrier ordering affect conclusions |

No MFE-derived “optimal exit” will be presented as an achievable return. Learning an
exit from a realized path requires a separate, later evaluation period.

## Abacus publication and future reference

The proposed stable study slug is **camarilla-ema-reversals**. After approved
execution and verification, its study page will link the selected immutable
report publication and any related negative or later results. Final URLs will use
the existing website's /studies/ and /reports/ routes; no URL is claimed as
published at the proposal stage.

Sahadeva will prepare the selected source content before sealing the analytical
run. Narada will consume that saved content through source contract 1.1. The
current renderer supports static evidence sections; this proposal does not assume
a live parameter optimizer on the website. Changing research criteria produces
a newly identified analytical run and report.

The current contract permits up to 30 sections, 12 columns and 100 rows per
displayed table. A practical main publication can use approximately 24 sections:
scope, findings, coverage, rules, three product horizon tables, three product
confluence tables, excursion quantiles, weekly table, annual table, two trade-policy
tables, six figures, robustness, limitations and provenance. A finalized outline
must be counted against the schema rather than extending it ad hoc.

Select at most four compact CSV downloads:

1. Core horizon grid: 3 products × 3 pairs × 4 EMA modes × 2 sides × 5 horizons =
   360 rows for the designated final evaluation period.
2. Core 15-bar annual grid: 3 products × 3 pairs × 4 EMA modes × 2 sides × 9 calendar
   years = at most 648 rows.
3. Weekly R3/S3 alignment summary: one clearly identified product per selected
   download, normally ES; the other product histories remain in local evidence or
   a supporting publication.
4. Trade-policy and cost summary, keeping the selected row count below 1,000.

Each CSV must respect 24 columns, 1,000 rows, 256 KiB per file and 512 KiB combined.
If a summary exceeds the byte budget, select a smaller explicitly declared scope
or create a supporting publication. Never truncate silently or expose the private
event ledger or vendor bars to fit the report.

Every public estimate carries its units, denominator, horizon, branch, evaluation
period, uncertainty, evidence status and a saved-source reference. The publication
record carries its report/asset hashes and analytical run identity. Preserve
existing public reports and sealed runs; later changed methods, values or
interpretation receive new analytical identities.

The later handoff is: validate source bundle, publisher dry run, selected
publication, authored study catalog entry, app verify/test/lint/build, static
preview, then the repository's verified hosted release process. The current scope
finishes at this reviewable proposal. Implementation, analysis and website changes
follow the user's review.
