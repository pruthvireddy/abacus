# Daily Facts volume pilot protocol

Protocol 1.0.0, frozen November 8, 2026 before the notebook calculation.
This pilot checks the handoff from the immutable Bhishma Daily Facts release to
an ordinary study notebook. The population is the full weekday roster for ES,
NQ and GC from June 28, 2021 through September 18, 2026. Use the same product
calendar and independent window readiness stored by the release.

| Theme / insight | Question | Population and observation unit | Input | Estimate and denominator | Visual |
|---|---|---|---|---|---|
| Coverage / pairing | How many asset sessions can support the hour comparison? | Weekday roster by asset, one row per asset/session | Calendar status and first60/last60/RTH readiness | Count roster, calendar exclusions, missing paired windows, valid pairs, and pairs with complete positive RTH volume | Table |
| Volume / paired hours | How does first-hour volume compare with last-hour volume on the same session? | Paired valid first60 and last60 windows within each asset | Pinned first60/last60 volume | Mean and median contracts for both windows, median paired difference and fraction of pairs with higher first-hour volume | Table |
| Volume / RTH share | What share of RTH volume occurs in each hour? | Valid pairs with complete positive RTH volume | Pinned share fields and RTH volume | Mean per-session shares on one common denominator per asset | Grouped bar chart and table |

Pair within each asset and date. Asset denominators can differ. Use equal weight
per qualifying session for mean shares, preserve zero observed volume, and count
ties in the paired denominator. Keep gaps outside the relevant windows separate
from eligibility. Hour volumes and shares use completed windows and the shares
become available at RTH close. All figures are descriptive point estimates on
the retained pilot population. No sampling uncertainty is estimated.

Reconcile the emitted counts and statistics independently against the pinned
release. Check a saved GC session with complete RTH and incomplete Globex to
confirm that the independent windows survive the loader handoff.
