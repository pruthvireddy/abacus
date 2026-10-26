# VWAP OE fade statistics verification

Local checks on 2026-09-29 passed **15 numerical-helper tests**. They exercise
the actual Pine helper expressions for strict two-sigma signals, both fade
directions, every-close versus fresh-cross semantics, evolving prior bands,
five independent cooldowns, rejected-signal behavior, next-open timing,
missing/partial entries, inclusive session-end boundaries, path truncation,
directional MAE/MFE and close delta, translation invariance, and randomly
generated paths compared with independently computed signed-price offsets.

Manual code review checked that pending entries are processed before current
signals are queued, all statistical state commits on confirmed bars, long and
short signs are handled symmetrically, all consumers use the selected cooldown,
session clocks reset independently, arrays stop paths at 100 candles, and
incomplete horizons do not contribute zero-valued outcomes. The saved OE and
pasted-reference sources are preserved byte-for-byte.

The documentation/link checks, input-independent JSON validation, whitespace
checks and research-index freshness check passed. No published dataset, sealed
run or old indicator export was changed. No historical research calculation
or numerical report was generated for the larger planned study.

## Plot-limit correction, 2026 September 29

The user reported TradingView runtime error RE10140 with 74 plot counts and
requested only two days of VWAP curves while keeping historical buy/sell markers.
The correction uses polylines for all VWAP and sigma curves, retains the latest
two observed sessions per anchor, removes the invisible gradient fills, and
separates OE marker visibility from curve visibility. Historical buy/sell and
FADE markers remain plot shapes. Statistical-engine code, selected-cohort FADE
marker conditions, tables and the lower-pane diagram are unchanged.

Source accounting gives a conservative maximum of 33 plot counts: two `plot`
calls at up to two counts each, nine `plotshape` calls at up to three counts
each, and two `alertcondition` calls. No `fill` remains. Eight independent
two-session drawing queues can create at most 40 price-chart polylines; the two
lower-pane polylines bring the bound to 42 against the declaration's limit of
50. A temporary local probe translated the delivered queue helper with fake
drawing APIs and checked weekend retention, third-anchor eviction before its
first drawable point, repeated redraw/deletion, disabled streams and the
combined drawing bound. This checks queue logic, not native Pine rendering or
realtime rollback. All 15 existing numerical-helper tests passed again.

**Not verified:** native Pine compilation, historical/realtime execution,
native UDT/array behavior, compiler/runtime acceptance, actual table layout,
and TradingView-versus-Abacus numerical parity. A read-only TradingView editor
inspection found an existing unrelated saved script; it was not overwritten,
restored, saved or published. The new source was not uploaded to TradingView
or added to the existing saved chart.

Before relying on chart statistics, compile the delivered file in a new private
Pine Editor script, use standard two-minute candles, and replay an upper and
lower signal, a continuous outside-band sequence at each cooldown, a missing
bar, an anchor reset, a late-session event, a year boundary and an unfinished
right-edge path. Verify next-open references, full-path sample counts and that
input changes recalculate all tables together. Confirm original footprint and
TICK permissions and inspect the lower-pane layout at the intended pane size.
For the rendering correction, load at least three sessions of each anchor,
including a weekend if available; confirm that only the latest two curves per
anchor remain while older buy/sell markers remain visible. Switch to Active
local session, enable Globex, and advance into a third anchor with replay to
verify eviction. Hiding VWAPs must leave marker history and table counts intact.
