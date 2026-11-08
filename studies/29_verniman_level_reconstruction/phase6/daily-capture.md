# Phase 6B daily prediction capture

Run only for a date in [calendar.json](calendar.json), using the exact
[freeze](freeze.json). No prospective session has been captured during Phase 6A.
All times below are America/New_York; scheduled cutoffs are 09:25 EST/14:25 UTC.
Complete the map by 09:30 EST/14:30 UTC. Never move this deadline to accommodate
feed delay or reconstruct a missed record as timely.

## Before 09:25

1. Read only this workflow, the frozen protocol/settings and bounded non-answer
   guidance. Do not open source-collection directories, X, mutable knowledge-base
   maps, source galleries, historical hidden answers or other scheduled answers.
   Identify the actual prediction actor. Keep a source-access event log complete
   to best knowledge through within five minutes before execution; do not claim
   future non-access. Collector/scorer identities must refer to separate actual
   actors if independence is claimed.
2. In the logged-in **in-app browser**, create a separate Phase 6 layout through
   normal UI. Preserve the user's layouts and saved indicators. Add the exact
   private selector source pinned by the freeze, verifying its stored revision
   rather than silently using a mutable account script. The Phase 5 private copy
   was named *Verniman Levels Phase 5 verification 4.0.1*, revision 1, with LF
   source hash `1145834bfb240029f07342e52f98d805771ca4f2a39a646c19e80d3846794924`.
   Its prior native verification is historical implementation evidence only.
3. Check CME_MINI:ESZ2026/CME GLOBEX, individual unadjusted contract, standard
   five-minute candles, ETH, New York timezone, 16-tick rows, VA70, grid0, 09:25,
   P0/D1 and empty anchors. Record visible latency/entitlement status. Confirm
   genuine live delivery when the market is open; closed-market access or absence
   of a delay badge does not prove it. Do not buy data or modify subscriptions.
4. Load all eight identified coverage windows, including the complete previous
   futures week and three expected prior RTH members. Check readiness before
   cutoff. Capture chart/settings/source-revision evidence with local clock
   evidence. Each day's input provenance must identify that day and file hashes;
   do not leave the old Phase 5 input label as purported current provenance.

## At 09:25, before 09:30

Wait for the confirmed 09:20–09:25 terminal bar. The actual current 09:25–09:30
bar must not enter execution. Record the native included-bar boundary, cutoff P,
pivot, both target branches, IDs/reasons/fallback and readiness in screenshot/AX
captures. Hash each actual evidence file; a required file pin is not automated
OCR or proof that a human transcribed it correctly.

Use the normal chart-data download. Retain its original CSV unchanged. The
preparer makes a separate OHLCV-only prefix and discloses excluded rows; execution
rejects post-cutoff rows. For the examples below, replace `DAY`, `RAW_CSV`,
`NEW_INPUT_DIR`, `REQUEST_JSON` and `NEW_CAPTURE_DIR` with exact paths. Each output
directory must be new under `work/29_verniman_level_reconstruction/`.

```sh
UV_CACHE_DIR=/private/tmp/abacus-study29-uv-cache ./scripts/uv run --locked --no-sync python studies/29_verniman_level_reconstruction/phase6/capture.py --freeze studies/29_verniman_level_reconstruction/phase6/freeze.json prepare-input --session DAY --raw-csv RAW_CSV --output NEW_INPUT_DIR
```

Prepare the [capture request template](templates/capture-request.json) with the
actual actor, fresh access-log pin, input-manifest pin, native evidence pins and
observed completed boundary. Use `capture_mode=prospective` only for actual same-day
capture. Then execute once and retain every failure/attempt:

```sh
UV_CACHE_DIR=/private/tmp/abacus-study29-uv-cache ./scripts/uv run --locked --no-sync python studies/29_verniman_level_reconstruction/phase6/capture.py --freeze studies/29_verniman_level_reconstruction/phase6/freeze.json capture --request REQUEST_JSON --output NEW_CAPTURE_DIR
```

The wrapper loads exact retained model/dependency snapshots, generating the full
map and all six unchanged configurations. It records baseline19, cutoff P,
five profiles, complete candidates/rejections/cap omissions, composite members,
PBT eligibility, original IDs/prices/reasons and all fallback/abstention/partial
states. Eight-window coverage is retained separately. No answer loader is imported.
Compare saved P0/D1 numerics to actual native evidence; discrepancies remain
implementation findings. The local wrapper never claims to execute Pine.

Do not rerun to repair a miss after answers or overwrite a first capture. Save a
new ledger revision binding the immutable receipt and the freeze. The initial
stage ledger has all 20 pending dates; update only the scheduled row's final
status in a new revision, preserving the previous ledger. Do not finalize other
future dates. Keep source content closed after a successful daily capture.

## Missing, late or reconstructed records

If live delivery/input readiness or capture fails, preserve the failure. After
that date's 09:30 deadline, use a fresh access log and
[status request](templates/status-request.json):

```sh
UV_CACHE_DIR=/private/tmp/abacus-study29-uv-cache ./scripts/uv run --locked --no-sync python studies/29_verniman_level_reconstruction/phase6/capture.py --freeze studies/29_verniman_level_reconstruction/phase6/freeze.json finalize-status --request REQUEST_JSON --output NEW_STATUS_DIR
```

This creates an explicit missing/input-unavailable receipt with no fake map.
An actual later map retains `late`; a later historical Replay reconstruction
uses `historical_replay` and remains `reconstructed`. Unsupported maps keep
coverage/readiness failures. Exposure keeps its event and effective classification.
Do not invent a future capture, change the clock, backdate a receipt, back-solve
anchors, select another contract/date or extend the sample.

Saved-record verification does not recompute selection:

```sh
UV_CACHE_DIR=/private/tmp/abacus-study29-uv-cache ./scripts/uv run --locked --no-sync python studies/29_verniman_level_reconstruction/phase6/capture.py --freeze studies/29_verniman_level_reconstruction/phase6/freeze.json verify-capture --receipt CAPTURE_RECEIPT_JSON
```

Local process clocks, browser screenshots and operator attestations are the
available timestamp evidence. Hashes prove bytes, not independently certified
existence time or enforced non-access. No recurring capture/notification runs
automatically. End each daily task after the immutable receipt and ledger revision.
