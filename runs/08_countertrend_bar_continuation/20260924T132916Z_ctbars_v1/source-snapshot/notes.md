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
