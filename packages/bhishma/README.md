# Bhishma — Data & Features

Use the [component instructions](AGENTS.md) for task routing and checks, and the
[repository map](../../ARCHITECTURE.md) for file placement and dependencies.

Bhishma owns ingestion, calendars, continuous contracts, reusable features,
validation, and immutable data publication. Sahadeva consumes its public loaders.

Moving this package and its storage into Abacus did not create a data release.
The configured publication project root is the workspace (`.`), containing
`catalog/`, `data/`, `reports/`, and `requests/`. Physical `raw/`, `staging/`,
`inbox/`, `curated/`, and `features/` trees are directly under `data/`, preserving
their original nesting and bytes. See the [data layer guide](../../data/README.md)
and [storage relocation record](../../docs/migration/storage-relocation-20260922.md).
The original project folder remains preserved but is no longer a storage dependency.

Set `paths.publication_root` in the workspace's `config/paths.local.toml`, or
`ABACUS_PUBLICATION_ROOT`. Explicit CLI `--root` or `--project-root` arguments
take precedence. An explicit `--output` on the Databento CLI takes precedence
over its default destination. Paths are resolved at command execution; they are
never inferred from this installed package's directory. `--help` requires no
data configuration or network access.

The [TradingView daily-context snapshot](../../docs/daily-context-20260924.md)
adds nine source-supplied OHLCV/indicator series for lower-timeframe context.
`abacus_bhishma.daily_context.load_daily_context` reads one asset by trading-day
range, while `align_daily_context_asof` aligns a batch of timezone-aware
intraday timestamps to the latest completed daily values. The source Pine
formula script and limitations are cataloged with the release.

The existing loaders retain their public interfaces and require an explicit
publication root. The feature loader also requires an explicit release version.
Use the read-only `abacus-research doctor --read-sample` from the workspace root
to check access to the pinned VWAP publication. Build/download commands remain
separate operations and must not be used as workspace verification.

