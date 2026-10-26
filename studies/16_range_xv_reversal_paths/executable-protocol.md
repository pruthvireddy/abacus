# Executable protocol 2.0.0 — ordinary choices before outcomes

The revised plan governs this run. The user authorized implementation, execution,
verification, reporting and sealing on October 1, 2026. No external publication
or laptop/browser interaction is authorized. These implementation details resolve
ordinary choices before event outcomes are extracted.

- Price arithmetic uses signed int64 at scale 1e-9, converted exactly from Decimal.
  All classifications, price differences, grids and extrema use integers. A price
  with finer precision stops execution rather than being rounded. Floating-point
  ratios are calculated only after exact differences. Raw rows remain retained.
- A valid segment contains consecutive original nonbarrier rows within one session.
  The final row has no within-segment completion; the preceding bar can complete
  at its start. A flagged repeated row is excluded as a barrier, without stitching.
  It cannot anchor the prior row's completion. Include-all retains originals.
  Invalid OHLC always creates a barrier. Gaps strictly greater than 3600 seconds
  are flagged, retained primarily and omitted in the declared sensitivity.
- A segment's initial leg has an unknown start. After a completed opposite/doji
  predecessor, the next leg has a known start. Unknown L remains null in evidence
  and never enters the primary baseline. All export-edge and unknown events stay
  in the audit ledger. The feature dictionary fixes formulas and null flags.
- Every order-k cohort requires k physical followers completed through the next
  observed bar's start. Strict-k also requires positive durations from R through
  Bk. Known failures outside a complete window are saved as known failures in
  all-candidate bounds, but do not enter complete-window probabilities.
- Ordinary numeric transformations use log1p on known nonnegative sizes, durations
  and pace before training-only median imputation and z-score scaling. All other
  predictors remain as declared in the feature dictionary. Missing indicators are
  kept if they vary in training. Zero-variance columns are removed using training
  only. Decision window, era and compact L bins use training-observed vocabulary,
  sorted with the first category as reference; unseen categories use zero dummies.
- Logistic minimizes summed binary log loss plus lambda/2 times squared coefficients.
  Ridge minimizes summed squared error plus lambda times squared coefficients.
  Intercepts are unpenalized. Penalties are exactly 0.1, 1, 10, chosen by validation
  loss/MAE, ties favour smaller penalty. Newton uses deterministic line search,
  80 iterations maximum and step tolerance 1e-8 or mean-gradient tolerance 1e-9.
  Ridge uses NumPy linear solve. Nonconvergence stops execution. Probability score
  clipping is 1e-6; capped-F predictions clip to [0,10] with raw predictions saved.
- Development/validation/later sessions are synchronized across all eight charts.
  The last and first observed sessions around 2020 and 2023 are embargoed only
  for prediction/selection. Future windows remain within segments/sessions, and
  their endpoint proxies are audited against the next evaluation block.
- Development-only chart/direction quartiles use pandas linear quantiles at
  .25/.5/.75; duplicate cuts collapse. Bins are right-closed; missing is separate.
  Interactions are log1p(L) times pace, efficiency, chop20 and relative R body.
- The finite condition pool has one L-only predicate for each displayed L bin;
  context candidates pair L in {2,3,5,6,7} with lower/upper development quartiles
  of pace, efficiency or chop20. R candidates add relative R body above its upper
  quartile. Each condition is chart/direction-specific, with at most three predicates.
  Nomination requires positive development and validation F3 lift, at least 300
  events/100 dates in each, and validation synchronized 95% lower lift bound >0.
  At most one per condition type, three total, is chosen by largest validation
  lower bound, then support, then stable ID. All inspected candidates are saved.
- Standardization uses unique events in the union of subgroup and reference as
  pooled weights on common supported decision-window/era strata. With an ordinary
  all-reversal reference this equals baseline counts; direct L3/L2 uses both groups.
  Fixed point-estimate weights are used
  in uncertainty; intervals condition on those descriptive weights.
- The synchronized bootstrap uses all observed input sessions, including zero-event
  dates, 2000 replicates and NumPy default_rng seed 161001. Repeated session draws
  are converted to event-sum weights. Five-session moving blocks sample starts
  uniformly from valid consecutive observed-date blocks, concatenate and truncate
  to the original date count. All comparisons use the same paired weights.
- Clock marks require the segment to be observed through decision+T; then the
  last future-bar close with completion <=T is saved. Same-second future chains
  are descriptive order marks; strict coverage requires positive duration through
  the marked bar. No-future-completion and boundary censoring stay separate.
- Nonoverlap accepts the earliest strict eligible path and a subsequent entry row
  strictly after its exit row per chart/direction/horizon. It does not claim independence.
- Reports and SVG figures render saved tables only. Programmatic checks validate
  numeric provenance, local links, XML assets, input preservation and event recounts.
  Final prose/renderer corrections do not alter frozen numerical code or outcomes.

The selection lock is saved after development/validation and before later metrics.
Prior study/input inspection is disclosed; no pristine or confirmatory holdout claim
is made. Failure profiles, correlated settings, unverified clocks/rolls/fills, OHLC
intrabar ambiguity and fixed assumed costs limit this to price-path associations.
