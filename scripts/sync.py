#!/usr/bin/env python3
"""Keep the generated copies in this repo in sync with their sources.

What it does, in order:

1. Rewrites the ground-rules block in every ``skills/*/SKILL.md``. The block is
   everything between ``<!-- ground-rules:start -->`` and
   ``<!-- ground-rules:end -->`` and must equal ``scripts/ground_rules.md``.
2. Mirrors ``skills/`` into ``agent-plugin/skills/`` byte for byte (Agent
   Plugins hosts reject symlinks that leave the plugin root, so it is a real
   copy). Files that no longer exist in ``skills/`` are deleted from the mirror.

Usage::

    python3 scripts/sync.py            # apply
    python3 scripts/sync.py --check    # change nothing; exit 1 and list drift
    python3 scripts/sync.py --root DIR # operate on another checkout (tests)

Exit codes: 0 = in sync (or synced), 1 = drift found in --check mode or an
error sync cannot fix (for example a SKILL.md without the markers).

Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

GROUND_START = "<!-- ground-rules:start -->"
GROUND_END = "<!-- ground-rules:end -->"
RULES_FILE = Path("scripts") / "ground_rules.md"
SKILLS_DIR = Path("skills")
MIRROR_DIR = Path("agent-plugin") / "skills"

# Never copied into the mirror (and validate.py forbids most of them anyway).
IGNORED_NAMES = {".DS_Store", "Thumbs.db", "__pycache__", ".pytest_cache"}
IGNORED_SUFFIXES = (".pyc", ".pyo", ".swp", "~")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _ignored(name: str) -> bool:
    return name in IGNORED_NAMES or name.endswith(IGNORED_SUFFIXES)


def read_text(path: Path) -> str:
    """Read UTF-8 text without newline translation (byte-faithful)."""
    return path.read_bytes().decode("utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def load_ground_rules(root: Path) -> str:
    return read_text(root / RULES_FILE)


def render_block(rules: str) -> str:
    """The canonical marked block: markers on their own lines around the rules."""
    return f"{GROUND_START}\n{rules.strip(chr(10))}\n{GROUND_END}"


def rewrite_ground_rules(text: str, rules: str) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(new_text, None)`` or ``(None, error)``.

    Only the marked region is touched; everything else is preserved byte for byte.
    """
    starts = text.count(GROUND_START)
    ends = text.count(GROUND_END)
    if starts == 0 and ends == 0:
        return None, (
            f"no ground-rules block. Add a line '{GROUND_START}' and a line "
            f"'{GROUND_END}' right after the H1 title and one-line purpose, then "
            "run python3 scripts/sync.py to fill it"
        )
    if starts != 1 or ends != 1:
        return None, (
            f"expected exactly one '{GROUND_START}' and one '{GROUND_END}', "
            f"found {starts} and {ends}"
        )
    i = text.index(GROUND_START)
    j = text.index(GROUND_END)
    if j < i:
        return None, f"'{GROUND_END}' appears before '{GROUND_START}'"
    new = text[:i] + render_block(rules) + text[j + len(GROUND_END):]
    return new, None


def skill_dirs(root: Path) -> List[Path]:
    base = root / SKILLS_DIR
    if not base.is_dir():
        return []
    return sorted(
        p for p in base.iterdir() if p.is_dir() and not p.name.startswith(".") and not _ignored(p.name)
    )


def collect_tree(base: Path) -> Tuple[Dict[str, bytes], List[str]]:
    """Map every regular file under ``base`` (posix relative path) to its bytes.

    Returns ``(files, problems)``; symlinks are reported, not followed.
    """
    files: Dict[str, bytes] = {}
    problems: List[str] = []
    if not base.is_dir():
        return files, problems
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if not _ignored(d))
        for d in list(dirnames):
            if os.path.islink(os.path.join(dirpath, d)):
                problems.append(f"{Path(dirpath, d)}: symlinked directory (hosts reject symlinks; use a real copy)")
                dirnames.remove(d)
        for name in sorted(filenames):
            if _ignored(name):
                continue
            full = Path(dirpath) / name
            rel = full.relative_to(base).as_posix()
            if full.is_symlink():
                problems.append(f"{full}: symlink (hosts reject symlinks; use a real file)")
                continue
            files[rel] = full.read_bytes()
    return files, problems


@dataclass
class Drift:
    kind: str  # "ground_rules" | "mirror"
    path: str  # repo-relative posix path
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass
class SyncResult:
    drift: List[Drift] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.drift and not self.errors


