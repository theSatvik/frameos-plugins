#!/usr/bin/env python3
"""Build the distributable ZIPs into dist/.

Layouts:

* ``dist/claude-ai/<skill>.zip`` - the skill FOLDER is the top-level entry
  (``<skill>/SKILL.md``), as claude.ai / Claude Desktop Skills upload expects.
* ``dist/perplexity/<skill>.zip`` - ``SKILL.md`` at the ZIP root, as Perplexity
  Computer's skill upload expects (max 10 MB).
* ``dist/frameos-plugin-<version>.zip`` - the plugin contents at the ZIP root
  (exactly one ``.claude-plugin/plugin.json``) for claude.ai / Desktop "Upload
  plugin" and the OpenAI plugin portal. Excludes repo tooling and anything that
  is not part of the plugin: tests/, dev/, evals/, docs/submission/, dist/,
  .git/, .github/, plus scripts/ (maintainer tooling), agent-plugin/ (the Agent
  Plugins copy installed from GitHub; shipping it would put a second plugin
  manifest and a second copy of every skill in the archive) and the
  marketplace catalogs .claude-plugin/marketplace.json and .agents/ (a plugin
  upload is one plugin, not a marketplace).
* ``dist/SHA256SUMS`` - checksums of every ZIP above.

Builds are deterministic: sorted entries, fixed timestamps (1980-01-01),
fixed permissions, fixed compression level. Refuses to build when
``scripts/sync.py --check`` reports drift.

Usage::

    python3 scripts/build_dist.py [--root DIR] [--out DIR] [--skip-sync-check]

Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync as _sync  # noqa: E402
import validate as V  # noqa: E402

FIXED_DATE = (1980, 1, 1, 0, 0, 0)
FILE_MODE = 0o100644
DIR_MODE = 0o040755
PERPLEXITY_MAX_BYTES = 10 * 1024 * 1024

# Top-level paths (posix, relative to the repo root) never shipped in the plugin ZIP.
PLUGIN_EXCLUDES = (
    ".git", ".github", "tests", "dev", "evals", "dist", "docs/submission",
    "scripts", "agent-plugin", ".agents", ".claude-plugin/marketplace.json", ".gitignore",
)
# Names skipped everywhere (junk, caches, local test homes).
JUNK_NAMES = {
    ".DS_Store", "Thumbs.db", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "node_modules", ".codex-test", ".claude-test",
}
JUNK_SUFFIXES = (".pyc", ".pyo", ".swp", "~")


class BuildError(RuntimeError):
    pass


def _is_junk(name: str) -> bool:
    return name in JUNK_NAMES or name.endswith(JUNK_SUFFIXES)


def collect(base: Path, excludes: Iterable[str] = ()) -> Tuple[List[str], Dict[str, Path]]:
    """Return (sorted dir arcnames ending in '/', {file arcname: path}) under base."""
    excl = {e.strip("/") for e in excludes}
    dirs: List[str] = []
    files: Dict[str, Path] = {}
    for dirpath, dirnames, filenames in os.walk(base):
        here = Path(dirpath)
        keep = []
        for d in sorted(dirnames):
            r = (here / d).relative_to(base).as_posix()
            if _is_junk(d) or r in excl:
                continue
            if (here / d).is_symlink():
                raise BuildError(f"{here / d}: symlinked directory; hosts reject symlinks")
            keep.append(d)
            dirs.append(r + "/")
        dirnames[:] = keep
        for name in sorted(filenames):
            r = (here / name).relative_to(base).as_posix()
            if _is_junk(name) or r in excl:
                continue
            if (here / name).is_symlink():
                raise BuildError(f"{here / name}: symlink; hosts reject symlinks")
            files[r] = here / name
    return sorted(dirs), files


def write_zip(dest: Path, dirs: Sequence[str], files: Dict[str, Path], prefix: str = "") -> None:
    """Write a deterministic ZIP. ``prefix`` (e.g. 'frameos-clip/') is prepended to every entry."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    entries: List[Tuple[str, Optional[Path]]] = []
    if prefix:
        entries.append((prefix, None))
    entries += [(prefix + d, None) for d in dirs]
    entries += [(prefix + f, p) for f, p in files.items()]
    entries.sort(key=lambda e: e[0])
    with zipfile.ZipFile(tmp, "w") as zf:
        for arcname, path in entries:
            info = zipfile.ZipInfo(arcname, date_time=FIXED_DATE)
            info.create_system = 3  # Unix, so the permission bits below are honoured
            if path is None:
                info.external_attr = (DIR_MODE << 16) | 0x10
                info.compress_type = zipfile.ZIP_STORED
                zf.writestr(info, b"")
            else:
                info.external_attr = FILE_MODE << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                zf.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    os.replace(tmp, dest)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify(path: Path, kind: str, skill: str = "") -> None:
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
    if kind == "claude-ai":
        if f"{skill}/SKILL.md" not in names or any(not n.startswith(f"{skill}/") for n in names):
            raise BuildError(f"{path}: every entry must sit under {skill}/ with {skill}/SKILL.md present")
    elif kind == "perplexity":
        if "SKILL.md" not in names:
            raise BuildError(f"{path}: SKILL.md must be at the ZIP root")
        if path.stat().st_size > PERPLEXITY_MAX_BYTES:
            raise BuildError(f"{path}: larger than 10 MB")
    elif kind == "plugin":
        manifests = [n for n in names if n.endswith(".claude-plugin/plugin.json")]
        if manifests != [".claude-plugin/plugin.json"]:
            raise BuildError(f"{path}: needs exactly one .claude-plugin/plugin.json at the root, found {manifests}")
        leaked = [n for n in names if any(n == e or n.startswith(e + "/") for e in PLUGIN_EXCLUDES)]
        if leaked:
            raise BuildError(f"{path}: excluded paths leaked into the plugin ZIP: {leaked[:5]}")


