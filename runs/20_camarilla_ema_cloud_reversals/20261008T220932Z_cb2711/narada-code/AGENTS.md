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
- Use Node 24 and this app's npm lockfile. Generated dependencies, build output,
  and local Vercel state stay out of Git; selected publication bundles are
  versioned inputs.
- Run `npm run verify`, `npm test`, `npm run lint`, and `npm run build` from this app for
  publication or UI changes. Verify the generated pages with the static preview
  when presentation changes. Keep research verification separate.
- For documentation-only changes, run `python3 scripts/check-agent-docs.py`
  from the workspace root. It checks navigation, not report validity.
- Deployment is separate from local implementation and preview. Follow the
  user's deployment instructions before changing hosted state.
- Use the [release guide](releases/README.md) for authorized hosted releases.
  Preparation never deploys. Keep durable metadata under `releases/<id>/`, payloads
  and reconstruction snapshots ignored under `.release-artifacts/<id>/`, and upload
  only the isolated `deploy/` directory. Preserve exact prepared bytes through
  preview, staged production and promotion. Verify the explicit project/team and
  no Git connection; retain hosted hash and browser gates, never credentials.
