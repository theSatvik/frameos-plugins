#!/usr/bin/env python3
"""Build the distributable ZIPs into dist/.

Layouts:

* ``dist/claude-ai/<skill>.zip`` - the skill FOLDER is the top-level entry
  (``<skill>/SKILL.md``), as claude.ai / Claude Desktop Skills upload expects.
* ``dist/perplexity/<skill>.zip`` - ``SKILL.md`` at the ZIP root, as Perplexity
  Computer's skill upload expects (max 10 MB).
* ``dist/frameos-plugin-<version>.zip`` - the Claude plugin, ``plugins/frameos/``,
  at the ZIP root (exactly one ``.claude-plugin/plugin.json``) for claude.ai /
  Desktop "Upload plugin". It is the same folder the marketplace and the Claude
  Directory install: manifest, icon, ``.mcp.json``, skills, README and licence, with
  none of the repo's docs, scripts, tests or other apps' manifests.
* ``dist/frameos-openai-<version>.zip`` - the OpenAI Plugin Directory upload
  (ChatGPT and Codex). One Codex-format plugin root and nothing else:
  ``.codex-plugin/plugin.json`` (the repo's Codex manifest, pointed at the root
  ``.mcp.json``, plus docs/submission/openai-package.json), a generated
  ``.mcp.json`` (the connector URL and OpenAI's CIMD sign-in block, no
  headers), ``skills/`` (with the setup skill narrowed to ChatGPT and Codex),
  ``assets/`` and ``LICENSE``. No Claude, Cursor or Gemini files.
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
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync as _sync  # noqa: E402
import validate as V  # noqa: E402

FIXED_DATE = (1980, 1, 1, 0, 0, 0)
FILE_MODE = 0o100644
DIR_MODE = 0o040755
PERPLEXITY_MAX_BYTES = 10 * 1024 * 1024

# The Claude plugin folder; the plugin ZIP is exactly its contents.
CLAUDE_PLUGIN_DIR = "plugins/frameos"
# What a Claude plugin may hold (the same rule validate.py enforces on the folder).
PLUGIN_TOP_LEVEL = {".claude-plugin", ".mcp.json", "skills", "README.md", "LICENSE"}
# Names skipped everywhere (junk, caches, local test homes).
JUNK_NAMES = {
    ".DS_Store", "Thumbs.db", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "node_modules", ".codex-test", ".claude-test",
}
JUNK_SUFFIXES = (".pyc", ".pyo", ".swp", "~")

# The OpenAI ZIP copies only these repo paths; its manifest and .mcp.json are generated.
OPENAI_COPY = ("skills", "assets", "LICENSE")
OPENAI_TOP_LEVEL = {".codex-plugin", ".mcp.json", "skills", "assets", "LICENSE"}
# A Plugin Directory install only runs in ChatGPT or Codex, and OpenAI asks skills
# to drop instructions for other products, so the setup skill's per-app guidance
# is narrowed to these two in that ZIP. skills/ itself is unchanged. Each edit is
# skipped when its text is absent; the banned-text check below catches drift.
OPENAI_HOST_SECTIONS = ("Codex", "ChatGPT", "Any other MCP client")
OTHER_APPS = ("Claude", "Cursor", "Gemini", "VS Code", "GitHub Copilot", "Perplexity", "Devin")
OTHER_APPS_LINE = "Steps for every other app are at https://frameos.studio/plugin."
OPENAI_BANNED = (
    ("another AI product's name", re.compile(r"\b(claude|cowork|anthropic)\b", re.I)),
    ("an unfilled placeholder", re.compile(r"__[A-Z][A-Z0-9_]*__")),
    ("an install from GitHub or npm", re.compile(r"\b(?:npx skills add|plugin marketplace add)\b")),
)


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


def write_zip(dest: Path, dirs: Sequence[str], files: Dict[str, Union[Path, bytes]], prefix: str = "") -> None:
    """Write a deterministic ZIP. ``prefix`` (e.g. 'frameos-clip/') is prepended to every entry.

    A file value is a path to read or the bytes to store."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    entries: List[Tuple[str, Optional[Union[Path, bytes]]]] = []
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
                data = path if isinstance(path, bytes) else path.read_bytes()
                zf.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
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
        stray = sorted({n.split("/")[0] for n in names} - PLUGIN_TOP_LEVEL)
        if stray:
            raise BuildError(f"{path}: only {sorted(PLUGIN_TOP_LEVEL)} belong in the plugin ZIP, found {stray}")
    elif kind == "openai":
        manifests = [n for n in names if n.endswith("plugin.json")]
        if manifests != [".codex-plugin/plugin.json"]:
            raise BuildError(f"{path}: needs exactly one plugin manifest, .codex-plugin/plugin.json, found {manifests}")
        stray = sorted({n.split("/")[0] for n in names} - OPENAI_TOP_LEVEL)
        if stray:
            raise BuildError(f"{path}: only {sorted(OPENAI_TOP_LEVEL)} belong in the OpenAI ZIP, found {stray}")
        extra = [n for n in names if n.startswith(".codex-plugin/") and n not in (".codex-plugin/", ".codex-plugin/plugin.json")]
        if extra:
            raise BuildError(f"{path}: .codex-plugin/ may hold only plugin.json, found {extra}")


