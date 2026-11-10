"""Project the pinned NQ opening facts to the existing local Daily Facts database."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pyarrow as pa

from .daily_facts_postgres import SQL_TYPES, _json_rows, _matches, _psql
from .nq_opening_range import ID, SCHEMA, VERSION, load_opening_range
from .paths import resolve_publication_root

TABLE = "nq_opening_range_facts"
VIEW = "nq_opening_range_v1"
TYPES = {**SQL_TYPES, pa.uint16(): "integer", pa.decimal128(21, 10): "numeric(21,10)"}


def project(root, pin, *, executable, socket_dir, port, database):
    rows = load_opening_range(root, manifest_sha256=pin).to_pylist()
    names = ", ".join(f'"{field.name}"' for field in SCHEMA)
    columns = ", ".join(f'"{field.name}" {TYPES[field.type]}' for field in SCHEMA)
    identity = {"definition_version": VERSION, "manifest_sha256": pin, "ready": True}

    def verify(execute):
        actual = _json_rows(execute, f"SELECT {names} FROM {VIEW} ORDER BY session_date")
        if len(actual) != len(rows):
            raise ValueError("NQ opening range Postgres roster differs")
        for source, stored in zip(rows, actual):
            for field in SCHEMA:
                if not _matches(source[field.name], stored[field.name], field.type):
                    raise ValueError(f"Postgres mismatch for {source['session_date']}/{field.name}")
        joined, = execute(f"SELECT count(*) FROM {VIEW} JOIN daily_facts_v1 USING (asset, session_date) "
                          "WHERE daily_facts_v1.release_id = 'daily_market_facts__1.0.0';")
        expected = sum(not row["historical_window_qualification"] for row in rows)
        if int(joined) != expected:
            raise ValueError("NQ opening range join does not match the Daily Facts overlap")
        return expected

    with _psql(executable, socket_dir, port, database) as execute:
        execute("BEGIN; SET LOCAL search_path TO daily_facts; SET LOCAL TimeZone TO 'UTC'; "
                "SET LOCAL DateStyle TO 'ISO, YMD'; SET LOCAL extra_float_digits TO 3;")
        execute("SELECT pg_advisory_xact_lock(hashtext('abacus.daily_facts.import'));")
        existing = _json_rows(execute, "SELECT definition_version, manifest_sha256, ready "
                              f"FROM dataset_releases WHERE release_id = '{ID}'")
        if existing and existing != [identity]:
            raise ValueError("NQ opening facts already registered with a different pin")
        if not existing:
            execute(f"CREATE TABLE {TABLE} (release_id text REFERENCES dataset_releases, {columns}, "
                    "PRIMARY KEY (release_id, asset, session_date), CHECK (asset = 'NQ'));")
            execute(f"CREATE VIEW {VIEW} AS SELECT f.release_id, {', '.join('f.' + name.strip() for name in names.split(','))} "
                    f"FROM {TABLE} AS f JOIN dataset_releases AS r USING (release_id) "
                    f"WHERE r.ready AND f.release_id = '{ID}';")
            execute("INSERT INTO dataset_releases (release_id, definition_version, manifest_sha256) "
                    f"VALUES ('{ID}', '{VERSION}', '{pin}');")
            execute(f"COPY {TABLE} (release_id, {names}) FROM STDIN;",
                    ([ID, *(row[field.name] for field in SCHEMA)] for row in rows))
            execute(f"UPDATE dataset_releases SET ready = true WHERE release_id = '{ID}';")
        overlap = verify(execute)
        execute("COMMIT;")

    with _psql(executable, socket_dir, port, database) as execute:
        execute("SET search_path TO daily_facts; SET TimeZone TO 'UTC'; SET DateStyle TO 'ISO, YMD'; "
                "SET extra_float_digits TO 3;")
        verify(execute)
    return {"release_id": ID, "manifest_sha256": pin, "view": f"daily_facts.{VIEW}",
            "action": "verified_existing" if existing else "imported", "sessions": len(rows),
            "overlap_join_rows": overlap, "field_comparisons_per_readback": len(rows) * len(SCHEMA),
            "mismatches": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--psql", required=True, type=Path)
    parser.add_argument("--socket-dir", required=True, type=Path)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--database", required=True)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    with args.receipt.open("x") as receipt:
        result = project(resolve_publication_root(), args.manifest_sha256, executable=args.psql,
                         socket_dir=args.socket_dir, port=args.port, database=args.database)
        json.dump(result, receipt, indent=2)
        receipt.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
