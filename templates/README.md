# Research artifact conventions

Use a study to define a question, a run to preserve one execution, and a strategy card to maintain current interpretation across runs. Templates are starting documents; replace placeholders and remove sections that do not apply. They do not calculate statistics or implement a trading system.

## Completed run bundle

Publish into `runs/<study_id>/<unique_run_id>/` only after validation. Build in `work/` first. Completed bundles are immutable; corrections receive a new run or explicit report revision linked to the original.

| File | Required contents |
|---|---|
| `manifest.json` | Study/run ID, UTC execution time, exact command, Git revision and dirty-source snapshot if needed, dependency lock hash, input/config identities, checks, artifact hashes |
| `config.json` | Exact executed settings, including exclusions, comparisons, splits, and execution assumptions |
| `inputs.lock.json` | Release/manifest hashes and portable locations resolved through local configuration |
| `metrics.json` | Stable metric IDs, estimates, units, denominators, uncertainty, horizon, cohort, split, and missing/ambiguous counts |
| `tables/` | Exact numerical evidence in portable tabular files |
| `figures/` | Local SVG/PNG or interactive HTML figures generated from saved numerical evidence |
| `report.html` and `report.md` | Question, findings, methods, uncertainty, limits, and reproduction instructions |
| `advice.md` | Dated interpretation, applicability, supporting and opposing evidence, costs tested, and next research action |
| `events.manifest.json` | Retained event-evidence location, schema, row count, hash, and retention status when event files are external |

All displayed numbers and charts must derive from the saved metrics/tables. Rendering a new format must not rerun the analysis. Record a template version. HTML should work offline with local assets; PDF or Excel can be additional exports of the same evidence. Do not label behavioral hit rates as net profitability.

See [report.md](report.md), [report.html](report.html), [strategy.md](strategy.md), and [study.md](study.md). The HTML template uses `{{name}}` placeholders: a future report renderer must escape text and sanitize any HTML inserted into content slots. No renderer is included yet.

## Research library

`python scripts/build-research-index.py` rebuilds `reports/index.html` and `reports/index.md` deterministically using only Python's standard library. It reads `studies/*/study.json`, `strategies/index.json`, and the existing run/artifact directories. Run it after adding or publishing evidence. `--check` verifies generated files are current without writing them.

The library labels historical imports as unreviewed. “Latest” means the greatest natural run-ID ordering within a study; it is a navigation aid, not a recommendation. Choose future run IDs with sortable UTC timestamps and a unique suffix. A reference run must be selected explicitly with a documented review decision.

Historical runs keep their original naming and artifact formats. Their additive import manifests distinguish provenance added during consolidation from original results. Historical presentation exports have unresolved source-run attribution unless an explicit mapping has been verified.
