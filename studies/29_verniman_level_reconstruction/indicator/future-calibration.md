# Future Autopivot calibration protocol — proposed, not executed

User-supplied daily pivots can support gradual, testable rule improvements.
This is supervised calibration from examples; Pine does not train itself and
no future improvement is guaranteed. Reinforcement learning would require a
separately defined reward and evaluation protocol. No labels were loaded and
no training, fitting or target-source inspection was performed for this draft.

## Label intake

A simple user list of `date, actual contract, pivot price, optional note` is
sufficient to start intake. The attached blank CSV supplies a fuller audit
schema; unavailable fields stay blank instead of being invented.

Required before fitting: trading date, actual dated contract, target point or
explicit target interval, minimum tick, unadjusted-price convention and an
identified feed/configuration for the feature bars. The default prediction
cutoff remains 09:25 America/New_York on standard five-minute ETH candles.
Keep source publication time distinct from the time the label was observed
or entered. Unknown source availability remains unknown. A label may be learned
from after the cutoff as supervised hindsight; that does not establish that the
source had published or selected it before the cutoff. A later-published or
retrospective label must retain that qualification.

`label_role` distinguishes an intended pre-open pivot, a retrospective analyst
choice, a revised pivot or another kind of reference. Do not combine roles as
though they were the same ground truth. Use point price or low/high interval;
retain uncertainty rather than silently rounding. Append label revisions with
stable IDs; preserve earlier values and source references.

## Freeze the experiment

1. Retain the current indicator, candidate generation, settings, code hash and
   daily frozen feature snapshots as the baseline. All features must be
   available by 09:25; include the 09:20–09:25 bar, exclude 09:25–09:30 and later
   session information. Label prices or labels' later context never enter the
   prediction features.
2. Choose chronological training, validation and untouched final holdout ranges
   before fitting. The existing protected October 15–20 development and October 21–27
   hidden-test material remains untouched unless separately authorized. If dates
   or answers have already influenced design, record that exposure and reserve
   later genuinely untouched dates. Do not use random train/test shuffles that
   leak adjacent sessions or future regimes into model selection.
3. Use the training portion to diagnose candidate coverage first, then compare a
   small declared set of interpretable scoring weights, thresholds or branch
   rules. Do not insert date-specific prices or choose different windows for
   different days. Preserve all tried variants and failed hypotheses.
4. Select a version using only validation results and predeclared metrics; use
   the final holdout once. Reject changes that merely improve training fit or
   trade away too much coverage. Keep the existing rule if evidence is weak.
5. Freeze the chosen version and log predictions prospectively before receiving
   the next day's target. Review later batches on an expanding chronological
   training window with separate later validation windows. New examples update
   a future version; they do not rewrite historical predictions or old reports.

## Metrics and comparisons

Use price error in minimum ticks, not instrument-dependent points. For interval
labels, error is zero inside the declared interval and distance to its nearest
boundary outside it. Retain point/interval identity and original prices.

Report median and mean absolute error, a tail measure such as 90th-percentile
error, fixed-tolerance hit rate, top-k candidate coverage and availability.
Choose k and tolerances before looking at comparison results. Report the full
eligible-day count, defined predictions, unavailable predictions, missing labels
and excluded/contract-incompatible rows separately. An unavailable prediction is
not silently dropped from the all-eligible coverage denominator. Conditional
price-error metrics must state their defined-prediction denominator.

Compare every proposed change on the same sessions with the frozen indicator
and a simple declared POC baseline: select whichever of YPOC or ONPOC is closer
to the cutoff price P, tied to YPOC. Also retain the nearest eligible candidate's
error as an oracle diagnostic: if the label is far from every generated
candidate, improving ranking alone cannot solve the missing-candidate problem.
The training candidate ledger must include the existing selected pivot as well
as the other ranked references. The UI omits the primary price only to avoid
duplicate display; it must not become an omitted training option. Report primary
plus top-k-other coverage separately from full-pool coverage. A smaller label-price
error does not prove better trade outcomes or profitability.

## CSV columns

- `label_id`, `label_revision`: stable identity and append-only revision number.
- `trading_date`: YYYY-MM-DD in New York; `contract`: actual dated exchange symbol.
- `pivot_price`: point target, or `pivot_price_low` / `pivot_price_high`: interval.
- `minimum_tick`, `feed`, `price_adjustment`: tick/measurement compatibility;
  adjustment must identify unadjusted actual-contract prices for this version.
- `label_role`: intended pre-open / retrospective / revised / other, with notes.
- `cutoff_local`, `timezone`: normally 09:25 and America/New_York.
- `source_published_at`, `label_observed_at`: offset-aware ISO timestamps when
  known; blank means unknown, never a fabricated pre-open availability time.
- `source_reference`, `notes`: provenance, qualification and concise reasoning.

The feature-bar data, history coverage, settings and code hashes belong in a
separate frozen input manifest. Providing target labels alone cannot resolve
feed, session or contract differences.