def build(root: Path, out: Optional[Path] = None, skip_sync_check: bool = False) -> Dict[str, Path]:
    """Build every ZIP; return {label: path}. Raises BuildError on any problem."""
    root = Path(root).resolve()
    out = Path(out).resolve() if out else root / "dist"
    if out == root:
        raise BuildError("--out must not be the repo root")

    version = (root / "VERSION").read_text(encoding="utf-8").strip() if (root / "VERSION").is_file() else ""
    if not V.SEMVER_RE.match(version):
        raise BuildError(f"VERSION {version!r} is not semver")
    if not skip_sync_check:
        result = _sync.sync(root, check=True)
        if not result.ok:
            detail = "\n  ".join([str(d) for d in result.drift] + result.errors)
            raise BuildError(f"sync --check failed; run python3 scripts/sync.py first:\n  {detail}")
    skills = _sync.skill_dirs(root)
    if not skills:
        raise BuildError("no skills found under skills/")

    # Clean only what this script produces.
    for sub in ("claude-ai", "perplexity"):
        if (out / sub).exists():
            shutil.rmtree(out / sub)
    if out.is_dir():
        for old in out.glob("frameos-plugin-*.zip"):
            old.unlink()

    built: Dict[str, Path] = {}
    for sdir in skills:
        if not (sdir / "SKILL.md").is_file():
            raise BuildError(f"{sdir}: no SKILL.md")
        dirs, files = collect(sdir)
        dest = out / "claude-ai" / f"{sdir.name}.zip"
        write_zip(dest, dirs, files, prefix=f"{sdir.name}/")
        _verify(dest, "claude-ai", sdir.name)
        built[f"claude-ai/{sdir.name}"] = dest
        dest = out / "perplexity" / f"{sdir.name}.zip"
        write_zip(dest, dirs, files)
        _verify(dest, "perplexity")
        built[f"perplexity/{sdir.name}"] = dest

    dirs, files = collect(root, PLUGIN_EXCLUDES)
    # The output dir may live inside the repo under another name; never zip it into itself.
    try:
        out_rel = out.relative_to(root).as_posix()
    except ValueError:
        out_rel = None
    if out_rel:
        dirs = [d for d in dirs if not (d == out_rel + "/" or d.startswith(out_rel + "/"))]
        files = {k: v for k, v in files.items() if not k.startswith(out_rel + "/")}
    dest = out / f"frameos-plugin-{version}.zip"
    write_zip(dest, dirs, files)
    _verify(dest, "plugin")
    built["plugin"] = dest

    sums = "".join(f"{sha256(p)}  {p.relative_to(out).as_posix()}\n" for p in sorted(built.values()))
    (out / "SHA256SUMS").write_text(sums, encoding="utf-8")
    return built


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Build FrameOS skill and plugin ZIPs.")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--out", type=Path, default=None, help="output directory (default: <root>/dist)")
    ap.add_argument("--skip-sync-check", action="store_true", help="build even if sync --check reports drift")
    args = ap.parse_args(argv)
    try:
        built = build(args.root, args.out, skip_sync_check=args.skip_sync_check)
    except BuildError as exc:
        print(f"build_dist: {exc}", file=sys.stderr)
        return 1
    for label, path in sorted(built.items()):
        print(f"{path.stat().st_size:>9}  {sha256(path)[:12]}  {path}")
    print(f"build_dist: {len(built)} ZIP(s) written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
