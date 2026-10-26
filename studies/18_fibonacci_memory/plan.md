# Fibonacci Memory v1 implementation protocol

Prepared 2026-10-06. Scope: implement the user's attached Pine v6 specification
and validate deterministic synthetic examples. No historical market-data run,
profitability finding, parameter selection, dataset publication, or deployment
is authorized or performed by this implementation task.

The observation unit is a first eligible retracement touch per confirmed swing
and bucket. The five buckets are 0.236, 0.382, 0.500, the combined 0.618–0.650
pocket, and 0.786. Long and short populations remain separate; Combined pools
their retained records. Endpoints and continuation extensions are drawings only.

## Timing and frozen references

At each completed bar, process already scheduled observations first, detect
touches against the previously established ladder second, and accept newly
confirmed pivots last. A ladder confirmed on bar t first permits touches on
t+1. A touch on t uses ATR(14)[1] and previous close, signals at t's close,
and enters at the next available chart bar's open. The signal bar is excluded.

Freeze the swing identity (direction and both pivot bar indexes), zone, ATR,
entry, horizon, distances, and estimated round-trip tick cost. An observation
survives later swing replacement. The horizon includes the entry bar as bar 1.
Defaults: H=16, target=1 ATR, stop=0.5 ATR, cost=0 ticks, 200 completed records
per bucket and direction, display emphasis minimum=30. These are initial
research settings, not optimized findings.

## Outcomes and uncertainty

Maintain full-window MAE/MFE after any hypothetical exit. Classify the first
barrier as target, stop, or same-bar ambiguous; classify unresolved events as
timeout at the Hth bar's close. Inspect the open before intrabar extremes.
Targets fill at their configured price; stop gaps fill at the open. Ambiguous
payoffs retain stop/target bounds. Subtract frozen round-trip tick cost in R.

Pre-exit excursions use previous-bar extrema plus the observed exit-bar open
as a guaranteed lower bound. Intrabar exits retain bounds including the exit
bar's adverse/favorable extreme; open-gap exits are exact. No exit-bar order is
invented. Bars to exit count entry as bar 1; gaps between chart bars are not
invented observation bars.

Completed cohorts include timeouts and ambiguous events, exclude pending rows,
and use the same bounded sample for every statistic. Combined can contain up to
400 records at the default capacity. Use linear interpolation at rank
(n-1)*p for medians and P90. Report target-first W/N to (W+A)/N; Wilson 95%
intervals are displayed only with no ambiguous outcomes. These binomial
intervals do not correct clustering by swing/day. No composite score is added.

## Implementation and verification

Source belongs in `pine/`; deterministic checks and a restricted Python adapter
for the Pine numerical kernel belong in `tests/`. Save transient verification
output under `work/18_fibonacci_memory/`. The adapter executes the actual Pine
kernel's supported syntax; it is not a TradingView compiler or full runtime.
Embed optional deterministic Pine self-checks using the same production helpers.

Check long/short symmetry, first-bar gaps, touch availability and deduplication,
H=1 and H=16 indexing, same-bar ambiguity, pre-exit bounds, immutable resolved
payoff, incomplete events, pooled samples, ring eviction, percentiles, Wilson
limits, equal-price/different-bar anchors, and extension prices. Do not claim
TradingView compilation/runtime validation unless it actually occurs.

No input market dataset is pinned: this artifact consumes the user's chart when
installed. The two pasted source/specification attachments are retained with
hashes as implementation inputs. Future offline research needs its own pinned
data and execution protocol before any market-data calculation.
