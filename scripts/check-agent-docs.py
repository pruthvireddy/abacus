#!/usr/bin/env python3
"""Check only active navigation guides; never recurse into their link targets.

Maintained guide paths come from owner records in config/workspace-checks.json.
The registry is an explicit allowlist, not a recursive Markdown inventory.

Supported: single-line inline links/images, full/collapsed reference links,
reference shortcuts with definitions, ATX/setext headings and explicit HTML IDs.
Inline destinations may use angle brackets, percent escapes, an optional quoted
link title, or one nested pair of parentheses. Fenced and inline code is ignored.
Multiline links, nested link labels, HTML hrefs and Markdown extensions are not
parsed. Heading slugs cover ordinary GitHub Markdown (including duplicate IDs);
HTML rendering and extension-specific slug generation are outside this check.
External schemes are ignored without network access; file: URLs are rejected.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

DEST = r'(<[^>\n]*>|(?:\\.|[^()\s]|\([^()\n]*\))+)'
INLINE = re.compile(r'!?\[[^\]\n]*\]\(\s*' + DEST + r'(?:\s+(?:"[^"]*"|\x27[^\x27]*\x27))?\s*\)')
DEFINITION = re.compile(r'^ {0,3}\[([^\]]+)\]:\s*' + DEST + r'(?:\s+(?:"[^"]*"|\x27[^\x27]*\x27))?\s*$')
REFERENCE = re.compile(r'!?\[([^\]\n]+)\]\[([^\]\n]*)\]')
SHORTCUT = re.compile(r'!?\[([^\]\n]+)\]')
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')
CODE = re.compile(r'(`+)(?!`)(.+?)(?<!`)\1(?!`)')


def without_code(source: str) -> list[tuple[int, str, str]]:
    """Keep line numbers and heading text while masking examples/comments."""
    source = re.sub(r'<!--[\s\S]*?-->', lambda m: re.sub(r'[^\n]', ' ', m[0]), source)
    result, fence = [], None
    for number, line in enumerate(source.splitlines(), 1):
        match = FENCE.match(line)
        if fence:
            if match and match[1][0] == fence[0] and len(match[1]) >= fence[1] and not match[2].strip():
                fence = None
            continue
        if match:
            fence = (match[1][0], len(match[1]))
            continue
        result.append((number, CODE.sub(lambda m: ' ' * len(m[0]), line), line))
    return result


def reference_key(label: str) -> str:
    return ' '.join(label.split()).casefold()


def destination(value: str) -> str:
    value = value[1:-1] if value.startswith('<') and value.endswith('>') else value
    return re.sub(r'\\([!"#$%&\x27()*+,\-./:;<=>?@\[\]\\^_`{|}~])', r'\1', value)


def links(source: str) -> list[tuple[int, str | None, str]]:
    lines = without_code(source)
    definitions = {}
    result = []
    for number, masked, _ in lines:
        match = DEFINITION.match(masked)
        if match:
            definitions.setdefault(reference_key(match[1]), destination(match[2]))
            result.append((number, destination(match[2]), match[1]))
    for number, masked, _ in lines:
        if DEFINITION.match(masked):
            continue
        for match in INLINE.finditer(masked):
            result.append((number, destination(match[1]), match[0]))
        remainder = INLINE.sub(lambda m: ' ' * len(m[0]), masked)
        for match in REFERENCE.finditer(remainder):
            key = reference_key(match[2] or match[1])
            result.append((number, definitions.get(key), key))
        remainder = REFERENCE.sub(lambda m: ' ' * len(m[0]), remainder)
        for match in SHORTCUT.finditer(remainder):
            key = reference_key(match[1])
            if key in definitions:
                result.append((number, definitions[key], key))
    return result


def anchors(source: str) -> set[str]:
    used = set()
    previous = ''
    for _, _, line in without_code(source):
        for explicit in re.finditer(r'<[A-Za-z][^>]*\b(?:id|name)=["\x27]([^"\x27]+)["\x27]', line):
            used.add(html.unescape(explicit[1]))
        heading = re.match(r'^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$', line)
        title = heading[1] if heading else previous if previous.strip() and re.fullmatch(r' {0,3}(?:=+|-+)\s*', line) else None
        previous = line
        if title is None:
            continue
        title = re.sub(r'!?\[([^\]]+)\]\([^)]*\)', r'\1', title)
        title = re.sub(r'<[^>]*>', '', html.unescape(title)).lower()
        title = ''.join(c for c in title if c in ' -_' or unicodedata.category(c)[0] in 'LN')
        base = title.replace(' ', '-')
        slug, suffix = base, 0
        while slug in used:
            suffix += 1
            slug = f'{base}-{suffix}'
        used.add(slug)
    return used


def guide_inventory(root: Path) -> tuple[str, ...]:
    """Resolve maintained owner declarations without reading guide contents."""
    # Sibling loading also supports callers importing this hyphenated script by
    # file path from another directory. Do not create bytecode during a check.
    previous_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from check_registry import load_registry, maintained_guides
        return maintained_guides(load_registry(root))
    finally:
        sys.path.pop(0)
        sys.dont_write_bytecode = previous_bytecode


def registry_error(error: Exception) -> str:
    return f'config/workspace-checks.json:1: invalid maintained guide registry: {error}'


def check(root: Path, guides: tuple[str, ...] | None = None) -> list[str]:
    root = root.resolve()
    if guides is None:
        try:
            guides = guide_inventory(root)
        except (OSError, UnicodeError, ValueError) as error:
            return [registry_error(error)]
    errors, cache, seen = [], {}, set()
    for guide in guides:
        if guide in seen:
            errors.append(f'{guide}:1: duplicate required navigation guide')
            continue
        seen.add(guide)
        path = root / guide
        try:
            resolved = path.resolve()
            if not resolved.is_relative_to(root):
                errors.append(f'{guide}:1: required guide resolves outside repository')
                continue
            if not path.is_file():
                errors.append(f'{guide}:1: missing required navigation guide')
                continue
            source = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError, RuntimeError) as error:
            errors.append(f'{guide}:1: cannot read required guide: {error}')
            continue
        for line, href, label in links(source):
            location = f'{guide}:{line}'
            if href is None:
                errors.append(f'{location}: undefined link reference [{label}]')
                continue
            try:
                url = urlsplit(html.unescape(href))
                if url.scheme or url.netloc:
                    if url.scheme.lower() == 'file':
                        errors.append(f'{location}: file: URLs are unsupported; use a relative repository path')
                    continue
                raw_path = unquote(url.path)
                target = (path.parent / raw_path).resolve() if raw_path else resolved
                if not target.is_relative_to(root):
                    errors.append(f'{location}: link resolves outside repository: {href}')
                elif not target.exists():
                    errors.append(f'{location}: missing link target: {href}')
                elif url.fragment and target.is_file() and target.suffix.lower() in {'.md', '.markdown'}:
                    if target not in cache:
                        cache[target] = anchors(target.read_text(encoding='utf-8'))
                    if unquote(url.fragment) not in cache[target]:
                        errors.append(f'{location}: missing Markdown heading anchor: {href}')
            except (OSError, UnicodeError, ValueError, RuntimeError) as error:
                errors.append(f'{location}: cannot check link {href!r}: {error}')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    try:
        guides = guide_inventory(args.root)
        errors = check(args.root, guides)
    except (OSError, UnicodeError, ValueError) as error:
        guides, errors = (), [registry_error(error)]
    for error in errors:
        print(error, file=sys.stderr)
    print(f'Checked {len(guides)} active navigation guides: {len(errors)} error(s).')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
