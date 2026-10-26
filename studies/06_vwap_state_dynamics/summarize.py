"""Build numerical evidence tables from frozen event Parquet; no threshold search."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.features import PRODUCTS
from src.reporting import (classify, describe_condition, matched_difference,
                           paired_errors, rate, raw_difference)


def subset(frame: pd.DataFrame, product: str, split: str) -> pd.DataFrame:
    if product != "ALL":
        frame = frame[frame["product"] == product]
    if split != "all":
        frame = frame[frame.split == split]
    return frame


def describe_breakdowns(primary: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    dimensions = ["product", "split", "year", "clock_window", "side", "age_bin"]
    for dimension in dimensions:
        for value, part in primary.groupby(dimension, dropna=False):
            for question, classes in (("Q1", ["persistent", "rotational", "other"]),
                                      ("Q2", ["opposing", "aligned", "flat_or_unavailable"]),
                                      ("Q3", ["all", "material", "near_identical"])):
                for condition in classes:
                    row = describe_condition(part, question, condition, rng)
                    rows.append({"dimension": dimension, "value": str(value), **row})
    return pd.DataFrame(rows)


def barrier_table(primary: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame,pd.DataFrame]:
    rows, comparisons = [], []
    for product in ("ALL", *PRODUCTS):
        part = subset(primary, product, "all")
        for question, key, treated, baseline, classes in (
            ("Q1", "state", "persistent", "rotational", ["persistent", "rotational", "other"]),
            ("Q2", "slope_class", "opposing", "aligned", ["opposing", "aligned", "flat_or_unavailable"])):
            for barrier, column in (("fixed_8tick", "barrier_8tick"), ("half_sigma", "barrier_half_sigma")):
                valid = part[part[column].isin(["favorable","adverse","neither","ambiguous"])]
                for condition in classes:
                    selection = valid[valid[key] == condition]
                    info = rate(selection, column, rng, "favorable")
                    rows.append({"product": product, "question": question, "condition": condition,
                        "barrier": barrier, **info, **{name: int((selection[column] == name).sum())
                            for name in ("favorable","adverse","neither","ambiguous")}})
                # The binary favorable indicator retains adverse, neither, and ambiguous in its denominator.
                binary = valid.copy()
                binary["barrier_favorable"] = binary[column] == "favorable"
                diff = raw_difference(binary, key, treated, baseline, "barrier_favorable", rng)
                comparisons.append({"product": product, "question": question, "barrier": barrier,
                    "condition": treated, "baseline": baseline, **diff,
                    "treated_n": int((binary[key] == treated).sum()),
                    "baseline_n": int((binary[key] == baseline).sum())})
    return pd.DataFrame(rows), pd.DataFrame(comparisons)


def examples(events: pd.DataFrame) -> pd.DataFrame:
    primary = events[(events.timeframe == "2m") & (events.anchor == "globex")].copy()
    primary["q1_class"] = np.where(primary.y1_residence == True, "residence", "cross")
    primary["q3_class"] = np.where(primary.paired_tie == True, "tie",
                                  np.where(primary.vwap_win == True, "vwap", "twap"))
    groups = []
    for product in PRODUCTS:
        part = primary[primary["product"] == product].sort_values("landmark_ts")
        for domain, column in (("Q1", "q1_class"), ("Q3", "q3_class"),
                               ("8tick", "barrier_8tick"), ("half_sigma", "barrier_half_sigma")):
            for outcome in part[column].dropna().unique():
                row = part[part[column] == outcome].iloc[0]
                groups.append({"product": product, "domain": domain, "outcome": outcome,
                               "event_id": row.event_id, "landmark_ts": row.landmark_ts,
                               "session_date": row.session_date, "state": row.state,
                               "slope_class": row.slope_class, "source_partition":
                               f"events_{product}_2m_{row.year}.parquet"})
    return pd.DataFrame(groups)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[2]
    stage = workspace / "work/06_vwap_state_dynamics" / args.run_id
    if not (stage / "extraction-summary.json").exists():
        raise FileNotFoundError("complete extraction required")
    (stage / "tables").mkdir(exist_ok=True)
    config = json.loads((stage / "config.json").read_text())
    rng = np.random.default_rng(config["uncertainty"]["seed"])
    events = pd.concat([pd.read_parquet(path) for path in sorted((stage / "events").glob("events_*.parquet"))], ignore_index=True)
    events = classify(events, config)
    if events.event_id.duplicated().any():
        raise ValueError("duplicate event IDs")
    valid = events[events.outcome_missing.isna()]
    complement = valid[valid.side != 0]
    if not (complement.y1_residence.astype(int) + complement.y2_cross.astype(int) == 1).all():
        raise ValueError("Y1/Y2 complement identity failed")
    primary = events[(events.timeframe == "2m") & (events.anchor == "globex")].copy()
    primary_count = len(primary)
    gate = json.loads((stage / "feature-feasibility.json").read_text())
    if primary_count != gate["primary_landmarks"]:
        raise ValueError("primary landmark count changed after gate")
    tables = stage / "tables"
    def save(name: str, data: pd.DataFrame) -> None:
        data.to_csv(tables / f"{name}.csv", index=False)

    # Complete funnel retains state classes, zero sides, and unavailable outcomes.
    funnel = []
    for cohort, view in [("primary", primary), *[(f"{tf}/{anchor}", group) for (tf,anchor), group in events.groupby(["timeframe","anchor"]) if (tf,anchor) != ("2m","globex")]]:
        for product in ("ALL", *PRODUCTS):
            part = view if product == "ALL" else view[view["product"] == product]
            funnel.append({"cohort": cohort, "product": product, "eligible_product_days": int(part.session_key.nunique()),
                "landmarks": len(part), "outcome_capable": int(part.outcome_missing.isna().sum()),
                "missing_outcome": int(part.outcome_missing.notna().sum()),
                "side_zero": int((part.side == 0).sum()),
                **{f"state_{name}": int((part.state == name).sum()) for name in ("persistent","rotational","other")},
                **{f"slope_{name}": int((part.slope_class == name).sum()) for name in ("opposing","aligned","flat_or_unavailable")},
                "material_reference_separation": int(part.material_separation.sum()),
                "paired_ties": int(part.paired_tie.fillna(False).sum()),
                **{f"fixed_{name}": int((part.barrier_8tick == name).sum()) for name in ("favorable","adverse","neither","ambiguous")}})
    save("funnel", pd.DataFrame(funnel))
    missing = events.groupby(["timeframe","anchor","product","outcome_missing"], dropna=False).size().reset_index(name="count")
    save("exclusions", missing)

    # Three frozen primary questions. All pooled rates also appear separately by product and chronology.
    probability_rows, comparison_rows, paired_rows = [], [], []
    for product in ("ALL", *PRODUCTS):
        for split in ("all","development","validation","final"):
            part = subset(primary, product, split)
            for question, classes in (("Q1", ["persistent","rotational","other"]),
                                      ("Q2", ["opposing","aligned","flat_or_unavailable"]),
                                      ("Q3", ["all","material","near_identical"])):
                for condition in classes:
                    probability_rows.append({"product": product, "split": split,
                                             **describe_condition(part, question, condition, rng)})
            for question, key, treated, baseline, outcome in (
                ("Q1", "state", "persistent", "rotational", "y1_residence"),
                ("Q2", "slope_class", "opposing", "aligned", "y2_cross")):
                eligible = part[part[outcome].notna() & (part.side != 0)]
                raw = raw_difference(eligible, key, treated, baseline, outcome, rng)
                matched = matched_difference(eligible, key, treated, baseline, outcome,
                                             question == "Q2", rng)
                comparison_rows.append({"product": product, "split": split, "question": question,
                    "condition": treated, "baseline": baseline,
                    "treated_n": int((eligible[key] == treated).sum()),
                    "baseline_n": int((eligible[key] == baseline).sum()),
                    "other_n": int((eligible[key] == ("other" if question == "Q1" else "flat_or_unavailable")).sum()),
                    **{f"raw_{k}": v for k,v in raw.items()}, **matched})
            paired_rows.append({"product": product, "split": split, **paired_errors(part, rng)})
    probabilities = pd.DataFrame(probability_rows)
    comparisons = pd.DataFrame(comparison_rows)
    for (product, split), group in probabilities.groupby(["product","split"]):
        q1 = group[(group.question == "Q1") & (group.condition == "rotational")].probability.iloc[0]
        q2 = group[(group.question == "Q2") & (group.condition == "aligned")].probability.iloc[0]
        mask = (probabilities["product"] == product) & (probabilities.split == split)
        probabilities.loc[mask & (probabilities.question == "Q1"), "baseline_probability"] = q1
        probabilities.loc[mask & (probabilities.question == "Q2"), "baseline_probability"] = q2
    save("primary_probabilities", probabilities)
    save("matched_comparisons", comparisons)
    save("paired_errors", pd.DataFrame(paired_rows))
    save("breakdowns", describe_breakdowns(primary, rng))
    barrier, barrier_comparisons = barrier_table(primary, rng)
    save("barrier_outcomes", barrier)
    save("barrier_comparisons", barrier_comparisons)
    frozen_rows = []
    for product in ("ALL", *PRODUCTS):
        for state in ("persistent","rotational","other"):
            part = subset(primary, product, "all")
            part = part[(part.state == state) & part.frozen_residence.notna()]
            frozen_rows.append({"product": product, "state": state, **rate(part, "frozen_residence", rng),
                "evolving_probability": float(part.y1_residence.mean()) if len(part) else None})
    save("frozen_reference_sensitivity", pd.DataFrame(frozen_rows))

    # Replication views have their own denominators and never enter the primary pool.
    replications = []
    for (timeframe, anchor), view in events.groupby(["timeframe","anchor"]):
        if (timeframe,anchor) == ("2m","globex"):
            continue
        for product in ("ALL", *PRODUCTS):
            part = view if product == "ALL" else view[view["product"] == product]
            for question, condition in (("Q1","persistent"),("Q1","rotational"),
                                        ("Q2","opposing"),("Q2","aligned"),("Q3","all")):
                replications.append({"timeframe": timeframe, "anchor": anchor, "product": product,
                                     **describe_condition(part, question, condition, rng)})
    save("replications", pd.DataFrame(replications))
    save("examples", examples(events))
    atlas = probabilities[(probabilities["product"] == "ALL") & (probabilities.split == "all")].copy()
    atlas["outcome_definition"] = atlas.question.map({"Q1": "no opposite causal-VWAP close",
        "Q2": "opposite causal-VWAP close", "Q3": "VWAP error < TWAP error to future 1m-close median"})
    atlas["horizon_minutes"] = 30
    atlas["baseline"] = atlas.question.map({"Q1": "rotational", "Q2": "aligned", "Q3": "TWAP wins, ties explicit"})
    save("probability_atlas", atlas)
    metrics = {"study_id": "06_vwap_state_dynamics", "run_id": args.run_id,
        "protocol_version": "1.0.0", "primary_landmarks": primary_count,
        "all_view_landmarks": len(events), "primary_product_days": int(primary.session_key.nunique()),
        "y1_y2_complement_checked": int(len(complement)),
        "primary_probabilities": probabilities[(probabilities["product"] == "ALL") & (probabilities.split == "all")].replace({np.nan: None}).to_dict("records"),
        "primary_comparisons": comparisons[(comparisons["product"] == "ALL") & (comparisons.split == "all")].replace({np.nan: None}).to_dict("records"),
        "event_files": len(list((stage / "events").glob("events_*.parquet")))}
    (stage / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str) + "\n")
    print(json.dumps({"events": len(events), "primary": primary_count,
                      "q1_q2_complement": len(complement)}))


if __name__ == "__main__":
    main()
