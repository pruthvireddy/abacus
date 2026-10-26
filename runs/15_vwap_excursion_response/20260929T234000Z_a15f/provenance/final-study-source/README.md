# Anchored VWAP excursion and return study

Study `15_vwap_excursion_response` is a new, **planned** investigation of price
movement after a band departure, return to VWAP, and the response after that
return. No outcomes have been computed and no executable protocol is frozen.

The scope is ES, NQ and GC, separately for Asia, London, New York and the full
Globex day, on two-minute candles. The proposed thresholds are 2, 2.5 and 3 sigma;
the primary horizons are 5, 10, 20 and 50 candles, with 15 candles also reported.
The old VWAP studies remain historical records; their statistics will not be
inputs to this study.

- [Detailed research plan](plan.md)
- [Copyable coding agent prompt](handoff-prompt.md)
- [Proposed settings](study.yaml)
- [Pinned input identities](inputs.lock.json)
- [Decisions and assumptions](notes.md)

The three-module historical study remains at planning and handoff stage. The
handoff prompt authorizes the receiving agent to implement, execute, verify and
seal a new local research run. The receiving agent must first check current
repository instructions, verify inputs and freeze the executable protocol.
Actual research run commands must be documented here once that code exists.

## Chart indicator companion

A subsequent user request authorized the separate
[VWAP OE two-sigma fade statistics indicator](pine/README.md). It keeps the OE
visuals on the price chart and adds a lower-pane MAE/MFE diagram, horizon table,
independent cooldown comparisons and weekly opportunities. It computes from
loaded TradingView bars; it does not use old saved rates or execute the planned
historical study. Its every-close/fresh-cross options and inherited OE session
defaults are documented separately from the proposed research protocol.

The [Pine source](pine/vwap_oe_fade_stats.pine) has passed 15 focused local scalar
helper tests; native TradingView compilation and replay remain unverified.
Run those checks with:

```sh
python3 -m unittest discover -s studies/15_vwap_excursion_response/tests -p 'test_pine_fade_stats.py' -v
```

See the [study guide](../AGENTS.md), [architecture](../../ARCHITECTURE.md), and
[evidence lifecycle](../../runs/README.md). The chart companion is separately
authorized; external publication, deployment and order execution are outside
the current scope.
