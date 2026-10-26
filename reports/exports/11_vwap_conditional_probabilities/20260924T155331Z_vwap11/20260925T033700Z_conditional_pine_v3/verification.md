# Presentation verification — revision 3

Revision 1 compiled with `CE10205` at the monolithic lookup switch. Revision 2 split it into six-case functions, then compiled with `CE10117`: 117,267 tokens against a 100,256-token limit. Revision 3 removes repeated explanatory prose from lookup strings while preserving all 123 keys, rates, denominators, and uncertainty. The new Pine compile result remains to be checked.

Checked 2026-09-25 UTC. This is a presentation export from sealed study 11, not a new numerical run.

Commands from the Abacus root:

```sh
python3 reports/exports/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/20260925T033700Z_conditional_pine_v3/generate.py
.venv/bin/python -m unittest discover -s studies/11_vwap_conditional_probabilities/tests -v
python3 scripts/check-agent-docs.py
python3 scripts/build-research-index.py --check
git diff --check -- studies/11_vwap_conditional_probabilities reports/exports/11_vwap_conditional_probabilities
```

Result: 123 product-specific lookup cells were rendered from the sealed A/B/C and updated-C tables; all four-class group numerators reconcile to their denominators. All 15 focused tests passed, including one-minute price-path edge cases, source preservation, sparse suppression, generated lookup checks, and exact comparison of the 123 displayed rates/support counts with revision 2. Agent-documentation, research-index, and whitespace checks passed. The original OE, footprint, TICK, and alert logic is preserved apart from the indicator title. The generated Pine source shrank from 143,471 to 78,455 bytes; compiled-token reduction is not directly inferable and awaits TradingView.

Not verified: TradingView Pine Editor compilation, account-specific `request.footprint` entitlement, live chart rendering, and bar-by-bar TradingView-vs-Databento numeric parity. The browser-verification CLI is unavailable locally. The user's source was **not** sent to TradingView or published as part of this export. A private editor compile on a raw 2-minute ES/NQ/GC contract and replay across an anchor warm-up, a departure checkpoint, a corridor event, a missing one-minute bar, and a session boundary are still required before chart use.
