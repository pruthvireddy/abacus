# Exploratory findings

All 217,366 A→one B→R setups were independently reconstructed from 2,815,095
input rows. Counts are 99,632 / 68,017 / 49,717 for 4/5/6 RXV. The settings
observe the same underlying history and are not independent replications.

Overall pooled-direction continuation has known-outcome P(n≥1) of
80.25% / 80.32% / 80.35% and P(n≥2) of 52.00% / 52.24% / 52.52%. R is
excluded. These coincide with the prior single-opposite-leg reversal subset;
the new evidence adds explicit earlier A length. Refer to
`tables/pullback_continuation.csv`: year blank, timeframe_id=all_hours,
direction=all, earlier_leg_bucket=all, n=1 or 2, settings 4/5/6.

At 50% F1 body depth, the joint touch-and-favorable frequency is
18.84% / 17.76% / 19.00%; favorable given touch is
48.81% / 47.44% / 49.16%. These denominators differ. Refer to
`tables/pullback_retracement.csv`, the same overall selectors, level_percent=50.

The fixed next-open structural-stop OHLC proxy has negative overall gross mean
R under both target scenarios, even using the favorable intrabar-order bound.
Upper mean R is approximately −0.0237 / −0.0212 / −0.0185 for 1R targets and
−0.0337 / −0.0316 / −0.0284 for 2R targets. Refer to
`tables/pullback_payoff.csv`, the same overall selectors, target_multiple=1 or 2
and horizon_candles=10. Unknown and invalid cases remain excluded and counted.
This tests one fixed hypothetical price path model, not fills or net P&L.

A high candle-colour continuation rate therefore does not establish a profitable
entry/payoff model. Earlier-length/session cells can suggest follow-up hypotheses,
but choosing the best historical cell would require new fixed rules and unseen
forward validation. All historical years have already been inspected.
