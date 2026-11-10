"""Import and verify the pinned Daily Facts v1 release over a local Unix socket."""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
import json
import math
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryFile

import pyarrow as pa

from .daily_facts import CHECKPOINTS, DISTANCES, output_schema
from .daily_facts_loader import ASSETS, DATASET_ID, DATA_PATH, VERSION, WINDOWS, load_daily_facts
from .manifest_selection import read_pinned_manifest
from .paths import resolve_publication_root

SCHEMA = "daily_facts"
KEY = ("release_id", "asset", "session_date")
WINDOW_KEY = (*KEY, "window")
VWAP_PREFIXES = (*CHECKPOINTS, *DISTANCES, "globex_to_rth_end")
SQL_TYPES = {
    pa.string(): "text",
    pa.date32(): "date",
    pa.timestamp("us", tz="UTC"): "timestamp with time zone",
    pa.bool_(): "boolean",
    pa.int16(): "smallint",
    pa.uint32(): "bigint",
    pa.uint64(): "numeric(20,0)",
    pa.decimal128(20, 9): "numeric(20,9)",
    pa.float64(): "double precision",
    pa.list_(pa.field("element", pa.string())): "text[]",
}


def _layout(schema):
    """Map every release column to a typed table and its wide-view expression."""
    tables = {name: {} for name in ("daily_sessions", "daily_window_facts",
                                   "daily_vwap_facts", "daily_context_facts")}
    window_fields = tables["daily_window_facts"]
    projection = {}
    for field in schema:
        name, kind = field.name, field.type
        prefix, _, suffix = name.partition("_")
        if name.startswith("vol_index_"):
            table, alias, column = "daily_context_facts", "context", name
        elif any(name == prefix or name.startswith(prefix + "_") for prefix in VWAP_PREFIXES):
            table, alias, column = "daily_vwap_facts", "vwap", name
        elif prefix == WINDOWS[0] or (prefix in WINDOWS and suffix in window_fields):
            alias, column = prefix, suffix
            table = "daily_window_facts"
            if alias != WINDOWS[0] and window_fields[column] != kind:
                raise ValueError(f"inconsistent Daily Facts window field: {name}")
        else:
            table, alias, column = "daily_sessions", "sessions", name
        tables[table][column] = kind
        projection[name] = f'{alias}."{column}" AS "{name}"'
    return tables, projection


def _ddl(schema):
    tables, projection = _layout(schema)
    statements = [f"CREATE SCHEMA {SCHEMA}", """CREATE TABLE dataset_releases (
        release_id text PRIMARY KEY,
        definition_version text NOT NULL,
        manifest_sha256 text NOT NULL,
        ready boolean NOT NULL DEFAULT false
    )"""]
    for table, fields in tables.items():
        types = {name: schema.field(name).type for name in KEY}
        if table == "daily_window_facts":
            types["window"] = pa.string()
        types.update(fields)
        key = WINDOW_KEY if table == "daily_window_facts" else KEY
        columns = [f'"{name}" {SQL_TYPES[kind]}' for name, kind in types.items()]
        key_columns = ", ".join(f'"{name}"' for name in key)
        columns.append(f"PRIMARY KEY ({key_columns})")
        if table == "daily_sessions":
            columns.extend(("FOREIGN KEY (release_id) REFERENCES dataset_releases (release_id)",
                            "CHECK (asset IN ('ES', 'NQ', 'GC'))"))
        else:
            columns.append(f"FOREIGN KEY ({', '.join(KEY)}) REFERENCES daily_sessions")
        if table == "daily_window_facts":
            columns.append(f'CHECK ("window" IN ({", ".join(map(repr, WINDOWS))}))')
        statements.append(f"CREATE TABLE {table} ({', '.join(columns)})")
    joins = ["JOIN daily_vwap_facts AS vwap USING (release_id, asset, session_date)",
             "JOIN daily_context_facts AS context USING (release_id, asset, session_date)"]
    joins.extend(f"JOIN daily_window_facts AS {window} ON {window}.release_id = sessions.release_id "
                 f"AND {window}.asset = sessions.asset AND {window}.session_date = sessions.session_date "
                 f"AND {window}.\"window\" = '{window}'" for window in WINDOWS)
    statements.append(f"CREATE VIEW daily_facts_v1 AS SELECT {', '.join(projection.values())} "
                      "FROM daily_sessions AS sessions " + " ".join(joins) +
                      " JOIN dataset_releases AS releases "
                      "ON releases.release_id = sessions.release_id AND releases.ready")
    return ";\n".join(statements) + ";"


