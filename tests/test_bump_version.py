"""bump_version.py: updates every version site, round-trips byte for byte, refuses bad input."""
from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_fixture as fx  # noqa: E402

import bump_version  # noqa: E402  (scripts/ is on sys.path via test_fixture)

validate = fx.validate
DOC = "docs/install/vscode-copilot.md"
DOC_TEXT = '# VS Code\n\n```json\n{{"headers": {{"X-FrameOS-Plugin-Version": "{v}"}}}}\n```\n'


def tree(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


class BumpVersionTest(fx.FixtureCase):
    def setUp(self) -> None:
        super().setUp()
        self.old = self.read("VERSION").strip()
        self.write(DOC, DOC_TEXT.format(v=self.old))
        self.write("CHANGELOG.md", f"# Changelog\n\n## {self.old}\n\n- X-FrameOS-Plugin-Version: {self.old} header added.\n")

    def bump(self, *args: str) -> int:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = bump_version.main([*args, "--root", str(self.root)])
        self.output = out.getvalue() + err.getvalue()
        return code

    def test_bump_updates_every_site(self) -> None:
        self.assertEqual(self.bump("9.8.7"), 0, self.output)
        self.assertEqual(self.read("VERSION"), "9.8.7\n")
        for name, path in validate.VERSION_SITES:
            found, value = validate.get_path(json.loads(self.read(name)), path)
            self.assertTrue(found, f"{name} {path}")
            self.assertEqual(value, "9.8.7", f"{name} {validate.fmt_path(path)}")
        self.assertIn('"X-FrameOS-Plugin-Version": "9.8.7"', self.read(DOC))
        self.assertIn(f"X-FrameOS-Plugin-Version: {self.old} header added", self.read("CHANGELOG.md"), "CHANGELOG is history")
        report = validate.run(self.root)
        version_errors = [e for e in report.errors if "VERSION" in e or "version" in e]
        self.assertEqual(version_errors, [])
        self.assertEqual(report.errors, [])

    def test_round_trip_is_byte_identical(self) -> None:
        before = tree(self.root)
        self.assertEqual(self.bump("9.8.7"), 0, self.output)
        self.assertNotEqual(tree(self.root), before)
        self.assertEqual(self.bump(self.old, "--allow-downgrade"), 0, self.output)
        after = tree(self.root)
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        self.assertEqual(changed, [], "files differ after bumping there and back")

    def test_rejects_non_semver(self) -> None:
        before = tree(self.root)
        for bad in ("1.2", "v1.2.3", "01.2.3", "1.2.3.4", "latest", ""):
            with self.subTest(bad=bad):
                self.assertEqual(self.bump(bad), 2)
                self.assertIn("not a semantic version", self.output)
        self.assertEqual(tree(self.root), before)

    def test_prerelease_is_accepted(self) -> None:
        self.assertEqual(self.bump("9.0.0-rc.1"), 0, self.output)
        self.assertEqual(self.read("VERSION"), "9.0.0-rc.1\n")

    def test_refuses_downgrade_without_flag(self) -> None:
        self.assertEqual(self.bump("9.0.0"), 0, self.output)
        self.assertEqual(self.bump("8.0.0"), 2)
        self.assertIn("--allow-downgrade", self.output)
        self.assertEqual(self.read("VERSION"), "9.0.0\n")

    def test_dry_run_writes_nothing(self) -> None:
        before = tree(self.root)
        self.assertEqual(self.bump("9.8.7", "--dry-run"), 0, self.output)
        self.assertIn("would update .mcp.json", self.output)
        self.assertEqual(tree(self.root), before)

    def test_missing_site_aborts_before_writing(self) -> None:
        data = json.loads(self.read(".cursor-plugin/plugin.json"))
        del data["version"]
        self.write(".cursor-plugin/plugin.json", json.dumps(data, indent=2) + "\n")
        before = tree(self.root)
        self.assertEqual(self.bump("9.8.7"), 1)
        self.assertIn(".cursor-plugin/plugin.json: version not found", self.output)
        self.assertEqual(tree(self.root), before)

    def test_extra_header_in_other_json_is_updated(self) -> None:
        self.write("dev/mock.mcp.json", json.dumps({"mcpServers": {"frameos": {"headers": {"X-FrameOS-Plugin-Version": self.old}}}}, indent=2) + "\n")
        self.assertEqual(self.bump("9.8.7"), 0, self.output)
        self.assertIn('"X-FrameOS-Plugin-Version": "9.8.7"', self.read("dev/mock.mcp.json"))


if __name__ == "__main__":
    unittest.main()
