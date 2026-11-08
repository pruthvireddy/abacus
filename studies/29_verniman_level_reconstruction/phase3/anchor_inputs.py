"""Encode an explicitly supplied provenance ledger for manual Pine entry.

No file is sent to TradingView. Validation records eligibility; it cannot verify
that an evidence assertion is true or establish historical publication timing.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

FIELDS = ("anchor_id", "lower", "upper", "contract", "reference_period", "measurement",
          "observed_at", "confirmed_at", "evidence", "reason", "selection_status",
          "independently_supported", "reading_precision")
STATUS = {"explicit_source": "explicit-source", "analyst_proposed": "analyst-proposed"}


def timestamp(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return stamp


def encode_record(record: dict, *, contract: str, cutoff: datetime) -> tuple[str, list[str]]:
    missing = [name for name in FIELDS if name not in record or record[name] is None]
    if missing:
        raise ValueError("missing anchor fields: " + ", ".join(missing))
    try:
        low, high = Decimal(str(record["lower"])), Decimal(str(record["upper"]))
    except InvalidOperation as exc:
        raise ValueError("invalid price interval") from exc
    if not low.is_finite() or not high.is_finite() or low > high:
        raise ValueError("finite ordered price interval required")
    if record["selection_status"] not in STATUS:
        raise ValueError("explicit_source or analyst_proposed status required")
    if not isinstance(record["independently_supported"], bool):
        raise ValueError("independently_supported must be a boolean")
    observed, confirmed = timestamp(record["observed_at"]), timestamp(record["confirmed_at"])
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("timezone-aware cutoff required")
    reasons = []
    if record["contract"] != contract:
        reasons.append("contract_mismatch")
    if observed > confirmed:
        reasons.append("observation_after_confirmation")
    if confirmed > cutoff:
        reasons.append("later_confirmed_anchor")
    if not record["independently_supported"]:
        reasons.append("independent_causal_evidence_unsupported")
    parts = [record["anchor_id"], str(low), str(high), record["contract"],
             record["reference_period"], record["measurement"],
             str(int(observed.astimezone(timezone.utc).timestamp() * 1000)),
             str(int(confirmed.astimezone(timezone.utc).timestamp() * 1000)),
             record["evidence"], record["reason"], STATUS[record["selection_status"]],
             str(record["independently_supported"]).lower(), record["reading_precision"]]
    if not str(record["reading_precision"]).strip():
        raise ValueError("reading precision required in local ledger")
    if any(not str(part).strip() or any(char in str(part) for char in "|\n\r") for part in parts):
        raise ValueError("nonempty single-line fields without pipe delimiters required")
    return "|".join(map(str, parts)), reasons


def encode_ledger(ledger: dict, *, contract: str, cutoff: datetime) -> dict:
    if ledger.get("schema") != "abacus.study29.phase3.anchors/v1":
        raise ValueError("unsupported anchor ledger schema")
    records = ledger.get("anchors")
    if not isinstance(records, list):
        raise ValueError("anchors must be an explicit list")
    roles, ids, output = set(), set(), {}
    for record in records:
        role = record.get("role")
        if role not in ("C", "E", "L", "H") or role in roles:
            raise ValueError("unique C/E/L/H role required")
        if record.get("anchor_id") in ids:
            raise ValueError("duplicate anchor identity")
        encoded, reasons = encode_record(record, contract=contract, cutoff=cutoff)
        roles.add(role)
        ids.add(record["anchor_id"])
        output[role] = {"pine_input": encoded, "recorded_eligibility": not reasons, "reasons": reasons,
                        "source_historical_available_at": record.get("source_historical_available_at")}
    return {"anchors": output, "missing_roles": sorted(set("CELH") - roles),
            "independently_verified_by_encoder": False,
            "notice": "Manual copy only. Recorded eligibility does not prove causal evidence or historical availability."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--contract", default="CME_MINI:ESZ2026")
    parser.add_argument("--cutoff", required=True, help="timezone-aware ISO timestamp")
    args = parser.parse_args()
    print(json.dumps(encode_ledger(json.loads(args.ledger.read_text()), contract=args.contract,
                                   cutoff=timestamp(args.cutoff)), indent=2))


if __name__ == "__main__":
    main()
