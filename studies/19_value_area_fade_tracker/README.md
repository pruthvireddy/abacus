# Value-area fade: external trade tracker

Study 19 documents two user-supplied community posts and seven screenshots:
55 cumulative trades over four weeks, then 100 over seven weeks. Browser inspection attributes both posts to Christopher Thornton; displayed dates
are Aug 5 and Aug 28 (edited), with no visible year. The raw trade ledger and
exact trading rules were not supplied.

**Evidence status:** completed external source review; independent Abacus analysis
is planned. The reported results are unaudited and are not an Abacus backtest.
The two snapshots overlap. Changing trade management, ticker mix and context
definitions prevents treating them as independent validation samples.

Read the [live study](https://abacus-narada.vercel.app/studies/value-area-fade-tracker/),
[sealed offline report](../../runs/19_value_area_fade_tracker/20261007T143300Z_tracker19/report.html),
[Markdown report](../../runs/19_value_area_fade_tracker/20261007T143300Z_tracker19/report.md),
and [evidence manifest](../../runs/19_value_area_fade_tracker/20261007T143300Z_tracker19/manifest.json).

The central candidate is a balanced-market fade from developing/current-session
VAH or VAL toward POC, with profile shape, touch count and VWAP as possible
context filters. The source reported 40 such fades among its first 55 trades;
it did not publish that subset's win rate. Grades and execution rules remain
undefined. No claim of profitable implementation follows from these summaries.

Read the [protocol and future analysis plan](plan.md), [settings](study.yaml),
[source lock](inputs.lock.json), [decisions](notes.md), and
[strategy card](../../strategies/value_area_first_touch_fade.md).

The source-specific `document.py` packages selected observations into tables,
an offline report and Narada content. It verifies transfers and arithmetic; it
does not calculate market-data outcomes or implement the candidate strategy.
Inputs are retained with hashes in ignored `data/research/sahadeva/` storage,
resolved through publication-root configuration. Retention needs a separate backup.

```sh
.venv/bin/python studies/19_value_area_fade_tracker/document.py prepare --run-id 20261007T143300Z_tracker19
.venv/bin/python studies/19_value_area_fade_tracker/document.py verify --bundle work/19_value_area_fade_tracker/20261007T143300Z_tracker19
.venv/bin/python studies/19_value_area_fade_tracker/document.py seal --run-id 20261007T143300Z_tracker19
.venv/bin/python studies/19_value_area_fade_tracker/document.py export --run-id 20261007T143300Z_tracker19 --revision-id 20261007T145000Z_web19r2
python3 scripts/check-agent-docs.py
python3 scripts/build-research-index.py --check
```

Creation commands refuse existing destinations. Verify the saved run at
`runs/19_value_area_fade_tracker/20261007T143300Z_tracker19` without changing it.
Future interpretations or empirical work require a new run and a frozen protocol.
Publication follows [Narada's workflow](../../docs/narada.md).

The selected web revision uses the canonical `sahadeva` producer identifier. An
initial local publication failed catalog attribution; it was retained in private
work storage and never deployed. The corrected presentation uses a new immutable
publication ID; the completed source-review run remains unchanged.
