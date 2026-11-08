# Decision notes

## 2026-10-30 — Phase 1 scope and provenance

- Chose unused study ID `29_verniman_level_reconstruction`. This is indicator
  implementation, separate from qualitative Study 27 and from Study 14's
  numerical/profile work. No shared Sahadeva extraction is needed.
- Read the user-supplied `VP Levels` attachment and preserved its exact bytes as
  [the baseline](reference/vp_levels_original.pine), pinned by
  [source-manifest.json](reference/source-manifest.json). Develop a separate
  `Verniman Levels` derivative; do not replace the baseline with Study 14's code.
- Read only the allowed generic Study 27 README, levels, glossary, method-model
  and unknowns-and-tensions documents. Their source definitions do not recover
  a deterministic HVE, PBT or LIS algorithm.
- Retain the supplied volume-profile arithmetic as a documented approximation.
  Choose strict period readiness and confirmed-bar timing before adding
  speculative candidate families. Defaults are inherited, not scientifically
  calibrated.
- Fix the initial supported clock to 18:00–17:00 futures, 09:30–16:00 RTH and
  18:00–09:30 overnight in New York on standard 1/5-minute equity-index futures
  ETH charts. A missing required boundary or period remains unavailable.
- Define the pre-open map as a copied information state at a configurable
  cutoff, default 09:25 NY. Today's actual RTH open and opening gap cannot enter
  that map. Later developing levels are separate.
- Require completed full-session/RTH sources to match the expected prior weekday
  (Friday for Monday), preventing an entirely absent day from leaving older
  references in a new pre-open map. Ignore off-session bars, enforce an exact
  overnight terminal bar, and roll previous-week references at Sunday 18:00.
- Keep status compact by default. Expand all 19 frozen/live candidate values
  when recording browser evidence. The optional live lines default off.
- The user's existing working tree includes data-publication and registry/index
  changes. Preserve those changes; do not inspect the protected daily-level
  releases or private intake to implement this indicator.
- October target/observation/answer sources were not opened by this documentation
  task. No target values were used and no accidental exposure is known here.
  The [verification record](verification.md) owns the complete task's exposure
  and browser status.
- Keep all new execution/browser evidence under a unique study-specific `work/`
  stage. Do not seal incomplete verification or publish the private script.

Later modules and the chronological evaluation design remain planned in
[plan.md](plan.md). Changes to those boundaries require a new recorded decision.
