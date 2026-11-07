#!/usr/bin/env python3
"""Keep the generated copies in this repo in sync with their sources.

What it does, in order:

1. Rewrites the ground-rules block in every ``skills/*/SKILL.md``. The block is
   everything between ``<!-- ground-rules:start -->`` and
   ``<!-- ground-rules:end -->`` and must equal ``scripts/ground_rules.md``.
2. Mirrors ``skills/`` into ``agent-plugin/skills/`` byte for byte (Agent
   Plugins hosts reject symlinks that leave the plugin root, so it is a real
   copy). Files that no longer exist in ``skills/`` are deleted from the mirror.
3. Builds the Claude plugin's copy, ``plugins/frameos/skills/``, from ``skills/``
   with the setup skill's per-app steps narrowed to Claude Code, claude.ai,
   Claude Desktop and Cowork, and copies ``LICENSE`` and ``assets/icon.png``
   (as ``.claude-plugin/icon.png``) into ``plugins/frameos/``.
   That folder is the whole Claude plugin (the marketplace's ``source``), so the
   repo's docs, scripts and tests never ship with it.

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
import re
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
CLAUDE_PLUGIN_DIR = Path("plugins") / "frameos"
CLAUDE_SKILLS_DIR = CLAUDE_PLUGIN_DIR / "skills"
# The Claude plugin installs only in Claude apps, so its setup skill keeps the
# Claude sections and the generic one; every other app's steps (and their
# install commands) stay out of it. Each edit is skipped when its text is absent.
CLAUDE_HOST_SECTIONS = ("Claude", "Any other MCP client")
CLAUDE_OTHER_APPS = ("Codex", "ChatGPT", "Cursor", "Gemini", "VS Code", "GitHub Copilot", "Perplexity", "Devin")
CLAUDE_HOSTS_NOTE = (
    "This copy covers Claude Code, claude.ai, Claude Desktop and Cowork. "
    "Steps for every other app are at https://frameos.studio/plugin."
)

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


def _keep_sections(text: str, keep: Tuple[str, ...], note: str) -> str:
    """Keep the preamble and the '## ' sections whose heading starts with one of ``keep``; put ``note`` first."""
    parts = re.split(r"(?m)^(?=## )", text)
    kept = [p for p in parts[1:] if p[3:].startswith(keep)]
    if len(parts) == 1 or not kept:
        return text
    return parts[0] + note + "\n\n" + "".join(kept)


def _claude_frontmatter(text: str) -> str:
    """Drop SKILL.md frontmatter keys the Claude Directory refuses from an organization
    that isn't Verified (it accepts name, description and argument-hint)."""
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---", 4)
    if end < 0:
        return text
    head = re.sub(r"(?m)^license:.*\n", "", text[: end + 1])
    return head + text[end + 1:]


def claude_skill_text(rel: str, text: str) -> str:
    """The Claude plugin's copy of one file under skills/ (``rel`` is relative to skills/)."""
    if rel.endswith("/SKILL.md"):
        text = _claude_frontmatter(text)
    if rel == "frameos-setup/references/hosts.md":
        return _keep_sections(text, CLAUDE_HOST_SECTIONS, CLAUDE_HOSTS_NOTE)
    if rel == "frameos-setup/SKILL.md":
        text = re.sub(r"(?m)^1\. Identify the app: .*$",
                      "1. Identify the app: Claude Code, claude.ai / Claude Desktop / Cowork, or another MCP client. If unclear, ask once.",
                      text)
        text = re.sub(r"; in Codex `[^`]*` also works", "", text)
        # Table rows for other apps (reconnect steps, app-specific errors).
        return re.sub(r"(?m)^\| (?:" + "|".join(map(re.escape, CLAUDE_OTHER_APPS)) + r").*\n", "", text)
    if rel == "frameos-clip/references/workflow-details.md":
        text = re.sub(r"(?m)^(\| Has a shell \| )[^|]*\|", r"\1Claude Code, or any agent with a terminal |", text)
        return re.sub(r"(?m)^(\| Chat only \| )[^|]*\|", r"\1claude.ai, Claude Desktop chat and Cowork |", text)
    return text


