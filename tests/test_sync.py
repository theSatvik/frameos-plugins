"""sync.py: ground-rules rewrite, agent-plugin/skills mirror, --check mode."""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_fixture as fx  # noqa: E402

sync = fx.sync
CLIP_MD = "skills/frameos-clip/SKILL.md"
MIRROR_CLIP_MD = "agent-plugin/skills/frameos-clip/SKILL.md"


def snapshot_tree(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


class GroundRulesTest(fx.FixtureCase):
    def test_check_reports_drift_without_writing(self) -> None:
        self.replace(CLIP_MD, "Never post anything publicly", "Post whatever")
        before = snapshot_tree(self.root)
        result = sync.sync(self.root, check=True)
        self.assertEqual(snapshot_tree(self.root), before, "--check must not write")
        # The mirror already matches what sync would write, so only the source drifts.
        self.assertEqual([(d.kind, d.path) for d in result.drift], [("ground_rules", CLIP_MD)])
        self.assertFalse(result.ok)

    def test_apply_restores_block_and_preserves_the_rest(self) -> None:
        original = self.read(CLIP_MD)
        self.replace(CLIP_MD, "Never post anything publicly", "Post whatever")
        self.replace(CLIP_MD, "## Workflow", "## Workflow (edited)")
        result = sync.sync(self.root)
        self.assertFalse(result.errors)
        self.assertEqual(self.read(CLIP_MD), original.replace("## Workflow", "## Workflow (edited)", 1))
        self.assertEqual(self.read(MIRROR_CLIP_MD), self.read(CLIP_MD))
        self.assertTrue(sync.sync(self.root, check=True).ok, "second run must be clean (idempotent)")

    def test_block_matches_rules_file_exactly(self) -> None:
        rules = self.read("scripts/ground_rules.md")
        text = self.read(CLIP_MD)
        start = text.index(sync.GROUND_START) + len(sync.GROUND_START) + 1
        end = text.index(sync.GROUND_END)
        self.assertEqual(text[start:end], rules.rstrip("\n") + "\n")

    def test_rules_file_change_propagates(self) -> None:
        self.write("scripts/ground_rules.md", self.read("scripts/ground_rules.md") + "- A new rule.\n")
        self.assertFalse(sync.sync(self.root, check=True).ok)
        sync.sync(self.root)
        for name in fx.TITLES:
            self.assertIn("- A new rule.\n" + sync.GROUND_END, self.read(f"skills/{name}/SKILL.md"))
            self.assertIn("- A new rule.\n" + sync.GROUND_END, self.read(f"agent-plugin/skills/{name}/SKILL.md"))

    def test_missing_markers_is_an_error(self) -> None:
        text = self.read(CLIP_MD)
        self.write(CLIP_MD, text.replace(sync.GROUND_START, "").replace(sync.GROUND_END, ""))
        result = sync.sync(self.root)
        self.assertTrue(any(CLIP_MD in e and "no ground-rules block" in e for e in result.errors), result.errors)

    def test_duplicate_markers_is_an_error(self) -> None:
        self.write(CLIP_MD, self.read(CLIP_MD) + "\n" + sync.GROUND_START + "\n")
        result = sync.sync(self.root, check=True)
        self.assertTrue(any("expected exactly one" in e for e in result.errors), result.errors)


class MirrorTest(fx.FixtureCase):
    def test_mirror_is_byte_identical(self) -> None:
        src = snapshot_tree(self.path("skills"))
        dst = snapshot_tree(self.path("agent-plugin/skills"))
        self.assertEqual(src, dst)

    def test_stale_files_and_empty_dirs_are_removed(self) -> None:
        self.write("agent-plugin/skills/frameos-gone/references/x.md", "stale\n")
        self.write("agent-plugin/skills/frameos-clip/references/old.md", "stale\n")
        self.assertFalse(sync.sync(self.root, check=True).ok)
        sync.sync(self.root)
        self.assertFalse(self.path("agent-plugin/skills/frameos-gone").exists())
        self.assertFalse(self.path("agent-plugin/skills/frameos-clip/references/old.md").exists())
        self.assertEqual(snapshot_tree(self.path("skills")), snapshot_tree(self.path("agent-plugin/skills")))

    def test_new_and_changed_files_are_copied(self) -> None:
        self.write("skills/frameos-clip/references/new.md", "new\n")
        self.write(MIRROR_CLIP_MD, "tampered\n")
        drift = {d.path for d in sync.sync(self.root, check=True).drift}
        self.assertIn("agent-plugin/skills/frameos-clip/references/new.md", drift)
        self.assertIn(MIRROR_CLIP_MD, drift)
        sync.sync(self.root)
        self.assertEqual(snapshot_tree(self.path("skills")), snapshot_tree(self.path("agent-plugin/skills")))

    def test_junk_is_not_mirrored_and_is_removed(self) -> None:
        self.path("skills/frameos-clip/.DS_Store").write_bytes(b"x")
        self.path("agent-plugin/skills/frameos-clip/.DS_Store").write_bytes(b"x")
        sync.sync(self.root)
        self.assertFalse(self.path("agent-plugin/skills/frameos-clip/.DS_Store").exists())

    def test_mirror_created_when_missing(self) -> None:
        import shutil

        shutil.rmtree(self.path("agent-plugin/skills"))
        sync.sync(self.root)
        self.assertEqual(snapshot_tree(self.path("skills")), snapshot_tree(self.path("agent-plugin/skills")))


class CliTest(fx.FixtureCase):
    def run_sync(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(fx.SCRIPTS / "sync.py"), "--root", str(self.root), *args],
            capture_output=True, text=True, env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"},
        )

    def test_check_exit_codes(self) -> None:
        self.assertEqual(self.run_sync("--check").returncode, 0)
        self.write(MIRROR_CLIP_MD, "tampered\n")
        proc = self.run_sync("--check")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("DRIFT  " + MIRROR_CLIP_MD, proc.stdout)
        self.assertEqual(self.run_sync().returncode, 0)
        self.assertEqual(self.run_sync("--check").returncode, 0)

    def test_apply_exit_code_on_unfixable_error(self) -> None:
        text = self.read(CLIP_MD)
        self.write(CLIP_MD, text.replace(sync.GROUND_START, ""))
        proc = self.run_sync()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("ERROR", proc.stderr)


if __name__ == "__main__":
    unittest.main()
