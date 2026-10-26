# Evidence integrity and exact references

The opt-in future research contract is `abacus.evidence/v1`. Existing manifests
have not adopted it merely because they contain `schema_version: 1`. Historical
and unknown future contracts return **unsupported**, with no artifact assessment;
their research is not judged invalid because its format differs.

Validate one explicitly selected bundle directory or manifest, from any cwd:

```sh
python3 /Users/ppanati/Documents/projects/abacus/scripts/check-evidence-bundle.py /tmp/synthetic-bundle --json
```

The caller must supply the target. The checker never scans runs, seals evidence,
executes recorded commands, follows archived external paths, or writes reports.
Exit codes are 0 for `verified_declared_artifacts`, 1 for invalid metadata or local
artifact bytes, and 2 for an unsupported contract. The structured result identifies
the verified local count, unverified external declarations, recorded check statuses,
source verification scope, and limitations. A recorded failed check remains failed
even when its retained evidence passes the integrity check.

## Future research bundle fields

Adopt the identifier explicitly in a new `manifest.json`. Version 1 supports
`bundle_kind: "research"` only; a presentation variant is deferred. All paths below
are relative to the selected bundle, and all referenced local files must appear in
the artifact inventory. The manifest is excluded from its own inventory.

| Field | Required declaration |
|---|---|
| `contract` | Exactly `abacus.evidence/v1` |
| `bundle_kind` | Exactly `research` |
| `study_id`, `run_id` | Explicit study and unique run identity; the checker does not register or discover either |
| `inventory_scope` | Exactly `declared_artifacts`; undeclared files are not assessed |
| `results` | `kind` (`quantitative` or `qualitative`), `state` (`computed` or `not_computed`), and `artifacts` (array of inventoried file paths); `reason` required for `not_computed` |
| `provenance.settings` | Inventoried frozen settings file |
| `provenance.input_lock`, `provenance.exclusions` | Inventoried lock/exclusions file, or `{ "state": "not_applicable", "reason": "..." }` where appropriate |
| `provenance.commands` | Inventoried JSON array of exact command records |
| `provenance.checks` | Inventoried JSON array of recorded check evidence |
| `provenance.environment_lock` | Inventoried retained environment lock |
| `provenance.code` | `revision` (pinned 40/64-character lowercase hexadecimal revision), actual boolean `dirty`, inventoried `status` file, and `source_snapshot` |
| `provenance.code.source_snapshot` | Nonempty `paths` of retained source files, all inventoried; `scope` states which source bytes the list covers |
| `artifacts` | Nonempty array of `{ "path": "...", "bytes": 123, "sha256": "..." }` records |
| `external_artifacts` (optional) | Array of `{ "id": "...", "locator": "...", "bytes": 123, "sha256": "..." }` declarations; external bytes remain unverified |

The source snapshot retains actual source bytes for both clean and dirty code.
Hashes of files in today's workspace are insufficient. Its declared scope does
not establish dependency completeness or prove which code executed historically.
An environment lock pins retained bytes; it does not prove the installed execution
environment matched that lock.

`results.state` records whether statistics were computed. A qualitative review can
use `not_computed`, cite an authored claim ledger, and explain that no market
statistics were computed. It needs no trading metrics or fabricated sample. A
`computed` result requires at least one inventoried result artifact. The validator
does not interpret those results. Null and false remain distinct JSON values;
`dirty: null` is rejected rather than treated as false.

An exact command record has `argv` (nonempty string array), `cwd` (recorded string),
and optional `environment` (object of string values). These are records, never
instructions to the checker. A check record has a unique `name`, `status` (`passed`,
`failed`, `not_run`, or `not_applicable`), an inventoried `record` for passed/failed
checks, and a `reason` for checks not run or not applicable. Check outcomes are
retained claims, not independently rerun verification.

Unknown fields in this narrow adopted version, duplicate JSON keys, non-finite
numbers, duplicate inventory paths, malformed hashes and boolean byte sizes are
rejected. Paths reject absolute/traversal/dot/empty segments, ambiguous separators
or encodings, and symlink components, including symlinked ancestor directories.
Local artifacts must be ordinary files. The checker verifies their recorded size
and SHA-256. External locators are opaque declarations and are never resolved.

The disposable adoption examples live in
[synthetic fixture tests](../scripts/tests/test_evidence_contract.py), which create
quantitative and qualitative bundles under temporary directories and delete them
after testing:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_evidence_contract.py'
python3 -O -m unittest discover -s scripts/tests -p 'test_evidence_contract.py'
```

To inspect one complete, self-cleaning synthetic adoption example from the root:

```sh
python3 -B - <<'PY'
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path('scripts').resolve()))
sys.path.insert(0, str(Path('scripts/tests').resolve()))
from evidence_contract import assess_bundle
from test_evidence_contract import bundle
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory).resolve()
    bundle(root, qualitative=True)  # computes inventory pins for synthetic bytes
    print(json.dumps(assess_bundle(root), indent=2))
