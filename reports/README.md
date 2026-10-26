# Reports and presentation exports

See the current [repository map](../ARCHITECTURE.md) for ownership and the
[artifact conventions](../templates/README.md) for evidence and revision rules.

| Location | Purpose | How to update |
|---|---|---|
| `index.html`, `index.md` | Generated offline research library | Edit study/strategy metadata or add a completed run, then run the index generator |
| `quality/` | Data-quality reports | Follow Bhishma's release/validation workflow; preserve imported release evidence |
| `exports/<study-id>/<run-id>/<revision-id>/` | Later presentation exports from frozen evidence | Create a new identified revision and record its source artifacts and hashes |

An original report produced with an analysis belongs in its completed run under
`runs/`. A later layout, format, or selected web presentation belongs in an
export revision here; its numerical evidence remains in the source run.
The `exports/` tree is created only when a revision is needed. There is no
automatic export generator or index integration for it yet; link each revision
explicitly from the relevant study notes or strategy card.

Narada's public bundles are generated publication copies under its app, not the
source of report content. Build them through the [publisher](../apps/narada/README.md).

From the workspace root:

```sh
python3 scripts/build-research-index.py --check
```

Remove `--check` to regenerate after changing indexed metadata. Do not edit the
generated index files directly.

Before regeneration, run `./scripts/check-workspace --profile metadata` for
study/strategy shapes and local target declarations. Hash-pinned strategy rows
have a separate `--profile evidence-references` gate; the builder links authored
selectors and columns without reading CSV values or checking artifact hashes.
`--profile navigation` checks freshness. These categories remain distinct.

Indicator implementations such as Study 18 render their actual README, plan,
settings, lock and source links with explicit validation limits. Current
presentation revisions remain explicitly linked rather than recursively indexed.
See the [contract/reference guide](../docs/evidence-contract.md) for task routing.
