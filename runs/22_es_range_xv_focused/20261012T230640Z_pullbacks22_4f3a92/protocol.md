# Earlier trend → one-candle pullback → resumption

Protocol 0.4.0 is authorized for calculation and selected Vercel publication.
Read [settings](pullback.yaml), [input lock](inputs.lock.json), [decision notes](notes.md)
and the [study guide](README.md). This phase preserves both completed runs.

A is a nonempty uninterrupted completed directional leg. B is exactly one
completed opposite candle; R resumes A's direction. All rows are contiguous in
one eligible inferred session. Select at R's completion proxy without consulting
future outcomes. Unknown A starts enter only `unknown_start`, plus the overlapping
all cohort. Exact A buckets are 1–10, 11–15, 16–20 and 21+. A=1 is retained.

Continuation n=1–20 excludes R. An observed opposite/doji is failure for every
larger horizon; barriers are unknown above observed successes. F1 retracement
uses inclusive 25/50/75/100% R-body levels and a strict close beyond R.close.
Joint rates use all known F1; conditional rates use touched F1. Preserve unknowns.

Every metric is saved by setting, direction, A cohort, overall, session year,
all seven declared windows and year×window. Use R's completion as the window
anchor. Follow-up can cross named-window endpoints but not inferred sessions or
completion barriers. 2019/2026 coverage is partial and the terminal 2026-09-24
session is excluded. Input wall time is already normalized and inferred.

## Gross OHLC payoff proxy

Executable P&L is unsupported: RXV inputs lack contract identities/roll treatment,
exact completion timestamps, tick/quote sequencing and volume. Delivered minute
bars cannot resolve same-candle crossings or reliably match these signals.

Use F1.open as a hypothetical reference entry only when immediate completed
eligible F1 is known. Set a bullish stop at min(B.low,R.low)−0.25, mirrored for
bearish setups. The 0.25 buffer is a nominal exported-price assumption. Require
positive signed risk; retain invalid entries separately. Test fixed 1R and 2R
targets with ten physical completed candles starting F1, including opposite/doji.
These are two scenarios, not two simultaneous trades.

For each candle, evaluate its open before extrema. An opening cross exits the
proxy at the observed open, with its signed move/risk, including gaps. Otherwise,
stop-only is −1R, target-only is the target multiple; both levels touched gives
lower −1R and upper targetR. Do not infer intrabar order. An unresolved ten-bar
path exits at the tenth close. An earlier barrier is unknown unless the bracket
already resolved. Show missing entry, invalid risk, unresolved, ambiguous, stop,
target, timeout and known-outcome counts, gross mean-R bounds and positive-payoff
bounds. No commissions, slippage, dollar P&L or portfolio curve are invented.

## Verification and lifecycle

Stage in a fresh direct child of `work/22_es_range_xv_focused/`. Freeze settings,
this plan, notes, input lock, environment lock, exact source bytes and execution
command before examining outcomes. Verify all eight input pins. Retain ordered
setup and proxy-scenario ledgers, complete saved tables and input diagnostics.

Run the synthetic study suite in ordinary locked Python. The independent audit
must reconstruct every setup and proxy scenario from pinned input OHLC without
importing the numerical engine, compare every ledger/table cell and check group
conservation. Save the actual numerical TestResult, test-source bytes and command.
Prepare nine selected publication bundles before sealing and independently check
all displayed numeric cells, context bindings and selected CSV strings.

Seal only after artifact-bound execution, reconstruction, publication-transfer
and preseal receipts pass. Retain large ledgers in ignored research storage with
locators/checksums; never overwrite existing evidence. Export byte-identical
publication sources into unique presentation revisions. Narada only renders
saved rows. Run its verify/test/lint/build, private source audit, desktop/mobile
browser checks and exact hosted-byte release gates before production promotion.

This phase follows inspection of prior reversal outcomes. All historical results
remain exploratory; no year is claimed as untouched out-of-sample evidence.
Subsequent robustness tests need fixed decision rules and genuinely unseen data.