def _keep_sections(text: str, keep: Sequence[str], note: str) -> str:
    """Keep the preamble and the '## ' sections whose heading starts with one of ``keep``; put ``note`` first."""
    parts = re.split(r"(?m)^(?=## )", text)
    kept = [p for p in parts[1:] if p[3:].startswith(tuple(keep))]
    if len(parts) == 1 or not kept:
        return text
    return parts[0] + note + "\n\n" + "".join(kept)


def openai_skill_text(rel_path: str, text: str) -> str:
    """The ChatGPT and Codex copy of one skills/ file (see OPENAI_HOST_SECTIONS)."""
    if rel_path == "skills/frameos-setup/references/hosts.md":
        text = re.sub(r" \(in Claude Code[^)]*\)", "", text)
        # A directory install comes from OpenAI's own Plugins directory, so this copy
        # never tells an agent to fetch code from GitHub or npm (OpenAI's skill scan
        # flags "install or load code from an untrusted or mutable source").
        text = re.sub(r"(?m)^- Install the plugin:\n(?:  .*\n)+",
                      "- Install the plugin: open the Plugins directory (`/plugins` in the TUI, or Plugins in the app), "
                      "search for FrameOS and add it. Plugin skills and tools load in a new session.\n", text)
        text = re.sub(r"(?m)^- Skills only, for agents that read SKILL\.md folders: .*\n", "", text)
        return _keep_sections(text, OPENAI_HOST_SECTIONS, "This copy covers ChatGPT and Codex. " + OTHER_APPS_LINE)
    if rel_path == "skills/frameos-setup/SKILL.md":
        text = re.sub(r"(?m)^1\. Identify the app: .*$",
                      "1. Identify the app: ChatGPT, Codex or another MCP client. If unclear, ask once.", text)
        text = re.sub(r"(?m)^If FrameOS was added by hand rather than as the plugin, .*$",
                      "Full install steps, sign-out commands and app limits are in [hosts](references/hosts.md). "
                      + OTHER_APPS_LINE, text)
        # Table rows for other apps (reconnect steps, app-specific errors).
        return re.sub(r"(?m)^\| (?:" + "|".join(map(re.escape, OTHER_APPS)) + r").*\n", "", text)
    if rel_path == "skills/frameos-clip/references/workflow-details.md":
        text = re.sub(r"(?m)^(\| Has a shell \| )[^|]*\|", r"\1Codex, or any agent with a terminal |", text)
        return re.sub(r"(?m)^(\| Chat only \| )[^|]*\|", r"\1ChatGPT on the web, desktop or mobile |", text)
    return text


