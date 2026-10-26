# Dated interpretation — 2026-09-24

Use the study as a chart-reading base rate: after the first countertrend RXV
bar closes, about three quarters of eligible signals get one more directional
bar, while roughly half get both C2 and C3. Read the exact product, setting,
direction, prior-run, and session row in `tables/lookup.csv` before applying a
number. The 1–2 prior-run bin is context; the 3–4, 5–7, and 8+ bins are the
prespecified main comparisons.

No positive main cell passed the frozen familywise and chronological screen
(`tables/headline_screen.csv`). The supported GC 10 bullish 8+ London cell has
a relatively high point estimate, but its adjusted difference interval includes
zero (`tables/headline_screen.csv` and `tables/period.csv`). Six cells have
negative adjusted difference intervals; they are descriptive downside checks,
not a new trading rule. In the stricter larger-chart sample, a one-bar aligned
snapback has a high C2-only rate but a much lower C2-and-C3 rate
(`tables/onebar_larger.csv`). Do not transfer the former rate to an extended
countertrend attempt.

The main opposing evidence is the lack of a stable positive two-more advantage
after multiplicity control, limited contrast for some candle-structure flags,
and GC export differences in selected 2026 sessions. RXV settings of one
product share underlying trades; they do not replicate independently. The
2024–2026 period was previously inspected. No fills, costs, stops, or payoff
distribution were tested, and prior work found large failures could outweigh
frequent small directional continuations.

Next research should first verify ATAS timezone and export/contract settings,
obtain independent later sessions, and retain a signal-level payoff and
execution study only if a clearly prespecified bar-count filter persists.
