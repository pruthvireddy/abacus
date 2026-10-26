"""Frozen H15 development guards, deterministic nominees and validation fallback."""
from __future__ import annotations

import numpy as np
import pandas as pd

CELL = ("product", "interval_minutes", "touch_mode")
GUARDS = ("completed", "sessions", "weeks", "fold_completed", "fold_sessions", "retention", "mae", "mfe", "positive_folds", "improvement", "defined")


def fixed_gate_id(product, cfg):
    return "abs_" + format(float(cfg["minimum_width_points"][product]), ".12g").replace(".", "p")


def h15_support(outcomes):
    scored = outcomes.loc[outcomes.horizon.eq(15) & outcomes.score_eligible & outcomes.atr_support]
    good = scored.loc[scored.status.eq("completed")]
    return dict(accepted=len(outcomes.loc[outcomes.horizon.eq(15)]), scoring_accepted=len(scored),
                completed=len(good), censored=int(scored.status.eq("censored").sum()),
                contributing_sessions=good.session.nunique(), contributing_weeks=good.week.nunique(),
                mean_terminal_delta_atr=float(good.terminal_delta_atr.mean()) if len(good) else np.nan,
                mean_mfe_atr=float(good.mfe_atr.mean()) if len(good) else np.nan,
                mean_mae_atr=float(good.mae_atr.mean()) if len(good) else np.nan)


def fold_records(outcomes, gate, product, interval_minutes, touch_mode, fold_ids):
    rows = []
    key = dict(product=product, interval_minutes=int(interval_minutes), touch_mode=touch_mode,
               gate_id=gate["gate_id"], gate_family=gate["family"], gate_threshold=float(gate["threshold"]))
    for fold in fold_ids:
        rows.append(key | dict(fold_id=fold) | h15_support(outcomes.loc[outcomes.fold_id.eq(fold)]))
    pooled = outcomes.loc[outcomes.fold_id.isin(fold_ids)]
    rows.append(key | dict(fold_id="pooled") | h15_support(pooled))
    return pd.DataFrame(rows)


def assess_candidates(folds, cfg, *, phase):
    """Compare independent populations; never join on accepted event timestamps."""
    if phase not in ("development", "validation"):
        raise ValueError("selection guards only apply in explicit development/validation")
    fold_ids = [x["id"] for x in cfg["development_folds" if phase == "development" else "validation_folds"]]
    rules = cfg["selection" if phase == "development" else "validation"]
    rows = []
    for cell, group in folds.groupby(list(CELL), sort=True):
        fixed = fixed_gate_id(cell[0], cfg)
        baseline = group.loc[group.gate_id.eq(fixed)].set_index("fold_id")
        if baseline.index.duplicated().any() or not set(fold_ids + ["pooled"]) <= set(baseline.index):
            raise ValueError("complete own-touch fixed baseline fold inventory required")
        for gate_id, candidate in group.groupby("gate_id", sort=True):
            candidate = candidate.set_index("fold_id")
            if candidate.index.duplicated().any() or not set(fold_ids + ["pooled"]) <= set(candidate.index):
                raise ValueError("complete candidate fold inventory required")
            c, b = candidate.loc["pooled"], baseline.loc["pooled"]
            cc, bb = candidate.loc[fold_ids], baseline.loc[fold_ids]
            diff = cc.mean_terminal_delta_atr.to_numpy(float) - bb.mean_terminal_delta_atr.to_numpy(float)
            score = float(cc.mean_terminal_delta_atr.mean()) if np.isfinite(cc.mean_terminal_delta_atr.to_numpy(float)).all() else np.nan
            base_score = float(bb.mean_terminal_delta_atr.mean()) if np.isfinite(bb.mean_terminal_delta_atr.to_numpy(float)).all() else np.nan
            overall = score - base_score if phase == "development" else c.mean_terminal_delta_atr - b.mean_terminal_delta_atr
            retention = c.completed / b.completed if b.completed else np.nan
            defined = bool(np.isfinite(diff).all() and np.isfinite([score, base_score, overall, retention,
                c.mean_mae_atr, b.mean_mae_atr, c.mean_mfe_atr, b.mean_mfe_atr]).all())
            checks = dict(completed=c.completed >= rules["minimum_completed"],
                sessions=c.contributing_sessions >= rules["minimum_sessions"],
                weeks=c.contributing_weeks >= rules["minimum_weeks"],
                fold_completed=bool((cc.completed >= rules["minimum_fold_completed"]).all()),
                fold_sessions=bool((cc.contributing_sessions >= rules["minimum_fold_sessions"]).all()),
                retention=bool(retention >= rules["minimum_baseline_retention"]),
                mae=bool(c.mean_mae_atr <= b.mean_mae_atr * rules["maximum_mean_mae_baseline_multiple"]),
                mfe=bool(c.mean_mfe_atr >= b.mean_mfe_atr * rules["minimum_mean_mfe_baseline_multiple"]),
                positive_folds=int((diff > 0).sum()) >= rules["minimum_positive_folds"],
                improvement=bool(overall > 0), defined=defined)
            row = dict(zip(CELL, cell)) | dict(gate_id=gate_id, gate_family=c.gate_family,
                gate_threshold=float(c.gate_threshold), phase=phase, fixed_gate_id=fixed,
                selection_score=score, baseline_equal_fold_score=base_score,
                overall_improvement=float(overall), positive_folds=int((diff > 0).sum()),
                fold_count=len(fold_ids), retention=retention, completed=int(c.completed),
                contributing_sessions=int(c.contributing_sessions), contributing_weeks=int(c.contributing_weeks),
                mean_terminal_delta_atr=c.mean_terminal_delta_atr, baseline_mean_terminal_delta_atr=b.mean_terminal_delta_atr,
                mean_mfe_atr=c.mean_mfe_atr, baseline_mean_mfe_atr=b.mean_mfe_atr,
                mean_mae_atr=c.mean_mae_atr, baseline_mean_mae_atr=b.mean_mae_atr,
                eligible=all(checks.values()), failed_guards=";".join(k for k in GUARDS if not checks[k]))
            row.update({"guard_" + k: bool(v) for k, v in checks.items()})
            for fold, delta in zip(fold_ids, diff):
                row["improvement_" + fold] = float(delta)
            rows.append(row)
    return pd.DataFrame(rows)


