#!/usr/bin/env python3
"""Set the plugin version everywhere it appears.

Usage::

    python3 scripts/bump_version.py 0.2.0
    python3 scripts/bump_version.py 0.2.0 --dry-run      # show what would change
    python3 scripts/bump_version.py 0.1.1 --allow-downgrade
    python3 scripts/bump_version.py 0.2.0 --root DIR     # another checkout (tests)

Updates ``VERSION``, every manifest and marketplace ``version`` (the sites are
listed in ``VERSION_SITES`` in scripts/validate.py), every
``X-FrameOS-Plugin-Version`` header in any JSON file, and header values quoted
in docs (``*.md``, ``*.toml``, ``*.yaml``; CHANGELOG.md is history and is left
alone). Refuses anything that is not semver. Nothing is written unless every
site is found.

Exit codes: 0 = done, 1 = a version site is missing or the result does not
validate, 2 = bad arguments (non-semver, downgrade without the flag).

Python 3.9+, standard library only. Add the CHANGELOG.md entry by hand.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate as V  # noqa: E402  (sibling module)


def _dump_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _set_all_headers(obj: Any, version: str) -> int:
    """Set every X-FrameOS-Plugin-Version key at any depth; return how many."""
    n = 0
    if isinstance(obj, dict):
        for k in list(obj):
            if k == V.VERSION_HEADER:
                obj[k] = version
                n += 1
            else:
                n += _set_all_headers(obj[k], version)
    elif isinstance(obj, list):
        for item in obj:
            n += _set_all_headers(item, version)
    return n


def plan_bump(root: Path, new: str) -> Dict[Path, str]:
    """Return {path: new_text} for every file that must change. Raises ValueError on a missing site."""
    root = Path(root)
    changes: Dict[Path, str] = {}
    missing: List[str] = []

    vfile = root / "VERSION"
    if (vfile.read_text(encoding="utf-8") if vfile.is_file() else None) != new + "\n":
        changes[vfile] = new + "\n"

    by_file: Dict[str, List[V.JsonPath]] = {}
    for name, path in V.VERSION_SITES:
        by_file.setdefault(name, []).append(path)

    json_files = {V.rel(root, p): p for p in V.iter_repo_files(root) if p.suffix == ".json"}
    for name in sorted(set(by_file) | set(json_files)):
        path = root / name
        if not path.is_file():
            missing.append(f"{name}: file missing")
            continue
        original = path.read_bytes().decode("utf-8")
        try:
            data = json.loads(original)
        except ValueError as exc:
            if name in by_file:
                missing.append(f"{name}: invalid JSON ({exc})")
            continue
        touched = 0
        for site in by_file.get(name, []):
            if not V.set_path(data, site, new):
                missing.append(f"{name}: {V.fmt_path(site)} not found")
            else:
                touched += 1
        touched += _set_all_headers(data, new)
        if touched:
            text = _dump_json(data)
            if text != original:
                changes[path] = text

    # Header values quoted in docs and snippets.
    for path in V.iter_repo_files(root):
        name = V.rel(root, path)
        if path.suffix not in (".md", ".toml", ".yaml", ".yml", ".txt") or name == "CHANGELOG.md":
            continue
        text = V.read_text_or_none(path)
        if not text or V.VERSION_HEADER not in text:
            continue
        new_text = V.HEADER_MENTION_RE.sub(lambda m: m.group(0)[: m.start(1) - m.start(0)] + new, text)
        if new_text != text:
            changes[path] = new_text

    if missing:
        raise ValueError("version sites not found:\n  " + "\n  ".join(missing))
    return changes


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Set the FrameOS plugin version everywhere.")
    ap.add_argument("version", help="new semantic version, e.g. 0.2.0")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--dry-run", action="store_true", help="list the files that would change")
    ap.add_argument("--allow-downgrade", action="store_true", help="permit a version lower than the current one")
    args = ap.parse_args(argv)

    new = args.version.strip()
    if not V.SEMVER_RE.match(new):
        print(f"bump_version: {new!r} is not a semantic version like 1.2.3 (no 'v' prefix)", file=sys.stderr)
        return 2
    root = args.root.resolve()
    vfile = root / "VERSION"
    old = vfile.read_text(encoding="utf-8").strip() if vfile.is_file() else None
    if old and V.SEMVER_RE.match(old) and not args.allow_downgrade:
        if V.semver_key(new) < V.semver_key(old):
            print(f"bump_version: {new} is lower than the current {old}; pass --allow-downgrade to force", file=sys.stderr)
            return 2

    try:
        changes = plan_bump(root, new)
    except ValueError as exc:
        print(f"bump_version: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        for path in sorted(changes):
            print(f"would update {V.rel(root, path)}")
        print(f"bump_version: {len(changes)} file(s) would change ({old} -> {new})")
        return 0

    for path, text in sorted(changes.items()):
        path.write_bytes(text.encode("utf-8"))
        print(f"updated {V.rel(root, path)}")

    # Verify with the validator's own version checks.
    report = V.Report()
    ctx = V.Ctx(root, report)
    V.check_manifests_parse(ctx)
    V.check_versions(ctx)
    if report.errors:
        for e in report.errors:
            print(f"ERROR  {e}", file=sys.stderr)
        return 1
    print(f"bump_version: {old} -> {new} ({len(changes)} file(s)). Add a CHANGELOG.md entry, then run python3 scripts/test.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
