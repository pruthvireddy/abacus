"""Stage 2 shared file/API conventions frozen before parallel implementation.

Numerical inherited behavior is defined by the explicitly pinned Stage 1 run.
This module contains no event, outcome or statistical calculation.
"""
STUDY_ID = "21_ema_cloud_trend_follow_opportunity"
BASELINE_RUN_ID = "20261010T221954Z_s1_8c6e_r3"
PROTOCOL_VERSION = "0.1.0-stage2.0"
DELIVERY_SHA256 = "59010a558b4e727dbfaa37a64b4a209590288f23744127ab98747cd27ff56d44"
BRANCHES = ("fast", "slow")
PRIMARY_FAMILY_ID = "S2-primary-six-h15-All-points-event-terminal-fast-minus-slow"
PRIMARY_FAMILY_SIZE = 6
PRIMARY_ALPHA = 0.05
TABLES = {
    "S2-T00": "S2-T00_coverage.csv",
    "S2-T01": "S2-T01_signal_flow.csv",
    "S2-T02": "S2-T02_horizon_scorecard.csv",
    "S2-T03": "S2-T03_quantiles.csv",
    "S2-T04": "S2-T04_stability.csv",
    "S2-T05": "S2-T05_calendar.csv",
    "S2-T06": "S2-T06_examples.csv",
    "S2-T07": "S2-T07_geometry_membership.csv",
    "S2-T08": "S2-T08_branch_contrasts.csv",
    "S2-T09": "S2-T09_episode_pairing.csv",
    "S2-T10": "S2-T10_union_overlap.csv",
}
GEOMETRY_VALUES = ("fast_only", "slow_only", "both", "neither", "undefined")
ACCEPTED_MEMBERSHIP_VALUES = ("fast_only", "slow_only", "both", "neither")
PAIR_ORDER_VALUES = ("same_bar", "fast_before_slow", "slow_before_fast", "fast_only", "slow_only", "neither")
PARITY_EXCLUDED_WRAPPER_FIELDS = ("stage", "shared_episode_id", "selected_ema", "accepted_membership", "geometry", "union_id")
SCIENTIFIC_PARITY_TOLERANCE = 0.0

# Independent stream API:
# generate_streams(mapped_bars, interval_minutes, thresholds=None)
#     -> (technical_long, events_long), with touch_mode fast/slow.
# Every inherited slow field/event ID remains unchanged except stage=2.
# Fast IDs replace only the terminal |slow suffix with |fast.
# build_membership(mapped_bars, technical_long, events_long, endpoint=...)
#     -> dict[membership, episodes, pairs, union].
# Shared-episode first accepted IDs retain full causal history. Outcome scoring,
# retrospective contact descriptors and report comparison counts are development
# only. Never replace a warmup first event with a later scoped event.
# Union contains only development accepted events.
# attach_episode_metadata(events, membership) adds shared_episode_id.
# Ledger records identify product, interval_minutes, role and optional branch.
# Technical/event/outcome roles use one file per cell containing both streams,
# or separate branch files with explicit branch metadata. Consumers filter rows
# by touch_mode and must not infer branch from ordering or filenames.
# membership: one scheduled row per product/interval/timestamp, geometry,
# independent accepted booleans/IDs/reasons, shared_episode_id.
# episodes: separate geometric episode identity and explicit terminal cause.
# pairs: first accepted event in each stream only, including unpaired cases.
# union: one product/interval/direction/signal timestamp identity, both IDs.

# Shared geometric departures require usable matching-contract, valid nonzero
# cloud direction. Width is not required to start/rearm a geometric episode.
# Consecutive departures retain identity; a departure after a non-departure
# closes the old episode and starts a new one. Reset terminates before its bar.
# Contact descriptors after first accepted fast distinguish same-bar from
# strictly later geometric slow contact and strictly later accepted slow signal.
# Observed contact is True. No contact is False only after a new full departure;
# interrupted/reset/development-end episodes retain None/unresolved if absent.
# Matching and future labels never influence either stream or primary support.

# Geometry is computed from finite candle range and available valid mapped
# EMA20/50 independently of directional/arming decisions. Equal EMAs can have
# defined geometry but neither stream can signal. Eligibility is exactly usable
# AND feature_valid, preserving All support when direction is undefined.