def openai_mcp() -> Dict[str, object]:
    """The OpenAI ZIP's .mcp.json: the connector and OpenAI's sign-in block, and no headers."""
    return {"mcpServers": {V.SERVER_KEY: {"url": V.MCP_URL, "extensions": {"com.openai": {"auth": V.OPENAI_MCP_AUTH}}}}}


def _json_bytes(data: object) -> bytes:
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def openai_package(root: Path, version: str) -> Tuple[Dict[str, object], List[str]]:
    """Return (the OpenAI ZIP's Codex manifest, owner TODOs still open)."""
    try:
        codex = V.load_json_strict(root / ".codex-plugin" / "plugin.json")
        package = V.load_json_strict(root / V.OPENAI_PACKAGE)
    except (OSError, ValueError) as exc:
        raise BuildError(f"cannot build the OpenAI ZIP: {exc}") from exc
    return V.merge_openai_manifest(codex, package, version)


def build_openai(root: Path, dest: Path, version: str) -> Path:
    """Write the OpenAI Plugin Directory ZIP to ``dest``."""
    manifest, _ = openai_package(root, version)
    files: Dict[str, Union[Path, bytes]] = {
        ".codex-plugin/plugin.json": _json_bytes(manifest),
        ".mcp.json": _json_bytes(openai_mcp()),
    }
    for name in OPENAI_COPY:
        src = root / name
        if src.is_file():
            files[name] = src
            continue
        if not src.is_dir():
            raise BuildError(f"{name} is missing; the OpenAI ZIP needs it")
        for arc, path in collect(src)[1].items():
            rel_path = f"{name}/{arc}"
            if name == "skills" and path.suffix == ".md":
                files[rel_path] = openai_skill_text(rel_path, path.read_text(encoding="utf-8")).encode("utf-8")
            else:
                files[rel_path] = path
    # Every referenced file must ship, and nothing may carry another product's name,
    # a placeholder client ID, a credential or a header.
    itf = manifest.get("interface") or {}
    refs = [itf.get(k) for k in ("logo", "composerIcon", "logoDark", "composerIconDark") if itf.get(k)]
    refs.append((manifest.get("extensions") or {}).get("com.openai", {}).get("onboardingSkill"))
    for ref in filter(None, refs):
        if str(ref)[2:] not in files:
            raise BuildError(f"the OpenAI manifest references {ref}, which is not in the ZIP")
    for arc, value in sorted(files.items()):
        data = value if isinstance(value, bytes) else value.read_bytes()
        if Path(arc).suffix.lower() in V.IMAGE_EXTS - {".svg"}:
            continue
        text = data.decode("utf-8", errors="replace")
        for label, pattern in OPENAI_BANNED + V.SECRET_PATTERNS:
            m = pattern.search(text)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                raise BuildError(f"OpenAI ZIP {arc}:{line} contains {label} ({m.group(0)!r}); fix openai_skill_text or the source")
    dirs = sorted({"/".join(arc.split("/")[:i]) + "/" for arc in files for i in range(1, arc.count("/") + 1)})
    write_zip(dest, dirs, files)
    _verify(dest, "openai")
    return dest


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
        for pattern in ("frameos-plugin-*.zip", "frameos-openai-*.zip"):
            for old in out.glob(pattern):
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

    claude_dir = root / CLAUDE_PLUGIN_DIR
    if not (claude_dir / ".claude-plugin" / "plugin.json").is_file():
        raise BuildError(f"{CLAUDE_PLUGIN_DIR}/.claude-plugin/plugin.json is missing; the plugin ZIP is built from that folder")
    dirs, files = collect(claude_dir)
    dest = out / f"frameos-plugin-{version}.zip"
    write_zip(dest, dirs, files)
    _verify(dest, "plugin")
    built["plugin"] = dest
    built["openai"] = build_openai(root, out / f"frameos-openai-{version}.zip", version)

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
    version = (args.root / "VERSION").read_text(encoding="utf-8").strip()
    for todo in openai_package(args.root.resolve(), version)[1]:
        print(f"TODO(owner) before uploading {built['openai'].name}: {todo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
