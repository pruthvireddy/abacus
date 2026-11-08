# Verification record

Study `30_verniman_pivot_statistics_es` · 2026-10-31

## Before historical outcomes

- Study 30: 115 synthetic tests passed in the existing locked environment.
- New Bhishma indicator module: 15 focused synthetic tests passed, plus the
  independent full retained-data feature audit in [Phase 1/input audit](phase1-audit.md).
- Documentation: 160 maintained guides checked, zero errors.
- Workspace tooling: 230 tests passed; navigation metadata valid for 30 studies.
- Compatibility default gate: failed in Bhishma with two existing missing-input
  integration prerequisites, after 1,003 tests. Missing volume-lead mapping JSON
  and the original ES roll-1 definition pair are unrelated to this delivery.
  Sahadeva (51 tests), legacy 01 (13), legacy 02 (24), and the bounded VWAP
  input doctor passed when run separately; the default remains failed.

The outcome run will freeze exact source/settings/input/environment identities
before execution and independently verify saved events, paths and summaries.
Source integrity, numerical validity and local Narada verification are separate
records. No outcome, application or browser checks are claimed before execution.

## Input qualifications

Repository-only selected-contract fragments are reused. Original raw vendor
mapping reconstruction, native chart parity and historical pivot availability
remain unverified. All missing dates, ambiguous sources, contract mismatches,
calendar uncertainty and warmup failures remain explicit. No external data
was requested or acquired; no trade fills, costs or profitability are tested.
