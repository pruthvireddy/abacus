# Phase 4: explainable pivot and target selection

Study 29 · protocol 4.0.0 · training dates only.

Phase 4 now has ten complete candidate maps, a retained first-pass capture gate,
source-role comparisons and a separate privately saved Pine implementation 4.0.1.
It is ready for a separately authorized development evaluation of this bounded
engineering control. Source construction and historical availability remain
unresolved, so this is not a validated reconstruction of Verniman's method.

This phase evaluates a small, explainable engineering rule family using the
unchanged N1/E1 candidate control. It does not claim Verniman's method has been
recovered. Read the [readiness reconciliation](readiness-reconciliation.md),
[frozen protocol](protocol.md), [settings](settings.json),
[input declaration](input-declaration.json), [decisions](decisions.md) and
[implementation clarifications](interpretation-record.md).

The [rulebook](rulebook.md) distinguishes source statements, manual explanations
and executable controls. P0 adapts the existing Autopivot hypothesis to the
strict Phase 3 candidate interface. B0/B1 are simple pivot baselines; D0 is a
price-distance destination baseline; D1 tests an auction-exit/range-extreme/
external-boundary priority. Targets are capped at three per branch. Missing
inputs and fallback pivots abstain. No date-specific overrides or profitability
optimization are used.

Use the separate [Phase 4 Pine source](../indicator/verniman_levels_phase4.pine),
[local specification model](../src/phase4_model.py) and
[Pine implementation guide](pine-implementation.md). The saved **Autopivot
Levels - Daily** remains a separate comparator with its name, styling, primary
and alternate policy preserved. Its alternate is not a target.

Earlier Phase 3 failures remain unchanged. New native corrections are recorded
in [candidate implementation corrections](candidate-implementation-corrections.md),
including standalone [generator 3.0.2](../indicator/verniman_levels_phase3_3_0_2.pine).
The underlying v3.0.0 settings and candidate mathematics remain fixed.

The [assessed source-role ledger](source-role-ledger-assessed.json),
[candidate-choice index](candidate-choice-ledger.json), [training results](training-results.md)
and [verification record](verification.md) distinguish actual generated maps,
source identity, selection, ordering and abstention. Exact source windows and
historical availability can remain unresolved; descriptive proximity is not
construction identity. New answer access requires the guarded
[source selector](select_sources.py) and all seven retained expanded maps plus
current Autopivot predictions. Failure placeholders do not satisfy that gate.

Follow [installation and Replay instructions](installation-replay.md) and the
[Phase 5 handoff](phase5-handoff.md) for exact proposed versions and remaining
gates. No development or hidden evaluation was executed, and protected Replay
dates were never visited. A later review agent accidentally encountered hidden
October 21/22/23/26 answer snippets in a concurrently expanded repository guide;
the verification record preserves that incident. Those dates are not pristine
for an exposed evaluator, and Phase 6 requires a fresh unexposed evaluator.
No publication, deployment, trading or P&L test is part of this phase. Evidence
remains in the declared work stage; no incomplete research run is sealed.

Current execution stage: `work/29_verniman_level_reconstruction/phase4_20261031T010249Z/`.
