#!/usr/bin/env python3
"""Validate every invariant of the FrameOS plugin repo.

Usage::

    python3 scripts/validate.py                 # validate this checkout
    python3 scripts/validate.py --root DIR      # validate another copy (tests)
    python3 scripts/validate.py --strict        # warnings fail too

Exit codes: 0 = no errors (warnings are printed), 1 = errors (or warnings with
--strict), 2 = the validator itself could not run.

Python 3.9+, standard library only. PyYAML / tomllib are used for extra checks
when importable, never required.

What is checked (see the check_* functions):
  * every manifest parses (no duplicate keys) and names the plugin ``frameos``;
  * one version everywhere: VERSION, all manifests and marketplace entries,
    and every ``X-FrameOS-Plugin-Version`` header; VERSION is semver;
  * MCP configs: endpoint https://frameos.studio/mcp, oauth_resource == url,
    exactly one server named ``frameos`` per host config, right transport;
  * host-specific manifest rules (Agent Plugins keys, Cursor schema keys,
    Codex ``interface`` fields and limits, Gemini extension, icons);
  * skills: portable frontmatter, body limits, ground-rules block identical to
    scripts/ground_rules.md, relative links resolve inside the skill, tool names
    exist in the MCP snapshot, ``agents/openai.yaml`` metadata, and the
    ``agent-plugin/skills`` mirror (via scripts/sync.py);
  * Gemini commands, README/LICENSE, evals tool references, workflow pinning;
  * forbidden files (root bin/, hooks, CLAUDE.md, AGENTS.md, .DS_Store, big
    files, secrets, the wrong contact address, prices and discount codes).
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import struct
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Set, Tuple
from urllib.parse import unquote

sys.dont_write_bytecode = True  # keep scripts/ free of __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync as _sync  # noqa: E402  (sibling module)

try:  # optional extra syntax check
    import yaml as _pyyaml  # type: ignore
except Exception:  # pragma: no cover - depends on the environment
    _pyyaml = None

try:  # Python 3.11+
    import tomllib as _toml  # type: ignore
except Exception:  # pragma: no cover
    try:
        import tomli as _toml  # type: ignore
    except Exception:
        _toml = None

# --------------------------------------------------------------------------
# Identity and constants
# --------------------------------------------------------------------------

PLUGIN_NAME = "frameos"
SERVER_KEY = "frameos"
MCP_URL = "https://frameos.studio/mcp"
OAUTH_SCOPE = "frameos:mcp"
VERSION_HEADER = "X-FrameOS-Plugin-Version"
SNAPSHOT = "tests/fixtures/mcp-snapshot.json"

EXPECTED_SKILLS = (
    "frameos-setup",
    "frameos-clip",
    "frameos-captions",
    "frameos-find-moments",
    "frameos-thumbnails",
    "frameos-publish",
    "frameos-library",
    "frameos-repurpose",
)

# Gemini CLI commands: commands/frameos/<cmd>.toml -> /frameos:<cmd>
GEMINI_COMMANDS = {
    "setup": "frameos-setup",
    "clip": "frameos-clip",
    "captions": "frameos-captions",
    "moments": "frameos-find-moments",
    "thumbnails": "frameos-thumbnails",
    "publish": "frameos-publish",
    "library": "frameos-library",
    "repurpose": "frameos-repurpose",
}

MANIFESTS = (
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".codex-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
    ".mcp.json",
    ".cursor-plugin/plugin.json",
    "gemini-extension.json",
    "agent-plugin/plugin.json",
    "agent-plugin/mcp.json",
    ".github/plugin/marketplace.json",
)

# A path element that is a dict selects the list item whose fields match it.
JsonPath = Tuple[Any, ...]
_SEL = {"name": PLUGIN_NAME}

# Every place the plugin version must appear (bump_version.py rewrites these).
VERSION_SITES: Tuple[Tuple[str, JsonPath], ...] = (
    (".claude-plugin/plugin.json", ("version",)),
    (".claude-plugin/marketplace.json", ("plugins", _SEL, "version")),
    (".codex-plugin/plugin.json", ("version",)),
    (".cursor-plugin/plugin.json", ("version",)),
    ("gemini-extension.json", ("version",)),
    ("agent-plugin/plugin.json", ("version",)),
    (".github/plugin/marketplace.json", ("plugins", _SEL, "version")),
    (".mcp.json", ("mcpServers", SERVER_KEY, "headers", VERSION_HEADER)),
    (".mcp.json", ("mcpServers", SERVER_KEY, "http_headers", VERSION_HEADER)),
    (".cursor-plugin/plugin.json", ("mcpServers", SERVER_KEY, "headers", VERSION_HEADER)),
    ("gemini-extension.json", ("mcpServers", SERVER_KEY, "headers", VERSION_HEADER)),
    ("agent-plugin/mcp.json", ("mcpServers", SERVER_KEY, "headers", VERSION_HEADER)),
)

SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)

AGENT_PLUGIN_KEYS = {
    "$schema", "name", "version", "description", "author", "homepage",
    "repository", "license", "keywords", "extensions",
}
AGENT_MCP_KEYS = {"$schema", "mcpServers"}
CURSOR_KEYS = {
    "name", "displayName", "description", "version", "minClientVersions", "author",
    "publisher", "homepage", "repository", "license", "logo", "keywords", "category",
    "tags", "commands", "agents", "skills", "rules", "hooks", "variables", "mcpServers",
}
CODEX_INTERFACE_REQUIRED = (
    "displayName", "shortDescription", "longDescription", "developerName", "category",
    "capabilities", "websiteURL", "supportURL", "privacyPolicyURL", "termsOfServiceURL",
    "defaultPrompt", "composerIcon", "logo",
)
CODEX_CATEGORIES = {
    "Productivity", "Creativity", "Developer Tools", "Business & Operations",
    "Data & Analytics", "Communication", "Education & Research", "Security",
    "Finance", "Healthcare", "Travel", "Entertainment", "Other",
}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico"}

FRONTMATTER_KEYS = {"name", "description", "license"}
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SKILL_MAX_LINES = 500
SKILL_TARGET_LINES = 250
REFERENCE_TARGET_LINES = 200
GEMINI_MD_MAX_LINES = 60
MAX_FILE_BYTES = 256 * 1024

# Identifiers that look like tool names (snake_case) but are not tools: response
# fields, job states, failure codes, config keys. Snapshot parameter names are
# added automatically. Add to this list only for real FrameOS identifiers.
NON_TOOL_IDENTIFIERS = frozenset({
    # whoami / get_usage response fields
    "user_id", "organization_id", "organization_name", "paid_credits", "trial_credits",
    "trial_credits_expires_at", "trial_credits_expired", "has_more",
    # submit / jobs / projects
    "already_running", "eta_seconds", "eta_remaining_seconds", "source_duration_seconds",
    "started_at_ms",
    "clips_count", "clip_count", "created_at", "credits_charged_minutes",
    # uploads and transcripts
    "upload_url", "next_offset", "speaker_id", "speaker_label", "diarized_speaker",
    # clips
    "duplicated_from",
    # job failure codes (core/failure_codes.py), shown as "(code)" in job messages
    "source_too_short", "no_clips_found", "no_publishable_clips", "render_failed",
    "source_bot_check", "source_forbidden", "source_rate_limited", "source_download_failed",
    "source_download_timeout", "download_failed", "direct_download_failed",
    "google_drive_failed", "cookie_fetch_failed", "dns_failed", "empty_download",
    "no_audio_track", "not_a_video", "unreadable_source",
    # social
    "share_to_feed", "w_member_social",
    # agents/openai.yaml and host MCP config keys
    "display_name", "short_description", "default_prompt", "allow_implicit_invocation",
    "streamable_http", "oauth_resource", "http_headers", "mcp_servers",
})

SNAKE_RE = re.compile(r"^[a-z]+(?:_[a-z]+)+$")
CALL_IN_SPAN_RE = re.compile(r"^([a-z]+(?:_[a-z]+)+)\s*\(")
DOTTED_IN_SPAN_RE = re.compile(r"^([a-z]+(?:_[a-z]+)+)\.[A-Za-z_]")
CALL_IN_TEXT_RE = re.compile(r"(?<![\w.$/-])([a-z]+(?:_[a-z]+)+)\(")
CODE_SPAN_RE = re.compile(r"(`+)(.+?)\1")
FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
LINK_RE = re.compile(r"!?\[(?:[^\]\\]|\\.)*\]\(\s*<?([^)\s>]+)>?(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)")
REF_DEF_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s+.*)?$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
NON_ASCII_PUNCT = {
    "—": "em dash", "–": "en dash", "‘": "curly quote", "’": "curly quote",
    "“": "curly quote", "”": "curly quote", "…": "ellipsis", " ": "no-break space",
}

# Built from pieces so this file never matches its own patterns.
_BEGIN = "-" * 5 + "BEGIN"
SECRET_PATTERNS = (
    ("OpenAI/Anthropic-style secret key", re.compile(r"\bsk-(?:ant-|proj-|live-)?[A-Za-z0-9_\-]{20,}")),
    ("Stripe-style live key", re.compile(r"\b[sp]k_" + "live" + r"_[A-Za-z0-9]{10,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_" + "pat" + r"_[A-Za-z0-9_]{20,}")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("PEM block (private key or certificate)", re.compile(re.escape(_BEGIN))),
)
FORBIDDEN_EMAIL = "hello" + "@" + "frameos.studio"
NEGATION_RE = re.compile(r"\b(never|not|don't|do not)\b", re.I)
PRICE_RE = re.compile(r"(?<![\w$\\])[$€£₹]\s?\d[\d,]*(?:\.\d+)?(?=$|[\s/).,;:!?])")
DISCOUNT_CODE_RE = re.compile(r"\bFRAMEOS\d{2,}\b")
HEADER_MENTION_RE = re.compile(re.escape(VERSION_HEADER) + r"""["']?\s*[:=]\s*["']?(\d+\.\d+\.\d+[0-9A-Za-z.+-]*)""")
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*['\"]?([^\s#'\"]+)")

# Walked directories that never ship (build output, caches, local test homes).
WALK_EXCLUDED_DIRS = {
    ".git", "dist", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".codex-test", ".claude-test",
}
WALK_EXCLUDED_PATHS = {"evals/results"}

# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


class Report:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def error(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")

    @property
    def ok(self) -> bool:
        return not self.errors


# --------------------------------------------------------------------------
# Generic helpers
# --------------------------------------------------------------------------


class DuplicateKeyError(ValueError):
    pass


def _no_dupes(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise DuplicateKeyError(f"duplicate key {k!r}")
        out[k] = v
    return out


def load_json_strict(path: Path) -> Any:
    return json.loads(path.read_bytes().decode("utf-8"), object_pairs_hook=_no_dupes)


def get_path(obj: Any, path: JsonPath) -> Tuple[bool, Any]:
    cur = obj
    for part in path:
        if isinstance(part, dict):
            if not isinstance(cur, list):
                return False, None
            match = [x for x in cur if isinstance(x, dict) and all(x.get(k) == v for k, v in part.items())]
            if len(match) != 1:
                return False, None
            cur = match[0]
        else:
            if not isinstance(cur, dict) or part not in cur:
                return False, None
            cur = cur[part]
    return True, cur


def set_path(obj: Any, path: JsonPath, value: Any) -> bool:
    found, parent = get_path(obj, path[:-1])
    if not found or not isinstance(parent, dict) or path[-1] not in parent:
        return False
    parent[path[-1]] = value
    return True


def fmt_path(path: JsonPath) -> str:
    out = []
    for p in path:
        if isinstance(p, dict):
            out.append("[" + ",".join(f"{k}={v}" for k, v in p.items()) + "]")
        else:
            out.append(("." if out else "") + str(p))
    return "".join(out)


def find_key_values(obj: Any, key: str, prefix: str = "") -> Iterator[Tuple[str, Any]]:
    """Yield (path, value) for every occurrence of ``key`` at any depth."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            here = f"{prefix}.{k}" if prefix else k
            if k == key:
                yield here, v
            yield from find_key_values(v, key, here)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from find_key_values(v, key, f"{prefix}[{i}]")


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def iter_repo_files(root: Path) -> Iterator[Path]:
    """Every file that could ship: skips .git, build output and caches."""
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        keep = []
        for d in sorted(dirnames):
            r = rel(root, here / d)
            if d in WALK_EXCLUDED_DIRS or r in WALK_EXCLUDED_PATHS:
                continue
            keep.append(d)
        dirnames[:] = keep
        for name in sorted(filenames):
            yield here / name


def read_text_or_none(path: Path) -> Optional[str]:
    try:
        return path.read_bytes().decode("utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def png_size(path: Path) -> Optional[Tuple[int, int]]:
    try:
        with path.open("rb") as fh:
            head = fh.read(24)
    except OSError:
        return None
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def is_https(url: Any) -> bool:
    return isinstance(url, str) and url.startswith("https://") and len(url) > len("https://")


def semver_key(v: str) -> Tuple[int, int, int, int]:
    m = SEMVER_RE.match(v)
    if not m:
        raise ValueError(v)
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), 0 if m.group(4) else 1


# --------------------------------------------------------------------------
# Minimal YAML subset (frontmatter and agents/openai.yaml) - no PyYAML needed
# --------------------------------------------------------------------------


class MiniYAMLError(ValueError):
    def __init__(self, lineno: int, msg: str) -> None:
        super().__init__(f"line {lineno}: {msg}")
        self.lineno = lineno


class PlainStr(str):
    """A string that was written as an unquoted YAML plain scalar."""


_DQ_ESC = {
    '"': '"', "\\": "\\", "/": "/", "n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f",
    "0": "\0", " ": " ", "e": "\x1b", "a": "\a", "v": "\v", "N": "\x85", "_": "\xa0",
    "L": " ", "P": " ",
}
_INT_RE = re.compile(r"^[-+]?(0|[1-9]\d*)$")
_FLOAT_RE = re.compile(r"^[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?$")


def _parse_dq(t: str, lineno: int) -> Tuple[str, int]:
    """Parse a double-quoted scalar starting at t[0]; return (value, index of closing quote)."""
    out: List[str] = []
    i = 1
    while i < len(t):
        ch = t[i]
        if ch == "\\":
            nxt = t[i + 1] if i + 1 < len(t) else ""
            if nxt in _DQ_ESC:
                out.append(_DQ_ESC[nxt])
                i += 2
            elif nxt in ("x", "u", "U"):
                width = {"x": 2, "u": 4, "U": 8}[nxt]
                hexpart = t[i + 2:i + 2 + width]
                if len(hexpart) != width or not re.fullmatch(r"[0-9A-Fa-f]+", hexpart):
                    raise MiniYAMLError(lineno, f"bad \\{nxt} escape in double-quoted string")
                out.append(chr(int(hexpart, 16)))
                i += 2 + width
            else:
                raise MiniYAMLError(lineno, f"unknown escape \\{nxt} in double-quoted string")
        elif ch == '"':
            return "".join(out), i
        else:
            out.append(ch)
            i += 1
    raise MiniYAMLError(lineno, "unterminated double-quoted string")


def _parse_sq(t: str, lineno: int) -> Tuple[str, int]:
    out: List[str] = []
    i = 1
    while i < len(t):
        if t[i] == "'":
            if i + 1 < len(t) and t[i + 1] == "'":
                out.append("'")
                i += 2
                continue
            return "".join(out), i
        out.append(t[i])
        i += 1
    raise MiniYAMLError(lineno, "unterminated single-quoted string")


def _dq_closed(t: str) -> bool:
    try:
        _parse_dq(t, 0)
        return True
    except MiniYAMLError:
        return False


def _strip_comment(s: str, notes: Optional[List[str]] = None, lineno: int = 0) -> str:
    in_s = in_d = False
    i = 0
    while i < len(s):
        ch = s[i]
        if in_d:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_d = False
        elif in_s:
            if ch == "'":
                in_s = False
        else:
            if ch == '"' and (i == 0 or s[i - 1] in " \t:-[,{"):
                in_d = True
            elif ch == "'" and (i == 0 or s[i - 1] in " \t:-[,{"):
                in_s = True
            elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
                if notes is not None and s[:i].strip() and not s[:i].rstrip().endswith(":"):
                    notes.append(f"line {lineno}: text after ' #' is a YAML comment and is dropped; quote the value")
                return s[:i].rstrip()
        i += 1
    return s.rstrip()


def _split_key(content: str) -> Optional[Tuple[str, str]]:
    """Split 'key: value' (quotes respected). None if the line is not a mapping entry."""
    in_s = in_d = False
    i = 0
    while i < len(content):
        ch = content[i]
        if in_d:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_d = False
        elif in_s:
            if ch == "'":
                in_s = False
        else:
            if ch == '"' and i == 0:
                in_d = True
            elif ch == "'" and i == 0:
                in_s = True
            elif ch == ":" and (i + 1 == len(content) or content[i + 1] in " \t"):
                key = content[:i].strip()
                if not key:
                    return None
                if key[0] == '"':
                    key = _parse_dq(key, 0)[0]
                elif key[0] == "'":
                    key = _parse_sq(key, 0)[0]
                return key, content[i + 1:].strip()
            elif ch in "[{" and i == 0:
                return None
        i += 1
    return None


class MiniYAML:
    """Block mappings, block sequences, scalars, simple flow lists, block scalars."""

    def __init__(self, text: str) -> None:
        self.raw = text.replace("\r\n", "\n").split("\n")
        self.n = len(self.raw)
        self.notes: List[str] = []
        for idx, line in enumerate(self.raw):
            lead = line[: len(line) - len(line.lstrip(" \t"))]
            if "\t" in lead and line.strip():
                raise MiniYAMLError(idx + 1, "tab used for indentation")

    def _skip(self, i: int) -> int:
        while i < self.n:
            s = self.raw[i].strip()
            if s and not s.startswith("#"):
                return i
            i += 1
        return i

    def _indent(self, i: int) -> int:
        return len(self.raw[i]) - len(self.raw[i].lstrip(" "))

    def _content(self, i: int) -> str:
        return _strip_comment(self.raw[i].strip(), self.notes, i + 1)

    @staticmethod
    def _is_seq(c: str) -> bool:
        return c == "-" or c.startswith("- ")

    def parse(self) -> Any:
        i = self._skip(0)
        if i >= self.n:
            return None
        if self.raw[i].strip() == "---":
            i = self._skip(i + 1)
            if i >= self.n:
                return None
        val, i = self._block(i, self._indent(i))
        i = self._skip(i)
        if i < self.n and self.raw[i].strip() not in ("---", "..."):
            raise MiniYAMLError(i + 1, "unexpected content (check the indentation)")
        return val

    def _block(self, i: int, indent: int) -> Tuple[Any, int]:
        c = self._content(i)
        if self._is_seq(c):
            return self._seq(i, indent)
        if _split_key(c) is None:
            val = self._scalar(c, i + 1)
            return val, i + 1
        return self._map(i, indent)

    def _map(self, i: int, indent: int) -> Tuple[Dict[str, Any], int]:
        out: Dict[str, Any] = {}
        while True:
            i = self._skip(i)
            if i >= self.n:
                break
            ind = self._indent(i)
            if ind < indent:
                break
            if ind > indent:
                raise MiniYAMLError(i + 1, "unexpected indentation")
            c = self._content(i)
            if c in ("---", "..."):
                break
            if self._is_seq(c):
                break
            kv = _split_key(c)
            if kv is None:
                raise MiniYAMLError(i + 1, f"expected 'key: value', got {c!r}")
            key, rest = kv
            if key in out:
                raise MiniYAMLError(i + 1, f"duplicate key {key!r}")
            out[key], i = self._value(i, indent, rest)
        return out, i

    def _seq(self, i: int, indent: int) -> Tuple[List[Any], int]:
        out: List[Any] = []
        while True:
            i = self._skip(i)
            if i >= self.n:
                break
            ind = self._indent(i)
            if ind < indent:
                break
            if ind > indent:
                raise MiniYAMLError(i + 1, "unexpected indentation in list")
            c = self._content(i)
            if not self._is_seq(c):
                break
            rest = c[1:].lstrip(" ")
            if rest == "":
                val, i = self._value(i, indent, "")
            elif _split_key(rest) is not None:
                s = self.raw[i].lstrip(" ")
                k = 1
                while k < len(s) and s[k] == " ":
                    k += 1
                virt = ind + k
                self.raw[i] = " " * virt + s[k:]
                val, i = self._map(i, virt)
            else:
                val, i = self._value(i, indent, rest)
            out.append(val)
        return out, i

    def _value(self, i: int, indent: int, rest: str) -> Tuple[Any, int]:
        lineno = i + 1
        if rest == "":
            j = self._skip(i + 1)
            if j < self.n:
                ind = self._indent(j)
                c = self._content(j)
                if ind > indent or (ind == indent and self._is_seq(c)):
                    return self._block(j, ind)
            return None, i + 1
        if rest[0] in "|>":
            return self._block_scalar(i, indent, rest)
        if rest[0] == '"' and not _dq_closed(rest):
            parts = [rest]
            j = i + 1
            while j < self.n and not _dq_closed(" ".join(parts)):
                parts.append(self.raw[j].strip())
                j += 1
            return self._scalar(" ".join(parts), lineno), j
        val = self._scalar(rest, lineno)
        j = i + 1
        if isinstance(val, PlainStr):
            parts = [str(val)]
            k = self._skip(j)
            while k < self.n and self._indent(k) > indent:
                cont = self._content(k)
                if ": " in cont or cont.endswith(":"):
                    raise MiniYAMLError(k + 1, "':' followed by a space inside an unquoted value; quote the value")
                parts.append(cont)
                j = k + 1
                k = self._skip(j)
            if len(parts) > 1:
                val = PlainStr(" ".join(parts))
        return val, j

    def _block_scalar(self, i: int, indent: int, header: str) -> Tuple[str, int]:
        style = header[0]
        chomp = "strip" if "-" in header else ("keep" if "+" in header else "clip")
        lines: List[str] = []
        j = i + 1
        block_indent: Optional[int] = None
        while j < self.n:
            raw = self.raw[j]
            if raw.strip() == "":
                lines.append("")
                j += 1
                continue
            ind = self._indent(j)
            if ind <= indent or (block_indent is not None and ind < block_indent):
                break
            if block_indent is None:
                block_indent = ind
            lines.append(raw[block_indent:])
            j += 1
        trailing = 0
        while lines and lines[-1] == "":
            lines.pop()
            trailing += 1
        if style == "|":
            text = "\n".join(lines)
        else:
            text = ""
            for idx, ln in enumerate(lines):
                if idx == 0:
                    text = ln
                elif ln == "":
                    text += "\n"
                elif lines[idx - 1] == "":
                    text += ln
                else:
                    text += " " + ln
        if chomp == "clip" and lines:
            text += "\n"
        elif chomp == "keep":
            text += "\n" * (trailing + (1 if lines else 0))
        return text, j

    def _scalar(self, text: str, lineno: int) -> Any:
        t = text.strip()
        if t == "":
            return None
        if t[0] == '"':
            val, end = _parse_dq(t, lineno)
            if t[end + 1:].strip():
                raise MiniYAMLError(lineno, "unexpected text after closing double quote")
            return val
        if t[0] == "'":
            val, end = _parse_sq(t, lineno)
            if t[end + 1:].strip():
                raise MiniYAMLError(lineno, "unexpected text after closing single quote")
            return val
        if t[0] == "[":
            if not t.endswith("]"):
                raise MiniYAMLError(lineno, "unterminated flow list")
            inner = t[1:-1].strip()
            if not inner:
                return []
            items, buf, q = [], "", ""
            for ch in inner:
                if q:
                    buf += ch
                    if ch == q:
                        q = ""
                elif ch in "\"'":
                    q = ch
                    buf += ch
                elif ch == ",":
                    items.append(buf)
                    buf = ""
                elif ch in "[]{}":
                    raise MiniYAMLError(lineno, "nested flow collections are not supported here")
                else:
                    buf += ch
            items.append(buf)
            return [self._scalar(x, lineno) for x in items]
        if t[0] == "{":
            if t.replace(" ", "") == "{}":
                return {}
            raise MiniYAMLError(lineno, "flow mappings are not supported here; use block style")
        if t[0] in "&*!%@`|>":
            raise MiniYAMLError(lineno, f"an unquoted value cannot start with {t[0]!r}; quote the value")
        if t[0] in "-?:" and (len(t) == 1 or t[1] in " \t"):
            raise MiniYAMLError(lineno, f"an unquoted value cannot start with {t[:2]!r}; quote the value")
        if ": " in t or t.endswith(":"):
            raise MiniYAMLError(lineno, "':' followed by a space inside an unquoted value; quote the value")
        if t in ("true", "True", "TRUE"):
            return True
        if t in ("false", "False", "FALSE"):
            return False
        if t in ("null", "Null", "NULL", "~"):
            return None
        if _INT_RE.match(t):
            return int(t)
        if _FLOAT_RE.match(t):
            return float(t)
        return PlainStr(t)


def parse_mini_yaml(text: str) -> Tuple[Any, List[str]]:
    """Parse a YAML document with the supported subset; return (value, notes)."""
    y = MiniYAML(text)
    return y.parse(), y.notes


def split_frontmatter(text: str) -> Tuple[Optional[str], str, int]:
    """Return (frontmatter_text, body, body_first_lineno). Frontmatter None if absent."""
    if text.startswith("﻿"):
        text = text[1:]
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != "---":
        return None, text, 1
    for idx in range(1, len(lines)):
        if lines[idx].rstrip() == "---":
            return "\n".join(lines[1:idx]), "\n".join(lines[idx + 1:]), idx + 2
    return None, text, 1


# --------------------------------------------------------------------------
# Snapshot-derived vocabulary
# --------------------------------------------------------------------------


def _schema_param_names(schema: Any, out: Set[str]) -> None:
    if isinstance(schema, dict):
        props = schema.get("properties")
        if isinstance(props, dict):
            for k, v in props.items():
                out.add(k)
                _schema_param_names(v, out)
        for key in ("anyOf", "oneOf", "allOf"):
            for alt in schema.get(key, []) or []:
                _schema_param_names(alt, out)
        if "items" in schema:
            _schema_param_names(schema["items"], out)
        for defs in ("$defs", "definitions"):
            for v in (schema.get(defs) or {}).values():
                _schema_param_names(v, out)


def load_snapshot_vocab(root: Path, report: Report) -> Tuple[Set[str], Set[str]]:
    """Return (tool_names, parameter_names) from the MCP snapshot."""
    path = root / SNAPSHOT
    if not path.is_file():
        report.error(SNAPSHOT, "missing; tool names cannot be checked")
        return set(), set()
    try:
        data = load_json_strict(path)
    except (ValueError, OSError) as exc:
        report.error(SNAPSHOT, f"does not parse: {exc}")
        return set(), set()
    tools = (data.get("tools_list") or {}).get("tools") if isinstance(data, dict) else None
    if not isinstance(tools, list) or not tools:
        report.error(SNAPSHOT, "expected tools_list.tools to be a non-empty list")
        return set(), set()
    names: Set[str] = set()
    params: Set[str] = set()
    for t in tools:
        if isinstance(t, dict) and isinstance(t.get("name"), str):
            names.add(t["name"])
            _schema_param_names(t.get("inputSchema"), params)
    if len(names) != 27:
        report.warn(SNAPSHOT, f"expected 27 tools, found {len(names)} (update docs and skills if the server changed)")
    return names, params


# --------------------------------------------------------------------------
# Tool-name checks in markdown/prose
# --------------------------------------------------------------------------


def _suggest(name: str, tools: Set[str]) -> str:
    close = difflib.get_close_matches(name, sorted(tools), n=3, cutoff=0.6)
    return f" Did you mean {', '.join('`' + c + '`' for c in close)}?" if close else ""


def check_tool_tokens(
    report: Report, where: str, text: str, tools: Set[str], allowed: Set[str], first_lineno: int = 1
) -> None:
    """Flag snake_case identifiers used like tools that are not FrameOS tools."""
    if not tools:
        return
    in_fence: Optional[str] = None
    for offset, line in enumerate(text.split("\n")):
        lineno = first_lineno + offset
        fm = FENCE_RE.match(line)
        if fm:
            marker = fm.group(1)[0] * 3
            if in_fence is None:
                in_fence = marker
                continue
            if marker == in_fence:
                in_fence = None
                continue
        if "mcp__" in line:
            report.error(f"{where}:{lineno}", "use bare tool names in backticks (e.g. `submit_video`), never host-prefixed mcp__ names")
        if in_fence is not None:
            for m in CALL_IN_TEXT_RE.finditer(line):
                name = m.group(1)
                if name not in tools:
                    report.error(
                        f"{where}:{lineno}",
                        f"`{name}(...)` is called like a tool but is not one of the {len(tools)} FrameOS MCP tools.{_suggest(name, tools)}",
                    )
            continue
        spans = list(CODE_SPAN_RE.finditer(line))
        for m in spans:
            content = m.group(2).strip()
            if SNAKE_RE.match(content):
                if content not in tools and content not in allowed:
                    report.error(
                        f"{where}:{lineno}",
                        f"`{content}` looks like a tool name but is not one of the {len(tools)} FrameOS MCP tools "
                        f"(tests/fixtures/mcp-snapshot.json).{_suggest(content, tools)} If it is a field or parameter "
                        "name, add it to NON_TOOL_IDENTIFIERS in scripts/validate.py; otherwise write it as prose.",
                    )
                continue
            cm = CALL_IN_SPAN_RE.match(content)
            if cm and cm.group(1) not in tools:
                report.error(
                    f"{where}:{lineno}",
                    f"`{content}` calls `{cm.group(1)}`, which is not a FrameOS MCP tool.{_suggest(cm.group(1), tools)}",
                )
                continue
            dm = DOTTED_IN_SPAN_RE.match(content)
            if dm and dm.group(1) not in tools and dm.group(1) not in allowed:
                report.error(
                    f"{where}:{lineno}",
                    f"`{content}` starts with `{dm.group(1)}`, which is not a FrameOS MCP tool or known field.{_suggest(dm.group(1), tools)}",
                )
        prose = CODE_SPAN_RE.sub(" ", line)
        for m in CALL_IN_TEXT_RE.finditer(prose):
            name = m.group(1)
            if name not in tools:
                report.error(
                    f"{where}:{lineno}",
                    f"'{name}(' reads like a tool call but `{name}` is not a FrameOS MCP tool.{_suggest(name, tools)}",
                )


def _strip_code(text: str) -> str:
    """Blank out fenced code blocks and inline code spans (keeps line count)."""
    out: List[str] = []
    in_fence: Optional[str] = None
    for line in text.split("\n"):
        fm = FENCE_RE.match(line)
        if fm:
            marker = fm.group(1)[0] * 3
            if in_fence is None:
                in_fence = marker
            elif marker == in_fence:
                in_fence = None
            out.append("")
            continue
        out.append("" if in_fence else CODE_SPAN_RE.sub(" ", line))
    return "\n".join(out)


def check_relative_links(report: Report, root: Path, md_path: Path, text: str, boundary: Path) -> Set[Path]:
    """Every relative link must resolve to an existing file inside ``boundary``."""
    targets: Set[Path] = set()
    where = rel(root, md_path)
    clean = _strip_code(text)
    for lineno, line in enumerate(clean.split("\n"), start=1):
        found = [m.group(1) for m in LINK_RE.finditer(line)]
        rm = REF_DEF_RE.match(line)
        if rm:
            found.append(rm.group(1))
        for target in found:
            if SCHEME_RE.match(target) or target.startswith("#") or target.startswith("//"):
                continue
            if target.startswith("/"):
                report.error(f"{where}:{lineno}", f"absolute link '{target}' - use a path relative to the file")
                continue
            path_part = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not path_part:
                continue
            resolved = (md_path.parent / path_part).resolve()
            try:
                resolved.relative_to(boundary.resolve())
            except ValueError:
                report.error(f"{where}:{lineno}", f"link '{target}' points outside {rel(root, boundary)}/ (skills must be self-contained)")
                continue
            if not resolved.exists():
                report.error(f"{where}:{lineno}", f"broken relative link '{target}'")
                continue
            targets.add(resolved)
    return targets


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------


class Ctx:
    def __init__(self, root: Path, report: Report) -> None:
        self.root = root
        self.report = report
        self.manifests: Dict[str, Any] = {}
        self.version: Optional[str] = None
        self.tools: Set[str] = set()
        self.allowed: Set[str] = set(NON_TOOL_IDENTIFIERS)


def check_manifests_parse(ctx: Ctx) -> None:
    r, root = ctx.report, ctx.root
    for name in MANIFESTS:
        path = root / name
        if not path.is_file():
            r.error(name, "missing")
            continue
        try:
            data = load_json_strict(path)
        except (ValueError, OSError) as exc:
            r.error(name, f"invalid JSON: {exc}")
            continue
        if not isinstance(data, dict):
            r.error(name, "top level must be a JSON object")
            continue
        ctx.manifests[name] = data
    # Every other JSON file in the repo must parse too.
    for path in iter_repo_files(root):
        if path.suffix != ".json":
            continue
        name = rel(root, path)
        if name in MANIFESTS:
            continue
        try:
            load_json_strict(path)
        except (ValueError, OSError) as exc:
            r.error(name, f"invalid JSON: {exc}")


def check_identity(ctx: Ctx) -> None:
    r, m, root = ctx.report, ctx.manifests, ctx.root
    for name in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json",
                 "gemini-extension.json", "agent-plugin/plugin.json"):
        if name in m and m[name].get("name") != PLUGIN_NAME:
            r.error(name, f"name must be {PLUGIN_NAME!r}, found {m[name].get('name')!r}")
    for name in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json"):
        if name in m and "hooks" in m[name]:
            r.error(name, "declares hooks; lifecycle hooks are forbidden (directories reject them)")
    if ".codex-plugin/plugin.json" in m and "apps" in m[".codex-plugin/plugin.json"]:
        r.error(".codex-plugin/plugin.json", "declares 'apps'; app references cannot be submitted publicly")

    def plugin_entry(name: str) -> Optional[Dict[str, Any]]:
        data = m.get(name)
        if data is None:
            return None
        found, entry = get_path(data, ("plugins", _SEL))
        if not found:
            r.error(name, f"needs exactly one plugins[] entry named {PLUGIN_NAME!r}")
            return None
        return entry

    e = plugin_entry(".claude-plugin/marketplace.json")
    if e is not None and e.get("source") != "./":
        r.error(".claude-plugin/marketplace.json", f"plugins[frameos].source must be './', found {e.get('source')!r}")
    if ".claude-plugin/marketplace.json" in m and m[".claude-plugin/marketplace.json"].get("name") != PLUGIN_NAME:
        r.error(".claude-plugin/marketplace.json", f"marketplace name must be {PLUGIN_NAME!r}")
    e = plugin_entry(".agents/plugins/marketplace.json")
    if e is not None:
        src = e.get("source")
        if not (isinstance(src, dict) and src.get("source") == "local" and src.get("path") == "./"):
            r.error(".agents/plugins/marketplace.json", "plugins[frameos].source must be {source: local, path: ./}")
    e = plugin_entry(".github/plugin/marketplace.json")
    if e is not None:
        src = e.get("source")
        if not isinstance(src, str) or not (root / src).is_dir() or not (root / src / "plugin.json").is_file():
            r.error(".github/plugin/marketplace.json", f"plugins[frameos].source {src!r} must be a directory with plugin.json")
    # Contact address and https URLs in author/owner blocks.
    for name, data in m.items():
        blob = json.dumps(data)
        if FORBIDDEN_EMAIL in blob:
            r.error(name, f"uses {FORBIDDEN_EMAIL}; the contact address is support@frameos.studio")
        for key in ("homepage", "repository"):
            v = data.get(key)
            if isinstance(v, str) and not is_https(v):
                r.error(name, f"{key} must be an https URL")


def check_versions(ctx: Ctx) -> None:
    r, root, m = ctx.report, ctx.root, ctx.manifests
    vpath = root / "VERSION"
    if not vpath.is_file():
        r.error("VERSION", "missing")
        return
    raw = vpath.read_bytes().decode("utf-8", "replace")
    version = raw.strip()
    if raw != version + "\n":
        r.error("VERSION", "must contain exactly the version followed by one newline")
    if not SEMVER_RE.match(version):
        r.error("VERSION", f"{version!r} is not a semantic version (X.Y.Z)")
        return
    ctx.version = version
    for name, path in VERSION_SITES:
        if name not in m:
            continue
        found, value = get_path(m[name], path)
        if not found:
            r.error(name, f"{fmt_path(path)} is missing (expected {version})")
        elif value != version:
            r.error(name, f"{fmt_path(path)} is {value!r}, VERSION is {version!r}. Run: python3 scripts/bump_version.py {version}")
    # Any other version header anywhere in any JSON file.
    for path in iter_repo_files(root):
        if path.suffix != ".json":
            continue
        name = rel(root, path)
        try:
            data = m[name] if name in m else load_json_strict(path)
        except (ValueError, OSError):
            continue
        for where, value in find_key_values(data, VERSION_HEADER):
            if value != version:
                r.error(name, f"{where} is {value!r}, VERSION is {version!r}")
    # Header values quoted in docs/snippets (CHANGELOG is history and is skipped).
    for path in iter_repo_files(root):
        name = rel(root, path)
        if path.suffix not in (".md", ".toml", ".yaml", ".yml", ".txt") or name == "CHANGELOG.md":
            continue
        text = read_text_or_none(path)
        if not text or VERSION_HEADER not in text:
            continue
        for lineno, line in enumerate(text.split("\n"), start=1):
            for mm in HEADER_MENTION_RE.finditer(line):
                if mm.group(1) != version:
                    r.error(f"{name}:{lineno}", f"{VERSION_HEADER} {mm.group(1)!r} does not match VERSION {version!r}")
    changelog = root / "CHANGELOG.md"
    if changelog.is_file() and version not in (read_text_or_none(changelog) or ""):
        r.warn("CHANGELOG.md", f"has no entry for {version}")


def _servers(ctx: Ctx, name: str) -> Optional[Dict[str, Any]]:
    data = ctx.manifests.get(name)
    if data is None:
        return None
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        ctx.report.error(name, "mcpServers must be an object")
        return None
    if list(servers) != [SERVER_KEY]:
        ctx.report.error(name, f"must define exactly one MCP server named {SERVER_KEY!r}, found {sorted(servers)}")
    server = servers.get(SERVER_KEY)
    if not isinstance(server, dict):
        return None
    return server


def _scope_list(v: Any) -> List[str]:
    if isinstance(v, str):
        return v.split()
    if isinstance(v, list):
        return [x for x in v if isinstance(x, str)]
    return []


def check_mcp_configs(ctx: Ctx) -> None:
    r = ctx.report
    s = _servers(ctx, ".mcp.json")
    if s is not None:
        if s.get("type") != "http":
            r.error(".mcp.json", f"mcpServers.frameos.type must be 'http' (Claude Code drops url-only servers), found {s.get('type')!r}")
        if s.get("url") != MCP_URL:
            r.error(".mcp.json", f"mcpServers.frameos.url must be {MCP_URL}, found {s.get('url')!r}")
        if s.get("oauth_resource") != s.get("url"):
            r.error(".mcp.json", f"mcpServers.frameos.oauth_resource must equal url ({MCP_URL}), found {s.get('oauth_resource')!r}")
        if OAUTH_SCOPE not in _scope_list((s.get("oauth") or {}).get("scopes")):
            r.error(".mcp.json", f"mcpServers.frameos.oauth.scopes must include {OAUTH_SCOPE}")
        if OAUTH_SCOPE not in _scope_list(s.get("scopes")):
            r.error(".mcp.json", f"mcpServers.frameos.scopes must include {OAUTH_SCOPE}")
    s = _servers(ctx, ".cursor-plugin/plugin.json")
    if s is not None:
        if s.get("url") != MCP_URL:
            r.error(".cursor-plugin/plugin.json", f"mcpServers.frameos.url must be {MCP_URL}, found {s.get('url')!r}")
        if s.get("type") not in (None, "http", "streamable-http"):
            r.error(".cursor-plugin/plugin.json", f"mcpServers.frameos.type must be http or streamable-http, found {s.get('type')!r}")
    s = _servers(ctx, "gemini-extension.json")
    if s is not None:
        if s.get("httpUrl") != MCP_URL:
            r.error("gemini-extension.json", f"mcpServers.frameos.httpUrl must be {MCP_URL}, found {s.get('httpUrl')!r}")
        if "url" in s:
            r.error("gemini-extension.json", "mcpServers.frameos.url selects SSE in Gemini CLI; use httpUrl only")
        oauth = s.get("oauth") or {}
        if oauth.get("enabled") is not True:
            r.error("gemini-extension.json", "mcpServers.frameos.oauth.enabled must be true")
        if OAUTH_SCOPE not in _scope_list(oauth.get("scopes")):
            r.error("gemini-extension.json", f"mcpServers.frameos.oauth.scopes must include {OAUTH_SCOPE}")
    s = _servers(ctx, "agent-plugin/mcp.json")
    if s is not None:
        if s.get("type") != "streamable-http":
            r.error("agent-plugin/mcp.json", f"mcpServers.frameos.type must be 'streamable-http', found {s.get('type')!r}")
        if s.get("url") != MCP_URL:
            r.error("agent-plugin/mcp.json", f"mcpServers.frameos.url must be {MCP_URL}, found {s.get('url')!r}")
    # Any URL anywhere in the manifests that points at the FrameOS MCP endpoint must be canonical.
    for name, data in ctx.manifests.items():
        for where, value in _iter_strings(data):
            if "frameos.studio/mcp" in value and value != MCP_URL:
                r.error(name, f"{where} = {value!r}; the MCP endpoint is exactly {MCP_URL}")


def _iter_strings(obj: Any, prefix: str = "") -> Iterator[Tuple[str, str]]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _iter_strings(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _iter_strings(v, f"{prefix}[{i}]")
    elif isinstance(obj, str):
        yield prefix, obj


def check_agent_plugin(ctx: Ctx) -> None:
    r, m = ctx.report, ctx.manifests
    data = m.get("agent-plugin/plugin.json")
    if data is not None:
        extra = sorted(set(data) - AGENT_PLUGIN_KEYS)
        if extra:
            r.error("agent-plugin/plugin.json", f"keys not allowed by the Agent Plugins 1.0 schema: {extra}")
        if not str(data.get("$schema", "")).startswith("https://agent-plugins.org/schemas/"):
            r.error("agent-plugin/plugin.json", "$schema must point at https://agent-plugins.org/schemas/...")
    data = m.get("agent-plugin/mcp.json")
    if data is not None:
        extra = sorted(set(data) - AGENT_MCP_KEYS)
        if extra:
            r.error("agent-plugin/mcp.json", f"keys not allowed by the Agent Plugins 1.0 MCP schema: {extra}")
        if not str(data.get("$schema", "")).startswith("https://agent-plugins.org/schemas/"):
            r.error("agent-plugin/mcp.json", "$schema must point at https://agent-plugins.org/schemas/...")
    for forbidden in ("bin", "hooks", "hooks.json", "CLAUDE.md", "AGENTS.md"):
        if (ctx.root / "agent-plugin" / forbidden).exists():
            r.error(f"agent-plugin/{forbidden}", "forbidden in the plugin root")


def check_cursor(ctx: Ctx) -> None:
    r = ctx.report
    data = ctx.manifests.get(".cursor-plugin/plugin.json")
    if data is None:
        return
    extra = sorted(set(data) - CURSOR_KEYS)
    if extra:
        r.error(".cursor-plugin/plugin.json", f"keys not in the Cursor plugin schema: {extra}")
    logo = data.get("logo")
    if logo is not None:
        if not isinstance(logo, str) or not (ctx.root / logo).is_file():
            r.error(".cursor-plugin/plugin.json", f"logo {logo!r} does not exist")


def check_codex(ctx: Ctx) -> None:
    r, root = ctx.report, ctx.root
    name = ".codex-plugin/plugin.json"
    data = ctx.manifests.get(name)
    if data is None:
        return
    for key, kind in (("skills", "dir"), ("mcpServers", "file")):
        v = data.get(key)
        if not isinstance(v, str):
            r.error(name, f"{key} must be a './'-relative path")
            continue
        p = root / v
        if (kind == "dir" and not p.is_dir()) or (kind == "file" and not p.is_file()):
            r.error(name, f"{key} {v!r} does not exist")
    itf = data.get("interface")
    if not isinstance(itf, dict):
        r.error(name, "interface object is required")
        return
    for key in CODEX_INTERFACE_REQUIRED:
        if key not in itf or itf[key] in (None, "", []) and key != "capabilities":
            r.error(name, f"interface.{key} is required")
    limits = (("displayName", 30), ("shortDescription", 30), ("longDescription", 4000), ("developerName", 80))
    for key, limit in limits:
        v = itf.get(key)
        if v is not None and (not isinstance(v, str) or len(v) > limit):
            r.error(name, f"interface.{key} must be a string of at most {limit} characters (has {len(v) if isinstance(v, str) else type(v).__name__})")
    cat = itf.get("category")
    if cat is not None and cat not in CODEX_CATEGORIES:
        r.error(name, f"interface.category {cat!r} is not one of {sorted(CODEX_CATEGORIES)}")
    caps = itf.get("capabilities")
    if caps is not None:
        if not isinstance(caps, list) or len(caps) > 20 or not all(isinstance(c, str) and len(c) <= 120 for c in caps):
            r.error(name, "interface.capabilities must be a list of at most 20 strings of at most 120 characters")
    for key in ("websiteURL", "supportURL", "privacyPolicyURL", "termsOfServiceURL"):
        if key in itf and not is_https(itf[key]):
            r.error(name, f"interface.{key} must be an https URL")
    dp = itf.get("defaultPrompt")
    if dp is not None:
        prompts = [dp] if isinstance(dp, str) else dp
        if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3:
            r.error(name, "interface.defaultPrompt must have 1 to 3 entries")
        else:
            for i, p in enumerate(prompts):
                if not isinstance(p, str) or not p.strip():
                    r.error(name, f"interface.defaultPrompt[{i}] must be a non-empty string")
                elif len(p) > 128:
                    r.error(name, f"interface.defaultPrompt[{i}] is {len(p)} characters; the limit is 128")
                elif re.search(r"(^|\s)@\w", p):
                    r.error(name, f"interface.defaultPrompt[{i}] must not contain @mentions")
            if len(set(map(str, prompts))) != len(prompts):
                r.error(name, "interface.defaultPrompt entries must be unique")
    for key in ("brandColor", "brandColorDark"):
        v = itf.get(key)
        if v is not None and not (isinstance(v, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", v)):
            r.error(name, f"interface.{key} must be #RRGGBB")
    for key in ("composerIcon", "logo", "composerIconDark", "logoDark"):
        v = itf.get(key)
        if v is None:
            continue
        if not isinstance(v, str) or not v.startswith("./"):
            r.error(name, f"interface.{key} must be a './'-prefixed path")
            continue
        p = root / v
        if not p.is_file():
            r.error(name, f"interface.{key} {v!r} does not exist")
        elif p.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
            r.error(name, f"interface.{key} must be PNG, JPEG, WebP or SVG")
        elif p.stat().st_size > 5 * 1024 * 1024:
            r.error(name, f"interface.{key} is larger than 5 MiB")
    if itf.get("screenshots"):
        r.warn(name, "interface.screenshots are only allowed when the MCP server returns UI")


def check_icon(ctx: Ctx) -> None:
    r = ctx.report
    icon = ctx.root / "assets" / "icon.png"
    if not icon.is_file():
        r.error("assets/icon.png", "missing")
        return
    size = png_size(icon)
    if size is None:
        r.error("assets/icon.png", "not a valid PNG")
        return
    w, h = size
    if w != h:
        r.error("assets/icon.png", f"must be square, is {w}x{h}")
    if min(w, h) < 512:
        r.error("assets/icon.png", f"must be at least 512x512, is {w}x{h}")
    if max(w, h) > 4096:
        r.error("assets/icon.png", f"must be at most 4096 px, is {w}x{h}")
    # Every other PNG referenced by a manifest must be square as well.
    for name, data in ctx.manifests.items():
        for where, value in _iter_strings(data):
            if value.lower().endswith(".png") and not SCHEME_RE.match(value):
                p = ctx.root / value
                if p.is_file():
                    sz = png_size(p)
                    if sz is None or sz[0] != sz[1]:
                        r.error(name, f"{where} {value!r} must be a square PNG")


def check_gemini(ctx: Ctx) -> None:
    r, root = ctx.report, ctx.root
    data = ctx.manifests.get("gemini-extension.json")
    if data is not None:
        ctx_file = data.get("contextFileName")
        if ctx_file is not None:
            p = root / str(ctx_file)
            if not p.is_file():
                r.error("gemini-extension.json", f"contextFileName {ctx_file!r} does not exist")
            else:
                text = read_text_or_none(p) or ""
                n = len(text.rstrip("\n").split("\n"))
                if n > GEMINI_MD_MAX_LINES:
                    r.warn(str(ctx_file), f"{n} lines; keep the always-on context under {GEMINI_MD_MAX_LINES}")
                for skill in EXPECTED_SKILLS:
                    if skill not in text:
                        r.warn(str(ctx_file), f"does not mention the {skill} skill")
                check_tool_tokens(r, str(ctx_file), text, ctx.tools, ctx.allowed)
    cmd_dir = root / "commands" / "frameos"
    for cmd, skill in GEMINI_COMMANDS.items():
        p = cmd_dir / f"{cmd}.toml"
        name = rel(root, p)
        if not p.is_file():
            r.error(name, f"missing (Gemini command /frameos:{cmd} for {skill})")
            continue
        text = read_text_or_none(p)
        if text is None:
            r.error(name, "not valid UTF-8")
            continue
        if _toml is not None:
            try:
                data_t = _toml.loads(text)
            except Exception as exc:
                r.error(name, f"invalid TOML: {exc}")
                continue
            desc, prompt = data_t.get("description"), data_t.get("prompt")
            if not isinstance(desc, str) or not desc.strip():
                r.error(name, "needs a non-empty description string")
            if not isinstance(prompt, str) or not prompt.strip():
                r.error(name, "needs a non-empty prompt string")
                continue
            extra = sorted(set(data_t) - {"description", "prompt"})
            if extra:
                r.warn(name, f"unknown keys {extra}")
        else:  # Python < 3.11 without tomli: shallow check only
            if not re.search(r"(?m)^description\s*=", text) or not re.search(r"(?m)^prompt\s*=", text):
                r.error(name, "needs description = ... and prompt = ...")
            prompt = text
        if skill not in prompt:
            r.error(name, f"prompt must name the {skill} skill")
        if "{{args}}" not in prompt:
            r.warn(name, "prompt does not pass the user's request through {{args}}")
        check_tool_tokens(r, name, prompt, ctx.tools, ctx.allowed)
    if cmd_dir.is_dir():
        for p in sorted(cmd_dir.glob("*.toml")):
            if p.stem not in GEMINI_COMMANDS:
                r.warn(rel(root, p), "command not in the expected set " + str(sorted(GEMINI_COMMANDS)))


def _check_frontmatter(ctx: Ctx, skill_dir: Path, text: str) -> Optional[Tuple[str, int]]:
    """Validate frontmatter; return (body, body_first_lineno) or None if unusable."""
    r = ctx.report
    where = rel(ctx.root, skill_dir / "SKILL.md")
    if text.startswith("﻿"):
        r.error(where, "starts with a byte-order mark; save as UTF-8 without BOM")
    fm_text, body, body_line = split_frontmatter(text)
    if fm_text is None:
        r.error(where, "must start with YAML frontmatter between '---' lines")
        return None
    try:
        fm, notes = parse_mini_yaml(fm_text)
    except MiniYAMLError as exc:
        r.error(where, f"frontmatter: {exc}")
        return body, body_line
    for note in notes:
        r.warn(where, f"frontmatter {note}")
    if _pyyaml is not None:
        try:
            ref = _pyyaml.safe_load(fm_text)
        except Exception as exc:
            r.error(where, f"frontmatter is not valid YAML: {exc}")
            ref = None
        if isinstance(ref, dict) and isinstance(fm, dict):
            for k in FRONTMATTER_KEYS:
                if k in ref and k in fm and str(ref[k]) != str(fm[k]):
                    r.warn(where, f"frontmatter {k}: validator subset parser and PyYAML disagree; simplify the quoting")
    if not isinstance(fm, dict):
        r.error(where, "frontmatter must be a mapping")
        return body, body_line
    extra = sorted(set(fm) - FRONTMATTER_KEYS)
    if extra:
        r.error(where, f"frontmatter keys {extra} are not portable; only {sorted(FRONTMATTER_KEYS)} are allowed")
    name = fm.get("name")
    if not isinstance(name, str) or not name:
        r.error(where, "frontmatter name is required")
    else:
        if name != skill_dir.name:
            r.error(where, f"frontmatter name {name!r} must equal the directory name {skill_dir.name!r}")
        if not SKILL_NAME_RE.match(name) or len(name) > 64:
            r.error(where, f"frontmatter name {name!r} must match {SKILL_NAME_RE.pattern} and be at most 64 characters")
    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        r.error(where, "frontmatter description is required")
    else:
        if len(desc) > 1024:
            r.error(where, f"description is {len(desc)} characters; the limit is 1024")
        if "<" in desc or ">" in desc:
            r.error(where, "description must not contain '<' or '>'")
        if len(desc) < 100:
            r.warn(where, f"description is only {len(desc)} characters; say what it does, when to use it and which sibling skill owns adjacent work")
    lic = fm.get("license")
    if lic is None:
        r.warn(where, "frontmatter license is missing (use: license: MIT)")
    elif lic != "MIT":
        r.error(where, f"frontmatter license must be MIT, found {lic!r}")
    return body, body_line


def _check_ground_rules(ctx: Ctx, where: str, body: str, body_line: int, rules: Optional[str]) -> None:
    r = ctx.report
    s_count, e_count = body.count(_sync.GROUND_START), body.count(_sync.GROUND_END)
    if s_count != 1 or e_count != 1:
        r.error(where, f"needs exactly one ground-rules block ({_sync.GROUND_START} ... {_sync.GROUND_END}); found {s_count} start / {e_count} end markers")
        return
    start, end = body.index(_sync.GROUND_START), body.index(_sync.GROUND_END)
    if end < start:
        r.error(where, "ground-rules end marker comes before the start marker")
        return
    if rules is not None:
        block = body[start:end + len(_sync.GROUND_END)]
        if block != _sync.render_block(rules):
            r.error(where, "ground-rules block differs from scripts/ground_rules.md. Run: python3 scripts/sync.py")
    # Position: H1 first, then the block before any other section heading.
    before = body[:start]
    lines = [ln for ln in before.split("\n") if ln.strip()]
    if not lines or not lines[0].startswith("# "):
        r.error(where, "body must start with an H1 title ('# ...') before the ground-rules block")
    if any(ln.startswith("## ") for ln in lines):
        r.error(where, "the ground-rules block must come right after the H1 title and one-line purpose, before any '## ' section")


def _check_openai_yaml(ctx: Ctx, skill_dir: Path) -> None:
    r = ctx.report
    path = skill_dir / "agents" / "openai.yaml"
    where = rel(ctx.root, path)
    if not path.is_file():
        r.error(where, "missing (Codex/ChatGPT per-skill metadata)")
        return
    text = read_text_or_none(path)
    if text is None:
        r.error(where, "not valid UTF-8")
        return
    try:
        data, notes = parse_mini_yaml(text)
    except MiniYAMLError as exc:
        r.error(where, str(exc))
        return
    for note in notes:
        r.warn(where, note)
    if _pyyaml is not None:
        try:
            _pyyaml.safe_load(text)
        except Exception as exc:
            r.error(where, f"not valid YAML: {exc}")
    if not isinstance(data, dict):
        r.error(where, "must be a mapping")
        return
    itf = data.get("interface")
    if not isinstance(itf, dict):
        r.error(where, "interface mapping is required")
        return
    for key in sorted(itf):
        if key.startswith("icon_"):
            r.error(where, f"interface.{key}: no per-skill icons are shipped; remove it")
    dn = itf.get("display_name")
    if not isinstance(dn, str) or not dn.strip():
        r.error(where, "interface.display_name is required")
    elif not dn.startswith("FrameOS"):
        r.warn(where, f"interface.display_name {dn!r} should start with 'FrameOS'")
    sd = itf.get("short_description")
    if not isinstance(sd, str) or not sd.strip():
        r.error(where, "interface.short_description is required")
    elif not 25 <= len(sd) <= 64:
        r.warn(where, f"interface.short_description is {len(sd)} characters; 25-64 is recommended")
    dp = itf.get("default_prompt")
    if dp is None:
        r.error(where, f"interface.default_prompt is required (e.g. 'Use ${skill_dir.name} to ...', at most 128 characters)")
    else:
        if not isinstance(dp, str) or not dp.strip():
            r.error(where, "interface.default_prompt must be a non-empty string")
        else:
            if len(dp) > 128:
                r.error(where, f"interface.default_prompt is {len(dp)} characters; the limit is 128")
            if f"${skill_dir.name}" not in dp:
                r.error(where, f"interface.default_prompt must name the skill as ${skill_dir.name}")
    for key, val in itf.items():
        if isinstance(val, PlainStr):
            r.warn(where, f"interface.{key}: quote string values")
    pol = data.get("policy")
    if pol is not None:
        if not isinstance(pol, dict):
            r.error(where, "policy must be a mapping")
        elif "allow_implicit_invocation" in pol and not isinstance(pol["allow_implicit_invocation"], bool):
            r.error(where, "policy.allow_implicit_invocation must be true or false")
    deps = data.get("dependencies")
    if deps is not None:
        tools = deps.get("tools") if isinstance(deps, dict) else None
        if not isinstance(tools, list):
            r.error(where, "dependencies.tools must be a list")
        else:
            for i, t in enumerate(tools):
                if not isinstance(t, dict):
                    r.error(where, f"dependencies.tools[{i}] must be a mapping")
                    continue
                if t.get("type") != "mcp":
                    r.error(where, f"dependencies.tools[{i}].type must be 'mcp'")
                if t.get("value") != SERVER_KEY:
                    r.error(where, f"dependencies.tools[{i}].value must be {SERVER_KEY!r}")
                if "url" in t and t.get("url") != MCP_URL:
                    r.error(where, f"dependencies.tools[{i}].url must be {MCP_URL}")
                if "transport" in t and t.get("transport") != "streamable_http":
                    r.error(where, f"dependencies.tools[{i}].transport must be 'streamable_http'")


def check_skills(ctx: Ctx) -> None:
    r, root = ctx.report, ctx.root
    base = root / "skills"
    if not base.is_dir():
        r.error("skills/", "missing")
        return
    rules_path = root / _sync.RULES_FILE
    rules = read_text_or_none(rules_path) if rules_path.is_file() else None
    if rules is None:
        r.error(_sync.RULES_FILE.as_posix(), "missing or unreadable")
    present = set()
    for entry in sorted(base.iterdir()):
        if entry.name.startswith(".") and entry.name != ".DS_Store":
            r.warn(rel(root, entry), "hidden entry in skills/")
            continue
        if entry.is_symlink():
            r.error(rel(root, entry), "symlinks are rejected by hosts; use a real directory")
            continue
        if not entry.is_dir():
            if entry.name != ".DS_Store":
                r.error(rel(root, entry), "only skill directories belong in skills/")
            continue
        if not (entry / "SKILL.md").is_file():
            r.error(rel(root, entry), "skill directory without SKILL.md (every directory in skills/ loads as a skill)")
            continue
        present.add(entry.name)
        _check_one_skill(ctx, entry, rules)
    for name in EXPECTED_SKILLS:
        if name not in present:
            r.error(f"skills/{name}", "missing expected skill")
    for name in sorted(present - set(EXPECTED_SKILLS)):
        r.warn(f"skills/{name}", "not in the expected set of 8 skills (update EXPECTED_SKILLS, routing, docs and commands)")
    # Mirror into agent-plugin/skills (ground-rules drift is reported per skill above).
    result = _sync.sync(root, check=True)
    for d in result.drift:
        if d.kind == "mirror":
            r.error(d.path, f"{d.message}. Run: python3 scripts/sync.py")
    for e in result.errors:
        if "ground-rules" not in e:
            r.error("sync", e)


def _check_one_skill(ctx: Ctx, sdir: Path, rules: Optional[str]) -> None:
    r, root = ctx.report, ctx.root
    skill_md = sdir / "SKILL.md"
    where = rel(root, skill_md)
    text = read_text_or_none(skill_md)
    if text is None:
        r.error(where, "not valid UTF-8")
        return
    n_lines = len(text.rstrip("\n").split("\n"))
    if n_lines > SKILL_MAX_LINES:
        r.error(where, f"{n_lines} lines; the hard limit is {SKILL_MAX_LINES} (move detail into references/)")
    elif n_lines > SKILL_TARGET_LINES:
        r.warn(where, f"{n_lines} lines; aim for at most {SKILL_TARGET_LINES}")
    parsed = _check_frontmatter(ctx, sdir, text)
    if parsed is None:
        return
    body, body_line = parsed
    if not body.strip():
        r.error(where, "body is empty")
        return
    _check_ground_rules(ctx, where, body, body_line, rules)
    check_tool_tokens(r, where, text, ctx.tools, ctx.allowed)
    _warn_punctuation(r, where, body)
    linked = check_relative_links(r, root, skill_md, body, sdir)
    # Other files in the skill.
    for path in sorted(p for p in sdir.rglob("*") if p.is_file()):
        prel = path.relative_to(sdir).as_posix()
        pwhere = rel(root, path)
        if path.is_symlink():
            r.error(pwhere, "symlinks are rejected by hosts")
            continue
        if prel in ("SKILL.md", "agents/openai.yaml") or path.name == ".DS_Store":
            continue
        if prel.startswith("references/") and path.suffix == ".md":
            if prel.count("/") > 1:
                r.warn(pwhere, "keep references one level deep (references/<file>.md)")
            rtext = read_text_or_none(path)
            if rtext is None:
                r.error(pwhere, "not valid UTF-8")
                continue
            rn = len(rtext.rstrip("\n").split("\n"))
            if rn > SKILL_MAX_LINES:
                r.error(pwhere, f"{rn} lines; the hard limit is {SKILL_MAX_LINES}")
            elif rn > REFERENCE_TARGET_LINES:
                r.warn(pwhere, f"{rn} lines; aim for at most {REFERENCE_TARGET_LINES}")
            check_tool_tokens(r, pwhere, rtext, ctx.tools, ctx.allowed)
            _warn_punctuation(r, pwhere, rtext)
            check_relative_links(r, root, path, rtext, sdir)
            if path.resolve() not in linked:
                r.warn(pwhere, "not linked from SKILL.md, so agents will never load it")
        else:
            r.warn(pwhere, "unexpected file in a skill (expected SKILL.md, references/*.md, agents/openai.yaml)")
    _check_openai_yaml(ctx, sdir)


def _warn_punctuation(r: Report, where: str, text: str) -> None:
    counts: Dict[str, int] = {}
    for ch, label in NON_ASCII_PUNCT.items():
        c = text.count(ch)
        if c:
            counts[label] = counts.get(label, 0) + c
    if counts:
        detail = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
        r.warn(where, f"use plain ASCII punctuation in instructions ({detail})")


def check_forbidden(ctx: Ctx) -> None:
    r, root = ctx.report, ctx.root
    for name, why in (
        ("bin", "claude.ai refuses plugins with a root bin/"),
        ("hooks", "lifecycle hooks are forbidden"),
        ("hooks.json", "lifecycle hooks are forbidden"),
        ("CLAUDE.md", "not loaded from a plugin and warned about by claude plugin validate --strict"),
        ("AGENTS.md", "Devin would load it into every user's context"),
        (".app.json", "app references cannot be submitted to the OpenAI directory"),
    ):
        if (root / name).exists() or (root / name).is_symlink():
            r.error(name, f"forbidden at the repo root ({why})")
    for path in iter_repo_files(root):
        name = rel(root, path)
        if path.name == ".DS_Store":
            r.error(name, "remove it (find . -name .DS_Store -delete)")
            continue
        if path.name == "hooks.json":
            r.error(name, "lifecycle hooks are forbidden")
        if path.is_symlink():
            continue
        size = path.stat().st_size
        if size > MAX_FILE_BYTES and path.suffix.lower() not in IMAGE_EXTS:
            r.error(name, f"{size // 1024} KiB; files over 256 KiB (other than images) are not allowed")
        if path.suffix.lower() in IMAGE_EXTS - {".svg"}:
            continue
        text = read_text_or_none(path)
        if text is None:
            continue
        for label, pat in SECRET_PATTERNS:
            m = pat.search(text)
            if m:
                lineno = text.count("\n", 0, m.start()) + 1
                r.error(f"{name}:{lineno}", f"looks like a secret ({label}); never commit credentials")
        if FORBIDDEN_EMAIL in text:
            for lineno, line in enumerate(text.split("\n"), start=1):
                # A line that forbids the address ("Never hello@...") is documentation, not use.
                if FORBIDDEN_EMAIL in line and not NEGATION_RE.search(line):
                    r.error(f"{name}:{lineno}", f"uses {FORBIDDEN_EMAIL}; the contact address is support@frameos.studio")
        user_facing = (
            name.startswith(("skills/", "agent-plugin/skills/", "commands/", "docs/"))
            or name in ("README.md", "GEMINI.md")
        )
        if user_facing and path.suffix in (".md", ".toml", ".yaml", ".yml"):
            for lineno, line in enumerate(_strip_code(text).split("\n"), start=1):
                pm = PRICE_RE.search(line)
                if pm:
                    r.error(f"{name}:{lineno}", f"states a price ({pm.group(0).strip()}); never quote prices - link https://frameos.studio/pricing")
                dm = DISCOUNT_CODE_RE.search(line)
                if dm:
                    r.error(f"{name}:{lineno}", f"contains a discount code ({dm.group(0)}); never publish offers or codes")


def check_readme_license(ctx: Ctx) -> None:
    r, root = ctx.report, ctx.root
    readme = root / "README.md"
    if not readme.is_file():
        r.error("README.md", "missing")
    else:
        text = _strip_code(read_text_or_none(readme) or "")
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
        text = re.sub(r"\]\([^)]*\)", "]", text)
        words = re.findall(r"[A-Za-z][A-Za-z'\-]*", text)
        if len(words) < 40:
            r.error("README.md", f"only {len(words)} words of prose; at least 40 are required")
    lic = root / "LICENSE"
    if not lic.is_file() or not (read_text_or_none(lic) or "").strip():
        r.error("LICENSE", "missing or empty")
    elif "MIT" not in (read_text_or_none(lic) or ""):
        r.warn("LICENSE", "does not look like the MIT license declared in the manifests")


def check_evals(ctx: Ctx) -> None:
    r, root = ctx.report, ctx.root
    evals = root / "evals"
    if not evals.is_dir() or not ctx.tools:
        return
    prefixed = re.compile(r"mcp__plugin_frameos_frameos__([A-Za-z0-9_]+)")
    for path in iter_repo_files(root):
        if not rel(root, path).startswith("evals/"):
            continue
        text = read_text_or_none(path)
        if text is None:
            continue
        for m in prefixed.finditer(text):
            if m.group(1) not in ctx.tools:
                lineno = text.count("\n", 0, m.start()) + 1
                r.error(f"{rel(root, path)}:{lineno}", f"references unknown tool {m.group(1)!r}.{_suggest(m.group(1), ctx.tools)}")
    mocks = evals / "mocks" / "frameos"
    if mocks.is_dir():
        for p in sorted(mocks.glob("*.md")):
            if p.stem not in ctx.tools:
                r.error(rel(root, p), f"mock for unknown tool {p.stem!r}")
        tools_json = mocks / "_tools.json"
        if tools_json.is_file():
            try:
                data = load_json_strict(tools_json)
            except ValueError as exc:
                r.error(rel(root, tools_json), f"invalid JSON: {exc}")
                return
            tools = data.get("tools") if isinstance(data, dict) else data
            names = {t.get("name") for t in tools or [] if isinstance(t, dict)}
            if names != ctx.tools:
                missing, extra = sorted(ctx.tools - names), sorted(names - ctx.tools)
                r.error(rel(root, tools_json), f"must list the snapshot's tools (missing {missing}, extra {extra})")


def check_workflows(ctx: Ctx) -> None:
    r, root = ctx.report, ctx.root
    wf = root / ".github" / "workflows"
    if not wf.is_dir():
        return
    for path in sorted(list(wf.glob("*.yml")) + list(wf.glob("*.yaml"))):
        text = read_text_or_none(path) or ""
        for lineno, line in enumerate(text.split("\n"), start=1):
            m = USES_RE.match(line)
            if not m:
                continue
            ref = m.group(1)
            if ref.startswith("./") or ref.startswith("docker://"):
                continue
            if not re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", ref):
                r.error(f"{rel(root, path)}:{lineno}", f"'{ref}' must be pinned to a full 40-character commit SHA")


CHECKS = (
    check_manifests_parse,
    check_identity,
    check_versions,
    check_mcp_configs,
    check_agent_plugin,
    check_cursor,
    check_codex,
    check_icon,
    check_gemini,
    check_skills,
    check_forbidden,
    check_readme_license,
    check_evals,
    check_workflows,
)


def run(root: Path) -> Report:
    """Validate the repo at ``root`` and return the report (never raises on findings)."""
    root = Path(root).resolve()
    report = Report()
    ctx = Ctx(root, report)
    tools, params = load_snapshot_vocab(root, report)
    ctx.tools = tools
    ctx.allowed = set(NON_TOOL_IDENTIFIERS) | params
    # The 'gemini' check reads the vocab, so load it before running checks.
    for check in CHECKS:
        check(ctx)
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Validate the FrameOS plugin repo.")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent, help="repo root to validate")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--quiet", action="store_true", help="do not print warnings")
    args = ap.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        print(f"validate: {root} is not a directory", file=sys.stderr)
        return 2
    report = run(root)
    for e in report.errors:
        print(f"ERROR  {e}")
    if not args.quiet:
        for w in report.warnings:
            print(f"WARN   {w}")
    print(f"validate: {len(report.errors)} error(s), {len(report.warnings)} warning(s) in {root}")
    if report.errors or (args.strict and report.warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
