# Narada release operations

Run commands from `apps/narada` with Node 24 and the existing npm lockfile.
The website build reads the authored [study catalog](../content/studies.json)
and staged public bundles. The private [release-source locators](../content/release-sources.json)
bind every selected publication to its sealed run or completed presentation revision for the
release audit; they are never read by the website or uploaded.

For local maintenance, use the app's [command/source map](../README.md#maintenance-source-map).
`npm run audit:sources` performs the explicit private audit read-only, without
release preparation or an event. `npm run smoke:preview -- --origin
http://127.0.0.1:4173` checks an already running static preview; record actual
browser findings separately in temporary maintenance storage. These local checks
do not satisfy or append hosted release gates. Normal builds remain independent
of retained private research evidence.

## Target and setup

The dedicated static project is `abacus-narada` in team `brew-vee`
(`team_Nw4wZvuRefB6IZzHok6sIPul`), project
`prj_yNCdZap19oy5BDaDlI8U8F2lnxdE`. It has no Git connection, framework,
install command or source build. The unrelated `abacus-board` project is outside
this workflow. CLI 62.7.0 was verified against current official documentation.
Install that exact CLI outside the app dependency tree, then authenticate through
`vercel login`; never paste a token or copy authentication state into a release.
Use `vercel whoami --format json` to inspect identity and verify the intended scope
before binding. Normal CLI authentication completed for this release.

```sh
npm install --global vercel@62.7.0
vercel login
vercel whoami --format json
```

## Prepare locally

```sh
npm run release:prepare
npm run release -- check <release-id>
```

Preparation runs verify/test/lint/build (including the static-export verifier),
audits retained source/export hashes and checks, rejects unselected static files
and symlinks, and copies verified bytes into an isolated Build Output API v3
directory. It never calls a deploy command. Failures leave a failure event and no
completed release; fix the cause and prepare a new ID. Existing release records
and publication bundles are not overwritten.

Each `releases/<id>/release.json` records Git revision, relevant dirty source
identity, Node/npm/CLI versions, dependency lock/catalog/index hashes, publication
and asset identities, exact commands/results and the file inventory. `checksums.json`
identifies the payload; `source-audit.json` retains private evidence locators and
preserved qualifications. Timestamped events add target, deployment and verification
outcomes without rewriting the preparation record. The inventory hash is SHA-256
of the ordered JSON inventory with a trailing newline; individual hashes identify
exact file bytes.

New optimized releases also retain `staticJsonDelivery`: a versioned mapping
from each canonical publication file's SHA-256/byte count to the exact compact
JSON delivered in the static payload. The build verifier checks every saved
value against its canonical input. Canonical public files, report-content hashes,
figures, CSVs and historical release records stay unchanged; the deployment
inventory pins the generated delivery bytes.

For a performance-only release, preserve the accepted production catalog and
publication selection. If the working app has additional draft publications,
prepare a fresh ignored sibling app under `apps/narada-optimization-staging/`
using the accepted selection and reviewed current renderer/scripts. Do not edit
the previous release snapshot. Preparation records the actual `appDirectory`,
isolated status, source inventory and ignored staging Git status. Retain the new
record and its complete `.release-artifacts/<id>/` source/payload under the main
app before using the normal bind/preview/stage/promote gates. The source snapshot
and a separate selection receipt identify which accepted catalog was used.

