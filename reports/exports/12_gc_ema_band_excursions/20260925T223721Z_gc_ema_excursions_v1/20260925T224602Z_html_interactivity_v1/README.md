# GC EMA excursion report — HTML presentation revision

This revision fixes the offline report's JavaScript percentage formatter,
which previously stopped all dynamic rendering at startup. The default
10-bar cooldown and 20-bar horizon view is now present in the HTML before
JavaScript runs. The selectors still expose all 35 combinations.

The [revised report](report.html) uses the same 595 saved numerical result
records as the sealed [source run](../../../../../runs/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/report.html).
Only presentation behavior changed. The source run remains unchanged.

Run the selector check from the workspace root:

```sh
node studies/12_gc_ema_band_excursions/tests/verify_report_interactivity.mjs reports/exports/12_gc_ema_band_excursions/20260925T223721Z_gc_ema_excursions_v1/20260925T224602Z_html_interactivity_v1/report.html
```
