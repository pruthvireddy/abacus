# Narada — Publishing

Read the workspace [task map](../../AGENTS.md), [architecture](../../ARCHITECTURE.md),
this app's [README](README.md), and the [publication workflow](../../docs/narada.md)
before changing the publication boundary.

- Bhishma owns data and features. Sahadeva owns analysis, report content, units,
  and conclusions. Narada validates and presents explicitly selected content.
- Keep this app independent of the Python environment. A build must not import
  research modules, run analysis, or require ignored local input directories.
- Publish only through the strict report contract and publisher. Do not expose
  arbitrary workspace paths, add general HTML/Markdown imports, or copy an
  entire run directory into public output.
- Keep publication IDs immutable and preserve source/asset hashes. Use a new
  ID for changed content. Never rewrite historical research artifacts to make
  them fit a web report.
- Source content belongs in the source run before sealing, or in a separately
  identified later presentation revision. Follow the
  [artifact conventions](../../templates/README.md). Update source content and
  publish a new ID; never hand-edit generated public bundles or the publication index.
- `content/studies.json` is the authoritative authored study catalog. Edit it
  explicitly after publishing, validate attribution against selected run IDs,
  and generate `/studies/<slug>/` only from it. Never read research directories
  during the build or infer featured publications by date. Keep stable slugs;
  changing featured/related selections changes navigation, not research metadata
  or immutable `/reports/<id>/` content. The catalog schema is app-owned.
  Optional `publicationTabs` select distinct parallel reports from the featured
  source run, with the featured publication first. Use the shared study shell and Explore directory, with ordinary links to
  immutable saved report routes. Keep analytical
  groupings and chart meanings in the supplied reports, not the app.
  Optional `analyses` group parallel chart publications by an authored analysis
  label, with a single source run per group. It replaces top-level
  `publicationTabs`; the first group/tab must match the featured selection.
  Preserve a matching chart label when linking between analyses.
  Optional `phaseFamilies` replaces both legacy navigation containers with
  two to four authored families, each containing one to eight analysis groups
  and one to twelve report tabs per group. Keep source-run attribution within
  each analysis; a family may retain separate analyses from earlier runs.
  Family IDs/labels are unique within the study; analysis IDs/labels are unique
  within each family. Every publication remains uniquely selected across the
  whole study. The first family/group/tab matches the featured selection.
  Phase links preserve an existing condition ID and chart label when present,
  otherwise use the first authored condition or chart. All selections, audits,
  inventories and static checks use the shared authored-selection helpers.
- Optional catalog `overview` metadata owns the library brief and study landing
  sections. Its bounded prose abridges saved conclusions; exact metric/table-cell
  selectors pin a selected publication, source run, content hash and section.
  Resolve and validate these against staged app-owned bundles at build time.
  Preserve saved scalar meanings, formats and qualifications. All study destinations link to full reports instead of embedding their bodies
  or client table controls. Entries without authored overviews use their existing
  summary/evidence fallback in the same shell. Preserve every selected report.
- The shared `scripts/lib/study-routes.mjs` owns Overview, Findings, Explore,
  Method & scope and Evidence route projections. Keep export checks, preview
  smoke and reusable release allowlists aligned; never edit frozen release routes.
  Native route links use `aria-current="page"`, not tab-widget behavior. Retain
  legacy study fragments with explicit static links to saved report sections.
  Run preview smoke with `--all-routes` for the complete catalog-derived inventory.
  Evidence directories expose only already selected downloads/references and
  preserve each report’s population, units, scope and source run. Compact entries
  link to exact immutable report hash records; full reports retain all saved pins.
  Keep essential interpretation limits visible beside the evidence.
- Library discovery uses a bounded build-time projection of authored catalog
  fields. Keep complete cards in static HTML; search/filter controls are a client
  enhancement. Never search full reports, rows, research directories or private
  locators. Preserve authored order and the documented all-term search and
  OR-within/AND-between filter rule. Evidence-type filters use explicit overview
  metadata, not evidence-status prose. Bound and validate URL state against the
  current catalog, preserve native history/focus, and debounce count announcements.
- Optional study `keywords` and top-level `readingPaths` belong in the same
  app-owned catalog/schema/validator. Reading steps reference existing study IDs
  and valid destinations, with authored reasons and visible qualifications.
  Preserve negative/inconclusive findings; paths do not establish independent
  replication, pooled results or a performance ranking.
- Report contents pass only identities/titles to their shared client enhancement.
  Keep heading permalinks server-rendered and clipboard copying in the shared
  desktop/mobile contents control. Preserve ordinary anchors, no-JavaScript
  contents and all saved section IDs. Tables expose typed saved-selection links only after
  activation; opening pending links must not fetch data. Apply valid pending
  values after successful loading, preserve defaults through failures, and explain
  stale values. Keep shared requests, 100-row pages and null/false/zero meanings.
  Print only the shown slice with active selections and source identity; never
  load more data because a reader prints. Native pagination needs its own manual
  check; a screen wrapper applying print CSS verifies layout only.
