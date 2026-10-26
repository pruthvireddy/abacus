#!/usr/bin/env python3
"""Read-only, bounded GitHub upload hygiene checks; not a comprehensive secret audit."""
from __future__ import annotations

import argparse
from collections import defaultdict
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

sys.dont_write_bytecode = True

WARN_BYTES = 50 * 1024 * 1024
FAIL_BYTES = 100 * 1024 * 1024
CHUNK_BYTES = 1024 * 1024
OVERLAP_BYTES = 512
# Delimiters keep random URL path segments from being mistaken for API keys.
TOKEN_LEFT = rb"(?<![A-Za-z0-9_./-])"
TOKEN_RIGHT = rb"(?![A-Za-z0-9_/-])"
PATTERNS = {
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "github_token": re.compile(TOKEN_LEFT + rb"(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{40,255})" + TOKEN_RIGHT),
    "aws_access_id": re.compile(TOKEN_LEFT + rb"(?:AKIA|ASIA)[A-Z0-9]{16}" + TOKEN_RIGHT),
    "openai_key": re.compile(TOKEN_LEFT + rb"sk-(?:(?:proj-|svcacct-)[A-Za-z0-9_-]{32,240}|[A-Za-z0-9]{48})" + TOKEN_RIGHT),
    "slack_token": re.compile(TOKEN_LEFT + rb"xox[baprs]-[A-Za-z0-9-]{20,240}" + TOKEN_RIGHT),
}


class AuditError(Exception):
    pass


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if result.returncode:
        # Never echo arbitrary command output or credential-like bytes.
        raise AuditError(f"git {args[0]} failed (exit {result.returncode})")
    return result.stdout


def sensitive_name(path):
    name = Path(path).name.lower()
    if name.startswith(".env") and name not in {".env.example", ".env.sample", ".env.template", ".env.dist"}:
        return True
    return (name in {".netrc", ".pypirc", "credentials", "credentials.json", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "paths.local.toml"}
            or name.endswith((".key", ".pem", ".p12", ".pfx")))


def scan_stream(stream, limit=None):
    """Scan all bytes in bounded chunks, including signatures crossing a boundary."""
    tail = b""
    consumed = 0
    newlines = 0
    emitted = set()
    while limit is None or consumed < limit:
        amount = CHUNK_BYTES if limit is None else min(CHUNK_BYTES, limit - consumed)
        chunk = stream.read(amount)
        if not chunk:
            if limit is not None and consumed != limit:
                raise AuditError("Unexpected end of blob content")
            break
        data = tail + chunk
        origin = consumed - len(tail)
        first_line = newlines - tail.count(b"\n") + 1
        for kind, pattern in PATTERNS.items():
            for match in pattern.finditer(data):
                # Defer matches ending at a non-final boundary until the next chunk
                # supplies a right delimiter. All patterns fit within the overlap.
                final = limit is not None and consumed + len(chunk) == limit
                if match.end() == len(data) and len(chunk) == amount and not final:
                    continue
                key = (kind, origin + match.start())
                if match.start() == 0 and origin > 0:
                    continue
                if key not in emitted:
                    emitted.add(key)
                    yield {"kind": kind, "line": first_line + data.count(b"\n", 0, match.start())}
        consumed += len(chunk)
        newlines += chunk.count(b"\n")
        tail = data[-OVERLAP_BYTES:]
    # A file whose length is an exact multiple of CHUNK_BYTES needs one final
    # check for a token ending at EOF, where no next-chunk delimiter exists.
    if tail:
        for kind, pattern in PATTERNS.items():
            for match in pattern.finditer(tail):
                key = (kind, consumed - len(tail) + match.start())
                if match.start() == 0 and consumed > len(tail):
                    continue
                if key not in emitted:
                    emitted.add(key)
                    yield {"kind": kind, "line": newlines - tail.count(b"\n") + 1 + tail.count(b"\n", 0, match.start())}


