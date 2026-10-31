# Verification record

Study `30_verniman_pivot_statistics_es` · 2026-10-31

The selected [completed report](../../runs/30_verniman_pivot_statistics_es/20261031_repo_v2/report.md)
uses 875 eligible days, 4,059 price events, 1,886 EMA events, 38,910 outcomes and
9,853 feature snapshots. Completed evidence remains unchanged.

## Scientific and transfer checks

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

## Narada and local preview

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

## Workspace gates and limits

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
