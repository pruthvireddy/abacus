# EMA6 crossings of Globex VWAP

Authorized descriptive study of ES, NQ and GC: count completed-bar EMA(6)
crossings of Globex-anchored VWAP; describe variation by daily ATR volatility,
calendar year and calendar month. No trade entries, optimization or profitability.
Read the [frozen protocol](protocol-1.1.0.md), [settings](study.yaml),
[input identities](inputs.lock.json), and [decisions](notes.md).

Current user correction: use EMA6 on three-minute closing prices only. Derive
matching 3m bars/VWAP in memory using the pinned minute source and existing
Bhishma aggregation helpers; preserve the immutable VWAP 1.0.0 release and its
eligibility audit. The old 5m/2m run remains unchanged. Compute the EMA from its pinned
back-adjusted one-minute source across all observed history, including days
excluded from the VWAP sample; never bridge those omissions by calculating the
EMA from eligible days alone. Intraday resampling remains study-local, and does
not publish or rebuild a dataset. ATR is the existing TradingView daily-context
release, aligned as of the Globex open. Daily context has its own chart/roll
conventions and is an analytical context source only.

Stage new evidence in `work/28_globex_ema_crossings/<unique-run-id>/`; freeze
source/settings/input/environment bytes before calculating crossings. Verify
synthetic definitions and independently reconcile saved events/daily summaries
before sealing a fresh completed run. Preserve all prior records and dirty edits.
