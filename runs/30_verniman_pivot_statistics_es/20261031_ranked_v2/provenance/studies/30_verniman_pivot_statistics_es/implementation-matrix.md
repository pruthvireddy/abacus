# Ranked implementation matrix

Protocol: [2.0.0](protocol-2.0.0.md). Status begins as frozen implementation scope;
the final verification record identifies executed evidence and remaining limits.
Information time is distinct from the later outcome endpoint in every row.

Implemented source owners: [ranked_engine.py](src/ranked_engine.py) supplies new
events/exposures/episodes; [ranked_statistics.py](src/ranked_statistics.py) supplies
all 20 saved summaries, reusing the unchanged [engine.py](src/engine.py) baseline
for pivot price episodes, confirmation and retests. [verify_ranked.py](verify_ranked.py)
independently reconstructs new evidence; [verify_saved.py](verify_saved.py) checks
the unchanged baseline; [publish_ranked.py](publish_ranked.py) supplies both
bounded reports and exact cell/asset transfer checks. All rows are implemented;
the run's receipts determine whether their execution and verification passed.

| Rank / ID | Existing calculation / additional work | Observation unit and valid denominator | Information time | Narada target |
|---|---|---|---|---|
| 1 / S01 | New moving EMA6–VWAP transitions and separate RTH/Globex exposures | Eligible named day/section, including zero; per-day count | Three-minute close; full-day label later | Both: frequency |
| 2 / S02 | Reuse strict EMA6–pivot events unchanged | Pivot-matched day/section, including zero | Three-minute close | Pivot: frequency |
| 3 / S03 | Extend counts to fixed 0/1/2/3–4/5+ categories | Eligible named day/section | Window end | Both: count distribution |
| 4 / S04 | Extend observed native three-minute exposure rates | Valid observations × 3/60 hours; no exposure is null | Window end | Both: observed-hour frequency |
| 5 / S05 | Extend common-cohort price and EMA counts for both lines | Same eligible day/section for both series | Window end | Both: price versus EMA |
| 6 / S06 | Reuse initially unconfirmed pivot episode labels | Resolved confirmation or prior return; censored separate | Price break, label at resolution | Pivot: return before confirmation |
| 7 / S07 | Reuse returned unconfirmed penetration | Returned initially unconfirmed episodes with measured path | Return close | Pivot: break depth |
| 8 / S08 | Extend lag/movement distributions and confirmation-start paths | Confirmed pivot episodes; complete paths for each horizon | Actual confirmation close | Pivot: confirmation |
| 9 / S09 | Extend directional mean/median/positive shares to VWAP | Complete RTH forward event paths, each horizon/panel | Event close, outcome at endpoint | Both: movement |
| 10 / S10 | Extend excursions and 5/10/20-point reach to VWAP | Complete post-signal RTH minute paths | Event close, outcome at endpoint | Both: excursions and reach |
| 11 / S11 | New EMA-reference recross episodes | Complete RTH window or observed reverse; censored separate | EMA close; label at reverse/window end | Both: no recross |
| 12 / S12 | Extend first-event time/direction with no-cross days | Eligible days; timing conditional on first event | First close or window end | Both: first crossing |
| 13 / S13 | Extend day ordinals 1/2/3+ and first section panels | Complete RTH forward paths by ordinal | Event close | Both: crossing order |
| 14 / S14 | New pivot/VWAP ordering, tie/already-beyond separated | Matched EMA-origin episodes, 30-minute complete/resolved support | Origin close; label at second/reverse/end | Pivot: travel |
| 15 / S15 | New opening above/below/between/equal states | Matched eligible days and complete later event paths | Opening snapshot; later path labels | Pivot: opening path |
| 16 / S16 | Extend native cloud ordering/slope support/opposition | Events with known contemporaneous cloud; unknown retained | Event/confirmation snapshot | Both: cloud context |
| 17 / S17 | New continuous points/bps and fixed opening bands | Matched days and complete event paths by frozen band | 09:30 snapshot | Pivot: line separation |
| 18 / S18 | Reuse exact fixed-pivot retest fields | Complete 30m windows for incidence; observed touches for close classes | EMA close; label at touch/window end | Pivot: retests |
| 19 / S19 | Extend opening-range→AM/PM endpoint persistence | Eligible source-state day transitions, missing explicit | Section endpoints; never opening predictor | Both: persistence |
| 20 / S20 | Extend trailing20/60/120 versus disjoint preceding history | Each named cohort's chronological eligible sessions | Requested cutoff; actual coverage shown | Both: recent versus earlier |

No full Cartesian product is published. Public tables select bounded saved rows;
full private summaries retain supporting counts, periods, panels and null reasons.