Ignored `.release-artifacts/<id>/deploy/` contains only `vercel.json` and
`.vercel/output/{config.json,static/}`; binding adds nonsecret `.vercel/project.json`.
Only this directory is passed to Vercel. The serving config enumerates real page
routes, declares CSV attachment/media headers, checks static files and ends with
the saved 404 page and status 404. There are no functions or research dependencies.
Next.js `out/` alone is **not** `--prebuilt` input: the adapter deliberately creates
the [Build Output API format](https://vercel.com/docs/build-output-api/configuration).
The app-root `vercel.json` describes source builds and is not used by this upload.
Never deploy from the workspace, app root, research library or source snapshot.

Ignored `.release-artifacts/<id>/source/` retains the necessary dirty app source,
contracts, public inputs, catalog, tests, scripts and npm lock for reconstruction.
Keep both generated directories for each retained release or archive them separately
to approved storage. They are local files, not verified off-device backups. Metadata
alone cannot recover a deleted uncommitted source or static payload. Exact artifact
integrity is checked; byte-identical rebuilding has not been demonstrated. To
reconstruct, restore this snapshot into a separate directory, use Node 24, `npm ci`
and `npm run build`, then inspect the newly generated output and prepare a new release.

## Deploy, verify, then release

```sh
npm run release -- bind <release-id> team_Nw4wZvuRefB6IZzHok6sIPul brew-vee prj_yNCdZap19oy5BDaDlI8U8F2lnxdE abacus-narada
npm run release -- preview <release-id>
npm run release -- hosted <release-id> preview https://<preview-host>.vercel.app --protected
# Inspect representative pages in the browser; record browser-preview gate below.
npm run release -- stage <release-id>
npm run release -- hosted <release-id> staged-production https://<staged-host>.vercel.app --protected
npm run release -- promote <release-id> https://<staged-host>.vercel.app
npm run release -- hosted <release-id> production https://abacus-narada.vercel.app
```

Commands inspect the isolated directory's exact linked project and explicit owner,
require no Git link, check the pinned CLI identity, and verify the complete artifact
inventory before mutation. Preview explicitly selects `--target preview` with `vercel deploy --prebuilt`; production uses
`--prebuilt --prod --skip-domain`. Stage requires a passed preview HTTP gate. Promotion
requires the staged production HTTP gate and the preview browser record, and checks
that the target deployment is READY and production in this project. The CLI's
[staging/promotion workflow](https://vercel.com/docs/cli/deploy#skip-domain) assigns
domains to the already tested production deployment without rebuilding. Never
substitute a preview promotion: it can create a different production build.

The [gate lookup](../scripts/lib/release-gates.mjs) accepts a matching event
filename suffix, `result: "passed"`, and exact artifact hash. It also matches
the origin when the caller supplies one (the staged-production promotion gate).
The browser-preview caller supplies no origin. JSON `kind` and timestamp ordering
are not additional predicates; failed attempts can coexist with a matching passed
record. A malformed matching record encountered during lookup fails closed. Direct synthetic tests exercise
this behavior without invoking deployment commands.

The wrapper pins `--local-config` to the isolated static configuration, avoiding
ancestor source-build settings. Native CLI structured deployment output is parsed
explicitly. Its first deployment can auto-assign production; the initial bootstrap
outcome is retained separately, and the accepted release still follows Preview →
staged production → verification → promotion. Inspect first-project behavior before
using this workflow for a different new project.

Hosted verification retrieves **every** prepared file, not merely headline routes,
and matches exact bytes/hashes. It checks CSV MIME, attachment filename and `nosniff`,
plus unknown study/report and private paths returning the saved 404. Default verification
uses anonymous HTTPS without cookies, so an authentication wall fails rather than
passing as the website. `--protected` selects authenticated `vercel curl` for preview/staged URLs;
only selected response headers and body hashes are recorded. Native curl forwarding
requires process working-directory selection rather than passing global flags.
Public production must still pass anonymously.

Browser review covers the library, a quantitative pilot, qualitative review,
historical import, table-heavy and enhanced report at desktop/mobile widths:
navigation/contents, keyboard table overflow, figures/captions/alt, source/reference
links, downloads, publication records, 404s and console/network failures. Save
an evidence record to a fresh `events/<timestamp>-browser-preview.json` containing
`kind: "browser-preview"`, `result: "passed"`, `origin`, `artifactSha256` from
`release.json`, UTC `at`, viewports, routes and actual findings. Do not mark it passed
without inspecting the site. Record staged/production browser differences separately.
Screenshots stay in an ignored release evidence directory and may have checksums
in metadata; never retain authentication state or traces containing credentials.

Deployment attempts and successes are distinct events. After a timeout or unknown
outcome inspect Vercel by the recorded URL, release metadata and team/project before
retrying; a failed local command can still have created a deployment. Do not blindly
upload again or promote. Hosted failures do not create a passed gate. If bytes/config
change, prepare a fresh release; if report content changes, first publish a new ID.

## Protected previews

Keep project/team protection intact. `vercel curl https://<exact-deployment-host>.vercel.app/`
uses the CLI's authenticated protection mechanism. Do not print bypass headers,
share-link secrets, cookie jars or environment files, or store them as release evidence.
Browser protection may require normal human login; record that access separately
from anonymous production verification. Consult the current
[protected deployment guidance](https://vercel.com/docs/deployment-protection/methods-to-bypass-deployment-protection).

## Accepted production release

Current release `20261031T193451Z_d0c9c013` is live at
[abacus-narada.vercel.app](https://abacus-narada.vercel.app), production READY.
Its prepared app matches all 625 corresponding files in source commit
[`7098b4bdc68e919b7b2e8daf77d6651a08446c43`](https://github.com/pruthvireddy/abacus/commit/7098b4bdc68e919b7b2e8daf77d6651a08446c43).
Preparation captured dirty source over `2f890fb2e263fd3acd2a28082909d5c98c5d5166`;
the retained snapshot hash records that distinction. The checked staged production
artifact was promoted without rebuilding. See the
[public release receipt](20261031T193451Z_d0c9c013/public-receipt.json).

The collection now has 25 studies, 105 reports, 163 raster figures and 247 selected
CSVs. Study 30 adds 20 ranked descriptive measures in Pivot statistics and Globex
VWAP statistics from frozen run `20261031_ranked_v2`, with all six Original baseline
reports retained separately. Eligible populations remain distinct: 875 pivot-matched
RTH, 1,308 VWAP-only RTH and 1,292 full-Globex sessions, January 3, 2020–September 18,
2026. Requested dates remain January 1, 2020–October 30, 2026. Historical pivot
availability and native chart parity remain unverified; retrospective/exploratory
and no-profitability qualifications remain visible.

Node 24 verify, 250 tests without skips, lint, static build, compact JSON equivalence
and the private source audit passed. Protected preview, staged production and
anonymous production each matched all 2,718 exact static files, 247 CSV byte/header
checks and five hard 404s. Desktop/mobile preview and public production browser
checks passed with no application console warnings or errors. The native preview
CSV download matched the selected 26,094-byte asset exactly. Native print/PDF,
browser-wide JavaScript-disabled mode and assistive-technology testing were not
repeated. Full audits, deployment records and recovery snapshots remain local,
with off-device recovery unverified. The previous release below is the explicit
verified rollback reference.

## Previous research-priority production release

Previous release `20261027T003702Z_cc56f115` was live at
[abacus-narada.vercel.app](https://abacus-narada.vercel.app), production READY,
after [source PR #3](https://github.com/pruthvireddy/abacus/pull/3) merged as
`63b05dfa818e0bdaf271e4c195fd03f154747a12`. The prepared source commit was
`2153fdcc062dcaa667ebb34190232694b808a6bc`; its app tree exactly matches merged
main. The checked staged production artifact was promoted without rebuilding.
The existing 24 studies, 97 reports, 154 raster figures, 237 selected CSVs and
three reading paths are preserved. See the
[public release receipt](20261027T003702Z_cc56f115/public-receipt.json).

Research priority now appears as display-only accessible stars on study cards
and overviews, with dated explanations, supporting and contrary evidence,
candidate scope, blockers and proposed tests. The 24 assessments comprise
thirteen 1/5, seven 2/5, one 3/5, one Not assessed and two Not applicable;
none received four or five. Priority filters, shareable URLs and optional
highest-first ordering use only current numeric assessments. Needs review
retains prior dated reasoning while excluding the stale score from numeric
filtering and ordering. These are honestly identified AI-assisted editorial
judgments about further research, not profitability probabilities, trading
recommendations or independent scientific validation.

Node 24 verify, 249 tests without skips, lint, static build, compact JSON
equivalence and the private source audit passed. Protected preview, staged
production and anonymous production each matched all 2,570 exact static files,
237 CSV byte/header checks and five hard 404s. Desktop/mobile preview and
anonymous production browser checks passed with no application console errors.
The bounded discovery index remains 17,477 bytes within its unchanged 48 KiB
budget; local discovery/overview browser checks made no publication JSON
requests. Saved research values and canonical publication assets are unchanged;
integrity checks do not revalidate their scientific conclusions.

Fresh native hosted downloads, browser-wide JavaScript-disabled mode,
assistive-technology testing and native print/PDF were not repeated for this
release; static HTML, server-render and existing regression checks are retained.
Detailed source locators, full audits, deployment records and recovery snapshots
remain local, with off-device recovery unverified. This public summary and receipt
exclude those private records. The previous redesign release below is the
explicit verified rollback reference.

## Previous redesign production release

Previous release `20261026T173757Z_a949ceeb` was live at
[abacus-narada.vercel.app](https://abacus-narada.vercel.app), Vercel production
(READY), from source commit
`328b8458ba83efa5c11667d5b538b242a3c36387` after
[source PR #1](https://github.com/pruthvireddy/abacus/pull/1) merged. It publishes
the user-approved 24 studies and 97 reports, including the formerly local Trader
Assistant manual and ES opening pivot cloud study, with 154 raster figures and
237 selected CSVs. Search, shareable authored filters and three curated reading
paths accompany the report reader. Canonical publication inputs, saved evidence,
figures and CSVs remain unchanged. This uses the dedicated static project without
a Git connection. See the
[public release receipt](20261026T173757Z_a949ceeb/public-receipt.json). Detailed
source locators and full HTTP/audit records remain retained locally.

All four app gates passed, including 229 tests. Preview, staged production and
anonymous production each matched all 2,570 exact static files, all selected CSV
download headers and five hard 404s. The checked staged production artifact was
promoted without rebuilding. Hosted desktop/mobile browser checks passed; local
print-CSS and script-free HTML checks passed. Native paginated print/PDF and a
separate browser-wide JavaScript-disabled session remain unverified. Integrity
checks preserve canonical bytes and source identities; they do not revalidate
research. The public receipt summarizes the verified HTTP and browser outcomes
without publishing private source locators.
The previous optimized release below was that release's explicit rollback reference.

## Previous optimized production release

Previous optimized release `20261026T045038Z_308eb567` was accepted at
[abacus-narada.vercel.app](https://abacus-narada.vercel.app), deployment
`dpl_BwYJxUjWuzLUPVbQZQEpkdJeKPah` (READY, production), from source commit
`7205ba71bd30d45395f82e87887222f1c34150a5`. This performance-only release
preserves the accepted 22 studies and 94 publications, including all 229 CSVs
and 147 raster figures. At that checkpoint the separate local 24-study/97-report
selection remained outside the deployment. See the
[outcome](20261026T045038Z_308eb567/outcome.json).

Generated report JSON is compacted from 114,007,369 to 54,944,824 bytes; all
canonical bundles and parsed research values remain unchanged. Table filters
load their report only after reader activation, with saved default rows visible
before loading and through failures. All four app gates passed, including 185
tests. Preview, staged production and anonymous production each matched all
1,546 static files, CSV headers and five real 404s. Desktop/mobile preview,
keyboard activation, an exact CSV download and production interaction passed.
The tested staged production artifact was promoted without rebuilding.
Integrity checks found no changes in 7,196 recorded historical/canonical files;
these checks do not rerun research. Source and payload snapshots remain local.

## Previous accepted collection

Release `20261017T195854Z_37ab5c1a` established the collection at
[abacus-narada.vercel.app](https://abacus-narada.vercel.app), deployment
`dpl_EjvPZhUZRqCsvM2qV9cE55QX8Hik` (READY, production). The
[Forex News study](https://abacus-narada.vercel.app/studies/forex-news-ema/)
now has six contract tabs: 6E, 6B, 6J, 6A, 6C and 6S. Each report has 25 sections,
three figures and four selected CSV downloads, with event-type, weekly, monthly,
type-by-period, side, weekday, hour, quarter and year views across three calendar
selections and five candle horizons.

The new sealed run `20261017T193830Z_perfuture25_d2c74b` contains independently
reconstructed descriptive aggregates of 7,050 retained event/horizon rows:
22,405 aggregate rows across 72 tables. Its 702 combined observations are
contract-specific; the overlapping calendar selections must not be added.
Metadata-only presentation revisions select `forex-news-<contract>-20261017-v2-r1`.
The original common-64 comparison remains accessible as an earlier run.
Reconstructed prices, EMA signals and imported native-chart checks were not rerun.

All four isolated app gates passed, including 160 tests and static export checks;
the current local app also passed its four gates and 168 tests. Private source
audit, desktop/mobile interaction, keyboard table scrolling and an actual CSV
download passed. Preview, staged production and anonymous public production each
verified 1,546 exact static files, all 229 CSV download headers and five hard 404s.
The checked staged production artifact was promoted without rebuilding. See the
[accepted outcome](20261017T195854Z_37ab5c1a/outcome.json) for receipt hashes.

All 88 earlier publications remain byte-identical. The isolated source preserves
491 accepted files unchanged, updates only the two catalogs and generated index,
and adds 48 report/asset files. Local manual and phase-family drafts remain outside
the deployment. The broader compatibility workspace gate still has two unrelated
Bhishma data prerequisites; its four later checks did not execute. This does not
replace the focused Forex numerical checks or the passed web release gates.

## Previous production release

Previous release `20261017T190728Z_e6e3b607` was deployed at
[abacus-narada.vercel.app](https://abacus-narada.vercel.app), deployment
`dpl_DpEXQjkZhgt3JtWmCLnoDxqv5vii` (READY, production). The
[Forex News study](https://abacus-narada.vercel.app/studies/forex-news-ema/)
adds the final saved six-currency EMA comparison from `tv-indicators`: 64 shared
U.S. release timestamps, five chart-candle horizons, three figures, saved
horizon/category/month controls and four summary CSVs. Imported run
`20261017T190030Z_import25_4b8a21` was sealed before publication. Read the
[outcome](20261017T190728Z_e6e3b607/outcome.json).

Verify, 160 app tests without skips, lint, build and private source audit passed:
22 studies, 88 publications, 129 rasters, 205 CSVs and 2,902 retained source-file
hashes. Protected preview, protected staged production and anonymous production
each matched all 1,444 files, CSV headers and five hard 404s. The protected checks
used authenticated same-origin Vercel CLI URL batches and the unchanged app-owned
byte/header checker; the independently reviewed operational adapter is retained in
this release's `operations/`. Response credentials were held only in process memory.
The original slower partial preview check was superseded and is not a passed gate.
The exact checked production deployment was promoted without rebuilding.

Desktop/mobile browser review covered the Forex report and five representative
retained layouts, figures, saved controls, pagination, keyboard overflow,
provenance links, library navigation and a missing-page view. Public production
opened in the in-app browser with working saved controls and an empty captured
warning/error console. Native browser CSV completion was unconfirmed; all served
CSV bytes and download headers passed the independent HTTP checks.

The isolated release preserves the preceding production app's exact source:
483 existing source/publication files remain unchanged; only two explicit catalogs
and the generated publication index change, with eight Forex files added. All 87
previous publications remain exact. Local Trader Assistant manual and phase-family
drafts remain preserved outside this deployment. The new retained source snapshot
and isolated payload exist locally; off-device backup and byte-identical rebuilding
remain unverified.

This import did not rerun the market calculations or original validation. New checks
verified 22,098 mapped publication/CSV cells, 78 figure inputs, four metrics and
123 declared artifacts. Reconstructed/back-adjusted history, the corrected historical
calendar, retrospective eligibility, overlapping windows and shared shocks limit
interpretation. Native57 remains a separate cohort. Costs and executable fills are
unmodeled; MFE/MAE is not profit factor and no holdout or profitability is established.
The default workspace gate retains its two existing Bhishma input-prerequisite
errors after 226 tests; four later default checks were unexecuted. The following
previous verified production is the explicit rollback reference.

Previous release `20261013T211202Z_4c5b1446` is live at
[abacus-narada.vercel.app](https://abacus-narada.vercel.app), deployment
`dpl_CtfrwaVuh82zqVWDuaPDSRVzSzKC` (READY, production). The stable
[GC- Overnight Breakout 15M study](https://abacus-narada.vercel.app/studies/gc-overnight-breakout-15m/)
now has eight analysis groups and 26 tabs, including its preserved Phase 1
baseline, Phase 2 comparison, causal reclaim and passive-limit entries,
protected-boundary occurrence/recovery/reversal, annual/session/timing views
and separate actual-account evidence. Read the
[outcome](20261013T211202Z_4c5b1446/outcome.json).

Run `20261013T190208Z_phase2_gc_ob15m_v2` was sealed before publication.
Two subsequent presentation-only revisions expose the saved original-breakout
to actual-entry and protected-breach-session to entry transitions. They retain
the sealed source numbers. No primary reclaim replacement met the frozen validation rule;
the selected primary is null. One-contract outcomes remain simulations under
declared costs and OHLC ordering. Actual source-account observed executable
fills are zero, with unknown opportunities/equity retained separately.
Price recovery does not imply financial recovery. Phase 3, H10 and further
filter search remain unexecuted.

Verify, 160 app tests without skips, lint, build and private source audit passed:
21 studies, 87 publications, 126 raster assets, 201 CSVs and 2,879 retained
source-file hashes. Protected preview, protected staged production and anonymous
registered production each matched all 1,418 files, CSV bytes/headers and five
hard 404s. The exact staged production deployment was promoted without a new
build. Actual desktop/mobile browser review covered all 26 GC report routes,
saved controls, zero-support/null rows, session transitions, provenance,
figures/captions/alt text, pagination, keyboard scrolling, library navigation,
404s and representative retained layouts; captured consoles were empty.
Protection remains unchanged. Hosted CSV byte/header checks passed; a new
native hosted browser download is not claimed.

The study record has 336 tests, 353 successful callbacks and zero skips,
with separate independent scientific, metrics, account and publication checks.
All 225 prior production public files, 20 other catalog objects, previous
source mappings, Phase 1 attribution, the sealed run/two revision manifests
and 89 final PNG paths remain exact. Supplemental publication preservation
also checked all 407 pre-supplement public files and 85 prior mappings.
The final default workspace gate retains two unchanged Bhishma input-prerequisite
errors after 226 tests; four later default checks were not run. An initial
sandbox app test could not bind loopback; its retained normal-permission retry
passed without source changes. Integrity checks do not revalidate historical
research. The following verified Phase 1 production is the explicit rollback.

The Phase 1 description below records its scope when it was accepted.

Previous release `20261013T172420Z_c9cd5748` was live at
[abacus-narada.vercel.app](https://abacus-narada.vercel.app), deployment
`dpl_DipGeCPi9mnfquhRqevqNpQLk3LG` (READY, production). The stable
[GC- Overnight Breakout 15M study](https://abacus-narada.vercel.app/studies/gc-overnight-breakout-15m/)
now serves its sealed Phase 1 report: saved year/session/side controls, annual
and timing tables, eight original figures, four selected CSVs and exact run
provenance. The one-contract simulation uses disclosed assumed fees and
slippage; the separate source-account sizing run has zero executable whole-GC
fills. Partial coverage, censoring and sparse cohorts remain visible. Phase 2
and H10 results are uncomputed. Read the
[outcome](20261013T172420Z_c9cd5748/outcome.json).

Verify, 143 app tests without skips, lint, build and the private source audit
passed: 21 studies, 62 publications, 37 raster assets, 126 CSVs and 2,127 hashed
source files. Preview, staged production and anonymous registered production
each matched all 1,004 files, CSV bytes/headers and five hard 404s. The protected
preview and staged browser checks used an existing normal Vercel session; the
public production check used the signed-out in-app browser. Project protection
was unchanged. The preview browser covered desktop/mobile layout, all eight
images, saved controls, zero-support/null cohorts, pagination, keyboard table
scrolling, skip navigation and representative retained report layouts. Public
browser review confirmed the collection-to-study-to-report route, saved controls,
responsive layout, keyboard scrolling, the equity figure/captions and CSV link.
The no-loss ratio cohort was checked locally and on public production; the
[supplemental scope record](20261013T172420Z_c9cd5748/events/20261013T174858Z-browser-production-supplement.json)
clarifies the original outcome's preview wording without rewriting its hashes.
The native local browser CSV download matched its source hash; hosted download
bytes and headers were verified separately without claiming a new native hosted
download. Captured browser consoles were empty.

Independent publication verification checked 13,168 displayed cells, 9,165 CSV
cells, 37 claim conditions/tokens, eight saved SVG geometries and actual raster
appearance, and four empirical examples against their ledger and pinned minute
traces. The run was sealed before Narada publication. Existing renderer controls
were reused; all 212 prior selected public artifacts remained byte-identical.
Source audit accepts explicit sealed-run mappings and canonical signed-zero
serialization while retaining exact source-byte hashes. Historical research
qualifications remain in place. The following previous production is the
explicit rollback reference.

Previous release `20261013T035220Z_b4759d0f` was live at
[abacus-narada.vercel.app](https://abacus-narada.vercel.app), deployment
`dpl_CxsD7ZNDXY6PHu7zzWLmqFMekSq5` (READY, production). The
[focused ES study](https://abacus-narada.vercel.app/studies/es-range-xv-trend-length/)
uses slim filled green/purple candle bodies, thin matching wicks and tighter
spacing in all six analyses and 4/5/6 tabs. The light background is retained.
Only app-owned drawing/style code changed; publication IDs, authored OHLC,
statistics, CSVs and source revisions remain unchanged. Read the
[outcome](20261013T035220Z_b4759d0f/outcome.json).

Verify, 133 app tests without skips, lint, build and private source audit passed.
Preview, staged production and anonymous production each matched 973 files,
122 CSVs and five hard 404s. Browser checks covered all six analyses, chart
navigation, desktop/mobile candle shape and labels, annotation levels,
year/session/leg filters and five retained report layouts. The public appearance
and light background were checked separately. CSV components were unchanged;
served bytes and headers passed without a new native download-file claim.

Independent review checked 126 variants, 978 candles, 276 levels and 90 bands.
The affine display scale includes every authored OHLC and level/band bound,
preserving body retracement and risk/target relationships. All 504 current
publication/source files remain byte-identical; no market analysis was rerun.
The following previous production is the explicit rollback reference.

Previous release `20261013T031215Z_23c6c3b4` was live at
[abacus-narada.vercel.app](https://abacus-narada.vercel.app), deployment
`dpl_5CNpDzeHqiBqBVkgmauzduSvw2LA` (READY, production). The
[focused ES study](https://abacus-narada.vercel.app/studies/es-range-xv-trend-length/)
now has explanatory candle panels in all six analyses and all 4/5/6 chart tabs.
Each of the 216 quantitative sections identifies the part measured. Shared SVG
definitions and links to complete pattern keys keep repeated panels compact.
Schematics are normalized illustrative examples, not observed price samples.
Read the [outcome](20261013T031215Z_23c6c3b4/outcome.json).

Verify, 132 app tests without skips, lint, build and private source audit passed.
Preview, staged production and anonymous production each matched all 973 files,
122 CSVs and five hard 404s. Hosted browser checks covered all six analyses,
chart-preserving navigation, SVG rendering and references, pattern-key links,
year/session/leg selection and desktop/mobile layout. The public CSV link was
clicked, but a fresh local download file was unconfirmed; all served CSV bytes
and required headers passed the independent anonymous HTTP gate.

Ten presentation tests and independent semantic/transfer review passed. Eighteen
new presentation revisions retain 124,947 saved rows, 876,330 numeric cells,
54 CSVs and 18 source maps exactly. All 279 original source pins, 414 revision
output pins and 140 prior public artifacts remain unchanged. No market statistics
were rerun and no historical runs were modified. The broader default workspace
gate retains its two existing Bhishma prerequisite errors; required presentation
and publication checks passed. The following previous production is the explicit
rollback reference.

Previous release `20261012T231442Z_1cdfc236` was live at
[abacus-narada.vercel.app](https://abacus-narada.vercel.app), deployment
`dpl_99mVcPrYeAuiDK1E7DRKeqAwSsUz` (READY, production). The
[focused ES study](https://abacus-narada.vercel.app/studies/es-range-xv-trend-length/)
adds earlier trend → one opposite candle → resumption, with continuation,
retracement and gross OHLC payoff views, each with 4/5/6 tabs. Earlier A length,
year and all seven windows select saved rows. The three preceding analyses remain.
Read the [outcome](20261012T231442Z_1cdfc236/outcome.json).

Verify, 123 app tests, lint, build and private source audit passed. Preview,
staged production and anonymous production each matched 739 files and five
hard 404s, including 68 CSV header checks. Desktop/mobile navigation, filters,
pagination, keyboard overflow, retained reports/figures and source references
were inspected. The protected-preview download helper timed out; the public
native CSV download completed and its exact bytes matched.

Research run `20261012T230640Z_pullbacks22_4f3a92` passed 269 tests without skips,
independent reconstruction of 217,366 setups and 434,732 proxy scenarios, all
262,656 saved rows, 519,804 displayed numeric cells and 2,673,000 CSV cells.
Nine sources were prepared before sealing and exported byte-identically. The
fixed 1R/2R gross OHLC models have negative overall mean R; executable fills,
costs and net P&L remain unsupported. Old runs and all 107 prior publication files
remain unchanged. The explicit rollback is the following previous production.
The broader default gate remains blocked on existing Bhishma input prerequisites.

Previous release `20261012T220326Z_ae9abd9e` was live at
[abacus-narada.vercel.app](https://abacus-narada.vercel.app), deployment
`dpl_H6FX6FYCComA5QnesykoZtWoAgwP` (READY, production). It extends the
[focused ES Range XV study](https://abacus-narada.vercel.app/studies/es-range-xv-trend-length/)
with Reversal Continuation, Retracement & Recovery and preserved Trend Length
views, each with 4/5/6 RXV chart tabs. Every reversal metric has year, session
and preceding-leg cohorts; continuation uses n=1–20 additional candles and
F1 recovery uses 25/50/75/100% body retracement with a close beyond R.close.
Read the [outcome](20261012T220326Z_ae9abd9e/outcome.json).

Narada verify, 123 tests, lint, build and private source audit passed. Preview,
staged production and anonymous production each matched all 625 files and
five hard 404s, including 44 selected CSV header checks. Desktop/mobile filters,
pagination, keyboard overflow, chart-preserving analysis navigation, retained
figures and normal console were inspected. A native browser CSV download was
saved and its checksum matched. A generated local-preview-only asset outage
kept defaults visible and recovered through retry after exact restoration.
The research run passed 156 tests without skips, independent reconstruction of
all 890,921 reversals and every saved table cell, and independent web/CSV transfer
checks. All 83 prior public files and old trend evidence/export pins remain
unchanged. The recorded previous production below is the explicit rollback.
The broader default compatibility gate still fails on existing Bhishma input
prerequisites; this release does not claim full workspace coverage.

Earlier release `20261012T202906Z_936cb8c6` was live at
[abacus-narada.vercel.app](https://abacus-narada.vercel.app), deployment
`dpl_Hb8qn1HQLVe6agZDLtE4GN1ft2Dn` (READY, production). It adds the
[ES Range XV directional trend-length study](https://abacus-narada.vercel.app/studies/es-range-xv-trend-length/)
with separate 4/5/6 RXV tabs, all requested annual/window breakdowns and selected
CSV downloads. Read the [outcome](20261012T202906Z_936cb8c6/outcome.json).

Narada verify, 108 tests, lint and build passed. Preview, staged production and
anonymous public production each matched all 547 static files and five hard 404s.
Desktop/mobile and keyboard navigation were inspected in the browser. Native
browser download-event completion was unconfirmed; CSV bytes, media types,
attachment filenames and nosniff passed the HTTP gates. The research run passed
73 focused tests and independent reconstruction of all 896,267 trends and every
saved statistics cell. All 68 prior public artifacts and the pinned inputs remain
unchanged. The previous production below is the explicit rollback target.


Previous release `20261007T144659Z_db56da10` was live at
[abacus-narada.vercel.app](https://abacus-narada.vercel.app), deployment
`dpl_9DvB9EqapehTb3TGQeY6KtW6B6mx` (READY, production). It adds the
[study 19 external tracker review](https://abacus-narada.vercel.app/studies/value-area-fade-tracker/)
and proposed value-area fade strategy, explicitly leaving independent analysis planned.
The [outcome](20261007T144659Z_db56da10/outcome.json),
[preparation record](20261007T144659Z_db56da10/release.json),
[checksums](20261007T144659Z_db56da10/checksums.json) and
[source audit](20261007T144659Z_db56da10/source-audit.json) identify 18 studies,
24 publications, 23 rasters and ten CSVs. Local verify/38 tests/lint/build passed;
preview, staged production and anonymous production each matched all 467 files
and five hard 404s. Browser checks covered new content, mobile keyboard overflow,
actual CSV bytes and representative prior reports. All 3,251 pre-existing
run/export/publication artifact hashes remained unchanged.

The tested preview is
[ljrqeembg](https://abacus-narada-ljrqeembg-brew-vee.vercel.app),
`dpl_2w3weZxDM4GSnTQEQ9fjpxkGf6Dm`. Staged production is
[opoj7mibc](https://abacus-narada-opoj7mibc-brew-vee.vercel.app), the same deployment
now promoted to production. The previously verified release below is the explicit
rollback target. The initial study 19 local publication had incorrect producer
metadata and was never deployed; its rejected staging and export remain retained,
and the corrected public presentation has a new immutable ID.

### Previous verified production and rollback target

Release `20261007T014040Z_abdf5f57` was previously live at
[abacus-narada.vercel.app](https://abacus-narada.vercel.app), deployment
`dpl_8Ku2riANm66q78uvYSRwkFWJka2t` (READY, production).
Its [production outcome](20261007T014040Z_abdf5f57/outcome.json),
[preparation record](20261007T014040Z_abdf5f57/release.json),
[checksums](20261007T014040Z_abdf5f57/checksums.json) and
[source audit](20261007T014040Z_abdf5f57/source-audit.json) identify 17 studies,
23 publications, 16 rasters and six CSVs. Append-only events retain deployment,
HTTP, browser, preservation and production outcomes.

The accepted preview is
[9d8m849h7](https://abacus-narada-9d8m849h7-brew-vee.vercel.app),
`dpl_FKgzaobiTjtxN7UuEfNRedyBmFTv`. The tested staged production URL is
[j5brv0lgy](https://abacus-narada-j5brv0lgy-brew-vee.vercel.app), now the released
production deployment. Each passed all 437 file hashes and five hard-404 checks;
production passed anonymously. The optional Vercel feedback toolbar is disabled
on this dedicated project because it appended code to a runtime chunk. Preview
protection remains intact; no team policy changed. Keep the toolbar disabled or
expect the exact-byte gate to reject provider-modified files.

The initial upload auto-assigned production, before the intended gates. Bootstrap
`20261007T013423Z_7df6951f`, deployment `dpl_7y8ypnMxwBhaWGQKuLDLvRG5rnLd`, is
retained with its failed outcome. Its served runtime hash differs from the payload,
so it is **not an approved rollback target**. The first corrected preview also
failed that hash check and was not promoted. Neither failure counts as a passed
release. This is the first accepted release; there is no earlier verified rollback
target. For an issue now, prepare and verify a corrected release.

After a subsequent release, this accepted deployment can be an explicit rollback
target. Verify its retained metadata and project identity, then use:

```sh
vercel rollback dpl_8Ku2riANm66q78uvYSRwkFWJka2t --cwd .release-artifacts/20261007T014040Z_abdf5f57/deploy --scope brew-vee --non-interactive
npm run release -- hosted 20261007T014040Z_abdf5f57 production https://abacus-narada.vercel.app
```

Run browser checks again and record the outcome. This command is documented,
not executed as a demonstration.

## Updates and rollback

For content updates, prepare a new Sahadeva presentation revision and immutable
publication ID, run publisher dry-run/review/normal staging, and update the explicit
study mapping and private release-source locator. Preserve older publications and
their correction labels. Then prepare a new static release and follow the preview,
staged production, promotion and public checks above. Research publication and static
site release are separate actions. No CI, Git integration or recurring job is configured.

Before promotion record the current production deployment and its release record;
after promotion record the new production URL/deployment. Use explicit IDs, not
whichever deployment happens to be newest. For a known prior production release:

```sh
vercel project inspect --cwd .release-artifacts/<id>/deploy --scope brew-vee --non-interactive
vercel inspect <previous-production-id-or-url> --scope brew-vee --format json
vercel rollback <previous-production-id-or-url> --cwd .release-artifacts/<id>/deploy --scope brew-vee --non-interactive
npm run release -- hosted <previous-release-id> production https://abacus-narada.vercel.app
```

Confirm the prior target belongs to this project, previously served production and
has retained verified metadata before rollback. Record the rollback and restored
hash/browser checks in new events in both affected records. A first release has
no earlier production target; prepare a corrected release if needed. Do not perform
a rollback solely to test the command. [Rollback disables automatic production-domain
assignment](https://vercel.com/docs/cli/rollback#undo-a-rollback); resume with a newly
staged, verified production release and explicit `vercel promote`, then run the
public checks. This workflow stages every release explicitly even after promotion
restores auto-assignment.

See the [publication workflow](../../../docs/narada.md),
[phase records](../../../docs/narada-publication-plan.md) and app [README](../README.md).