def audit(root, refs=None):
    root = root.resolve()
    refs = refs or ["HEAD"]
    report = {
        "schema": "abacus.github-readiness/v1", "root": str(root),
        "scope": "Git-eligible working files, index blobs, and only history reachable from the requested refs. Symlink targets are assessed in the working tree and index only. Ignored files, unrelated refs, research validity, redistribution rights and exhaustive secret detection are not assessed.",
        "threshold_bytes": {"warning": WARN_BYTES, "failure": FAIL_BYTES},
        "findings": [], "errors": [],
    }
    findings = report["findings"]
    seen_findings = set()

    def add(severity, kind, path, scope, **extra):
        key = (severity, kind, path, scope, extra.get("line"), extra.get("object"))
        if key not in seen_findings:
            seen_findings.add(key)
            findings.append({"severity": severity, "kind": kind, "path": path, "scope": scope, **extra})

    def check_size(size, path, scope, **extra):
        if size > FAIL_BYTES:
            add("error", "file_above_100MiB", path, scope, bytes=size, **extra)
        elif size > WARN_BYTES:
            add("warning", "file_above_50MiB", path, scope, bytes=size, **extra)

    try:
        actual_root = Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel")).rstrip("\n")).resolve()
        if actual_root != root:
            raise AuditError("--root must be the Git working-tree root")
        paths = sorted(set(os.fsdecode(p) for p in git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0") if p))
        path_set = set(paths)

        def check_link(name, target_text, scope):
            if not target_text or "\0" in target_text:
                add("error", "invalid_symlink_target", name, scope)
                return
            target = (root / name).parent.joinpath(target_text).resolve()
            if not target.is_relative_to(root):
                add("error", "external_symlink", name, scope)
                return
            relative = target.relative_to(root).as_posix()
            if Path(target_text).is_absolute():
                add("warning", "absolute_internal_symlink", name, scope)
            if not target.exists() or not (relative in path_set or any(p.startswith(relative + "/") for p in paths)):
                add("warning", "symlink_target_requires_restore", name, scope)

        groups = defaultdict(lambda: {"files": 0, "bytes": 0})
        scanned_files = 0
        for name in paths:
            path = root / name
            if sensitive_name(name):
                add("error", "sensitive_filename", name, "working_tree")
            try:
                # Never follow a changed tracked directory into an external tree.
                parent = root
                unsafe_parent = False
                for segment in Path(name).parts[:-1]:
                    parent /= segment
                    if parent.is_symlink():
                        add("error", "symlink_ancestor", name, "working_tree")
                        unsafe_parent = True
                        break
                if unsafe_parent:
                    continue
                info = path.lstat()
                group = groups[name.split("/", 1)[0]]
                group["files"] += 1
                group["bytes"] += info.st_size
                if stat.S_ISLNK(info.st_mode):
                    check_link(name, os.readlink(path), "working_tree")
                    continue
                if not stat.S_ISREG(info.st_mode):
                    add("warning", "non_regular_file_not_scanned", name, "working_tree")
                    continue
                check_size(info.st_size, name, "working_tree")
                # O_NOFOLLOW guards the final component against symlink races.
                descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                with os.fdopen(descriptor, "rb") as stream:
                    for match in scan_stream(stream):
                        add("error", match["kind"], name, "working_tree", line=match["line"])
                scanned_files += 1
            except FileNotFoundError:
                add("warning", "candidate_missing", name, "working_tree")
            except (OSError, RuntimeError, AuditError) as error:
                report["errors"].append({"scope": "working_tree", "path": name, "kind": type(error).__name__})
        report["working_tree"] = {"candidate_paths": len(paths), "scanned_regular_files": scanned_files,
                                  "bytes": sum(g["bytes"] for g in groups.values()),
                                  "directories": dict(sorted(groups.items(), key=lambda item: (-item[1]["bytes"], item[0])))}

        # Index content can differ from the working file; inspect its objects too.
        index_objects = {}
        index_symlinks = defaultdict(list)
        for record in git(root, "ls-files", "--stage", "-z").split(b"\0"):
            if not record:
                continue
            metadata, raw_path = record.split(b"\t", 1)
            mode, oid, stage = metadata.split()
            name = os.fsdecode(raw_path)
            if stage != b"0":
                add("error", "unmerged_index", name, "index")
            if mode == b"160000":
                add("warning", "submodule_not_scanned", name, "index")
                continue
            if mode == b"120000":
                index_symlinks[oid.decode("ascii")].append(name)
            index_objects.setdefault(oid.decode("ascii"), name)

        history_objects = {}
        resolved_refs = []
        for ref in refs:
            if ref.startswith("-"):
                raise AuditError("History refs must not begin with '-'")
            result = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "--end-of-options", ref + "^{commit}"], capture_output=True)
            if result.returncode:
                if ref == "HEAD":
                    symbolic = subprocess.run(["git", "-C", str(root), "symbolic-ref", "-q", "HEAD"], capture_output=True)
                    if symbolic.returncode == 0:
                        existing = subprocess.run(["git", "-C", str(root), "show-ref", "--verify", "--quiet", os.fsdecode(symbolic.stdout).rstrip("\n")], capture_output=True)
                        if existing.returncode == 1:
                            add("warning", "no_committed_history", "HEAD", "history")
                            continue
                raise AuditError("Requested history ref does not resolve to a commit")
            resolved_refs.append(result.stdout.strip().decode("ascii"))
        if resolved_refs:
            for oid in git(root, "rev-list", "--objects", "--no-object-names", *resolved_refs, "--").splitlines():
                history_objects[oid.decode("ascii")] = None
            # Use NUL-delimited raw diffs for names: rev-list's path hints are
            # truncated at embedded newlines and are unsuitable for audit paths.
            records = iter(git(root, "log", "--format=", "--raw", "-z", "--no-abbrev", "--no-renames", "--root", "-m", *resolved_refs, "--").split(b"\0"))
            for record in records:
                if record.lstrip(b"\n").startswith(b":"):
                    metadata = record.lstrip(b"\n")[1:].split()
                    if len(metadata) != 5:
                        raise AuditError("Invalid Git raw-diff framing")
                    raw_path = next(records, None)
                    if raw_path is None:
                        raise AuditError("Invalid Git history path framing")
                    name = os.fsdecode(raw_path)
                    for raw_oid in metadata[2:4]:
                        oid = raw_oid.decode("ascii")
                        if oid in history_objects and history_objects[oid] is None:
                            history_objects[oid] = name
                    if sensitive_name(name):
                        add("error", "sensitive_filename", name, "history")
        report["history"] = {"refs": refs, "resolved_commits": resolved_refs, "scanned_blobs": 0, "blob_bytes": 0}
        object_scopes = defaultdict(dict)
        for oid, name in index_objects.items():
            object_scopes[oid]["index"] = name
        for oid, name in history_objects.items():
            object_scopes[oid]["history"] = name
        process = subprocess.Popen(["git", "-C", str(root), "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            for oid, scopes in object_scopes.items():
                process.stdin.write(oid.encode("ascii") + b"\n")
                process.stdin.flush()
                header = process.stdout.readline().split()
                if len(header) != 3 or header[0].decode("ascii") != oid:
                    raise AuditError("Cannot read a Git object")
                kind, size = header[1], int(header[2])
                if kind == b"blob":
                    if oid in index_symlinks and size <= 65536:
                        content = process.stdout.read(size)
                        matches = list(scan_stream(io.BytesIO(content), size))
                        for name in index_symlinks[oid]:
                            try:
                                check_link(name, os.fsdecode(content), "index")
                            except (OSError, RuntimeError, ValueError):
                                report["errors"].append({"scope": "index", "path": name, "kind": "symlink_resolution_failed"})
                    else:
                        matches = list(scan_stream(process.stdout, size))
                        for name in index_symlinks.get(oid, []):
                            add("error", "symlink_target_too_large", name, "index")
                    if "history" in scopes:
                        report["history"]["scanned_blobs"] += 1
                        report["history"]["blob_bytes"] += size
                    for scope, name in scopes.items():
                        name = name or f"<blob:{oid}>"
                        if sensitive_name(name):
                            add("error", "sensitive_filename", name, scope, object=oid)
                        check_size(size, name, scope, object=oid)
                        for match in matches:
                            add("error", match["kind"], name, scope, line=match["line"], object=oid)
                else:
                    remaining = size
                    while remaining:
                        chunk = process.stdout.read(min(CHUNK_BYTES, remaining))
                        if not chunk:
                            raise AuditError("Unexpected end of Git object")
                        remaining -= len(chunk)
                if process.stdout.read(1) != b"\n":
                    raise AuditError("Invalid Git object framing")
        finally:
            process.stdin.close()
            process.stdout.close()
            process.wait()
        if process.returncode:
            raise AuditError("Git object reader failed")
    except (AuditError, OSError, ValueError) as error:
        report["errors"].append({"scope": "audit", "kind": type(error).__name__, "message": str(error) if isinstance(error, AuditError) else "Local audit operation failed"})
    report["summary"] = {"errors": len(report["errors"]) + sum(f["severity"] == "error" for f in findings),
                         "warnings": sum(f["severity"] == "warning" for f in findings)}
    report["passed"] = report["summary"]["errors"] == 0
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Git working-tree root")
    parser.add_argument("--ref", action="append", dest="refs", help="History ref to include; repeatable, default HEAD. Unrelated/internal refs are excluded.")
    parser.add_argument("--json", action="store_true", help="Write the complete redacted report to stdout; no files are created")
    args = parser.parse_args(argv)
    report = audit(args.root, args.refs)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        total = report.get("working_tree", {})
        print(f"GitHub hygiene {'passed' if report['passed'] else 'failed'}: {report['summary']['errors']} errors, {report['summary']['warnings']} warnings.")
        print(f"Working tree: {total.get('candidate_paths', 0)} candidate paths, {total.get('bytes', 0) / 1024**2:.2f} MiB; history: {report.get('history', {}).get('scanned_blobs', 0)} reachable blobs.")
        for finding in report["findings"]:
            line = f":{finding['line']}" if "line" in finding else ""
            print(f"{finding['severity']}: {finding['scope']} {json.dumps(finding['path'])}{line}: {finding['kind']}")
        for error in report["errors"]:
            print(f"audit error: {json.dumps(error, ensure_ascii=True)}")
        print(report["scope"])
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
