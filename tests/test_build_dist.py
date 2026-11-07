"""build_dist.py: ZIP layouts per host, exclusions, determinism, sync gate."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_fixture as fx  # noqa: E402

import build_dist  # noqa: E402  (scripts/ is on sys.path via test_fixture)


# Built at runtime so this file never holds a literal placeholder client ID itself.
CLIENT_ID_PLACEHOLDER = re.compile("__[A-Z0-9_]*" + "CLIENT_ID__")
SCAN_SKIP_DIRS = {".git", "dist", "__pycache__", ".venv", "node_modules"}


def names(path: Path) -> list:
    with zipfile.ZipFile(path) as zf:
        return zf.namelist()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BuildDistTest(fx.FixtureCase):
    def setUp(self) -> None:
        super().setUp()
        # Content that must stay out of the plugin ZIP, and docs that must stay in.
        for rel in ("tests/test_x.py", "dev/mock_server.py", "evals/case/prompt.md",
                    "docs/submission/openai.md", ".github/workflows/validate.yml", "scripts/validate.py"):
            self.write(rel, "x\n")
        self.write("docs/install/codex.md", "# Codex\n")
        self.path("skills/frameos-clip/.DS_Store").write_bytes(b"junk")
        out_tmp = tempfile.TemporaryDirectory(prefix="frameos-dist-")
        self.addCleanup(out_tmp.cleanup)
        self.out = Path(out_tmp.name).resolve()
        self.version = self.read("VERSION").strip()

    def build(self, out: Path) -> dict:
        return build_dist.build(self.root, out)

    def test_claude_ai_zip_has_folder_at_top(self) -> None:
        built = self.build(self.out / "a")
        for skill in fx.TITLES:
            path = self.out / "a" / "claude-ai" / f"{skill}.zip"
            self.assertEqual(built[f"claude-ai/{skill}"], path)
            entries = names(path)
            self.assertIn(f"{skill}/SKILL.md", entries)
            self.assertIn(f"{skill}/references/notes.md", entries)
            self.assertIn(f"{skill}/agents/openai.yaml", entries)
            self.assertTrue(all(n.startswith(f"{skill}/") for n in entries), entries)
            self.assertFalse(any(n.endswith(".DS_Store") for n in entries))

    def test_perplexity_zip_has_skill_md_at_root(self) -> None:
        self.build(self.out / "a")
        for skill in fx.TITLES:
            entries = names(self.out / "a" / "perplexity" / f"{skill}.zip")
            self.assertIn("SKILL.md", entries)
            self.assertIn("references/notes.md", entries)
            self.assertFalse(any(n.startswith(f"{skill}/") for n in entries), entries)

    def test_plugin_zip_contents(self) -> None:
        built = self.build(self.out / "a")
        path = built["plugin"]
        self.assertEqual(path.name, f"frameos-plugin-{self.version}.zip")
        entries = names(path)
        # The ZIP is plugins/frameos/: the Claude plugin and nothing else.
        for required in (".claude-plugin/plugin.json", ".mcp.json", "README.md", "LICENSE",
                         "skills/frameos-clip/SKILL.md", "skills/frameos-setup/SKILL.md"):
            self.assertIn(required, entries)
        self.assertEqual(sorted({n.split("/")[0] for n in entries}),
                         [".claude-plugin", ".mcp.json", "LICENSE", "README.md", "skills"])
        for excluded in (".codex-plugin/", ".cursor-plugin/", "gemini-extension.json", "GEMINI.md", "VERSION",
                         "assets/", "commands/", "docs/", "tests/", "dev/", "evals/", "scripts/", "agent-plugin/",
                         "server.json", "plugins/"):
            self.assertFalse(any(n.startswith(excluded) for n in entries), f"{excluded} leaked: {entries}")
        self.assertFalse(any(n.endswith("/agents/openai.yaml") for n in entries))
        self.assertEqual([n for n in entries if n.endswith("plugin.json") and ".claude-plugin" in n],
                         [".claude-plugin/plugin.json"])
        self.assertFalse(any(n.endswith(".DS_Store") for n in entries))

    def _openai(self, out: Path) -> tuple:
        path = self.build(out)["openai"]
        with zipfile.ZipFile(path) as zf:
            return path, zf.namelist(), {n: zf.read(n) for n in zf.namelist() if not n.endswith("/")}

    def test_openai_zip_contents(self) -> None:
        path, entries, data = self._openai(self.out / "a")
        self.assertEqual(path.name, f"frameos-openai-{self.version}.zip")
        self.assertEqual({n.split("/")[0] for n in entries}, {".codex-plugin", ".mcp.json", "skills", "assets", "LICENSE"})
        self.assertEqual([n for n in entries if n.endswith("plugin.json")], [".codex-plugin/plugin.json"])
        self.assertIn("skills/frameos-clip/agents/openai.yaml", entries)
        self.assertIn("assets/icon.png", entries)
        for gone in (".claude-plugin/", ".cursor-plugin/", "commands/", "agent-plugin/", ".agents/", "GEMINI.md",
                     "gemini-extension.json", "README.md", "docs/", "dev/", "evals/", "tests/", ".codex-plugin/mcp.json"):
            self.assertFalse(any(n.startswith(gone) for n in entries), f"{gone} leaked: {entries}")
        manifest = json.loads(data[".codex-plugin/plugin.json"])
        self.assertEqual((manifest["version"], manifest["mcpServers"], manifest["skills"]),
                         (self.version, "./.mcp.json", "./skills/"))
        self.assertEqual(manifest["interface"]["brandColorDark"], "#D6FF3F")
        openai = manifest["extensions"]["com.openai"]
        self.assertEqual(openai["onboardingSkill"], "./skills/frameos-setup/SKILL.md")
        self.assertEqual([len(openai["review"]["test_cases"][k]) for k in ("positive", "negative")], [5, 3])
        self.assertIs(openai["review"]["commerce"], False)
        self.assertNotIn("test_credentials", json.dumps(manifest))
        server = json.loads(data[".mcp.json"])["mcpServers"]["frameos"]
        self.assertEqual(server, {"url": "https://frameos.studio/mcp", "extensions": {"com.openai": {"auth": {
            "type": "oauth", "client": {"mode": "cimd"}, "baseScopes": ["frameos:mcp"]}}}})
        # The repo's own Codex manifest still names Codex's connection file.
        self.assertEqual(json.loads(self.read(".codex-plugin/plugin.json"))["mcpServers"], "./.codex-plugin/mcp.json")

    def test_openai_zip_narrows_the_setup_skill(self) -> None:
        hosts = ("# Hosts\n\n- Server name used below: `frameos` (in Claude Code the plugin's copy is `plugin:frameos:frameos`)\n\n"
                 "## Claude Code (terminal)\n\n- `claude mcp list`\n\n## Codex (CLI and app)\n\n- `codex mcp list`\n\n"
                 "## ChatGPT (web)\n\n- Plugins\n\n## Devin and Windsurf\n\n- `devin mcp login frameos`\n\n"
                 "## Any other MCP client\n\n- Add the server.\n")
        self.write("skills/frameos-setup/references/hosts.md", hosts)
        setup = self.read("skills/frameos-setup/SKILL.md") + (
            "\n1. Identify the app: Claude Code, Codex, ChatGPT, Cursor or another MCP client. If unclear, ask once.\n\n"
            "| App | Reconnect | State |\n|---|---|---|\n| Claude Code | `/mcp` | `claude mcp list` |\n"
            "| Codex | `codex mcp login frameos` | `codex mcp list` |\n| ChatGPT | Plugins | details |\n"
            "| Devin | `devin mcp login frameos` | ask |\n\n"
            "If FrameOS was added by hand rather than as the plugin, the server name in Claude Code is `frameos`.\n")
        self.write("skills/frameos-setup/SKILL.md", setup)
        build_dist._sync.sync(self.root)
        _, _, data = self._openai(self.out / "a")
        got_hosts = data["skills/frameos-setup/references/hosts.md"].decode()
        self.assertEqual([line for line in got_hosts.splitlines() if line.startswith("## ")],
                         ["## Codex (CLI and app)", "## ChatGPT (web)", "## Any other MCP client"])
        self.assertIn("https://frameos.studio/plugin", got_hosts)
        got_setup = data["skills/frameos-setup/SKILL.md"].decode()
        self.assertIn("1. Identify the app: ChatGPT, Codex or another MCP client.", got_setup)
        self.assertIn("| Codex | `codex mcp login frameos`", got_setup)
        for gone in ("Claude", "| Devin", "devin mcp"):
            self.assertNotIn(gone, got_setup + got_hosts)
        # The shared skill is untouched.
        self.assertEqual(self.read("skills/frameos-setup/references/hosts.md"), hosts)

    def test_openai_zip_refuses_other_product_names(self) -> None:
        self.replace("skills/frameos-clip/references/notes.md", "Back to the", "Works best in Claude. Back to the")
        build_dist._sync.sync(self.root)
        with self.assertRaises(build_dist.BuildError) as cm:
            self.build(self.out / "a")
        self.assertIn("skills/frameos-clip/references/notes.md:4 contains another AI product's name", str(cm.exception))

    def test_openai_zip_refuses_placeholders(self) -> None:
        placeholder = "__EXAMPLE_" + "CLIENT_ID__"
        self.assertRegex(placeholder, CLIENT_ID_PLACEHOLDER)
        self.replace("skills/frameos-library/references/notes.md", "Back to the", f"Client `{placeholder}`. Back to the")
        build_dist._sync.sync(self.root)
        with self.assertRaises(build_dist.BuildError) as cm:
            self.build(self.out / "a")
        self.assertIn("an unfilled placeholder", str(cm.exception))
        self.assertIn(placeholder, str(cm.exception))

    def test_repo_has_no_placeholder_client_ids(self) -> None:
        # Every app either has a real client ID, signs in through a registered
        # client document, or is marked "coming soon"; none ships a stand-in ID.
        found = []
        for dirpath, dirnames, filenames in os.walk(fx.REPO):
            dirnames[:] = sorted(d for d in dirnames if d not in SCAN_SKIP_DIRS)
            for name in sorted(filenames):
                path = Path(dirpath) / name
                text = path.read_bytes().decode("utf-8", errors="ignore")
                for m in CLIENT_ID_PLACEHOLDER.finditer(text):
                    line = text.count("\n", 0, m.start()) + 1
                    found.append(f"{path.relative_to(fx.REPO)}:{line} {m.group(0)}")
        self.assertEqual(found, [], "placeholder client IDs left in the repo")

    def test_builds_are_deterministic(self) -> None:
        a = self.build(self.out / "a")
        b = self.build(self.out / "b")
        self.assertEqual(sorted(a), sorted(b))
        for label in a:
            self.assertEqual(digest(a[label]), digest(b[label]), label)
        with zipfile.ZipFile(a["plugin"]) as zf:
            infos = zf.infolist()
        self.assertEqual({i.date_time for i in infos}, {build_dist.FIXED_DATE})
        self.assertEqual([i.filename for i in infos], sorted(i.filename for i in infos))
        sums = (self.out / "a" / "SHA256SUMS").read_text(encoding="utf-8")
        self.assertIn(f"{digest(a['plugin'])}  frameos-plugin-{self.version}.zip", sums)

    def test_rebuild_replaces_old_outputs(self) -> None:
        out = self.out / "a"
        self.build(out)
        (out / "claude-ai" / "frameos-removed.zip").write_bytes(b"old")
        (out / "frameos-plugin-0.0.0.zip").write_bytes(b"old")
        (out / "frameos-openai-0.0.0.zip").write_bytes(b"old")
        self.build(out)
        self.assertFalse((out / "claude-ai" / "frameos-removed.zip").exists())
        self.assertFalse((out / "frameos-plugin-0.0.0.zip").exists())
        self.assertFalse((out / "frameos-openai-0.0.0.zip").exists())

    def test_default_out_inside_repo_is_not_zipped_into_itself(self) -> None:
        built = build_dist.build(self.root)
        entries = names(built["plugin"])
        self.assertFalse(any(n.startswith("dist/") for n in entries))

    def test_refuses_when_out_of_sync(self) -> None:
        self.write("agent-plugin/skills/frameos-clip/SKILL.md", "tampered\n")
        with self.assertRaises(build_dist.BuildError) as cm:
            self.build(self.out / "a")
        self.assertIn("sync --check failed", str(cm.exception))
        build_dist.build(self.root, self.out / "a", skip_sync_check=True)

    def test_cli_exit_codes(self) -> None:
        args = ["--root", str(self.root), "--out", str(self.out / "c")]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err:
            self.assertEqual(build_dist.main(args), 0)
            self.write("VERSION", "not-a-version\n")
            self.assertEqual(build_dist.main(args), 1)
        self.assertIn("not semver", err.getvalue())


if __name__ == "__main__":
    unittest.main()
