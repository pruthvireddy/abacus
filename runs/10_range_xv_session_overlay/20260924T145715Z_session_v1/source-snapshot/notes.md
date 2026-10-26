# Decision notes

- 2026-09-24: User requested Asia, London, and New York segments for the last
  two or three studies. Include all three recent Range XV studies, 07–09.
- This overlay follows inspection of their reports and is exploratory. It
  cannot supply an untouched holdout or alter sealed source runs.
- Study 07's old export-clock event selection is retained. Only the event's
  decision-time segment is remapped with the documented normalized clock;
  quiet-breakout calibration needs a separate corrected-clock rerun.
- After the first unsealed segment calculation, add the already-known study
  09 ordinary-pair run-age-two sensitivity as a **post-result diagnostic**.
  It does not enter the declared segment screens. Retain the first stage in
  `work/` and create a new stage with the additional table.
