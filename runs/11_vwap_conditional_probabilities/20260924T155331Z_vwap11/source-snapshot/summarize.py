"""Create frozen-protocol numerical tables from study 11 event evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.features import ANCHORS, LOCAL_ANCHORS, PRODUCTS
from src.statistics import (
    block_rate, brier_losses, calibration_rows, classify_ab, classify_corridor,
    outcome_counts, score_interval, supported_predictions,
)


def load_parts(folder: Path, pattern: str) -> pd.DataFrame:
    paths = sorted(folder.glob(pattern))
    return pd.concat([pd.read_parquet(path) for path in paths], ignore_index=True) if paths else pd.DataFrame()


def selection(frame: pd.DataFrame, product="ALL", anchor="ALL", split="all",
              anchor_column="anchor") -> pd.DataFrame:
    result = frame
    if product != "ALL":
        result = result[result["product"] == product]
    if anchor != "ALL":
        result = result[result[anchor_column] == anchor]
    if split != "all":
        result = result[result.split == split]
    return result


def rate_row(frame: pd.DataFrame, outcome: str, positive, metric: str,
             rng: np.random.Generator, **labels) -> dict:
    return {**labels, "metric": metric, **block_rate(frame, outcome, positive, rng)}


def question_a_table(primary: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    metrics = [
        ("frozen_return_30", True, "frozen_return_30"),
        ("evolving_return_30", True, "evolving_return_30"),
        ("frozen_return_window", True, "frozen_return_window"),
        ("evolving_return_window", True, "evolving_return_window"),
        ("evolving_without_frozen_30", True, "evolving_without_frozen_30"),
    ]
    for product in ("ALL", *PRODUCTS):
        for anchor in ("ALL", *ANCHORS):
            for split in ("all", "development", "validation", "final"):
                part = selection(primary, product, anchor, split)
                for column, positive, metric in metrics:
                    rows.append(rate_row(part, column, positive, metric, rng,
                                         product=product, anchor=anchor, split=split,
                                         facet="overall", facet_value="all"))
        product_part = selection(primary, product)
        for (anchor, elapsed), part in product_part.groupby(["anchor", "elapsed_bin"], observed=True):
            rows.append(rate_row(part, "frozen_return_30", True, "frozen_return_30", rng,
                                 product=product, anchor=anchor, split="all",
                                 facet="elapsed_bin", facet_value=elapsed))
        for (distance, elapsed), part in product_part.groupby(["distance_bin", "elapsed_bin"], observed=True):
            rows.append(rate_row(part, "frozen_return_30", True, "frozen_return_30", rng,
                                 product=product, anchor="ALL", split="all",
                                 facet="distance_x_elapsed", facet_value=f"{distance}|{elapsed}"))
        for (clock, elapsed), part in product_part.groupby(["clock_window", "elapsed_bin"], observed=True):
            rows.append(rate_row(part, "frozen_return_30", True, "frozen_return_30", rng,
                                 product=product, anchor="ALL", split="all",
                                 facet="clock_x_elapsed", facet_value=f"{clock}|{elapsed}"))
    return pd.DataFrame(rows)


def outcome_table(frame: pd.DataFrame, domain: str, outcome: str, classes: list[str],
                  anchor_column: str, anchors: tuple[str, ...], rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for product in ("ALL", *PRODUCTS):
        for anchor in ("ALL", *anchors):
            for split in ("all", "development", "validation", "final"):
                part = selection(frame, product, anchor, split, anchor_column)
                valid = part[part[outcome].isin(classes)]
                counts = outcome_counts(valid, outcome, classes)
                for name in classes:
                    rows.append({
                        "domain": domain, "product": product, "anchor": anchor,
                        "split": split, "facet": "overall", "facet_value": "all",
                        "outcome_class": name, **counts,
                        **block_rate(valid, outcome, name, rng),
                    })
        product_part = selection(frame, product)
        facet_column = "geometry_bin" if domain == "B" else "position_bin"
        for value, part in product_part.groupby(facet_column, observed=True):
            valid = part[part[outcome].isin(classes)]
            counts = outcome_counts(valid, outcome, classes)
            for name in classes:
                rows.append({
                    "domain": domain, "product": product, "anchor": "ALL",
                    "split": "all", "facet": facet_column, "facet_value": value,
                    "outcome_class": name, **counts,
                    **block_rate(valid, outcome, name, rng),
                })
        if domain == "C":
            for value, part in product_part.groupby("width_bin", observed=True):
                valid = part[part[outcome].isin(classes)]
                counts = outcome_counts(valid, outcome, classes)
                for name in classes:
                    rows.append({
                        "domain": domain, "product": product, "anchor": "ALL",
                        "split": "all", "facet": "width_bin", "facet_value": value,
                        "outcome_class": name, **counts,
                        **block_rate(valid, outcome, name, rng),
                    })
    return pd.DataFrame(rows)


def barrier_sensitivity(primary: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    classes = ["return_first", "extension_first", "neither", "ambiguous"]
    for product in ("ALL", *PRODUCTS):
        part = selection(primary, product)
        for label, column in (("0.25_sigma", "barrier_quarter_sigma"),
                              ("0.5_sigma", "barrier_primary"),
                              ("1.0_sigma", "barrier_one_sigma")):
            valid = part[part[column].isin(classes)]
            counts = outcome_counts(valid, column, classes)
            for name in classes:
                rows.append({"product": product, "extension_barrier": label,
                             "outcome_class": name, **counts,
                             **block_rate(valid, column, name, rng)})
    return pd.DataFrame(rows)


def timing_table(ab: pd.DataFrame, corridors: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for product in ("ALL", *PRODUCTS):
        part = selection(ab, product)
        for outcome, group in part.groupby("barrier_primary", dropna=False):
            resolved = group.barrier_primary_minute.dropna()
            rows.append({
                "domain": "B", "product": product, "outcome_class": str(outcome),
                "rows": len(group), "resolved_rows": len(resolved),
                "first_event_minute_p25": float(resolved.quantile(.25)) if len(resolved) else None,
                "first_event_minute_median": float(resolved.median()) if len(resolved) else None,
                "first_event_minute_p75": float(resolved.quantile(.75)) if len(resolved) else None,
                "toward_vwap_mfe_median": float(group.toward_vwap_mfe_points.median()),
                "away_mae_median": float(group.away_mae_points.median()),
                "return_distance_ticks_median": float(group.return_distance_ticks.median()),
                "extension_distance_ticks_median": float(group.extension_distance_ticks.median()),
            })
        part_c = selection(corridors, product)
        for outcome, group in part_c.groupby("frozen_outcome", dropna=False):
            resolved = group.first_event_minute.dropna()
            rows.append({
                "domain": "C", "product": product, "outcome_class": str(outcome),
                "rows": len(group), "resolved_rows": len(resolved),
                "first_event_minute_p25": float(resolved.quantile(.25)) if len(resolved) else None,
                "first_event_minute_median": float(resolved.median()) if len(resolved) else None,
                "first_event_minute_p75": float(resolved.quantile(.75)) if len(resolved) else None,
                "toward_vwap_mfe_median": None, "away_mae_median": None,
                "return_distance_ticks_median": float(group.distance_to_day_ticks.median()),
                "extension_distance_ticks_median": float(group.distance_to_session_ticks.median()),
            })
    return pd.DataFrame(rows)


def geometry_summary(ab: pd.DataFrame) -> pd.DataFrame:
    """Describe the frozen competing-barrier geometry over every eligible row."""
    rows = []
    for product in ("ALL", *PRODUCTS):
        part = selection(ab, product)
        valid = part[part.outcome_missing.isna()].copy()
        return_sigma = valid.return_distance_points / valid.sigma
        extension_sigma = valid.extension_distance_points / valid.sigma
        rows.append({
            "product": product,
            "rows": len(valid),
            "episodes": int(valid.episode_id.nunique()),
            "product_sessions": int(valid.session_key.nunique()),
            "return_distance_points_median": float(valid.return_distance_points.median()),
            "return_distance_ticks_median": float(valid.return_distance_ticks.median()),
            "return_distance_sigma_median": float(return_sigma.median()),
            "extension_distance_points_median": float(valid.extension_distance_points.median()),
            "extension_distance_ticks_median": float(valid.extension_distance_ticks.median()),
            "extension_distance_sigma_median": float(extension_sigma.median()),
            "return_geometry_share_median": float(valid.return_geometry_share.median()),
        })
    return pd.DataFrame(rows)


def updated_table(updates: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    if updates.empty:
        return pd.DataFrame()
    updates = updates.copy()
    updates["shared_week"] = pd.to_datetime(updates.session_date).dt.to_period("W-SUN").astype(str)
    updates["session_key"] = updates["product"] + ":" + updates.session_date
    updates["event_id_for_count"] = updates.event_id
    updates["episode_id"] = updates.event_id
    updates["position_bin"] = pd.cut(updates.position_from_day, [0, .25, .5, .75, 1.000001],
                                     labels=["day_quarter", "day_middle", "session_middle", "session_quarter"],
                                     right=False).astype(str)
    rows = []
    classes = ["day_first", "session_first", "neither", "ambiguous"]
    for product in ("ALL", *PRODUCTS):
        part = updates if product == "ALL" else updates[updates["product"] == product]
        for elapsed in (10, 20):
            elapsed_part = part[part.elapsed_minutes == elapsed]
            for anchor in ("ALL", *LOCAL_ANCHORS):
                chosen = elapsed_part if anchor == "ALL" else elapsed_part[elapsed_part.session_anchor == anchor]
                counts = outcome_counts(chosen, "future_outcome", classes)
                for name in classes:
                    rows.append({"product": product, "anchor": anchor, "elapsed_minutes": elapsed,
                                 "facet": "overall", "facet_value": "all", "outcome_class": name,
                                 **counts, **block_rate(chosen, "future_outcome", name, rng)})
            for position, chosen in elapsed_part.groupby("position_bin", observed=True):
                counts = outcome_counts(chosen, "future_outcome", classes)
                for name in classes:
                    rows.append({"product": product, "anchor": "ALL", "elapsed_minutes": elapsed,
                                 "facet": "position_bin", "facet_value": position,
                                 "outcome_class": name, **counts,
                                 **block_rate(chosen, "future_outcome", name, rng)})
    return pd.DataFrame(rows)


def model_tables(ab: pd.DataFrame, corridors: pd.DataFrame, config: dict,
                 rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    models = config["models"]
    floor = models["minimum_development_cell_support"]
    questions = []
    a = ab[ab.frozen_return_30.notna()].copy()
    a["model_outcome"] = np.where(a.frozen_return_30, "return", "no_return")
    questions.append(("A", a, ["return", "no_return"],
                      models["question_a_baseline_keys"], models["question_a_added_keys"]))
    b = ab[ab.barrier_primary.isin(["return_first", "extension_first", "neither", "ambiguous"])].copy()
    b["model_outcome"] = b.barrier_primary
    questions.append(("B", b, ["return_first", "extension_first", "neither", "ambiguous"],
                      models["question_b_baseline_keys"], models["question_b_added_keys"]))
    c = corridors[corridors.frozen_outcome.isin(["day_first", "session_first", "neither", "ambiguous"])].copy()
    c["model_outcome"] = c.frozen_outcome
    questions.append(("C", c, ["day_first", "session_first", "neither", "ambiguous"],
                      models["question_c_baseline_keys"], models["question_c_added_keys"]))
    score_rows, calibration = [], []
    for question, frame, classes, baseline_keys, extra_keys in questions:
        train = frame[frame.split == "development"]
        if train.empty:
            continue
        for split in ("validation", "final", "evaluation"):
            target = frame[frame.split == split] if split != "evaluation" else frame[frame.split.isin(["validation", "final"])]
            if target.empty:
                continue
            base_prob, augmented_prob, augmented_support = supported_predictions(
                train, target, "model_outcome", classes, baseline_keys, extra_keys, floor,
                models["dirichlet_alpha_per_class"],
            )
            base_loss = brier_losses(target.model_outcome, base_prob, classes)
            aug_loss = brier_losses(target.model_outcome, augmented_prob, classes)
            for product in ("ALL", *PRODUCTS):
                mask = np.ones(len(target), dtype=bool) if product == "ALL" else target["product"].to_numpy() == product
                if not mask.any():
                    continue
                score = score_interval(target.loc[mask], base_loss[mask], aug_loss[mask], rng)
                score_rows.append({
                    "question": question, "split": split, "product": product,
                    "rows": int(mask.sum()),
                    "product_sessions": int(target.loc[mask, "session_key"].nunique()),
                    "specific_augmented_rows": int((augmented_support[mask] > 0).sum()),
                    "specific_augmented_coverage": float((augmented_support[mask] > 0).mean()),
                    "median_specific_development_support": (float(np.median(augmented_support[mask][augmented_support[mask] > 0]))
                                                            if (augmented_support[mask] > 0).any() else None),
                    **score,
                })
            calibration.extend(calibration_rows(target, base_prob, target.model_outcome, classes,
                                                "baseline", question, split))
            calibration.extend(calibration_rows(target, augmented_prob, target.model_outcome, classes,
                                                "augmented", question, split))
    return pd.DataFrame(score_rows), pd.DataFrame(calibration)


def examples(ab: pd.DataFrame, corridors: pd.DataFrame) -> pd.DataFrame:
    rows = []
    primary_ab = ab.sort_values("forecast_ts")
    for product in PRODUCTS:
        part = primary_ab[primary_ab["product"] == product]
        a_class = np.where(part.evolving_without_frozen_30 == True, "evolving_only",
                           np.where(part.frozen_return_30 == True, "frozen_return", "no_frozen_return"))
        part = part.assign(_a_class=a_class)
        for outcome, group in part.groupby("_a_class"):
            row = group.iloc[0]
            rows.append({"product": product, "domain": "A", "outcome": outcome,
                         "event_id": row.event_id, "forecast_ts": row.forecast_ts,
                         "session_date": row.session_date, "timeframe": row.timeframe,
                         "source_partition": f"ab_{product}_{row.timeframe}_{row.year}.parquet"})
        for outcome, group in part.groupby("barrier_primary"):
            row = group.iloc[0]
            rows.append({"product": product, "domain": "B", "outcome": outcome,
                         "event_id": row.event_id, "forecast_ts": row.forecast_ts,
                         "session_date": row.session_date, "timeframe": row.timeframe,
                         "source_partition": f"ab_{product}_{row.timeframe}_{row.year}.parquet"})
    primary_c = corridors.sort_values("forecast_ts")
    for product in PRODUCTS:
        part = primary_c[primary_c["product"] == product]
        for outcome, group in part.groupby("frozen_outcome"):
            row = group.iloc[0]
            rows.append({"product": product, "domain": "C", "outcome": outcome,
                         "event_id": row.event_id, "forecast_ts": row.forecast_ts,
                         "session_date": row.session_date, "timeframe": row.timeframe,
                         "source_partition": f"c_{product}_{row.timeframe}_{row.year}.parquet"})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[2]
    stage = workspace / "work/11_vwap_conditional_probabilities" / args.run_id
    if not (stage / "extraction-summary.json").is_file():
        raise FileNotFoundError("complete extraction required")
    tables = stage / "tables"
    tables.mkdir(exist_ok=True)
    config = json.loads((stage / "config.json").read_text())
    rng = np.random.default_rng(config["uncertainty"]["seed"])
    ab = load_parts(stage / "events", "ab_*.parquet")
    corridor_paths = [path for path in sorted((stage / "events").glob("c_*.parquet"))
                      if not path.name.startswith("c_updates_")]
    corridors = pd.concat([pd.read_parquet(path) for path in corridor_paths], ignore_index=True)
    updates = load_parts(stage / "events", "c_updates_*.parquet")
    if ab.event_id.duplicated().any() or corridors.event_id.duplicated().any():
        raise ValueError("duplicate event IDs")
    ab = classify_ab(ab, config)
    corridors = classify_corridor(corridors, config)
    primary_ab = ab[ab.timeframe == "2m"].copy()
    primary_c = corridors[corridors.timeframe == "2m"].copy()

    def save(name: str, frame: pd.DataFrame) -> None:
        frame.to_csv(tables / f"{name}.csv", index=False)

    funnel_rows = []
    for domain, frame, id_column in (("AB", ab, "episode_id"), ("C", corridors, "event_id")):
        for (timeframe, product), part in frame.groupby(["timeframe", "product"]):
            funnel_rows.append({
                "domain": domain, "timeframe": timeframe, "product": product,
                "rows": len(part), "outcome_capable": int(part.outcome_missing.isna().sum()),
                "outcome_unavailable": int(part.outcome_missing.notna().sum()),
                "episodes_or_events": int(part[id_column].nunique()),
                "product_sessions": int(part.session_key.nunique()),
                "shared_weeks": int(part.shared_week.nunique()),
            })
    save("funnel", pd.DataFrame(funnel_rows))
    exclusions = pd.concat([
        ab.groupby(["timeframe", "product", "outcome_missing"], dropna=False).size().reset_index(name="rows").assign(domain="AB"),
        corridors.groupby(["timeframe", "product", "outcome_missing"], dropna=False).size().reset_index(name="rows").assign(domain="C"),
    ], ignore_index=True)
    save("exclusions", exclusions)

    q_a = question_a_table(primary_ab, rng)
    q_b = outcome_table(primary_ab, "B", "barrier_primary",
                        ["return_first", "extension_first", "neither", "ambiguous"],
                        "anchor", ANCHORS, rng)
    q_c = outcome_table(primary_c, "C", "frozen_outcome",
                        ["day_first", "session_first", "neither", "ambiguous"],
                        "session_anchor", LOCAL_ANCHORS, rng)
    save("question_a_rates", q_a)
    save("question_b_outcomes", q_b)
    save("question_c_outcomes", q_c)
    save("barrier_sensitivity", barrier_sensitivity(primary_ab, rng))
    save("updated_corridor", updated_table(updates, rng))
    save("timing_movements", timing_table(primary_ab, primary_c))
    save("barrier_geometry", geometry_summary(primary_ab))
    scores, calibration = model_tables(primary_ab, primary_c, config, rng)
    save("model_scores", scores)
    save("calibration", calibration)
    save("examples", examples(primary_ab, primary_c))

    sensitivity_rows = []
    for timeframe in ("2m", "5m"):
        part_ab = ab[ab.timeframe == timeframe]
        part_c = corridors[corridors.timeframe == timeframe]
        for product in ("ALL", *PRODUCTS):
            abp = part_ab if product == "ALL" else part_ab[part_ab["product"] == product]
            cp = part_c if product == "ALL" else part_c[part_c["product"] == product]
            sensitivity_rows.append(rate_row(abp, "frozen_return_30", True, "A_frozen_return_30", rng,
                                             timeframe=timeframe, product=product))
            for cls in ("return_first", "extension_first", "neither", "ambiguous"):
                sensitivity_rows.append(rate_row(abp, "barrier_primary", cls, f"B_{cls}", rng,
                                                 timeframe=timeframe, product=product))
            for cls in ("day_first", "session_first", "neither", "ambiguous"):
                sensitivity_rows.append(rate_row(cp, "frozen_outcome", cls, f"C_{cls}", rng,
                                                 timeframe=timeframe, product=product))
    save("timeframe_sensitivity", pd.DataFrame(sensitivity_rows))

    atlas_rows = []
    for product in PRODUCTS:
        arow = q_a[(q_a["product"] == product) & (q_a.anchor == "ALL") &
                   (q_a.split == "all") & (q_a.facet == "overall") &
                   (q_a.metric == "frozen_return_30")].iloc[0]
        for question, row, population, event in (
            ("A", arow, "at-risk departure checkpoints", "frozen VWAP contact within 30 minutes"),
        ):
            atlas_rows.append({"question": question, "product": product, "population": population,
                               "future_event": event, **{key: row[key] for key in
                               ("numerator", "denominator", "probability", "ci_low", "ci_high", "episodes", "product_sessions", "shared_weeks")}})
        for question, table, cls, population, event in (
            ("B", q_b, "return_first", "same at-risk checkpoints", "frozen VWAP before 0.5-sigma extension"),
            ("C", q_c, "day_first", "mature corridor failures", "frozen day VWAP before session reclaim"),
        ):
            row = table[(table["product"] == product) & (table.anchor == "ALL") &
                        (table.split == "all") & (table.facet == "overall") &
                        (table.outcome_class == cls)].iloc[0]
            atlas_rows.append({"question": question, "product": product, "population": population,
                               "future_event": event, **{key: row[key] for key in
                               ("numerator", "denominator", "probability", "ci_low", "ci_high", "episodes", "product_sessions", "shared_weeks")}})
    atlas = pd.DataFrame(atlas_rows)
    save("probability_atlas", atlas)
    metrics = {
        "study_id": "11_vwap_conditional_probabilities", "run_id": args.run_id,
        "protocol_version": "1.0.0", "primary_ab_rows": len(primary_ab),
        "primary_ab_episodes": int(primary_ab.episode_id.nunique()),
        "primary_corridor_rows": len(primary_c),
        "primary_corridor_product_sessions": int(primary_c.session_key.nunique()),
        "five_minute_ab_rows": int((ab.timeframe == "5m").sum()),
        "five_minute_corridor_rows": int((corridors.timeframe == "5m").sum()),
        "probability_atlas": atlas.replace({np.nan: None}).to_dict("records"),
        "model_scores_evaluation": scores[(scores.split == "evaluation") & (scores["product"] == "ALL")]
            .replace({np.nan: None}).to_dict("records"),
        "event_files": len(list((stage / "events").glob("*.parquet"))),
    }
    (stage / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str) + "\n")
    print(json.dumps({"primary_ab_rows": len(primary_ab), "primary_corridor_rows": len(primary_c),
                      "updates": len(updates), "model_score_rows": len(scores)}))


if __name__ == "__main__":
    main()
