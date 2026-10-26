# Research artifact conventions

Use a study to define a question, a run to preserve one execution, and a strategy card to maintain current interpretation across runs. Templates are starting documents; replace placeholders and remove sections that do not apply. They do not calculate statistics or implement a trading system.

## Completed run bundle

Publish into `runs/<study_id>/<unique_run_id>/` only after validation. Build in
`work/` first. Completed bundles are immutable. New calculations or findings
receive a new run; later presentation-only changes use the separate export
revision convention below. The [repository map](../ARCHITECTURE.md) defines ownership.

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
| `publication.json` (optional) | Selected content following Narada's source schema, with figures prepared before the run is sealed |

All displayed numbers and charts must derive from the saved metrics/tables. Rendering a new format must not rerun the analysis. Record a template version. HTML should work offline with local assets; PDF or Excel can be additional exports of the same evidence. Do not label behavioral hit rates as net profitability.

See [report.md](report.md), [report.html](report.html), [strategy.md](strategy.md), and [study.md](study.md). The HTML template uses `{{name}}` placeholders: a future renderer for this template must escape text and sanitize any HTML inserted into content slots. This template has no renderer yet. Narada separately renders its [JSON report contract](../apps/narada/contracts/report.schema.json).

For Narada content, use the [web study report authoring template](web-study-report.md).
The [publication plan](../docs/narada-publication-plan.md) owns the study inventory,
readiness decisions, and Phase 2 pilot handoff.

## Later presentation revisions

For frozen evidence, prepare an export under
`reports/exports/<study-id>/<run-id>/<revision-id>/`. Preserve numerical values,
definitions, and the meaning of the saved findings. New presentation revisions
receive new IDs; do not overwrite an earlier export. This is an authoring
convention, not an implemented export generator or machine-validated schema.

Include a `manifest.json` recording:

- Study, source run, and presentation revision IDs; UTC creation time.
- Exact source-artifact paths relative to the workspace and their SHA-256 hashes.
- Renderer version or code revision, exact command, and template/format version.
- What changed in the presentation and the checks performed.
- Output artifact paths and hashes, excluding the manifest's own hash.

Save the revised report or `publication.json` and selected figures alongside that
manifest. Use a new Narada publication ID for changed web content and run the
[publisher](../apps/narada/README.md); its public files are generated copies.
Link the revision from study notes or a strategy card so it remains discoverable.
The research index does not automatically scan this export directory.

The [opt-in evidence contract](../docs/evidence-contract.md) currently covers
future research bundles only. Presentation revisions retain the convention above
and remain unassessed by that validator. Do not retrofit either historical runs
or sealed export revisions. Study 12/13 phase provenance and the bounded
numerical-test records use companion formats within their existing manifest
families; they do not claim adoption of this general evidence contract. See the
[future-stage workflow](../studies/README.md#future-stage-evidence).

The active study 08/09 exporters share only prepared-revision writing through
Sahadeva's [presentation_revision.py](../packages/sahadeva/src/abacus_sahadeva/presentation_revision.py).
They retain exporter, saved-evidence projector and writer bytes plus a producer
inventory. All input reads, hash checks and serialization finish before creating
the fresh revision. Existing-revision refusal, read-only `--check` comparisons
and diagnostic partial output remain. The producer inventory is neither a
research seal nor a completion manifest; authored selections and claims stay
with the study and existing revisions/finalizers remain unchanged.

## Research library

`python scripts/build-research-index.py` rebuilds `reports/index.html` and `reports/index.md` deterministically using only Python's standard library. It reads `studies/*/study.json`, `strategies/index.json`, and the existing run/artifact directories. Run it after adding or publishing evidence. `--check` verifies generated files are current without writing them.

The library labels historical imports as unreviewed. “Latest” means the greatest natural run-ID ordering within a study; it is a navigation aid, not a recommendation. Choose future run IDs with sortable UTC timestamps and a unique suffix. A reference run must be selected explicitly with a documented review decision.

Historical runs keep their original naming and artifact formats. Their additive import manifests distinguish provenance added during consolidation from original results. Historical presentation exports have unresolved source-run attribution unless an explicit mapping has been verified.

Use separate root harness profiles for `metadata`, `evidence-references` and
`navigation`. Metadata validity does not verify table bytes; reference validation
does not certify all claims; freshness only compares generated index content.
Study 18's indicator branch links the prototype's implementation files and states
its synthetic/TradingView limits without advertising computed research.
