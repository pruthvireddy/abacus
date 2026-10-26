# Independent review before outcomes

Review date: 2026-10-21. This review used source inspection and synthetic inputs
only. It did not inspect strategy outcomes from the market-data sample. The
[frozen protocol](protocol-1.0.0.md) and
[reporting decisions](reporting-decisions.md) define the experiment; the eventual
freeze receipt records the executed source identities.

## Event and execution review

The event engine and separately authored verifier agreed across 400 reproducible
synthetic sessions, 285 generated candidate records, and 6,400 variant outcomes.
The test checks all returned reference fields, rather than only net profit. It
uses seed `2602101`, both directions, price and zone pivots, randomized valid
five-minute/minute OHLC and EMA/ATR values, the declared proximity and buffer
settings, and one/two/four tick slippage. The synthetic candidate count is a
recorded observation from this test, not an expected market-sample count or an
assertion about research performance.

The retained [reference parity test](tests/test_reference_parity.py) compares
candidate identities, reaction timing, stops, masks, entry timing, costs, target
selection, absent fills, unavailable targets, ambiguity bounds and excursions.
The focused [engine suite](tests/test_engine.py) separately covers explicit
boundary examples for DST, bar completion, entry cutoffs, episode expiration,
approach suppression, separate-bar touches, stop invalidation, gaps, target
trade-through, costs and missing inputs.

Known-open target gaps have temporal priority over later minute extremes; only
unresolved intraminute double touches receive adverse-first/optimistic bounds.
Exit timestamps for intraminute events mean minute completion, and excursion
values are through-exit-minute OHLC envelopes. They do not identify the ordered
post-entry or pre-exit path within that minute.

## Reporting and lifecycle review

Review findings were routed to their owners before outcome execution:

- Retain full-denominator primary estimates as undefined if an eligible daily
  pair is undefined, while labelling available-pair diagnostics separately.
- Use generic left/right labels for comparisons whose policies are targets or
  variants; reserve early/confirmed interpretation for entry comparisons.
- Retain target comparisons on common defined days and on the both-filled
  subset, with the subset selection disclosed.
- Give the board explicit robustness columns containing dollar differences and
  intervals, rather than selecting columns by insertion order.
- Label confirmation rates as confirmed-policy **fill** rates per common
  candidate. Filtering, cancellation, cutoff and target availability affect
  these rates. A saved hypothetical confirmation timestamp after structural
  invalidation is not an observed valid confirmation event.
- Separate expired confirmation examples from invalidated examples, show the
  coverage waterfall early, provide a model schematic and disclose table units.
- Use the last completed pre-open ATR14 for the prior-known opening volatility
  cut; keep completed-reaction ATR available separately in the event ledger.
- Hash consumed staged configuration/settings together with audited inputs, and
  check frozen identities before and after execution phases. Hardcoded scientific
  defaults agree with the versioned protocol and study settings.

The numerical verifier reconstructs candidate and execution behavior independently
without importing engine/reporting implementations. Hash verification of a saved
table is distinct from independent recalculation of that table; its verification
receipt must describe the actual recalculated scope. The owning agents resolved
and tested changes before the final freeze; the freeze and test receipts retain
their exact final source bytes and counts.

## Synthetic commands recorded during review

From the workspace root, using the existing locked environment without sync:

```sh
UV_CACHE_DIR=/private/tmp/abacus-uv-cache ./scripts/uv run --locked --no-sync python -m unittest discover -s studies/26_es_opening_pivot_cloud/tests -p test_engine.py
UV_CACHE_DIR=/private/tmp/abacus-uv-cache ./scripts/uv run --locked --no-sync python -m unittest discover -s studies/26_es_opening_pivot_cloud/tests -p test_reference_parity.py
UV_CACHE_DIR=/private/tmp/abacus-uv-cache ./scripts/uv run --locked --no-sync python -m unittest discover -s studies/26_es_opening_pivot_cloud/tests
```

Observed results at this review point: 50 engine tests passed; one reference
parity test passed; the combined suite passed 78 tests in 8.514 seconds. The
execution-phase test receipt is authoritative for the final frozen suite.
An initial invocation without the writable `UV_CACHE_DIR` failed to initialize
the sandbox-protected default uv cache; the commands above succeeded without
environment synchronization.
