"""build_dist.py: ZIP layouts per host, exclusions, determinism, sync gate."""
from __future__ import annotations

import hashlib
import io
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
        for required in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".mcp.json",
                         ".cursor-plugin/plugin.json", "gemini-extension.json", "GEMINI.md", "README.md",
                         "LICENSE", "VERSION", "assets/icon.png", "skills/frameos-clip/SKILL.md",
                         "commands/frameos/clip.toml", "docs/install/codex.md"):
            self.assertIn(required, entries)
        for excluded in ("tests/", "dev/", "evals/", "docs/submission/", ".github/", "dist/", ".git/",
                         "scripts/", "agent-plugin/", ".agents/", ".claude-plugin/marketplace.json"):
            self.assertFalse(any(n.startswith(excluded) for n in entries), f"{excluded} leaked: {entries}")
        self.assertEqual([n for n in entries if n.endswith("plugin.json") and ".claude-plugin" in n],
                         [".claude-plugin/plugin.json"])
        self.assertFalse(any(n.endswith(".DS_Store") for n in entries))

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
        self.build(out)
        self.assertFalse((out / "claude-ai" / "frameos-removed.zip").exists())
        self.assertFalse((out / "frameos-plugin-0.0.0.zip").exists())

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
