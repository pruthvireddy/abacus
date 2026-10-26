# Narada — Publishing

Use the [component instructions](AGENTS.md) and the current
[repository map](../../ARCHITECTURE.md) when extending this app.

Narada publishes selected Sahadeva reports as lightweight static webpages.
Sahadeva supplies the results and explanation; Narada validates, stages, and
renders them. The broader [research library](../../reports/index.html) remains
available locally.

## Setup and checks

Use Node 24. Run these commands from `apps/narada`:

```sh
npm ci
npm run verify
npm test
npm run lint
npm run build
npm run preview
```

`preview` serves the generated `out/` site at `http://127.0.0.1:4173`.
Use `PORT=4174 npm run preview` to change the port. The app has its own
package manifest and lockfile; no root JavaScript workspace setup is required.

## Publish a report

Create a report JSON following the [source contract](contracts/report.schema.json)
and the illustrative
[`examples/report.json`](examples/report.json). Use a new immutable publication
ID, identify its source run, and select the text, metrics, tables, and raster
figures intended for the web. Numeric results must have clear formats and
applicable units. `percent` values are ratios (`0.42` renders as `42%`), and
`unit` is a label without implicit scaling. Use `null` for an unavailable value.
PNG, JPEG, and WebP figures belong under `figures/` next to the source JSON and
must have alternative text.

Prepare source content before sealing a new run. For an already completed run,
create a later presentation revision under
`reports/exports/<study-id>/<run-id>/<revision-id>/` and record its provenance
using the [artifact guide](../../templates/README.md). Pass that revision's
`publication.json` to the same publisher command. Do not append it to the
completed source run.

```sh
npm run report:publish -- --report ../../runs/<study-id>/<run-id>/publication.json --dry-run
npm run report:publish -- --report ../../runs/<study-id>/<run-id>/publication.json
npm run verify
npm run build
npm run preview
```

The dry run validates without publishing. The publisher records a hash of the
canonicalized report JSON and hashes of the exact selected asset bytes. Repeating an
unchanged publication is safe; a changed report under an existing ID is
rejected. Use a new ID for a revision. Keep staged bundles in Git for
reproducible site builds.

The default output is `public/publications/`. For isolated checks, `--output`
can select a temporary publication directory. The normal site build always
reads `public/publications/`. See the [workflow](../../docs/narada.md) for size
and row limits.

The selected web library covers 19 studies, including the
[study 19 external tracker review](../../studies/19_value_area_fade_tracker/README.md) and
[study 20 Camarilla/EMA historical evidence](../../studies/20_camarilla_ema_cloud_reversals/README.md), retaining the two
[Phase 2 pilots](../../docs/narada-publication-plan.md#phase-2-completion-record).
The [Phase 3 record](../../docs/narada-publication-plan.md#phase-3-completion-record)
identifies every selected run, revision and publication. To publish the illustrative example
in a separate temporary output for testing:

```sh
npm run report:publish -- --report examples/report.json --output /tmp/narada-example-publications
```

The example is not computed research. Temporary output is separate from the
normal site build, which does not stage examples.

Report tables have a focusable horizontal scroll region and a linked keyboard
hint. Numeric cells stay on one line; long contents lists scroll within the
desktop viewport. On mobile, contents return to the ordinary page flow. Figures
keep their aspect ratio; native-size files are linked from the figure and publication record.

Narada accepts the defined JSON sections. It does not import arbitrary HTML or
Markdown, read whole research directories, or compute results. Sahadeva can add
a producer that writes publication content before a run is sealed, or creates
a separately identified presentation revision. Existing reports and run
artifacts are not converted or rewritten.

## Evidence context and downloads

Source versions 1.0 and 1.1 coexist. Use 1.1 for visible table descriptions/notes,
section reference links and a bounded `references`/`downloads` declaration. The
[contract and download guide](../../docs/narada.md#evidence-contract-11-and-compatibility)
describes required fields, safe URLs, provenance checks and CSV restrictions.
Old publication bundles do not need migration. New report content always needs a
new immutable ID.

Declare selected UTF-8 summary CSVs under `downloads/`; limits are 256 KiB per
file, 512 KiB total, four files, 1,000 rows and 24 columns. Figure limits remain
separate. Prepare exact saved-cell projections and verify their source map before
dry-running and staging. No full research-directory copy or live analytical code
belongs in the app. Publisher verification checks selected bytes, headers, row
counts and hashes; the author's source-cell check establishes analytical traceability.

Tables explain the missing/blank-cell display and expose context near their values, references have attributed labels and
media ranges, and CSV links show population/units/scope and filenames. Preview
serves CSV downloads with attachment headers. Verify real downloaded bytes in the
static preview as well as the generated links. The
[Phase 4 completion record](../../docs/narada-publication-plan.md#phase-4-completion-record)
identifies the enriched reports and reusable checks.

## Study catalog and navigation

[content/studies.json](content/studies.json) is the single authored catalog;
[contracts/studies.schema.json](contracts/studies.schema.json) owns its shape.
The homepage follows its explicit array order. Stable `/studies/<slug>/` pages
show scope, products, evidence wording and selected publication links. Immutable
reports remain at `/reports/<publication-id>/`; their study context comes from
the catalog without changing their saved content.

To add a publication, prepare a new presentation revision, dry-run it, review
saved-cell transfers and prose, and publish it normally. Then edit the catalog:
set the featured publication and its explicit source-run ID. Related entries
require publication/run IDs, a reader-facing label and one relationship:
`other-run`, `exploratory-supplement`, or `presentation-revision`. Revisions must
share the featured source run; the other relationships must use different runs.
Keep the existing stable study ID and slug. A changed navigation selection does
not register a research reference or rewrite an old publication.

`npm run verify` validates catalog fields, unique identities, ownership and all
publication/run relationships. `npm run build` generates and verifies library,
study and publication routes. Run the full checks above and inspect static
preview navigation after a catalog change. Do not maintain another catalog or
make a site build scan research directories. Superseded presentations retain
routes and a contextual label/link to the featured revision.

## Hosting

Use the [release operations guide](releases/README.md) to prepare an identifiable
static-only artifact and deploy to the dedicated `brew-vee/abacus-narada` project.
The workflow uploads an isolated Build Output API directory, without a repository
connection or remote source build. The app-root `vercel.json` describes source
build settings and is not used by the isolated upload.

```sh
npm run release:prepare
npm run release -- check <release-id>
```

Preparation runs local gates, audits explicit [source-revision locators](content/release-sources.json),
freezes selected output and records hashes under `releases/<id>/`. Generated payloads
and dirty-source snapshots stay ignored under `.release-artifacts/<id>/`. Neither
build nor preparation deploys. The guide specifies target binding, preview checks,
production staging/promotion, public verification and rollback. Deploy only the
recorded artifact; normal publication updates still require new immutable IDs.

See [the publication workflow](../../docs/narada.md) for ownership, preservation,
and the distinction between the local library and selected web reports.