def claude_copy(src_files: Dict[str, bytes]) -> Dict[str, bytes]:
    out: Dict[str, bytes] = {}
    for rel, data in src_files.items():
        if rel.endswith("/agents/openai.yaml"):
            continue  # Codex interface metadata; Claude never reads it
        if rel.endswith(".md"):
            out[rel] = claude_skill_text(rel, data.decode("utf-8")).encode("utf-8")
        else:
            out[rel] = data
    return out


@dataclass
class Drift:
    kind: str  # "ground_rules" | "mirror" | "claude"
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
    _mirror(root, src_files, MIRROR_DIR, "mirror", check, result)

    # 3. The Claude plugin folder: narrowed skills, the licence and the icon
    # (.claude-plugin/icon.png is where the directory looks for it; nothing in
    # the plugin refers to it, so it is not a file the plugin's code could run).
    _mirror(root, claude_copy(src_files), CLAUDE_SKILLS_DIR, "claude", check, result)
    for src, dst in (("LICENSE", "LICENSE"), ("assets/icon.png", ".claude-plugin/icon.png")):
        source = root / src
        if not source.is_file():
            continue
        target = root / CLAUDE_PLUGIN_DIR / dst
        if not target.is_file() or target.read_bytes() != source.read_bytes():
            result.drift.append(Drift("claude", (CLAUDE_PLUGIN_DIR / dst).as_posix(), f"differs from {src}"))
            if not check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
    return result


def _mirror(root: Path, src_files: Dict[str, bytes], mirror_dir: Path, kind: str, check: bool, result: SyncResult) -> None:
    """Make ``mirror_dir`` hold exactly ``src_files`` (posix paths relative to it)."""
    mirror_base = root / mirror_dir
    dst_files, dst_problems = collect_tree(mirror_base)
    result.errors.extend(dst_problems)

    mirror_rel = mirror_dir.as_posix()
    for rel, data in sorted(src_files.items()):
        if rel not in dst_files:
            result.drift.append(Drift(kind, f"{mirror_rel}/{rel}", "missing from the mirror"))
        elif dst_files[rel] != data:
            result.drift.append(Drift(kind, f"{mirror_rel}/{rel}", f"differs from {SKILLS_DIR.as_posix()}/{rel}"))
        else:
            continue
        if not check:
            target = mirror_base / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    for rel in sorted(set(dst_files) - set(src_files)):
        result.drift.append(Drift(kind, f"{mirror_rel}/{rel}", f"stale (not in {SKILLS_DIR.as_posix()}/)"))
        if not check:
            (mirror_base / rel).unlink()

    # Junk files in the mirror (e.g. .DS_Store) are never valid; remove them on apply.
    if mirror_base.is_dir():
        for dirpath, dirnames, filenames in os.walk(mirror_base):
            for name in filenames:
                if _ignored(name):
                    rel = (Path(dirpath) / name).relative_to(root).as_posix()
                    result.drift.append(Drift(kind, rel, "junk file in the mirror"))
                    if not check:
                        (Path(dirpath) / name).unlink()
            for d in list(dirnames):
                if _ignored(d):
                    rel = (Path(dirpath) / d).relative_to(root).as_posix()
                    result.drift.append(Drift(kind, rel + "/", "junk directory in the mirror"))
                    if not check:
                        shutil.rmtree(Path(dirpath) / d)
                    dirnames.remove(d)
        if not check:
            # Remove directories left empty by deletions (deepest first).
            for dirpath, dirnames, filenames in sorted(os.walk(mirror_base), key=lambda t: -len(t[0])):
                p = Path(dirpath)
                if p != mirror_base and not any(p.iterdir()):
                    p.rmdir()


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
            print("sync --check: ground-rules blocks, agent-plugin/skills and plugins/frameos are in sync")
        return 0 if result.ok else 1
    if not args.quiet:
        for d in result.drift:
            print(f"synced {d}")
    if not result.drift and not result.errors and not args.quiet:
        print("sync: nothing to do")
    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