PY
```

## What the assessment establishes

Structural metadata, verified declared local bytes, unverified external bytes, and
recorded checks are separate facts. Integrity does not reproduce calculations,
judge statistical/scientific validity, establish profitability, verify a native
TradingView compiler or chart runtime, or confirm an off-device backup. These
checks authorize no research, sealing, presentation export, publication or deployment.
Completed artifacts keep their historical contracts. Future study 12/13 phase
provenance and the bounded numerical-test records are study companion formats,
documented in [future-stage evidence](../studies/README.md#future-stage-evidence).
They do not claim partial adoption of `abacus.evidence/v1`; their sealers enforce
scientific/numerical gates separately from byte integrity.

## Exact strategy CSV-row references

Add optional `evidence_refs` to one entry in [strategies/index.json](../strategies/index.json)
after reading the card and its associated study plans. The only current kind is
`csv_row`; cards without references remain valid. Each record contains:

| Field | Meaning |
|---|---|
| `id`, `label` | Stable ID unique within the card and a useful evidence label |
| `kind` | Exactly `csv_row` |
| `study_id`, `run_id` | Explicit saved identity; the study must belong to the card's `study_ids` |
| `artifact` | Safe run-relative CSV file path |
| `sha256` | Actual lowercase SHA-256 of the saved file |
| `where` | Nonempty mapping of header names to exact saved string selectors |
| `columns` | Nonempty, unique, ordered header names to inspect |

The reference checker verifies the declared artifact hash, unique CSV headers,
selector/column existence, well-formed record widths and exactly one matching
row. Blank, `0` and `False` strings remain their saved strings. Do not copy
expected statistics into metadata, round them, recalculate outcomes or infer
references from prose. The saved table is the value source.

From the repository root:

```sh
python3 scripts/check-evidence-references.py --strategy gc_ema_outer_lower_long
python3 scripts/check-evidence-references.py --strategy vwap_return_after_departure
./scripts/check-workspace --profile evidence-references
```

Initial adoption covers the GC 2026 upper-half-close row and its unfiltered
comparison in the same cooldown/horizon cell, plus the original VWAP primary
`b.all.primary` scorecard. These three rows cover selected evidence, not every
claim. Card prose retains the previously inspected 2026 qualification,
inconclusive interval and untested GC implementation options, and the original
versus later exploratory VWAP distinction. Passing references verifies local
bytes/selection only and never promotes card evidence status or establishes
profitability.

## Navigation metadata and freshness

Study JSON keeps the existing common fields, optional integer `schema_version: 1`
and free status vocabulary. Optional `content_kind` defaults to `research`.
`indicator_implementation` adds an `implementation` object containing safe,
study-relative `plan`, `settings`, `inputs_lock` and `source` locators, without
selecting a research reference run. Harness ownership kind `study` is independent
of navigation kind. Study 18 links its actual prototype files and declares
synthetic adapter/kernel validation, no computed market outcomes, no native
TradingView validation and no strategy profitability finding.

The metadata checker validates shapes, unique IDs, owning directories,
associations, explicit reference-run existence, safe target paths and reference
shape. Associations need not be symmetric. It does not read table contents or
verify hashes. The builder labels the explicit `reference_run` independently of
natural-order latest runs; `run_id` and `latest_exploratory_run` do not select it.
Reference links show authored selectors/columns without copying numerical values.
Presentation exports remain explicitly linked; no recursive export discovery is
added.

```sh
./scripts/check-workspace --profile metadata
python3 scripts/build-research-index.py
./scripts/check-workspace --profile navigation
```

Regenerate only after navigation inputs change. The builder validates inputs
before writing either output; `--check` reads without writing and checks only
freshness. Metadata validity, reference integrity and freshness have separate
results. The harness registers future-contract **help** only; actual bundle
assessment always needs a caller-supplied target and never scans all runs.

## Task routing and bounded context

Use `./scripts/check-workspace --context workspace` or `--context sahadeva` for
entry points and exact focused commands. Planning does not execute validators,
load saved artifact bytes, inspect private settings or install dependencies.

| Task | Read first | Narrow gate |
|---|---|---|
| Metadata-only change | This guide, [study registration](../studies/README.md), affected study README/plan and `study.json` | `--profile metadata`; regenerate after inputs change, then `--profile navigation` |
| New evidence reference | This guide, [strategy guide](../strategies/README.md), card prose and associated study plans | `check-evidence-references.py --strategy <id>` plus metadata/freshness after changed inputs |
| Future evidence-bundle preparation | This guide, [run guide](../runs/README.md), owning protocol and [artifact conventions](../templates/README.md) | `check-evidence-bundle.py <explicit-bundle-or-manifest>`; preparation/sealing needs its own authorization |
| Historical evidence lookup | [Sahadeva guide](../packages/sahadeva/AGENTS.md), [runs](../runs/README.md), owning study README/plan and explicit saved locators | Bounded inspection; only a declared reference-byte check when appropriate, with historical contract unassessed |
| Presentation-only revision | [report exports](../reports/README.md), [revision convention](../templates/README.md#later-presentation-revisions), owning study and source-run pins | Owning export checks under separately authorized scope; future presentation contract remains deferred |

Critical validator paths are covered by disposable ordinary/optimized fixtures
under `scripts/tests/`. Integrity checks do not establish scientific validity,
complete claim coverage, executed dependency completeness or backup availability.
