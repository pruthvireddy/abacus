# Verification reference

Start with the [repository README](../README.md) and [contribution guide](../CONTRIBUTING.md).
This reference describes the existing checks and their prerequisites. A source-only
clone supports documentation, tooling and metadata checks; the default compatibility
gate also requires the prepared Python environment and separately restored data.

Git upload preparation has a separate explicit
`./scripts/check-workspace --profile github-readiness` selection. It requires an
actual Git checkout and inspects upload candidates and `HEAD` history; see the
[GitHub guide](github.md). It does not alter the default gate or validate research.

## Reproducibility checks

For agent guidance and navigation changes, run the read-only check:

```sh
python3 scripts/check-agent-docs.py
```

It checks local Markdown links/anchors in the guides explicitly declared by
owner records in [the check registry](../config/workspace-checks.json). This includes
current study READMEs, existing plans and maintained Pine guides. It does not
crawl historical reports or establish architectural behavior.

## Workspace check harness

The [versioned registry](../config/workspace-checks.json) is the allowlist for
[check-workspace](../scripts/check-workspace). The standard-library
[runner](../scripts/workspace_checks.py) selects checks; each owned Python suite
gets a fresh process, cwd and child environment. Numerical code remains with
its package or study. Root pytest still discovers only the two package suites.

The no-argument command preserves the bounded six-step gate, in order:
documentation, Bhishma, Sahadeva, legacy study 01, legacy study 02, then VWAP
`doctor --read-sample`. It fails fast. It does not include all studies, Node,
navigation freshness, private source auditing or storage verification.

```sh
./scripts/check-workspace --list
./scripts/check-workspace --profile documentation
./scripts/check-workspace --profile tooling
./scripts/check-workspace --profile studies --dry-run
./scripts/check-workspace --check study-12 --check study-13
./scripts/check-workspace --profile narada --dry-run
./scripts/check-workspace --context study-12
```

`--list`, `--dry-run`, `--context` and `--help` use system Python's standard
library without executing checks, probing tools, synchronizing environments,
reading data/private configuration or querying the network. Context prints a
bounded owner map: read-first paths, entry points, focused commands, prerequisites
and preservation notes. It does not load guides or infer the latest run.

Execution of package/study checks uses `scripts/uv run --locked --no-sync` and
requires the existing prepared environment; use `bootstrap` separately for setup.
The tooling profile runs only standard-library workspace utility tests with
temporary synthetic fixtures. Other profiles have their declared prerequisites:
full Bhishma tests invoke `clang++` and Ruby and include configured-publication
checks; study 06 reads real 2023 inputs; study 11 includes retained Pine-export
evidence. Clearing environment variables does not isolate those suites from data.
Pine scalar checks do not establish native TradingView compilation or replay.

Selections are deduplicated in registry order. Unknown or empty selections fail.
The execution summary records exact argv/cwd, scope, prerequisites, duration and
exit status; unittest counts and skip reasons come from the child's actual `TestResult`.
Empty discovery, import errors, failed tests and entirely skipped suites are
nonpassing. Mixed passes/skips retain normal unittest exit behavior and disclose
the skipped scope; checks after fail-fast are explicitly unexecuted. Command
checks have no invented test counts. Internal result files are cleaned up; use
`--report <path>` only when a saved versioned JSON summary is wanted.

Use `--list` for the current profile membership. Narada gates require Node 24/npm
and installed app dependencies; the runner does not run `npm ci`. Its local
preview smoke requires an explicit running loopback server and `--preview-origin`;
private source auditing remains separately selected and needs retained evidence.
Navigation uses only the index builder's `--check`, never regeneration. Exporter
and sealing guards have ordinary/optimized selections. `--profile study-evidence`
selects the new stage provenance and numerical-record guards. Future study
08/09/10 stages use structured numerical-test evidence; the old eight/six log
counts apply only to explicit legacy sealing. A suite pass or generic harness
summary does not create stage-bound evidence. See the
[study evidence workflow](../studies/README.md#future-stage-evidence).

Heavy read-only storage/migration checks remain separate. To check the historical
copies and all 46 VWAP partitions explicitly:

```sh
./scripts/uv run python scripts/verify-migration.py --publication-root .
```

Verify every relocated storage file against the recorded destination hashes:

```sh
python3 scripts/verify-storage.py
```

This check is read-only and uses the copies inside Abacus. See the
[storage relocation record](../docs/migration/storage-relocation-20260922.md) and
[storage file inventory](../docs/migration/storage-files-20260922.json).
The original [verification results](../docs/migration/verification.json),
[source mappings and hashes](../docs/migration/source-files.json), and
[approved architecture proposal](../docs/repository-structure-proposal.md) remain
unchanged historical records.

## Evidence and navigation checks

[Evidence contracts and exact references](../docs/evidence-contract.md) distinguish
four gates: future-bundle integrity, strategy CSV-row references, navigation
metadata, and generated-index freshness. They use the standard library and
never execute recorded research/rendering commands.

```sh
./scripts/check-workspace --profile metadata
./scripts/check-workspace --profile evidence-references
./scripts/check-workspace --profile navigation
python3 scripts/check-evidence-bundle.py --help
```

Future research bundles opt in with `contract: "abacus.evidence/v1"`; validation
requires one explicit bundle/manifest target. Existing historical manifests and
presentation revisions remain unassessed under that contract. It verifies
declared local artifact bytes and retained provenance, reports external bytes
as unverified, and does not reproduce calculations or certify research validity.

The initial strategy references select three exact saved CSV rows across the GC
EMA and VWAP-return cards. They cover selected evidence, not every claim. Values
remain in the saved tables; successful references do not promote card status.
Study 18 is registered as `indicator_implementation`, with synthetic kernel
validation and no market-data outcomes or native TradingView verification.

After metadata/reference inputs change, regenerate with
`python3 scripts/build-research-index.py`, then run the freshness check. Context
for `workspace` and `sahadeva` links the contract guide and focused entry points;
planning remains read-only and never verifies evidence bytes.
