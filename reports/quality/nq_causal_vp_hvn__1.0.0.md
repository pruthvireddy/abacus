# NQ causal VP/HVN 1.0.0

1,383,199 evening snapshots; 4,195 observed dates. Full source/lineage hashes and OHLC/tick/order checks passed. Feature-only validation and source bytes are retained with the release. No trade labels or outcomes are included.

- OHLCV uniform-row approximation; no tick-profile or transient intraminute selection.
- Historical last-bar gate replaced by sequential completed-minute replay.
- Final adjusted snapshot is retrospective; raw execution prices retained.
- Strict reference completeness uses normal sessions and flags holidays/early closes as incomplete; no bars filled.
- Source volume-leader choice is a saved historical mapping, not a certified live roll rule.
- Equal-strength suppression uses lower candidate order; Pine sort-indices tie stability not externally certified.
