# Presentation verification

Checked 2026-09-25 UTC. This is a presentation export from sealed study 11, not a new numerical run.

Commands from the Abacus root:

```sh
python3 reports/exports/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/20260925T031500Z_conditional_pine/generate.py
.venv/bin/python -m unittest discover -s studies/11_vwap_conditional_probabilities/tests -v
python3 scripts/check-agent-docs.py
python3 scripts/build-research-index.py --check
git diff --check -- studies/11_vwap_conditional_probabilities reports/exports/11_vwap_conditional_probabilities
```

Result: 123 product-specific lookup cells were rendered from the sealed A/B/C and updated-C tables; all four-class group numerators reconcile to their denominators. Fifteen focused tests passed, including the existing one-minute price-path edge cases and new source-preservation, sparse-suppression, and generated-lookup checks. Agent-documentation and index checks passed. The original OE, footprint, TICK, and alert logic was compared byte-for-byte apart from the indicator title.

Not verified: TradingView Pine Editor compilation, account-specific `request.footprint` entitlement, live chart rendering, and bar-by-bar TradingView-vs-Databento numeric parity. The browser-verification CLI is unavailable locally. The user's source was **not** sent to TradingView or published as part of this export. A private editor compile on a raw 2-minute ES/NQ/GC contract and replay across an anchor warm-up, a departure checkpoint, a corridor event, a missing one-minute bar, and a session boundary are still required before chart use.