- Support source contract versions 1.0 and 1.1 without rewriting old bundles.
  Table notes, references and selected CSVs use 1.1; follow the documented
  [evidence limits](../../docs/narada.md#selected-summary-downloads). Only declared
  assets cross the boundary. Source-cell provenance is checked by the export
  author; Narada validates selected content and hashes without reading research.
- Keep numeric formats and units explicit. Do not infer percentages, trading
  conclusions, or evidence status from labels or filenames.
- Examples stay outside the public output until explicitly published. Tests and
  visual verification may stage examples in temporary output; remove those
  fixtures before delivery without removing genuine publications.
  Illustrative values must be clearly labeled.
- Prefer generic report sections and small presentation components. Avoid
  strategy-specific routes, schemas, or analytical calculations in the app.
  Optional table `rowFilters` select saved rows by declared column values.
  Defaults are explicit saved values; filters never calculate or pool results.
  Render at most 100 initial/default rows. Fetch the selected immutable
  publication JSON only after the reader requests table filters, share one
  request per report, and paginate matching rows by 100. Keep defaults visible
  through idle/loading/failure and retain retry and no-JavaScript access.
  Filtered tables/reports/CSVs have separate conditional bounds documented in
  the publication contract; preserve ordinary report and static-page limits.
  Optional 1.1 candle `patterns` are explicitly authored schematic geometry.
  Render only the report's selected overview and section `patternId` references;
  preserve focus captions and role meanings. SVG elements are app-owned, with
  escaped text, accessible title/description IDs and distinct role styles.
  Do not infer empirical prices or sample paths from these illustrations.
- Use Node 24 and this app's npm lockfile. Generated dependencies, build output,
  and local Vercel state stay out of Git; selected publication bundles are
  versioned inputs.
- Run `npm run verify`, `npm test`, `npm run lint`, and `npm run build` from this app for
  publication or UI changes. Verify the generated pages with the static preview
  when presentation changes. Keep research verification separate.
- Use the [maintenance source map](README.md#maintenance-source-map) to choose
  an owner and focused test. Lint maintained `src`, `types`, `scripts`, and `tests`;
  keep Node globals scoped and exclude generated/retained snapshots. Preserve
  publication canonical key sorting separately from release JSON insertion order
  and its trailing newline. Mechanical cleanup must preserve serialized identities.
  Compact report JSON only in generated static output through the delivery
  transform; preserve canonical public bundles and record canonical/delivery
  byte identities separately in new releases. Verify exact semantic equality
  and compact output, including unchanged selected assets.
- After a build, run `npm run preview`, then in another terminal
  `npm run smoke:preview -- --origin http://127.0.0.1:4173`. The bounded HTTP check
  needs that explicit loopback server and checks app-owned exported bytes/headers
  and hard 404s. Inspect actual desktop/mobile interaction separately; HTTP and
  markup tests do not establish keyboard behavior or layout.
- `npm run audit:sources` is a separate read-only private integrity audit. It
  requires retained files named by the explicit release-source mapping; ordinary
  verify/build must not depend on those locators. Check containment, path ancestors,
  regular files and pins before reading. Keep explicit passed, qualified superseded,
  checks-only and inherited Phase 2 records distinct; integrity is not research
  revalidation. No producer import or dependency discovery belongs in Narada.
  Each mapping selects exactly one presentation `revision` or sealed `run`.
  New runs retain `publication-manifest.json`, `source-map.json`, and declared
  `publication-verification.json` beside the presealed `publication.json`;
  the ordinary evidence manifest remains separate. Follow the exact shape in
  the [private source audit guide](../../docs/narada.md#local-maintenance-verification).
  A run may select a per-report `publicationDirectory` exactly equal to
  `publications/<publication-id>`; keep its source files/assets inside that
  directory and retain the ordinary evidence manifest at the run root.
- Direct gate/audit/smoke tests use synthetic temporary fixtures. Local maintenance
  findings do not authorize release preparation, deployment, or a browser-preview
  event in a historical release. Run no numerical Python suite for app-only work.
- For documentation-only changes, run `python3 scripts/check-agent-docs.py`
  from the workspace root. It checks navigation, not report validity.
- Deployment is separate from local implementation and preview. Follow the
  user's deployment instructions before changing hosted state.
- The optional root [workspace harness](../../README.md#workspace-check-harness)
  has a `narada` profile for verify/test/lint/build using this cwd and Node 24.
  It does not synchronize Python or install npm dependencies. Live preview and
  retained source audit stay separately selected; release/publishing actions are
  excluded from the registry. The app's direct npm commands remain independent.
- Use the [release guide](releases/README.md) for authorized hosted releases.
  Preparation never deploys. Keep durable metadata under `releases/<id>/`, payloads
  and reconstruction snapshots ignored under `.release-artifacts/<id>/`, and upload
  only the isolated `deploy/` directory. Preserve exact prepared bytes through
  preview, staged production and promotion. Verify the explicit project/team and
  no Git connection; retain hosted hash and browser gates, never credentials.
