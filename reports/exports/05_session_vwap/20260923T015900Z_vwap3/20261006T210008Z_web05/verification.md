# Presentation verification

Content: all 96 numeric fields equal their saved selectors; primary values and
intervals also reconcile between metrics and scorecards. Metric notes are generated
from the same numerator, denominator, horizon and interval values. Percentage rates
remain ratios; baseline differences/intervals use explicit ×100 scaling to pp.
Count precision is zero; rates display one decimal and contrasts two decimals.
Semantic review against the saved report/protocol retains deadline dependence,
correlated views, retrospective day eligibility, exploratory overlap-conditional
baselines, adverse/ambiguous classes and unmodeled execution. No statistic is recomputed.

Figure: the raster was visually inspected against the saved SVG. Text, legend,
series order and geometry are retained; only the white right margin is extended.
The transfer check verifies the presentation SVG differs only by canvas/background
width and verifies the 1920×500 PNG. Exact conversion code, versions and hashes are retained.

Application: see [record](application-verification.json). The focused component
test checks the scroll-region description, caption, escaping, percentage scale,
percentage-point unit, zero, null/missing and false rendering. No synthetic missing
metric was added to the real report. Static checks compare all rendered table cells
with the selected source contract and check HTTP responses; they are not research tests.

Browser: [record](browser-verification.json) and [screenshots](provenance/browser/).
Desktop 1440×960 and mobile 390×844 inspected. Contents anchors, table focus/arrow
scrolling, ratio rounding, units, captions/alt, expanded publication records, library
and 404 behavior checked. Initial mobile tables concealed the existence of extra
columns; generic visible keyboard/scroll hints fix that. Numeric cells no longer
wrap, long first-column labels have more room, and long desktop contents lists are
bounded. No captured console errors or failed selected-image loads in the final checks.
The in-app browser stayed on the report after the JSON link click; target bytes and
HTTP 200 were verified independently. No new download feature is added.

Preservation: [record](preservation-verification.json) checks initial-tree and
consumed sealed-run identities. Old exports and research-index files remain
unchanged. No research execution, schema change, metadata selection, deployment,
commit or push occurred. This revision is complete on delivery; future content
changes require a fresh revision and publication ID.