Tests use synthetic examples plus the configured historical publication for
existing integration checks. Integration checks skip when no publication root
is configured; they fail if a configured root is invalid. Run
`./scripts/check-workspace --check bhishma` from the workspace root for this
suite through the [workspace harness](../../README.md#workspace-check-harness).
Its no-argument compatibility gate adds the other package, two legacy suites and
bounded VWAP doctor sample. It does not perform full storage/migration validation.
Full package discovery also invokes `clang++` and Ruby; the harness declares those
prerequisites and reports actual integration skips. Environment setup remains
separate from locked `--no-sync` execution.

## External daily outlook levels

The [Verniman fulfilled request](../../requests/fulfilled/verniman_daily_levels__1.0.0.yaml)
defines a ten-session ESZ26 sample for October 7–20, 2026. Source capture belongs
to `abacus_bhishma.verniman_capture`; offline extraction and immutable publication
belong to `abacus_bhishma.verniman_levels`. Both run with `python -m`; use
`--help` to inspect their arguments. Capture/download and publication are explicit
operations, separate from verification.

Raw HTML, per-post Atom and linked image bytes remain in a unique capture batch;
decoded text and extracted records use staging. The [data guide](../../data/README.md)
locates the versioned curated `outlooks` and `levels` Parquet/CSV tables and
viewing-only `daily_summary.csv`. Retain source text, contract, revision, plan
branch, trigger/target role, ordinal, ranges and confirmation conditions.
The summary's pivot is shorthand for the shared plan threshold; source labels
and discrepancies remain in the detailed tables. No market bars or independent
indicator calculations underlie this extraction.

Published/updated metadata and capture timestamps have separate meanings.
The reused historical posts do not verify pre-open availability of the captured
2026 plans: `available_at` remains null and the status is
`historical_availability_unverified`. Do not infer timing from permalink dates,
image filenames or an assumed posting hour. Preserve previous captures and
releases; source revisions require a new publication identity when delivered.

The separate [2.0.0 year-to-date specification](../../requests/fulfilled/verniman_daily_levels__2.0.0.yaml)
covers January 1–October 20, 2026 without changing 1.0.0. Chronological capture
belongs to `abacus_bhishma.verniman_backfill`; offline extraction/publication
belongs to `abacus_bhishma.verniman_history`. The older-link ledger retains
every encountered post and issue, with `coverage` and `issues` Parquet/CSV tables
exposing date gaps and extraction outcomes. Distinguish weekend/weekday absences
from capture failures and unparseable posts. Infer years through descending
month/day chronology anchored to 2026 and corroborate source contracts/update
claims; retain uncertainties and any raw 2025 boundary evidence. Only in-scope
2026 outlooks are selected. Contract changes remain explicit, prices stay as
stated, and all availability values remain null. Coverage and extraction checks
do not establish historical pre-open timing or trading results.

The separate [3.0.0 specification](../../requests/fulfilled/verniman_daily_levels__3.0.0.yaml)
covers January 1–December 31, 2025 and preserves the sample and 2026 releases.
Capture uses `abacus_bhishma.verniman_backfill` with a December 31, 2025 anchor;
offline extraction/publication belongs to `abacus_bhishma.verniman_history_2025`.
Use the same canonical outlooks, levels, coverage and issues tables, with new
raw captures and a public-feed comparison. The hash-pinned December 31 seed
retains its original prior-crawl captures and timestamps; newly traversed posts
receive new captures. Infer session year from chronological
month/day values rather than contract delivery year: late 2025 can legitimately
use ESH26. Preserve source disagreements and the out-of-range older boundary;
all `available_at` values remain null. New captures and the 3.0.0 publication
must not replace bytes from either earlier release.

The separate [4.0.0 specification](../../requests/fulfilled/verniman_daily_levels__4.0.0.yaml)
covers January 1–December 31, 2024 and preserves all three earlier releases.
Capture uses `abacus_bhishma.verniman_backfill` with a December 31, 2024 anchor;
offline extraction/publication belongs to `abacus_bhishma.verniman_history_2024`.
Use the same canonical tables and viewing summary, with source captures,
timestamp claims, chronological ledger and public-feed comparison. The seed
reuses the prior crawl's hash-pinned December 31, 2024 capture with its original
timestamps; newly traversed posts receive new captures. Coverage includes all
366 calendar dates and retains gaps, duplicate-date cases and source issues.
Infer the year from chronological month/day values; ESH25 can be legitimate
in late 2024. Keep source timing claims separate from capture time, and preserve
null `available_at` values and the unverified historical availability status.

The separate [5.0.0 specification](../../requests/fulfilled/verniman_daily_levels__5.0.0.yaml)
covers January 1–December 31, 2023 and preserves all earlier releases.
Capture uses `abacus_bhishma.verniman_backfill` with a December 31, 2023 anchor;
offline extraction/publication belongs to `abacus_bhishma.verniman_history_2023`.
Use the same canonical tables and viewing summary, source captures, timestamp
claims, chronological ledger and public-feed comparison. The December 29 seed
reuses the prior crawl's hash-pinned boundary capture with its original
timestamps; newly traversed posts receive new captures. Coverage includes all
365 calendar dates, including the December 30–31 weekend after the seed, and
retains gaps, duplicate-date cases and source issues. Infer the year from
chronological month/day values; late 2023 can legitimately use ESH24. Preserve
source timing claims separately from capture time, null `available_at` values
and the unverified historical availability status.

The separate [6.0.0 specification](../../requests/fulfilled/verniman_daily_levels__6.0.0.yaml)
covers January 1–December 31, 2022 and preserves all earlier releases.
Capture uses `abacus_bhishma.verniman_backfill` with a December 31, 2022 anchor;
offline extraction/publication belongs to `abacus_bhishma.verniman_history_2022`.
Use the same canonical tables and viewing summary, source captures, timestamp
claims, chronological ledger and public-feed comparison. The December 30 seed
reuses the prior crawl's hash-pinned boundary capture with its original
timestamps; newly traversed posts receive new captures. Coverage includes all
365 calendar dates, including the December 31 weekend date after the seed,
and retains gaps, duplicate-date cases and source issues. Infer the year from
chronological month/day values; late 2022 can legitimately use ESH23. Do not
assign a body to 2022 from updated metadata alone. Preserve source timing
claims separately from capture time, null `available_at` values and the
unverified historical availability status. Preserve the observed May 2022 to
December 2021 link discontinuity with its reviewed boundary evidence; month/day
ordering alone must not turn that older sequence into additional 2022 outlooks.

The separate [7.0.0 specification](../../requests/fulfilled/verniman_daily_levels__7.0.0.yaml)
covers January 1–December 31, 2021 and preserves all earlier releases.
Capture uses `abacus_bhishma.verniman_backfill`, anchored to the source body
explicitly describing the final trading session of 2021; offline extraction
and publication belong to `abacus_bhishma.verniman_history_2021`. Explicitly
selected prior context captures retain their original timestamps, while the
new traversal assigns their month/day chronology to 2021. Retain the full
365-date coverage, duplicate dates, extraction issues and older boundary.
The fresh public-feed comparison can identify detached source bodies: include
such a candidate only with supplemental captures and an explicit source-year
review, preserving its distinct date-assignment method and current navigation.
Supplementary captures retain linked extensionless or legacy-host chart images
that the frozen capture helper does not recognize. Preserve the original
capture ledger and separately pin the reviewed collection and image records.
Publication/update claims remain separate from capture timestamps; every
`available_at` remains null with historical availability unverified.

The separate [8.0.0 specification](../../requests/fulfilled/verniman_daily_levels__8.0.0.yaml)
covers January 1–December 31, 2020 and preserves all earlier releases.
Capture uses `abacus_bhishma.verniman_backfill`, anchored to the retained body
explicitly describing the final 2020 trading session; offline extraction and
publication belong to `abacus_bhishma.verniman_history_2020`. Keep the same
canonical tables and summary, all 366 calendar dates, source captures and
timestamps, gaps, duplicate-date cases, and extraction issues. Preserve the
older 2019 boundary and compare the navigation with a fresh public feed.
Pandemic-era bodies batch-updated in May 2021 can still describe 2020 plans:
infer dates from anchored body chronology and retained source context rather
than update years. Explicitly review detached candidates and retain full-size
image supplements where the frozen helper misses source links. Publication
and update claims remain separate from capture time; all `available_at`
values remain null with historical availability unverified.

In the 2020 release, Plan A can be bearish and Plan B bullish. Determine the
stored side from consistent explicit above/buy or below/sell wording, and
retain original A/B text and source-letter fields in the new schema and
summary. Consumers must use `side` for direction and `source_plan_branch` for
the original letter. Ambiguous or duplicated assignments remain text/issues.

The separate [9.0.0 specification](../../requests/fulfilled/verniman_daily_levels__9.0.0.yaml)
covers January 1–December 31, 2019 and preserves every earlier release.
Capture uses `abacus_bhishma.verniman_backfill` with the retained body explicitly
describing the final 2019 trading session as its seed; offline extraction and
publication belong to `abacus_bhishma.verniman_history_2019`. Retain the same
canonical tables, viewing summary and original A/B identity fields, with all
365 calendar dates, source captures, timestamp claims, gaps, duplicate-date
groups and extraction issues. Preserve the older 2018 boundary and a fresh
public-feed reconciliation, including explicit discovery exhaustion or other
retrieval qualifications. Infer dates from anchored body chronology and source
context, preserving disagreements with publication/update metadata. Economic
direction follows consistent source instructions rather than the A/B letter.
Every `available_at` remains null with historical availability unverified.

The 2019 extraction also recognizes bounded explicit be/become a buyer/seller
instructions, retaining their original wording and confirmation conditions.
Source prose with ambiguous direction, action or prices remains text/issues.
An exact single numeric trigger with no named label retains its price and
original text, with `source_label = null` and an `unlabelled_trigger_price`
issue. This nullable-label policy is specific to 9.0.0: only exact trigger
points qualify, while targets require labels and ambiguous bare ranges/lists
remain unsupported. Earlier releases and their extraction policies stay frozen.

The separate [10.0.0 specification](../../requests/fulfilled/verniman_daily_levels__10.0.0.yaml)
covers January 1–December 31, 2018 and preserves every earlier release.
Capture uses `abacus_bhishma.verniman_backfill`, starting from the retained
December 31 boundary assigned to 2018 by the prior anchored chronology and
New Year context; offline extraction and publication belong to
`abacus_bhishma.verniman_history_2018`. Keep the same canonical tables, viewing
summary and bounded null-label trigger policy. Preserve original A/B/C identity
with the new nullable `source_plan_c_text`; neutral branches remain source text.
Retain literal single-digit contract codes. Qualified generic `/ES Value`
posts can retain levels with `contract=null` and an explicit issue; never
infer a delivery month. Bounded below/bearish-internals “lean on” wording can
classify a bearish source scenario with a warning, keeping its conditional
trigger distinct from the ancillary lean reference in the unchanged text.
Retain all 365 calendar dates, source captures, timestamp claims, gaps,
duplicate-date cases, extraction qualifications and the older 2017 boundary.
Reconcile the observed navigation with a fresh public feed, recording actual
feed exhaustion and any retrieval limitations. Infer session years from body
chronology and source context, keeping metadata claims separate. Every
`available_at` remains null with historical availability unverified.

The separate [11.0.0 specification](../../requests/fulfilled/verniman_daily_levels__11.0.0.yaml)
requests January 1–December 31, 2017 using
`abacus_bhishma.verniman_history_2017`. The current source retains 40 daily
plans: 28 with body dates and 12 without a month/day. Preserve the undated
plans with null session dates and no numeric extraction; never repair dates
from publication claims, permalinks, images or neighboring posts. The December
29 seed explicitly describes the final trading day of 2017; December 31 is
the requested calendar limit, not an observed post date.

Keep the four canonical tables, viewing summary, source A/B/C identity and
qualified null-contract/null-label policies. Ancillary leaning references stay
in unchanged text and issues, separate from conditional triggers and targets.
Retain the entire traversal and classify educational context separately from
daily plans. Current navigation and the independent feed exhaust without an
observed 2016 dated boundary. Require pinned exhaustion/candidate reconciliation
evidence, keep `traversal_reached_lower_boundary=false`, and record all 365
calendar dates as observed coverage. Earlier months' absence does not establish
historical completeness. All source timestamp claims remain separate from
capture time; every `available_at` stays null. Earlier releases remain frozen.

The separate [12.0.0 specification](../../requests/fulfilled/verniman_daily_levels__12.0.0.yaml)
recovers available 2016 plans from archived HTML and historical feeds using
`abacus_bhishma.verniman_history_2016`. Retain archive indexes, every retrieval
attempt and the current-source baseline separately. An explicit Outlook date
may appear in the source post title; name that date method and independently
qualify its year. Archive observation, original timestamp claims and current
capture clocks stay separate, with all `available_at` values null.

Preserve unlettered Trading Plan prose without inventing A/B labels. A side
with explicit targets but no source threshold can retain `targets_only` rows,
with no inferred trigger and a required issue. Trigger interpretation separates
conditional thresholds from explicit at/around execution references and failure
references. Keep exact source wording, side statuses and partial extraction
visible in the schema and summary. Historical feed entries retain full response
bytes and exact entry selectors; do not attach current Atom content to archived
HTML. Archive/index coverage does not establish original full-year completeness.
Every earlier release, schema and producer remains unchanged.

The [13.0.0 consolidated specification](../../requests/fulfilled/verniman_daily_levels__13.0.0.yaml)
provides one cross-year snapshot through the October 28, 2026 retrieval review.
`abacus_bhishma.verniman_consolidated` unions explicitly pinned historical
tables with a separately reviewed update. It does not rerun legacy extraction.
Year-partitioned Parquet tables, CSVs, original release memberships, original
coverage observations and separate user-recollection tables follow the
[data guide](../../data/README.md). Exact source-revision/capture overlap is
deduplicated, with later extraction versions taking precedence and original
IDs retained. Different revisions and duplicate dates remain. One explicitly
qualified cross-release date conflict preserves both original assignments;
unknown conflicts are refused. Existing publications and consumers stay pinned.

Use `verniman_consolidated.load_release(root, manifest_path, manifest_sha256,
table="levels", start_date="2026-10-21", end_date="2026-10-29")` with the
explicit new manifest hash. The loader reads only manifest-listed partitions;
start is inclusive and end exclusive. Unbounded reads retain undated records.
Use `table="observations"` or `table="observation_levels"` for retrospective
user notes; these never replace freshly captured source records or establish
point-in-time availability. Every `available_at` remains null. Verification
checks saved bytes and relational integrity, not research validity.
Default loading verifies the immutable release's own files and retained
provenance. `verify_release(..., verify_inputs=True)` separately rehashes the
original pinned inputs, including source preparation paths; ordinary future
source edits do not make the saved release unreadable.

The [14.0.0 single-post specification](../../requests/fulfilled/verniman_daily_levels__14.0.0.yaml)
adds October 30, 2026 from the explicitly supplied "AI worries" source. Publish
with `--version 14.0.0` and a new input specification: `update` keeps the exact
original October 28 update pin, while `additional_updates` lists the separately
pinned new source additions in precedence order. Each update keeps its own
source identity, observations and coverage evidence. This reuses saved historical
extractions and preserves all prior master records; it does not rewrite 13.0.0.
The pinned loader reads the release version from the selected manifest and
restricts its artifact paths to that release. The publisher's default stays
13.0.0 and refuses existing destinations. Every new version requires a new
request, immutable output paths and an explicit preservation comparison.

The [16.0.0 image annotation specification](../../requests/fulfilled/verniman_daily_levels__16.0.0.yaml)
adds `user_supplied_image` evidence to the existing observation tables. Keep
it distinct from recollections and canonical source plans. Image observations
require retained image path/hash, literal chart date and displayed time; they
never establish pre-open availability. Only explicitly printed annotation
prices become neutral/reference observation levels. Preserve unpriced labels
on the parent observation rather than estimating numbers from chart geometry.
`image_observation_only` coverage records image evidence without filling the
canonical blog-plan gap. Earlier pinned schemas and releases stay compatible.

The [19.0.0 color-role specification](../../requests/fulfilled/verniman_daily_levels__19.0.0.yaml)
applies the user's explicit legend to those five images: light blue is the
pivot (`neutral/trigger`), green a bullish target, and red a bearish target.
Each new image interpretation pins that legend and explicitly supersedes its
same-image predecessor. The current observation tables select one interpretation
per image; prior parent/level snapshots, original input documents and older
releases preserve the earlier neutral references. Prices and labels stay exact,
and unpriced annotations retain null values with their newly identified roles.
The ordering counts unpriced target slots using nearest-pivot chart position;
it does not assert an independently verified execution sequence. These remain
image observations rather than captured blog outlooks.

Focused synthetic checks run with the prepared locked environment:

```sh
UV_CACHE_DIR=.uv-cache ./scripts/uv run --locked --no-sync python -m unittest discover -s packages/bhishma/tests -p 'test_verniman_consolidated.py' -v
```

The publisher CLI requires an explicit pinned `--input-spec` and `--request`,
uses the configured publication root or `--root`, and refuses existing output
or staging paths. A delivery is a new immutable release; publication is not a
verification or refresh command. Use `--help` to inspect its arguments.

## Consumer loaders and runtime prerequisites

Study 30's repository-only ES delivery is
[es_contract_session_indicators 1.0.0](../../requests/inbox/es_contract_session_indicators__1.0.0.yaml),
implemented by `es_contract_session_indicators.py`. It reuses pinned three-minute
OHLCV and five-minute EMA20/50, adds three-minute EMA6 and minute-HLC3 Globex
VWAP, and retains selected-delivery identity and source/calendar qualifications.
The [manifest](../../catalog/datasets/es_contract_session_indicators__1.0.0.json)
and [quality report](../../reports/quality/es_contract_session_indicators__1.0.0.md)
identify the new immutable delivery; no external data was acquired. Its pinned
loader selects `bars1`, `bars3`, `bars5` or `quality` and never repairs bytes.
Features require 250 preceding valid native bars. Contract mismatches and missing
history remain unavailable; no historical pivot is translated into adjusted prices.
Focused synthetic checks use `test_es_contract_session_indicators.py`.

Consumer loaders take an explicit publication root and remain read-only. The GC,
VWAP and continuous APIs support an optional hash-pinned manifest selection;
without those options their existing directory-loading behavior is preserved.
Loaders never repair a release. The VP/HVN loader retains its original guarantees.

| Canonical import | Result | Selection |
|---|---|---|
| `feature_loader.load_gc_5m_release` | `pyarrow.Table` | Explicit supported release and `version="1.0.0"`; year-ordered partitions and optional column projection |
| `feature_loader.load_session_anchored_vwap` | `pyarrow.Table` | Explicit version, product, timeframe, columns, and inclusive start/exclusive end on `session_date` |
| `continuous_loader.open_continuous_dataset` | Lazy `pyarrow.dataset.Dataset` | Product and named unadjusted/back-adjusted variant |
| `vp_hvn_loader.load_release` | Lazy `pyarrow.dataset.Dataset` | Explicit `"1.0.0"`, default `snapshots` or another supported table; only manifest-listed files |
| `ema_cloud_loader_v2.load_release` | `pandas.DataFrame` | Required manifest path and SHA256; one declared product/3m or 5m partition for `same_contract_ema_cloud__1.1.0`; pinned 1.0.0 delegates to its unchanged loader |

All imports above are under `abacus_bhishma`. The canonical VP/HVN loader can
import and scan independently of publication builders, the calculation engine,
and native tools. The compatibility import `vp_hvn_release.load_release` remains
available, but importing that builder still loads its builder dependencies.
Study 14 uses the thin loader and shared hashing directly. Its dataset identity,
minute scalar and JSON writing remain study-owned, without importing the publisher.

VP/HVN accepts `snapshots`, `candidates`, `decisions`, `sessions`, and `rhythm`.
Unsupported versions or tables, and supported tables without manifest-listed
files, raise `ValueError`. A schema-bearing zero-row Parquet file remains valid.
Missing manifests/data, malformed JSON, and invalid Parquet remain failures.
Arrow supplies lazy scanning and projection; the loader adds no implicit Hive
partition fields or directory discovery.

Bhishma declares pandas `2.3.3` directly alongside its existing Databento, NumPy,
and Arrow dependencies. The workspace development pandas entry remains in place.
Ruby is an operation-specific prerequisite for the derived five-minute request
reader's safe YAML parsing. Consumer imports and CLI `--help` do not invoke it.
`vp_hvn.enable_native(cache)` explicitly requires `clang++` and checks for it
before mutating the cache directory. Compilation and library-load errors remain
hard failures; VP/HVN publication requires native activation. Ordinary loader
imports and scans do not activate or compile native code.

Focused checks from the workspace root:

```sh
./scripts/check-workspace --profile bhishma-loaders
./scripts/uv run --locked --no-sync python -m unittest discover -s packages/bhishma/tests -p 'test_runtime_prerequisites.py'
./scripts/uv run --locked --no-sync python -m unittest discover -s packages/bhishma/tests -p 'test_vp_hvn.py'
./scripts/uv lock --check
```

The VP/HVN suite retains the strict native parity check and requires a working
compiler; an unmet prerequisite is not successful native verification. Fixtures
use temporary roots. The runtime-prerequisite suite also invokes Ruby on tiny
safe-YAML fixtures. Run the existing GC band tests and publication-maintenance
regressions as well, then finish with `scripts/check-workspace`.

## Continuous publication maintenance

Phase 1 and Phase 2 refuse existing manifests, quality reports, and any of their
owned final data destinations, including incomplete outputs and broken symlinks.
Their `build --force` flag permits recovery of only the builder's exact temporary
directory, `data/curated/.<dataset-name>.part`, when final state and recovery
artifacts are absent. It cannot replace a publication. Symlinked or redirected
staging is refused. Inspect partial final output, `.backup` directories, and
metadata `.part` files manually; builders preserve these for diagnosis.

Phase 1 owns the two `roll_schedule.{parquet,csv}` leaves under
`data/curated/continuous/1m/roll=volume_lead_v1/`. It preserves that shared parent,
including Phase 2's adjustment audit directory and unrelated siblings. Each
publisher rechecks destination conflicts before moving data. Rollback attempts to
restore only this invocation's outputs to staging and removes only empty parents
it created; failed restoration retains evidence for inspection. These checks do
not provide locking between concurrent writers.

The small shared helpers have explicit owners:

| Module | Responsibility | Consumers |
|---|---|---|
| `abacus_bhishma.provenance` | Streaming file SHA-256, Git provenance and verified retention of declared source bytes | Publication builders; selected-manifest byte checks; Study 14 hashing |
| `abacus_bhishma.calendar` | Existing holiday-session rules and their private date helpers | VWAP, VP/HVN release builder |

The old `_sha256` and `_git_version` imports remain available from the builders,
as does `session_anchored_vwap.holiday_sessions`. Holiday dates, reason ordering,
eligibility, and each consumer's session policies retain their existing behavior.
Future builder provenance records hash the extracted helper sources as well as
the builder; VP/HVN includes the calendar in its retained source list. Historical
contracts and manifests remain unchanged.

From the workspace root, run focused synthetic safety and helper checks:

```sh
./scripts/check-workspace --profile bhishma-safety
python3 scripts/check-agent-docs.py
./scripts/check-workspace
```

Existing phase regression tests and `abacus-research doctor --read-sample` read
configured pinned inputs. CLI `--help` needs neither data configuration nor
network access. `abacus-session-anchored-vwap validate` is also read-only, but its
saved builder-fingerprint comparison can fail after source maintenance; preserve
the check and historical fingerprint and report the mismatch. A synthetic test
pass does not certify a historical replay or revalidate a release's numbers.

## Focused publication and consumer maintenance

Use `./scripts/check-workspace --context bhishma` for concrete source/test paths.
The two focused profiles use the prepared locked Python environment without sync.
They exercise disposable fixtures, not configured historical data, Ruby parsing
or native compilation. `bhishma-loaders` also runs Study 14's import guards as a
separate study-owned process. `bhishma-safety` includes ordinary and optimized
publication guards, retained provenance and calendar fixtures. Full `bhishma`
discovery and the six-step default keep their configured/native prerequisites.

| Task | Source owner | Focused check |
|---|---|---|
| Publication refusal/recovery | Publisher output inventories in `continuous_phase1.py`, `continuous_phase2.py`, `vp_hvn_release.py`, `daily_context.py`, `gc_ema_bands.py`, `derived_ohlcv_5m.py`, `session_anchored_vwap.py`; shared mechanics in [publication_safety.py](src/abacus_bhishma/publication_safety.py) | `--profile bhishma-safety`; [continuous](tests/test_continuous_publication_safety.py) and [feature](tests/test_feature_publication_safety.py) fixtures |
| Future provenance | Publisher-declared source lists and [provenance.py](src/abacus_bhishma/provenance.py) | `--check bhishma-publication-provenance`; [retention fixtures](tests/test_publication_provenance.py) |
| Consumer loading | [feature_loader.py](src/abacus_bhishma/feature_loader.py), [continuous_loader.py](src/abacus_bhishma/continuous_loader.py), [vp_hvn_loader.py](src/abacus_bhishma/vp_hvn_loader.py) | `--profile bhishma-loaders` |
| Manifest identity/membership | Family checks in owning loaders; byte/path selection in [manifest_selection.py](src/abacus_bhishma/manifest_selection.py) | `--check bhishma-manifest-loaders`; [manifest fixtures](tests/test_manifest_selected_loaders.py) |
| Native calculations | Scalar/native activation in [vp_hvn.py](src/abacus_bhishma/vp_hvn.py) and [native source](src/abacus_bhishma/vp_hvn_native.cpp) | Prepared-environment `test_vp_hvn.py` command above; actual `clang++` required |
| Study 14 consumer integration | [Study 14 maintenance guide](../../studies/14_asia_session_vp_levels/README.md#consumer-maintenance) and its six consumers | `--check study-14-consumer-imports`; affected numerical fixtures remain study-owned |

### Owned outputs and failed attempts

Each publisher declares its actual final, staging and metadata recovery paths.
Required source manifests, specifications, Pine sources and request inputs are
not publication destinations. In particular, VP/HVN separates publication-owned
data/catalog/reports from workspace-owned requests and default work staging.
Its existing `.spec.json` and `.source.pine` inputs remain usable.

Before source processing where paths are known, and again before promotion or
metadata writes, publishers refuse existing outputs, broken symlinks, linked
ancestors and non-directory parents below their explicit roots. Metadata creation
does not replace an existing destination or recovery file. An explicit VP/HVN
`verified_stage` is inspected before resolution and verified as the selected
stage; another stage is never discovered or adopted automatically.

Inspect a failed stage, partial final output or recovery file before attempting
publication again. Daily context retains its failed feature stage for diagnosis.
Continuous `force` recovery retains its narrow staging-only meaning. No release
overwrite mode or recursive cleanup of shared parents is added. Conflict checks
do not lock concurrent writers or provide a crash-safe transaction across all
artifacts; an interrupted attempt can leave partial state that a retry refuses.

Future publications retain explicitly declared local source/helper bytes and
the environment lock, with copied hashes verified. Phase 2 includes its Phase 1
helpers; VP/HVN includes its loader/path helpers. The recorded scope identifies
the retained inventory, not complete dependency discovery or proof of historical
execution. These additions do not retrofit existing manifests or releases.

### Optional manifest-selected loading

Pass both `manifest_path` and `expected_manifest_sha256` to the GC five-minute,
VWAP or continuous loader. Relative manifest paths resolve from the explicit
publication root; an absolute caller-selected manifest may live elsewhere, while
its data locators remain root-relative and contained. A failed pin, identity or
membership check never falls back to directory discovery.
`verify_selected_files=True` additionally checks selected file sizes and hashes.
Every listed record must declare a nonnegative integer size and lowercase SHA-256;
valid declarations alone do not verify file bytes. For VWAP, select the interval
dataset manifest (`session_anchored_vwap_2m_v1.json` or `session_anchored_vwap_5m_v1.json`),
not the separate release manifest that pins those two manifests.

The guarantees are separate:

1. The supplied manifest hash and the owning family's actual identity fields
   match the requested release/version, interval or continuous variant.
2. Only listed files under the exact requested product/release directory are
   selected; duplicate records, unsafe paths and missing selected files fail.
   Continuous schedules, factors and instrument metadata are excluded.
3. Selected bytes are checked only when explicitly requested. Manifest identity
   and membership alone do not certify Parquet file content.
4. Unlisted files may exist and are ignored in manifest mode; the loader does not
   certify their absence or recursively audit a release or external storage.

GC retains individual year/path-ordered Parquet reads, Arrow schema promotion,
one-shot column iterables and empty projections. VWAP retains product/timeframe
aliases, Hive fields and inclusive/exclusive session-date filtering, including
filters on a field projected away. Continuous remains a lazy Arrow dataset with
caller-controlled scanning; explicit file lists use the canonical product path
as the Hive partition base. VP/HVN retains manifest file order and no Hive
inference. Invalid Parquet and incompatible Arrow schemas remain visible errors.

## Causal NQ volume-profile snapshots

The [NQ VP/HVN contract](../../catalog/indicators/nq_causal_vp_hvn__1.0.0.spec.json)
and [byte-preserved source](../../catalog/indicators/nq_causal_vp_hvn__1.0.0.source.pine)
define the new reusable feature release. The builder consumes pinned manifests
from that contract, independently of study code. The historical replay records
18:00–00:00 pre-bar profiles, cached candidates, selected zones, all filter
decisions, separate final-adjusted comparisons, and quality flags; references
use all source minutes. Execution prices and trade labels remain research work.

After delivery, load an explicit version and table through the public API:

```python
from abacus_bhishma.paths import resolve_publication_root
from abacus_bhishma.vp_hvn_loader import load_release

snapshots = load_release(resolve_publication_root(), "1.0.0", "snapshots")
```

Other table names are `candidates`, `decisions`, `sessions`, and `rhythm`.
The local source-hashed C++ accelerator requires `clang++`; its source is
included in the package and release provenance. It follows the same sequential
arithmetic as the scalar test reference, without fast-math. Never rebuild into
an existing release directory. Point-in-time certification and external
TradingView-feed parity are not asserted.

## Same-contract EMA cloud delivery

The [1.1.0 request](../../requests/inbox/same_contract_ema_cloud__1.1.0.yaml) and
[fulfilled specification](../../requests/fulfilled/same_contract_ema_cloud__1.1.0.yaml)
define the continuous 2017–2026 extension of the 1.0.0 fixed-clock delivery.
The separate [v2 builder](src/abacus_bhishma/ema_cloud_release_v2.py) publishes
new immutable data, schema, indicator, quality, and source/audit records. It
preserves the original 1.0.0 release and all inherited scientific columns,
dtypes, and nulls through its original endpoint. This input delivery contains
unadjusted prices and causal EMA20/50 plus Wilder ATR14; signals and forward
outcomes remain study-owned.

Use [ema_cloud_loader_v2.py](src/abacus_bhishma/ema_cloud_loader_v2.py) with the
explicit publication root, `product`, integer `interval` of 3 or 5,
`manifest_path`, and `expected_manifest_sha256`. Selected-byte verification
defaults to enabled. The loader reads only the declared partition and requires
its role, row count, product/interval identity, and ordered unique timestamps.
It never rebuilds or repairs data. Its pinned 1.0.0 branch preserves the existing
loader behavior.

Feature state follows the full causal roster across years and study periods.
The 250-observation readiness rule remains unchanged. The retained calendar
policy omits the ES/NQ 16:15–16:30 New York pause only before session date
2021-06-28; rule-generated uncertified holiday and early-close sessions remain
unusable slots with resets. Missing source minutes never establish a known
closure. The release records reconstruction limits, modeled completion timing,
and input-only 500-observation/seed sensitivity separately from study evidence.
Focused fixtures are `test_ema_cloud.py`, `test_ema_cloud_release.py`, and
[test_ema_cloud_v2.py](tests/test_ema_cloud_v2.py); tests use disposable inputs.

## ATAS Range XV ingestion

`abacus_bhishma.range_xv` converts headerless ATAS OHLC exports into the
established Range XV research schema, retaining all source strings and row
positions. It applies the explicitly inferred export-clock conversion, checks
OHLC and chronology, and produces separate quality flags/session profiles.
The [October 1 FX batch](../../docs/range-xv-fx-20261001.md) uses this module
through a workspace orchestrator; the stored inputs remain in Sahadeva's
`data/range_xv/` tree. It creates no volume or contract-roll metadata, and does
not change historical converters, snapshots, or completed studies.
