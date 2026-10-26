# Trader Assistant manual: reading companion

Study 24 records a qualitative reading of the public
[Trader Assistant manual](https://willyalgotrader.pro/strategy/manual/), reviewed
on October 13, 2026 in the user's New York timezone. The source navigation
contains twelve chapters and an update. Abacus supplies a concise original
companion, chapter links and its own schematic PNG illustrations.

**Evidence status:** external source review only. This work computes no market
statistics, implements no trading strategy and establishes no profitability or
independent validation. Source examples and claims retain their external status.
The source is a live webpage; its full text and image bytes are not retained or
pinned by this review, and later source changes cannot be reconstructed from it.

Read the [offline companion](../../runs/24_trader_assistant_manual/20261014T023500Z_manual24_8c1d7f/report.html),
[Markdown companion](../../runs/24_trader_assistant_manual/20261014T023500Z_manual24_8c1d7f/report.md),
and [run manifest](../../runs/24_trader_assistant_manual/20261014T023500Z_manual24_8c1d7f/manifest.json).
The selected Narada publication is
`trader-assistant-manual-20261013-companion-v1`, available through the authored
study slug `trader-assistant-manual` after the local site build.

The user confirmed that reproduction rights are unavailable or uncertain and
selected a reading companion. The publication therefore uses original brief
explanations and original illustrations, with links to the source for its full
chapters and charts. It does not mirror the manual's text or copy its images.
Schematic illustrations explain concepts and are not observed market samples.

Read the [review protocol](plan.md), [settings](study.yaml),
[source declaration](inputs.lock.json) and [decisions](notes.md).
No market datasets or executable strategy rules are introduced. A later request
for empirical research needs a separately authorized, frozen protocol and pinned
data; this companion does not register a tested strategy.

The authored [companion](companion.json) and [observations](source-observations.json)
feed the standard-library [document packager](document.py). The original
[illustration generator](illustrate.py) uses the existing locked Python runtime
and Narada's installed Node 24/Sharp dependency, without installing packages.
Generate illustrations only into a fresh staging directory, then prepare,
finalize and seal that unique identity. The packager refuses an existing
publication, finalized manifest or completed destination.

```sh
UV_CACHE_DIR=/private/tmp/abacus-manual24-uv ./scripts/uv run --locked --no-sync python studies/24_trader_assistant_manual/illustrate.py --output work/24_trader_assistant_manual/<new-run>/figures
python3 studies/24_trader_assistant_manual/document.py prepare --run-id <new-run> --publication-id <new-publication-id>
python3 studies/24_trader_assistant_manual/document.py finalize --run-id <new-run>
python3 studies/24_trader_assistant_manual/document.py seal --run-id <new-run>
```

Retain publication/browser check records in the stage before finalization.
The offline HTML uses local static images and contains no JavaScript; Narada
renders the same selected report through its existing static frontend.

The source-review bundle was staged in `work/` and prepared with its publication
source before sealing the unique run above. Preserve its authored source,
settings, source observations, environment/code records and asset hashes.
Updates to the review require a new run; later presentation-only changes use a
separate [revision](../../templates/README.md#later-presentation-revisions).

Run the read-only metadata and documentation checks from the workspace root
after the run exists:

```sh
python3 scripts/check-agent-docs.py
./scripts/check-workspace --profile metadata
python3 scripts/check-evidence-bundle.py runs/24_trader_assistant_manual/20261014T023500Z_manual24_8c1d7f
python3 scripts/build-research-index.py --check
```

The explicit bundle check applies only if this new run declares
`abacus.evidence/v1`. It checks recorded local bytes and metadata, not the live
source or trading validity. Regenerate the index only after changed navigation
inputs have passed metadata validation.

Publication follows [Narada's workflow](../../docs/narada.md). From
`apps/narada`, validate the source before staging it:

```sh
npm run report:publish -- --report ../../runs/24_trader_assistant_manual/20261014T023500Z_manual24_8c1d7f/publication.json --dry-run
npm run report:publish -- --report ../../runs/24_trader_assistant_manual/20261014T023500Z_manual24_8c1d7f/publication.json
npm run verify
npm test
npm run lint
npm run build
npm run preview
```

With the static preview running, use a separate terminal for
`npm run smoke:preview -- --origin http://127.0.0.1:4173` and inspect contents
navigation, source links, figures, keyboard access and desktop/mobile layout.
Local publication and verification do not deploy the site.