def _copy_cell(value):
    if value is None:
        return r"\N"
    if isinstance(value, list):
        elements = []
        for item in value:
            if item is None:
                elements.append("NULL")
            else:
                escaped = item.replace("\\", "\\\\").replace('"', '\\"')
                elements.append(f'"{escaped}"')
        value = "{" + ",".join(elements) + "}"
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Daily Facts v1 expects finite floats or nulls")
    return str(value).replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")


def _copy_batches(schema, rows):
    for table, fields in _layout(schema)[0].items():
        if table == "daily_window_facts":
            columns = (*WINDOW_KEY, *fields)
            records = ((*[row[name] for name in KEY], window,
                        *[row[f"{window}_{name}"] for name in fields])
                       for row in rows for window in WINDOWS)
        else:
            columns = (*KEY, *(name for name in fields if name not in KEY))
            records = ([row[name] for name in columns] for row in rows)
        yield table, columns, records


@contextmanager
def _psql(executable, socket_dir, port, database):
    if not socket_dir.is_absolute() or "," in str(socket_dir) or not re.fullmatch(r"[a-z_][a-z0-9_]*", database):
        raise ValueError("supply one absolute Unix socket directory and a simple database name")
    # Ignore libpq environment settings that can redirect an explicit local connection.
    env = {key: value for key, value in os.environ.items() if not key.startswith("PG")}
    env["PGCLIENTENCODING"] = "UTF8"
    with TemporaryFile(mode="w+t", encoding="utf-8") as errors, subprocess.Popen(
        [str(executable), "-XqAtw", "-v", "ON_ERROR_STOP=1", "-h", str(socket_dir),
         "-p", str(port), "-d", database], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=errors, text=True, encoding="utf-8", env=env,
    ) as process:
        marker = "abacus_daily_facts_query_done"

        def execute(sql, records=None):
            try:
                process.stdin.write(sql + "\n")
                if records is not None:
                    for record in records:
                        process.stdin.write("\t".join(map(_copy_cell, record)) + "\n")
                    process.stdin.write("\\.\n")
                process.stdin.write(f"\\echo {marker}\n")
                process.stdin.flush()
            except BrokenPipeError:
                pass  # Read the server or connection error below.
            lines = []
            for line in process.stdout:
                if line.rstrip("\n") == marker:
                    return lines
                lines.append(line)
            errors.seek(0)
            raise RuntimeError(f"psql stopped before completing a statement: {errors.read().strip()}")

        try:
            yield execute
        finally:
            # Closing an uncommitted session also rolls back DDL and copied rows.
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass


def _json_rows(execute, select):
    return [json.loads(line, parse_int=Decimal, parse_float=Decimal)
            for line in execute(f"SELECT row_to_json(result) FROM ({select}) AS result;")]


def _matches(source, stored, kind):
    if source is None or stored is None:
        return source is stored
    if pa.types.is_floating(kind):
        return isinstance(stored, Decimal) and source.hex() == float(stored).hex()
    if pa.types.is_date(kind):
        return source == date.fromisoformat(stored)
    if pa.types.is_timestamp(kind):
        return source == datetime.fromisoformat(stored)
    if pa.types.is_decimal(kind):
        return isinstance(stored, Decimal) and source.as_tuple() == stored.as_tuple()
    return source == stored


def _parity(execute, schema, expected, release_filter):
    columns = _json_rows(execute, "SELECT attname, format_type(atttypid, atttypmod) AS kind "
                         "FROM pg_attribute WHERE attrelid = 'daily_facts_v1'::regclass "
                         "AND attnum > 0 AND NOT attisdropped ORDER BY attnum")
    if columns != [{"attname": field.name, "kind": SQL_TYPES[field.type]} for field in schema]:
        raise ValueError("Postgres view schema differs from the typed v1 projection")
    actual = {}
    for row in _json_rows(execute, f"SELECT * FROM daily_facts_v1 {release_filter}"):
        key = (row["release_id"], row["asset"], date.fromisoformat(row["session_date"]))
        if key in actual:
            raise ValueError(f"duplicate Postgres session key: {key}")
        actual[key] = row
    if actual.keys() != expected.keys():
        raise ValueError("Postgres session keys differ from the pinned release")
    for key, source in expected.items():
        stored = actual[key]
        if stored.keys() != source.keys():
            raise ValueError("Postgres view columns differ from the pinned release")
        for field in schema:
            if not _matches(source[field.name], stored[field.name], field.type):
                raise ValueError(f"Postgres parity mismatch at {key[1:]} in {field.name}")
    window_rows = _json_rows(execute, 'SELECT release_id, asset, session_date, "window" '
                            f"FROM daily_window_facts {release_filter}")
    actual_windows = Counter((row["release_id"], row["asset"], date.fromisoformat(row["session_date"]),
                              row["window"]) for row in window_rows)
    if actual_windows != Counter((*key, window) for key in expected for window in WINDOWS):
        raise ValueError("Postgres window keys differ from the pinned release")
    return Counter((key[1], key[3]) for key in actual_windows)