def sync(root: Path, check: bool = False) -> SyncResult:
    """Run (or, with ``check=True``, simulate) the sync. Never raises on drift."""
    root = Path(root)
    result = SyncResult()

    rules_path = root / RULES_FILE
    if not rules_path.is_file():
        result.errors.append(f"{RULES_FILE.as_posix()}: missing (it is the source of the ground-rules block)")
        return result
    rules = load_ground_rules(root)
    if not (root / SKILLS_DIR).is_dir():
        result.errors.append(f"{SKILLS_DIR.as_posix()}/: missing")
        return result

    # 1. Ground-rules blocks. ``expected`` holds post-sync bytes per SKILL.md.
    expected_overrides: Dict[str, bytes] = {}
    for sdir in skill_dirs(root):
        skill_md = sdir / "SKILL.md"
        rel = skill_md.relative_to(root).as_posix()
        if not skill_md.is_file():
            continue  # validate.py reports missing SKILL.md files
        try:
            text = read_text(skill_md)
        except UnicodeDecodeError:
            result.errors.append(f"{rel}: not valid UTF-8")
            continue
        new, err = rewrite_ground_rules(text, rules)
        if err:
            result.errors.append(f"{rel}: {err}")
            continue
        if new != text:
            result.drift.append(Drift("ground_rules", rel, "ground-rules block differs from scripts/ground_rules.md"))
            if not check:
                write_text(skill_md, new)
            expected_overrides[skill_md.relative_to(root / SKILLS_DIR).as_posix()] = new.encode("utf-8")

    # 2. Mirror skills/ -> agent-plugin/skills/.
    src_files, problems = collect_tree(root / SKILLS_DIR)
    result.errors.extend(problems)
    src_files.update(expected_overrides)  # in --check mode the source was not rewritten
    mirror_base = root / MIRROR_DIR
    dst_files, dst_problems = collect_tree(mirror_base)
    result.errors.extend(dst_problems)

    mirror_rel = MIRROR_DIR.as_posix()
    for rel, data in sorted(src_files.items()):
        if rel not in dst_files:
            result.drift.append(Drift("mirror", f"{mirror_rel}/{rel}", "missing from the mirror"))
        elif dst_files[rel] != data:
            result.drift.append(Drift("mirror", f"{mirror_rel}/{rel}", f"differs from {SKILLS_DIR.as_posix()}/{rel}"))
        else:
            continue
        if not check:
            target = mirror_base / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    for rel in sorted(set(dst_files) - set(src_files)):
        result.drift.append(Drift("mirror", f"{mirror_rel}/{rel}", f"stale (not in {SKILLS_DIR.as_posix()}/)"))
        if not check:
            (mirror_base / rel).unlink()

    # Junk files in the mirror (e.g. .DS_Store) are never valid; remove them on apply.
    if mirror_base.is_dir():
        for dirpath, dirnames, filenames in os.walk(mirror_base):
            for name in filenames:
                if _ignored(name):
                    rel = (Path(dirpath) / name).relative_to(root).as_posix()
                    result.drift.append(Drift("mirror", rel, "junk file in the mirror"))
                    if not check:
                        (Path(dirpath) / name).unlink()
            for d in list(dirnames):
                if _ignored(d):
                    rel = (Path(dirpath) / d).relative_to(root).as_posix()
                    result.drift.append(Drift("mirror", rel + "/", "junk directory in the mirror"))
                    if not check:
                        shutil.rmtree(Path(dirpath) / d)
                    dirnames.remove(d)
        if not check:
            # Remove directories left empty by deletions (deepest first).
            for dirpath, dirnames, filenames in sorted(os.walk(mirror_base), key=lambda t: -len(t[0])):
                p = Path(dirpath)
                if p != mirror_base and not any(p.iterdir()):
                    p.rmdir()
    return result


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="report drift without changing files; exit 1 on drift")
    ap.add_argument("--root", type=Path, default=repo_root(), help="repo root (default: this checkout)")
    ap.add_argument("--quiet", action="store_true", help="print only problems")
    args = ap.parse_args(argv)

    root = args.root.resolve()
    result = sync(root, check=args.check)
    for err in result.errors:
        print(f"ERROR  {err}", file=sys.stderr)
    if args.check:
        for d in result.drift:
            print(f"DRIFT  {d}")
        if result.drift:
            print(f"{len(result.drift)} file(s) out of sync. Run: python3 scripts/sync.py", file=sys.stderr)
        elif not result.errors and not args.quiet:
            print("sync --check: ground-rules blocks and agent-plugin/skills mirror are in sync")
        return 0 if result.ok else 1
    if not args.quiet:
        for d in result.drift:
            print(f"synced {d}")
    if not result.drift and not result.errors and not args.quiet:
        print("sync: nothing to do")
    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
