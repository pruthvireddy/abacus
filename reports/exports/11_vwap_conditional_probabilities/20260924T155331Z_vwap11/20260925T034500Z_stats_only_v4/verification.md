# Presentation verification — revision 4

Revision 1 compiled with `CE10205` at the monolithic lookup switch. Revision 2 split it into six-case functions, then compiled with `CE10117`: 117,267 tokens against a 100,256-token limit. Revision 3 removed repeated explanatory prose from lookup strings. At the user's request, revision 4 is a standalone table-only indicator: it drops all visible VWAP, band, target, OE, TICK, and footprint output while preserving the 123 rate cells and A/B/C state logic. The new Pine compile result remains to be checked.

Checked 2026-09-25 UTC. This is a presentation export from sealed study 11, not a new numerical run.

Commands from the Abacus root:

```sh
python3 reports/exports/11_vwap_conditional_probabilities/20260924T155331Z_vwap11/20260925T034500Z_stats_only_v4/generate.py
.venv/bin/python -m unittest discover -s studies/11_vwap_conditional_probabilities/tests -v
python3 scripts/check-agent-docs.py
python3 scripts/build-research-index.py --check
git diff --check -- studies/11_vwap_conditional_probabilities reports/exports/11_vwap_conditional_probabilities
```

Result: 123 product-specific lookup cells were rendered from the sealed A/B/C and updated-C tables; all four-class group numerators reconcile to their denominators. All 15 focused tests passed, including exact comparison of the 123 displayed rates/support counts with revision 3. The standalone script contains no visible plot, fill, shape, label, line, OE, TICK, or footprint calls. It has one hidden `display.none` plot to satisfy Pine's output requirement. The generated source is 61,899 bytes, down from 78,455 bytes in revision 3. Agent-documentation, research-index, and whitespace checks passed. Pine's compiled-token size still requires an editor compile.

Not verified: TradingView Pine Editor compilation, live chart rendering, and bar-by-bar TradingView-vs-Databento numeric parity. The browser-verification CLI is unavailable locally. The user's source was **not** sent to TradingView or published as part of this export. A private editor compile on a raw 2-minute ES/NQ/GC contract and replay across an anchor warm-up, a departure checkpoint, a corridor event, a missing one-minute bar, and a session boundary are still required before chart use.