def import_release(root, manifest_path, manifest_sha256, *, executable, socket_dir, port, database):
    """Verify release bytes, stage typed rows, and commit only after full readback."""
    manifest = read_pinned_manifest(root, manifest_path, manifest_sha256, True)
    source = load_daily_facts(root, manifest_path=manifest_path, manifest_sha256=manifest_sha256)
    schema = output_schema()
    if not source.schema.equals(schema, check_metadata=True):
        raise ValueError("pinned Daily Facts columns differ from the v1 projection contract")
    rows = source.to_pylist()
    expected = {tuple(row[name] for name in KEY): row for row in rows}
    counts = Counter(row["asset"] for row in rows)
    if (len(expected) != len(rows) or counts != manifest["row_counts"] or set(counts) != set(ASSETS)
            or any(row["release_id"] != DATASET_ID or row["definition_version"] != VERSION for row in rows)):
        raise ValueError("invalid session roster or identity in the pinned Daily Facts release")

    release_filter = f"WHERE release_id = '{DATASET_ID}'"
    release_identity = {"definition_version": VERSION, "manifest_sha256": manifest_sha256, "ready": True}
    with _psql(executable, socket_dir, port, database) as execute:
        execute(f"BEGIN; SET LOCAL search_path TO {SCHEMA}; SET LOCAL TimeZone TO 'UTC'; "
                "SET LOCAL DateStyle TO 'ISO, YMD'; SET LOCAL extra_float_digits TO 3;")
        execute("SELECT pg_advisory_xact_lock(hashtext('abacus.daily_facts.import'));")
        version = execute("SHOW server_version;")[0].strip()
        if execute(f"SELECT to_regclass('{SCHEMA}.dataset_releases') IS NULL;") == ["t\n"]:
            execute(_ddl(schema))
        existing = _json_rows(execute, "SELECT definition_version, manifest_sha256, ready "
                              f"FROM dataset_releases {release_filter}")
        if existing:
            if existing != [release_identity]:
                raise ValueError("Postgres already has this release with a different pin or readiness")
        else:
            execute("INSERT INTO dataset_releases (release_id, definition_version, manifest_sha256) "
                    f"VALUES ('{DATASET_ID}', '{VERSION}', '{manifest_sha256}');")
            for table, columns, records in _copy_batches(schema, rows):
                names = ", ".join(f'"{name}"' for name in columns)
                # psql reads COPY payload from its input up to the explicit terminator.
                execute(f"COPY {table} ({names}) FROM STDIN;", records)
            # Test the real serving view. Readiness is provisional until COMMIT.
            execute(f"UPDATE dataset_releases SET ready = true {release_filter};")
        window_counts = _parity(execute, schema, expected, release_filter)
        storage_bytes = int(execute("SELECT sum(pg_total_relation_size(oid)) FROM pg_class "
                                    f"WHERE relnamespace = '{SCHEMA}'::regnamespace AND relkind = 'r';")[0])
        execute("COMMIT;")

    partitions = {str(DATA_PATH / f"product={asset}/part-000.parquet") for asset in ASSETS}
    return {
        "release_id": DATASET_ID,
        "manifest_sha256": manifest_sha256,
        "parquet_partitions": [record for record in manifest["output_files"]
                               if record["path"] in partitions],
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "postgres_version": version,
        "database": database,
        "action": "verified_existing" if existing else "imported",
        "sessions": len(rows),
        "window_rows": sum(window_counts.values()),
        "columns": len(schema),
        "field_comparisons": len(rows) * len(schema),
        "projection_storage_bytes": storage_bytes,
        "session_counts": dict(counts),
        "window_counts": {asset: {window: window_counts[asset, window] for window in WINDOWS}
                          for asset in ASSETS},
        "first_session": min(key[2] for key in expected).isoformat(),
        "last_session": max(key[2] for key in expected).isoformat(),
        "mismatches": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="override the configured publication root")
    parser.add_argument("--manifest", type=Path, default=Path(f"catalog/datasets/{DATASET_ID}.json"))
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--psql", default="psql")
    parser.add_argument("--socket-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--database", required=True)
    args = parser.parse_args()
    result = import_release(resolve_publication_root(args.root), args.manifest, args.manifest_sha256,
                            executable=args.psql, socket_dir=args.socket_dir, port=args.port,
                            database=args.database)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