def select_nominees(assessments, cfg):
    rows = []
    for cell, group in assessments.groupby(list(CELL), sort=True):
        eligible = group.loc[group.eligible].to_dict("records")
        # Approximate pairwise equality is nontransitive. Anchor the tie set to
        # the highest score, so chained near-ties cannot select a lower score
        # outside the declared tolerance of that highest score.
        maximum = max((r["selection_score"] for r in eligible), default=np.nan)
        tied = [r for r in eligible if abs(r["selection_score"] - maximum) <=
                cfg["selection_tie_epsilon_scale"] * max(1., abs(maximum), abs(r["selection_score"]))]
        ordered = sorted(tied, key=lambda r: (-int(r["completed"]),
            0 if r["gate_family"] == "absolute" else 1, float(r["gate_threshold"]), r["gate_id"]))
        fixed = fixed_gate_id(cell[0], cfg)
        chosen = ordered[0] if ordered else None
        selected = chosen["gate_id"] if chosen else fixed
        row = dict(zip(CELL, cell)) | dict(phase="development", fixed_gate_id=fixed,
            nominee_gate_id=selected, selected_gate_id=selected, eligible_candidates=len(eligible),
            highest_eligible_score=maximum, tied_to_highest_count=len(tied),
            nomination_status="eligible_nominee" if chosen else "no_eligible_improvement",
            fallback=chosen is None, selection_score=chosen["selection_score"] if chosen else np.nan,
            selection_improvement=chosen["overall_improvement"] if chosen else np.nan,
            selected_gate_family=chosen["gate_family"] if chosen else "absolute",
            selected_gate_threshold=chosen["gate_threshold"] if chosen else float(cfg["minimum_width_points"][cell[0]]))
        rows.append(row)
    return pd.DataFrame(rows)


def validation_decisions(assessments, nominees, cfg):
    rows = []
    for nominee in nominees.to_dict("records"):
        matches = assessments
        for k in CELL:
            matches = matches.loc[matches[k].eq(nominee[k])]
        matches = matches.loc[matches.gate_id.eq(nominee["nominee_gate_id"])]
        if len(matches) != 1:
            raise ValueError("exactly the frozen nominee assessment required")
        assessment = matches.iloc[0]
        identity = nominee["nominee_gate_id"] == nominee["fixed_gate_id"]
        passes = bool(assessment.eligible) and not identity
        chosen = nominee["nominee_gate_id"] if passes else nominee["fixed_gate_id"]
        row = nominee | dict(phase="validation", selected_gate_id=chosen,
            final_gate_id=chosen,
            validation_status="passed" if passes else "fixed_fallback_no_eligible_nominee" if identity else "fixed_fallback_validation_failed",
            validation_passed=passes, fallback=not passes, failed_validation_guards=assessment.failed_guards,
            validation_improvement=assessment.overall_improvement,
            selected_gate_family=nominee["selected_gate_family"] if passes else "absolute",
            selected_gate_threshold=nominee["selected_gate_threshold"] if passes else float(cfg["minimum_width_points"][nominee["product"]]))
        rows.append(row)
    return pd.DataFrame(rows)
