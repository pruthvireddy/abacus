# Session VWAP web presentation

Study `05_session_vwap` · registered source run `20260923T015900Z_vwap3` ·
revision `20261006T210008Z_web05`.

[Publication source](publication.json) · [source map](source-map.json) ·
[manifest](manifest.json) · [content checks](content-verification.json) ·
[static checks](static-verification.json) · [browser checks](browser-verification.json).

Publication ID: `session-vwap-vwap3-20261006-web05`.
Local route: `http://127.0.0.1:4173/reports/session-vwap-vwap3-20261006-web05/`.
Use [Narada's static preview](../../../../../apps/narada/README.md#setup-and-checks).

This bounded presentation selects three primary outcomes, exhaustive A/C classes,
all-history/final matched baselines at half-sigma and eight-tick barriers, and
saved 2026 eligibility rows. All 96 numerical values are transferred from saved
CSV/JSON evidence; percentage-point scaling is explicit. The saved SVG is rasterized
at twice its native resolution with an extended white right margin for existing
denominator labels. Bars, positions, values, text and colors remain unchanged.
The original unlabeled PNG is preserved in the source run.

Price-path evidence does not establish fills, costs or net profitability. The
exploratory context run is excluded. Research findings, reference and source
artifacts remain unchanged. Only the publication JSON and one raster enter Narada.

The manifest records exact preparation, publisher and verification commands.
`prepare.py`, `rasterize.mjs` and `verify-content.py` are presentation-only tools,
not analytical entry points. Reproduction must use a new revision/publication ID;
do not overwrite this completed revision. Renderer source and tool versions are
retained under `provenance/`. Browser images are verification artifacts, not public assets.
