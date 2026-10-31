# Verification record

## Ranked extension — selected completed run

Selected [20261031_ranked_v2](../../runs/30_verniman_pivot_statistics_es/20261031_ranked_v2/ranked-report.md)
implements all 20 rows of the [matrix](implementation-matrix.md). Requested dates
remain 2020-01-01–2026-10-30; retained market sessions span 2020-01-01–2026-09-18.
Eligible populations each span 2020-01-03–2026-09-18: 875 pivot-matched RTH,
1,308 VWAP-only RTH and 1,292 full-Globex sessions. Eligible-period downloads
retain exact window bounds/counts separately from valid-event coverage.

- 173 source-bound synthetic tests passed, zero skips, including the owning
  `--check study-30` harness gate. Locked execution used no synchronization.
- Baseline parity passed 3,394,961 ledger/summary cells at absolute tolerance
  1e-8 and relative tolerance 1e-11; identities, booleans and nulls match exactly.
- Independent native reconstruction checked 52,382 unique physical events
  through 64,916 mode-specific vectors, 92,910 forward outcomes, 17,007 recross
  windows, 4,336 sequence origins, snapshots, exposures and section transitions.
  All 379,091 summary rows and 5,307,274 numerical/support/quantile cells passed.
  Bootstrap intervals were calculated anew with 2,000 five-session replicates,
  seed 20261031; the independent checker does not re-estimate those intervals.
- Two publication sources passed 51,576 displayed/downloaded-cell checks and
  eight raster transfers. The period-bound supplement includes 288 saved roster
  rows and 2,016 checked cells. All public tables stay below 1,500 rows, 12
  columns, three filters and 100 default rows.
- Narada verify, 250 tests with zero failures/skips, lint and build passed.
  Static checks cover 125 study destinations, 105 reports and 2,187 bounded
  payloads. HTTP preview passed 231 pages, 234 exported files, six real 404s
  and 480 GET/HEAD requests.
- Desktop 1440×1000 and mobile 390×844 checks passed saved filters, separate
  populations, native contents links, 100-row pagination, pending shared-link
  restoration, baseline access and keyboard horizontal table scrolling.
  The native CSV download matched its saved 26,094-byte asset exactly;
  no console warnings/errors were captured during the tested interactions.
- After sealing, the full source audit passed 105 publications and 3,426 hashed
  files. A separate final transfer checked two reports, 30 file pins, eight PNGs
  and four CSVs. All 342 sealed artifacts, two retained bulk ledgers and 141
  protected original baseline/correction/public files passed byte checks.
  The [additive final verification](../../reports/exports/30_verniman_pivot_statistics_es/20261031_ranked_v2/20261031_final_verification_v1/manifest.json)
  records these post-seal checks without modifying the completed run.

### Diagnostic reconciliation and operational attempts

The unsealed ranked v1 stage remains retained. Independent checking found
checker censor-accounting errors for S11/S14 and omitted S13 censor support.
Regression tests and a full saved-row reconciliation preceded the fresh v2
freeze. Exactly 2,224 S13 censored-count cells changed; all other summary cells,
including newly recomputed intervals, match exactly. V1/v2 event, outcome and
coverage ledgers are byte-identical. These results were viewed before the
replacement run; neither stage is an untouched holdout.

The first parity attempt lacked the baseline's six selected download projections;
reconstructing them from recalculated saved summaries resolved that operational
prerequisite. An initial tooling check required its maintained-guide count to
advance from 160 to 162; its rerun passed 230 tests. Early default uv-cache access
was denied and resolved with a task cache. Recorded failed attempts, logs and
reconciliation receipts remain in the run's `provenance-operations/` and retained
diagnostic locators. The v1 chart-order correction is preserved separately;
v2 freezes chronological first-cross bins directly.

### Remaining limits

The compatibility default gate still fails on the two previously documented
Bhishma input prerequisites: the original volume-lead mapping JSON and the ES
roll-1 point-in-time definition pair (1,003 tests, two errors). Its later
Sahadeva (51), legacy01 (13), legacy02 (24) and bounded doctor checks passed
separately. This is not a passing default gate. Tooling/metadata checks passed;
final documentation and research-index checks are recorded with navigation upkeep.

Historical pivot availability, original vendor reconstruction and native chart
parity remain unverified. Eligibility is retrospective; broad conditional slices
are exploratory. Private large evidence has local locators/checksums, with no
off-device backup assertion. Fills, costs, net profitability, native print/PDF
pagination and hosted deployment were not tested.

## Original baseline — retained verification record

Study `30_verniman_pivot_statistics_es` · 2026-10-31

The selected [completed report](../../runs/30_verniman_pivot_statistics_es/20261031_repo_v2/report.md)
uses 875 eligible days, 4,059 price events, 1,886 EMA events, 38,910 outcomes and
9,853 feature snapshots. Completed evidence remains unchanged.

### Scientific and transfer checks

- 126 source-bound synthetic study tests passed; no skips.
- New Bhishma feature module: 15 focused tests passed. The independent
  [input audit](phase1-audit.md) checked all reused OHLC/EMA and minute identities,
  full-history EMA6, VWAP, timing and deterministic aggregation samples.
- Independent saved-evidence verification checked every event, episode,
  forward path, retest and snapshot/context link, 1,157 source quotes, and
  27,216 selected summary cells. Bootstrap intervals were not independently
  re-estimated; their algorithm and denominators have synthetic tests.
- Six publication sources passed 85,412 displayed/downloaded-cell checks and
  one raster transfer check. Original diagnostic event/outcome fields are
  identical; original summaries agree within floating-point roundoff.

### Narada and local preview

Verify, 249 tests (zero failures/skips), lint and build passed. The build checked
125 study destinations, 103 report routes and 2,169 bounded page payloads.
The private source audit passed for 103 publications and 3,332 hashed files;
this is integrity verification, not historical research revalidation.

Desktop and 390×844 mobile browser checks confirmed controls, saved scenario
selection, keyboard Enter reset, typed selection links, contained table overflow
and no console errors. The native browser CSV download exactly matched its saved
5,974-byte source. Keyboard horizontal scrolling was not conclusively observed;
the accessible horizontal table region and mobile overflow were inspected.

**Operational correction:** the sealed `local-verification.json` incorrectly
marked the first HTTP smoke attempt passed before its exit was checked. Its
retained log reports `fetch failed`. The separate
[correction manifest](../../reports/exports/30_verniman_pivot_statistics_es/20261031_repo_v2/20261031_local_verification_correction_v1/manifest.json)
records the successful rerun with local-network access: 229 pages, 232 exported
files, six real 404s and 476 GET/HEAD requests. Only that operational status is
superseded; sealed bytes, scientific results and public bundles remain unchanged.
The first website-test attempt is also retained; three catalog expectations were
updated and temporary loopback-server access supplied before all 249 tests passed.

### Workspace gates and limits

Documentation and workspace tooling/metadata checks passed during implementation.
The compatibility default gate remains failed on two pre-existing Bhishma input
prerequisites: missing original volume-lead mapping JSON and the ES roll-1
point-in-time definition pair. Its Bhishma process ran 1,003 tests with two errors.
Sahadeva (51 tests), legacy01 (13), legacy02 (24) and the bounded VWAP doctor
passed separately after that fail-fast stop. No missing inputs were downloaded.

Historical pivot availability, original vendor reconstruction and native chart
parity remain unverified. Source, contract, calendar, full-day completeness and
warmup exclusions are retrospective. No fills, costs, net profitability or hosted
deployment were tested or performed. Phase 6 remains a separate future strategy
or prospective research protocol.
