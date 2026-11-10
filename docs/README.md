# Documentation

- [Contributing](../CONTRIBUTING.md): source-only setup, private input requirements, ownership, preservation, checks, and review preparation.
- [Current architecture](../ARCHITECTURE.md): component ownership, file placement, and artifact lifecycle.
- [Verification reference](verification.md): check commands, prerequisites, evidence limits and the compatibility gate.
- [GitHub preparation](github.md): source-only clones, retained artifact restoration, upload auditing and a later first push.
- [Agent task map](../AGENTS.md): what to read, where to write, and which checks to run.
- [Evidence contracts and exact references](evidence-contract.md): opt-in future bundles, saved CSV-row pins, navigation gates and task routing.
- [Narada publication](narada.md): selected report bundles, web rendering, and static hosting.
- [Notebook study template](../templates/notebook-study/README.md): default insight layout, starter notebook, notebook-to-Narada workflow and safe migration of older studies.
- [Storage relocation](migration/storage-relocation-20260922.md): current in-repository bulk storage, internal compatibility links, and destination hash verification.
- [Daily market context](daily-context-20260924.md): nine TradingView one-day exports, indicator provenance, timing-safe lookup, and coverage limitations.
- [Daily Facts v1 design and implementation plan](daily-facts-v1-design.md): proposed ES/NQ/GC daily facts, availability rules, private Postgres/API delivery, and the input audit required before implementation.
- [Daily Facts v1 input audit](../reports/quality/daily-facts-v1-input-audit-20261108/README.md): retained ES/NQ/GC minute coverage by window and year, calendar exclusions, volatility-context lookup coverage, and integrity checks.
- [Range XV FX import](range-xv-fx-20261001.md): eight currency-futures exports, source/enhanced labels, clock assumptions, quality flags, provenance, and read-only verification.
- [Original consolidation record](migration/README.md): historical code/artifact import and its verification; the storage relocation supersedes its external-storage arrangement.
- [Approved structure proposal](repository-structure-proposal.md): the original architectural decision, preserved as a historical proposal.
- [Research library](../reports/index.md): studies, runs, strategy cards, and presentation artifacts.
- [VWAP study](../studies/05_session_vwap/README.md): planned scope; no strategy study has been run by the migration.

Current operating guidance starts with the architecture and agent map. The
structure proposal and migration records preserve historical decisions; update
current guidance when conventions change and leave those records intact.
