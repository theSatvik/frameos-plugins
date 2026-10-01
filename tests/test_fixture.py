"""Shared fixture: a small, known-good copy of the repo in a temp dir.

The fixture copies the real manifests, VERSION, LICENSE, icon, MCP snapshot and
ground rules from this checkout, and writes synthetic skills, Gemini commands,
GEMINI.md and README.md, then runs sync to build the agent-plugin mirror. The
other test modules mutate copies of it (``import test_fixture as fx``).

This module's own test checks that the fixture validates cleanly, so a false
positive in the validator shows up here first.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import sync  # noqa: E402
import validate  # noqa: E402

COPIED = list(validate.MANIFESTS) + [
    "VERSION",
    "LICENSE",
    "assets/icon.png",
    validate.SNAPSHOT,
    "scripts/ground_rules.md",
]

TITLES = {
    "frameos-setup": "Setup",
    "frameos-clip": "Clip",
    "frameos-captions": "Captions",
    "frameos-find-moments": "Find Moments",
    "frameos-thumbnails": "Thumbnails",
    "frameos-publish": "Publish",
    "frameos-library": "Library",
    "frameos-repurpose": "Repurpose",
}

SKILL_TEMPLATE = """---
name: {name}
description: "Synthetic test skill {name}. Use it when the user asks for the {title} part of FrameOS work, and hand adjacent work to the sibling FrameOS skills."
license: MIT
---

# FrameOS {title}

Synthetic skill used by the repo tests.

{block}

## Workflow

1. Call `whoami` once per conversation.
2. Call `submit_video` with `source_url`, `max_clips` and `aspect_ratio`, or `create_upload_link` and then `submit_uploaded_video` with the `gs_path`.
3. Poll `get_job` (see `get_job(job_id)`) until the state is final; the message may say `already_running`.
4. Read `list_projects.progress` (0-100) and call `list_clips`.

Details: [workflow notes](references/notes.md).

```text
export_clip(clip_id) -> {{status: rendering, job_id}}
```
"""

REFERENCE_TEMPLATE = """# Notes for {name}

Query `get_transcript` with `start_ms` and `end_ms` in milliseconds and page with `next_offset`.
Back to the [skill](../SKILL.md).
"""

OPENAI_YAML_TEMPLATE = """interface:
  display_name: "FrameOS {title}"
  short_description: "Synthetic FrameOS {title} test skill"
  default_prompt: "Use ${name} to help with my FrameOS videos."
policy:
  allow_implicit_invocation: true
dependencies:
  tools:
    - type: "mcp"
      value: "frameos"
      description: "FrameOS MCP server"
      transport: "streamable_http"
      url: "https://frameos.studio/mcp"
"""

COMMAND_TEMPLATE = '''description = "FrameOS {title}: synthetic test command"
prompt = """Use the {skill} skill (in this extension's skills/ folder) to handle this request.

Request: {{{{args}}}}"""
'''

README = """# FrameOS plugin (test fixture)

You can turn long videos into short captioned clips from your coding agent. This
synthetic README exists so the validator has enough plain prose to count, and it
deliberately says nothing about prices or offers. Install the plugin, connect
your FrameOS account, then ask your agent to clip a video for you.
"""


def gemini_md() -> str:
    lines = ["# FrameOS", "", "Skills:"]
    lines += [f"- {name}: the {title} skill." for name, title in TITLES.items()]
    lines += ["", "Call `whoami` first."]
    return "\n".join(lines) + "\n"


def build_fixture_repo(dest: Path) -> Path:
    """Create a valid fixture repo at ``dest`` (must not exist) and return it."""
    dest = Path(dest)
    dest.mkdir(parents=True)
    for rel in COPIED:
        src = REPO / rel
        if not src.is_file():
            raise unittest.SkipTest(f"fixture source {rel} is missing from the repo")
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
    rules = sync.load_ground_rules(dest)
    block = sync.render_block(rules)
    for name, title in TITLES.items():
        sdir = dest / "skills" / name
        (sdir / "references").mkdir(parents=True)
        (sdir / "agents").mkdir()
        (sdir / "SKILL.md").write_text(SKILL_TEMPLATE.format(name=name, title=title, block=block), encoding="utf-8")
        (sdir / "references" / "notes.md").write_text(REFERENCE_TEMPLATE.format(name=name), encoding="utf-8")
        (sdir / "agents" / "openai.yaml").write_text(OPENAI_YAML_TEMPLATE.format(name=name, title=title), encoding="utf-8")
    cmd_dir = dest / "commands" / "frameos"
    cmd_dir.mkdir(parents=True)
    for cmd, skill in validate.GEMINI_COMMANDS.items():
        (cmd_dir / f"{cmd}.toml").write_text(COMMAND_TEMPLATE.format(title=TITLES[skill], skill=skill), encoding="utf-8")
    (dest / "GEMINI.md").write_text(gemini_md(), encoding="utf-8")
    (dest / "README.md").write_text(README, encoding="utf-8")
    result = sync.sync(dest)
    if result.errors:
        raise RuntimeError(f"fixture sync failed: {result.errors}")
    return dest


class FixtureCase(unittest.TestCase):
    """Base class: ``self.root`` is a fresh fixture repo per test."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="frameos-fixture-")
        self.addCleanup(self._tmp.cleanup)
        self.root = build_fixture_repo(Path(self._tmp.name) / "repo")

    # helpers -------------------------------------------------------------
    def path(self, rel: str) -> Path:
        return self.root / rel

    def read(self, rel: str) -> str:
        return self.path(rel).read_text(encoding="utf-8")

    def write(self, rel: str, text: str) -> None:
        p = self.path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def replace(self, rel: str, old: str, new: str) -> None:
        text = self.read(rel)
        self.assertIn(old, text, f"fixture text to replace not found in {rel}")
        self.write(rel, text.replace(old, new, 1))

    def errors(self) -> list:
        return validate.run(self.root).errors

    def assertError(self, *fragments: str) -> list:
        errs = self.errors()
        for e in errs:
            if all(f in e for f in fragments):
                return errs
        self.fail(f"no error containing {fragments!r}; got:\n  " + "\n  ".join(errs or ["(no errors)"]))

    def assertNoErrors(self) -> None:
        """Re-sync the mirror (edits to skills/ are expected), then require zero errors."""
        sync.sync(self.root)
        errs = self.errors()
        self.assertEqual(errs, [], "unexpected errors:\n  " + "\n  ".join(errs))


class FixtureIsValidTest(FixtureCase):
    def test_fixture_validates_without_errors(self) -> None:
        self.assertNoErrors()

    def test_fixture_sync_check_is_clean(self) -> None:
        result = sync.sync(self.root, check=True)
        self.assertTrue(result.ok, [str(d) for d in result.drift] + result.errors)


if __name__ == "__main__":
    unittest.main()
