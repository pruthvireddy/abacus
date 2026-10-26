"""Safe command-line access to Databento for this repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import databento as db

from .databento_credentials import (
    DatabentoCredentialError,
    load,
    store_interactively,
)
from .paths import PathConfigurationError, resolve_publication_root


DATASET = "GLBX.MDP3"
CONTINUOUS_SYMBOLS = ("ES.v.0", "NQ.v.0", "GC.v.0")
START_DATE = "2010-06-06"
END_DATE = "2026-09-20"
DEFAULT_ROLL_MAP = (
    Path("data")
    / "raw"
    / "databento"
    / DATASET
    / "symbology"
    / "continuous"
    / "volume-rank-0"
    / f"{START_DATE}_{END_DATE}.json"
)
DEFAULT_DEFINITION_DIR = (
    Path("data")
    / "raw"
    / "databento"
    / DATASET
    / "definition"
    / "continuous"
    / "volume-rank-0"
    / f"{START_DATE}_{END_DATE}"
)
DEFAULT_DEFINITION_FILE = (
    DEFAULT_DEFINITION_DIR
    / "glbx-mdp3-20100606-20260920.definition.dbn.zst"
)


def _client() -> db.Historical:
    return db.Historical(key=load())


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    if temporary.exists():
        raise RuntimeError(f"Refusing to overwrite incomplete file: {temporary}")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True, default=str)
            stream.write("\n")
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _definition_request() -> dict[str, Any]:
    return {
        "dataset": DATASET,
        "symbols": list(CONTINUOUS_SYMBOLS),
        "stype_in": "continuous",
        "stype_out": "instrument_id",
        "schema": "definition",
        "start": START_DATE,
        "end": END_DATE,
    }


def _definition_cost(client: db.Historical) -> float:
    request = _definition_request()
    return float(
        client.metadata.get_cost(
            dataset=request["dataset"],
            symbols=request["symbols"],
            stype_in=request["stype_in"],
            schema=request["schema"],
            start=request["start"],
            end=request["end"],
            mode="historical-streaming",
        )
    )


def command_setup_key(_: argparse.Namespace) -> int:
    print("Paste the dedicated Databento API key at the hidden Keychain prompt.")
    store_interactively()
    print("Databento key stored in macOS Keychain.")
    return 0


def command_check(_: argparse.Namespace) -> int:
    datasets = _client().metadata.list_datasets()
    if DATASET not in datasets:
        raise RuntimeError(f"Authenticated, but {DATASET} is not available.")
    print(f"Databento authentication succeeded; {DATASET} is available.")
    return 0


def command_fetch_roll_map(args: argparse.Namespace) -> int:
    output = _output_path(args, DEFAULT_ROLL_MAP)
    if output.exists() and not args.force:
        raise FileExistsError(
            f"Roll map already exists: {output}. Pass --force to replace it."
        )

    request = {
        "dataset": DATASET,
        "symbols": list(CONTINUOUS_SYMBOLS),
        "stype_in": "continuous",
        "stype_out": "instrument_id",
        "start_date": START_DATE,
        "end_date": END_DATE,
    }
    response = _client().symbology.resolve(**request)
    payload = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "request": request,
        "response": response,
    }

    _write_json_atomic(output, payload)
    print(f"Saved volume-ranked continuous mapping to {output}")
    return 0


def command_estimate_definitions(_: argparse.Namespace) -> int:
    cost = _definition_cost(_client())
    print(f"Estimated definition-data cost: ${cost:.2f} USD")
    print("No billable data request was submitted.")
    return 0


def command_download_definitions(args: argparse.Namespace) -> int:
    output = _output_path(args, DEFAULT_DEFINITION_FILE)
    manifest_path = output.parent / "request.json"
    if output.exists() or manifest_path.exists():
        raise FileExistsError(
            f"Definition download already exists under {output.parent}."
        )

    client = _client()
    estimated_cost = _definition_cost(client)
    if estimated_cost > args.max_cost_usd:
        raise RuntimeError(
            f"Estimated cost ${estimated_cost:.2f} exceeds the approved maximum "
            f"${args.max_cost_usd:.2f}; no request was submitted."
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f"{output.stem}.part{output.suffix}")
    if temporary.exists():
        raise FileExistsError(f"Incomplete download already exists: {temporary}")

    request = _definition_request()
    started_at = datetime.now(timezone.utc)
    try:
        store = client.timeseries.get_range(path=temporary, **request)
        if str(store.dataset) != DATASET or str(store.schema) != "definition":
            raise RuntimeError("Downloaded DBN metadata does not match the request.")
        store.reader.close()
        os.replace(temporary, output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    completed_at = datetime.now(timezone.utc)
    manifest = {
        "request": request,
        "estimated_cost_usd": estimated_cost,
        "approved_max_cost_usd": args.max_cost_usd,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "file": {
            "path": output.name,
            "bytes": output.stat().st_size,
            "sha256": _sha256(output),
        },
    }
    _write_json_atomic(manifest_path, manifest)
    print(
        f"Downloaded definition data to {output} "
        f"({output.stat().st_size:,} bytes; estimated cost ${estimated_cost:.2f})."
    )
    return 0


def _output_path(args: argparse.Namespace, relative_default: Path) -> Path:
    if args.output is not None:
        return Path(args.output).expanduser().resolve()
    return resolve_publication_root(args.root) / relative_default


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Secure Databento utilities for Abacus Bhishma."
    )
    parser.add_argument("--root", type=Path, help="Publication project root; otherwise use configured storage")
    commands = parser.add_subparsers(dest="command", required=True)

    setup = commands.add_parser("setup-key", help="Store or rotate the API key.")
    setup.set_defaults(handler=command_setup_key)

    check = commands.add_parser("check", help="Verify API authentication safely.")
    check.set_defaults(handler=command_check)

    fetch = commands.add_parser(
        "fetch-roll-map",
        help="Fetch the free ES/NQ/GC volume-ranked continuous mapping.",
    )
    fetch.add_argument("--output", help="Explicit destination; otherwise use the publication root")
    fetch.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing mapping file.",
    )
    fetch.set_defaults(handler=command_fetch_roll_map)

    estimate = commands.add_parser(
        "estimate-definitions",
        help="Estimate definition-data cost without submitting a data request.",
    )
    estimate.set_defaults(handler=command_estimate_definitions)

    download = commands.add_parser(
        "download-definitions",
        help="Download continuous-contract definitions after enforcing a cost cap.",
    )
    download.add_argument(
        "--max-cost-usd",
        type=float,
        required=True,
        help="Abort unless Databento's current estimate is at or below this value.",
    )
    download.add_argument("--output", help="Explicit destination; otherwise use the publication root")
    download.set_defaults(handler=command_download_definitions)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.handler(args))
    except db.BentoClientError as exc:
        if "account_insufficient_funds" in str(exc):
            parser.exit(
                1,
                "error: Databento rejected the request because the account has "
                "insufficient API budget. Add funds in the Databento portal, then "
                "run the same command again. No download file was created.\n",
            )
        parser.exit(1, f"error: Databento API request failed: {exc}\n")
    except (DatabentoCredentialError, FileExistsError, RuntimeError, PathConfigurationError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
