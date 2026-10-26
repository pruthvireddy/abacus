# Study 08 decision notes

- 2026-09-24 05:47 UTC: froze the definitions, groups, five GC exclusion dates,
  session windows, support threshold, and 210-comparison positive screen in the
  plan and settings before the first outcome extraction.
- The 05:51 and 05:55 UTC stages were exploratory implementation checks and
  remain under `work/`; neither was sealed. An audit found that the early
  summary included equal-second larger-chart ties and that the initial ledger
  gave session-final signals with no completion a spurious larger state. These
  were implementation errors against the frozen protocol. Tests were added,
  the join and summary were corrected, and a fresh 13:29 UTC extraction was
  performed without changing outcome thresholds or group definitions.
- The long-history source timezone remains inferred from the export clock and
  daylight-saving session-open pattern. This study uses the normalized enhanced
  wall times exactly as stored and retains the raw source timestamps.
- This work is local research only. No Narada publication source or deployment
  was prepared.

## 2026-10-06 — Phase 3 local publication navigation

Featured presentation: [20261006T235500Z_web08r2](../../reports/exports/08_countertrend_bar_continuation/20260924T132916Z_ctbars_v1/20261006T235500Z_web08r2/publication.json) · [manifest](../../reports/exports/08_countertrend_bar_continuation/20260924T132916Z_ctbars_v1/20261006T235500Z_web08r2/manifest.json). Stable local study route: `/studies/countertrend-bar-continuation/`; immutable report route: `/reports/08-countertrend-bar-continuation-20261006-web-r2/`.

Registered reference retained: `20260924T132916Z_ctbars_v1`. Catalog navigation is maintained in [Narada](../../apps/narada/content/studies.json). Saved findings, evidence status and research-reference metadata are unchanged. This is local static publication; no deployment or research execution.
