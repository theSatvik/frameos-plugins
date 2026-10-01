"""validate.py passes on a known-good fixture and fails, with the right message,
on broken copies of it. Also covers the YAML subset parser and the CLI."""
from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_fixture as fx  # noqa: E402

validate = fx.validate
sync = fx.sync

CLIP_MD = "skills/frameos-clip/SKILL.md"
REAL_COPY_IGNORE = shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc", ".venv", "node_modules", ".DS_Store")


def _png(width: int, height: int) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\x00" * (width * 3) for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


class FrontmatterTest(fx.FixtureCase):
    def test_extra_frontmatter_key(self) -> None:
        self.replace(CLIP_MD, "license: MIT\n", "license: MIT\nallowed-tools: Bash\n")
        self.assertError(CLIP_MD, "allowed-tools", "not portable")

    def test_name_must_match_directory(self) -> None:
        self.replace(CLIP_MD, "name: frameos-clip", "name: frameos-clips")
        self.assertError(CLIP_MD, "must equal the directory name")

    def test_description_angle_brackets(self) -> None:
        self.replace(CLIP_MD, "Synthetic test skill", "Synthetic <b>test</b> skill")
        self.assertError(CLIP_MD, "'<' or '>'")

    def test_description_too_long(self) -> None:
        self.replace(CLIP_MD, "Synthetic test skill", "x" * 1100)
        self.assertError(CLIP_MD, "the limit is 1024")

    def test_unquoted_colon_in_description(self) -> None:
        self.replace(CLIP_MD, 'description: "Synthetic test skill frameos-clip.', "description: Synthetic test: skill frameos-clip.")
        # remove the now-unbalanced closing quote
        text = self.read(CLIP_MD).replace('sibling FrameOS skills."', "sibling FrameOS skills.", 1)
        self.write(CLIP_MD, text)
        self.assertError(CLIP_MD, "quote the value")

    def test_missing_frontmatter(self) -> None:
        text = self.read(CLIP_MD)
        self.write(CLIP_MD, text.split("---\n", 2)[2])
        self.assertError(CLIP_MD, "must start with YAML frontmatter")

    def test_block_scalar_description_is_accepted(self) -> None:
        text = self.read(CLIP_MD)
        start = text.index("description:")
        end = text.index("\n", start)
        self.write(CLIP_MD, text[:start] + "description: >-\n  Use this skill to clip long videos into shorts with FrameOS,\n  and hand captions, thumbnails and posting to the sibling skills." + text[end:])
        self.assertNoErrors()


class BodyTest(fx.FixtureCase):
    def test_skill_over_500_lines(self) -> None:
        self.write(CLIP_MD, self.read(CLIP_MD) + "\nfiller line\n" * 520)
        self.assertError(CLIP_MD, "hard limit is 500")

    def test_empty_body(self) -> None:
        text = self.read(CLIP_MD)
        fm_end = text.index("---\n", 4) + 4
        self.write(CLIP_MD, text[:fm_end] + "\n")
        self.assertError(CLIP_MD, "body is empty")

    def test_ground_rules_drift(self) -> None:
        self.replace(CLIP_MD, "Never post anything publicly", "Never post anything")
        self.assertError(CLIP_MD, "ground-rules block differs")

    def test_ground_rules_markers_missing(self) -> None:
        text = self.read(CLIP_MD)
        self.write(CLIP_MD, text.replace(sync.GROUND_START, "").replace(sync.GROUND_END, ""))
        self.assertError(CLIP_MD, "needs exactly one ground-rules block")

    def test_ground_rules_after_a_section(self) -> None:
        self.replace(CLIP_MD, "Synthetic skill used by the repo tests.\n", "Synthetic skill used by the repo tests.\n\n## Early section\n")
        self.assertError(CLIP_MD, "right after the H1 title")

    def test_broken_relative_link(self) -> None:
        self.replace(CLIP_MD, "(references/notes.md)", "(references/missing.md)")
        self.assertError(CLIP_MD, "broken relative link 'references/missing.md'")

    def test_link_outside_skill(self) -> None:
        self.replace(CLIP_MD, "(references/notes.md)", "(../frameos-setup/SKILL.md)")
        self.assertError(CLIP_MD, "points outside skills/frameos-clip/")

    def test_links_inside_code_are_ignored(self) -> None:
        self.replace(CLIP_MD, "## Workflow", "`[not a link](nowhere.md)`\n\n## Workflow")
        self.assertNoErrors()


class ToolTokenTest(fx.FixtureCase):
    def test_unknown_backticked_tool(self) -> None:
        self.replace(CLIP_MD, "## Workflow\n", "## Workflow\n\nThen call `get_video` for the details.\n")
        self.assertError(CLIP_MD, "`get_video` looks like a tool name", "not one of the 27")

    def test_unknown_tool_in_reference(self) -> None:
        ref = "skills/frameos-clip/references/notes.md"
        self.write(ref, self.read(ref) + "\nUse `start_processing` to begin.\n")
        self.assertError(ref, "`start_processing`")

    def test_unknown_tool_call_form(self) -> None:
        self.replace(CLIP_MD, "## Workflow\n", "## Workflow\n\nRun `fetch_clips(project_id)`.\n")
        self.assertError(CLIP_MD, "calls `fetch_clips`")

    def test_unknown_tool_call_in_code_block(self) -> None:
        self.replace(CLIP_MD, "export_clip(clip_id)", "render_clip(clip_id)")
        self.assertError(CLIP_MD, "`render_clip(...)` is called like a tool")

    def test_prefixed_tool_name(self) -> None:
        self.replace(CLIP_MD, "## Workflow\n", "## Workflow\n\nCall `mcp__frameos__submit_video`.\n")
        self.assertError(CLIP_MD, "bare tool names")

    def test_suggests_close_match(self) -> None:
        self.replace(CLIP_MD, "## Workflow\n", "## Workflow\n\nCall `list_clip`.\n")
        self.assertError(CLIP_MD, "Did you mean `list_clips`")

    def test_parameter_and_field_names_are_allowed(self) -> None:
        self.replace(CLIP_MD, "## Workflow\n", "## Workflow\n\nPass `focus_prompt`, `start_ms`, `include_words`; read `upload_url`, `eta_seconds`, `source_too_short`.\n")
        self.assertNoErrors()

    def test_gemini_command_prompt_checked(self) -> None:
        rel = "commands/frameos/clip.toml"
        self.replace(rel, "to handle this request.", "to handle this request with `make_clips`.")
        self.assertError(rel, "`make_clips`")


class OpenAIYamlTest(fx.FixtureCase):
    REL = "skills/frameos-clip/agents/openai.yaml"

    def test_missing_openai_yaml(self) -> None:
        self.path(self.REL).unlink()
        self.assertError(self.REL, "missing")

    def test_default_prompt_too_long(self) -> None:
        self.replace(self.REL, "to help with my FrameOS videos.", "to help " + "x" * 130)
        self.assertError(self.REL, "default_prompt is", "the limit is 128")

    def test_default_prompt_must_name_skill(self) -> None:
        self.replace(self.REL, "Use $frameos-clip to", "Use FrameOS to")
        self.assertError(self.REL, "must name the skill as $frameos-clip")

    def test_default_prompt_required(self) -> None:
        self.replace(self.REL, '  default_prompt: "Use $frameos-clip to help with my FrameOS videos."\n', "")
        self.assertError(self.REL, "default_prompt is required")

    def test_display_name_required(self) -> None:
        self.replace(self.REL, '  display_name: "FrameOS Clip"\n', "")
        self.assertError(self.REL, "display_name is required")

    def test_icon_keys_rejected(self) -> None:
        self.replace(self.REL, "interface:\n", 'interface:\n  icon_small: "./icon.svg"\n')
        self.assertError(self.REL, "icon_small")

    def test_wrong_dependency_url(self) -> None:
        self.replace(self.REL, 'url: "https://frameos.studio/mcp"', 'url: "https://frameos.studio/mcp/"')
        self.assertError(self.REL, "url must be https://frameos.studio/mcp")


class VersionTest(fx.FixtureCase):
    def _edit_json(self, rel: str, fn) -> None:
        data = json.loads(self.read(rel))
        fn(data)
        self.write(rel, json.dumps(data, indent=2) + "\n")

    def test_manifest_version_drift(self) -> None:
        self._edit_json(".cursor-plugin/plugin.json", lambda d: d.__setitem__("version", "9.9.9"))
        self.assertError(".cursor-plugin/plugin.json", "version is '9.9.9'")

    def test_marketplace_entry_drift(self) -> None:
        self._edit_json(".claude-plugin/marketplace.json", lambda d: d["plugins"][0].__setitem__("version", "9.9.9"))
        self.assertError(".claude-plugin/marketplace.json", "plugins[name=frameos].version")

    def test_header_drift(self) -> None:
        self._edit_json(".mcp.json", lambda d: d["mcpServers"]["frameos"]["http_headers"].__setitem__(validate.VERSION_HEADER, "0.0.1"))
        self.assertError(".mcp.json", "http_headers", "'0.0.1'")

    def test_missing_header(self) -> None:
        self._edit_json("agent-plugin/mcp.json", lambda d: d["mcpServers"]["frameos"].pop("headers"))
        self.assertError("agent-plugin/mcp.json", "is missing")

    def test_not_semver(self) -> None:
        self.write("VERSION", "1.0\n")
        self.assertError("VERSION", "not a semantic version")

    def test_header_in_docs_drift(self) -> None:
        self.write("docs/install/vscode.md", '# VS Code\n\n```json\n"X-FrameOS-Plugin-Version": "0.0.7"\n```\n')
        self.assertError("docs/install/vscode.md:4", "'0.0.7'")


class McpConfigTest(fx.FixtureCase):
    def _edit_json(self, rel: str, fn) -> None:
        data = json.loads(self.read(rel))
        fn(data)
        self.write(rel, json.dumps(data, indent=2) + "\n")

    def test_wrong_gemini_url(self) -> None:
        self._edit_json("gemini-extension.json", lambda d: d["mcpServers"]["frameos"].__setitem__("httpUrl", "https://frameos.studio/api/mcp"))
        self.assertError("gemini-extension.json", "httpUrl must be https://frameos.studio/mcp")

    def test_oauth_resource_mismatch(self) -> None:
        self._edit_json(".mcp.json", lambda d: d["mcpServers"]["frameos"].__setitem__("oauth_resource", "https://frameos.studio"))
        self.assertError(".mcp.json", "oauth_resource must equal url")

    def test_two_servers(self) -> None:
        self._edit_json(".mcp.json", lambda d: d["mcpServers"].__setitem__("other", {"type": "http", "url": "https://example.com/mcp"}))
        self.assertError(".mcp.json", "exactly one MCP server named 'frameos'")

    def test_agent_plugin_transport(self) -> None:
        self._edit_json("agent-plugin/mcp.json", lambda d: d["mcpServers"]["frameos"].__setitem__("type", "sse"))
        self.assertError("agent-plugin/mcp.json", "streamable-http")

    def test_agent_plugin_extra_key(self) -> None:
        self._edit_json("agent-plugin/plugin.json", lambda d: d.__setitem__("skills", "./skills"))
        self.assertError("agent-plugin/plugin.json", "not allowed by the Agent Plugins 1.0 schema", "skills")

    def test_cursor_extra_key(self) -> None:
        self._edit_json(".cursor-plugin/plugin.json", lambda d: d.__setitem__("interface", {}))
        self.assertError(".cursor-plugin/plugin.json", "not in the Cursor plugin schema", "interface")

    def test_duplicate_json_key(self) -> None:
        text = self.read(".mcp.json")
        self.write(".mcp.json", text.replace('"type": "http",', '"type": "http",\n      "type": "http",', 1))
        self.assertError(".mcp.json", "duplicate key")


class CodexTest(fx.FixtureCase):
    REL = ".codex-plugin/plugin.json"

    def _itf(self, fn) -> None:
        data = json.loads(self.read(self.REL))
        fn(data["interface"])
        self.write(self.REL, json.dumps(data, indent=2) + "\n")

    def test_default_prompt_over_128(self) -> None:
        self._itf(lambda i: i.__setitem__("defaultPrompt", ["x" * 129]))
        self.assertError(self.REL, "defaultPrompt[0] is 129 characters")

    def test_too_many_default_prompts(self) -> None:
        self._itf(lambda i: i.__setitem__("defaultPrompt", ["a", "b", "c", "d"]))
        self.assertError(self.REL, "1 to 3 entries")

    def test_short_description_over_30(self) -> None:
        self._itf(lambda i: i.__setitem__("shortDescription", "y" * 31))
        self.assertError(self.REL, "shortDescription", "at most 30")

    def test_missing_required_field(self) -> None:
        self._itf(lambda i: i.pop("supportURL"))
        self.assertError(self.REL, "interface.supportURL is required")

    def test_logo_must_exist(self) -> None:
        self._itf(lambda i: i.__setitem__("logo", "./assets/nope.png"))
        self.assertError(self.REL, "interface.logo './assets/nope.png' does not exist")

    def test_http_url_rejected(self) -> None:
        self._itf(lambda i: i.__setitem__("privacyPolicyURL", "http://frameos.studio/privacy"))
        self.assertError(self.REL, "privacyPolicyURL must be an https URL")


class FilesTest(fx.FixtureCase):
    def test_root_bin(self) -> None:
        self.write("bin/frameos", "#!/bin/sh\n")
        self.assertError("bin: forbidden at the repo root")

    def test_hooks_dir(self) -> None:
        self.write("hooks/hooks.json", "{}\n")
        self.assertError("hooks: forbidden at the repo root")

    def test_hooks_json_anywhere(self) -> None:
        self.write(".claude-plugin/hooks.json", "{}\n")
        self.assertError(".claude-plugin/hooks.json", "lifecycle hooks")

    def test_claude_md_and_agents_md(self) -> None:
        self.write("CLAUDE.md", "# no\n")
        self.write("AGENTS.md", "# no\n")
        self.assertError("CLAUDE.md: forbidden")
        self.assertError("AGENTS.md: forbidden")

    def test_ds_store(self) -> None:
        self.path("skills/frameos-clip/.DS_Store").write_bytes(b"\x00\x00")
        self.assertError("skills/frameos-clip/.DS_Store")

    def test_large_file(self) -> None:
        self.write("docs/big.md", "a" * (300 * 1024))
        self.assertError("docs/big.md", "over 256 KiB")

    def test_large_image_allowed(self) -> None:
        self.path("assets/big.png").write_bytes(b"\x00" * (300 * 1024))
        self.assertNoErrors()

    def test_secret_detected(self) -> None:
        fake = "AKIA" + "ABCDEFGHIJKLMNOP"
        self.write("docs/notes.md", f"key = {fake}\n")
        self.assertError("docs/notes.md:1", "AWS access key id")

    def test_private_key_detected(self) -> None:
        self.write("dev/key.txt", "-" * 5 + "BEGIN PRIVATE KEY" + "-" * 5 + "\nabc\n")
        self.assertError("dev/key.txt:1", "PEM block")

    def test_wrong_contact_address(self) -> None:
        self.write("docs/contact.md", "Write to " + "hello" + "@frameos.studio\n")
        self.assertError("docs/contact.md:1", "support@frameos.studio")

    def test_rule_forbidding_the_address_is_allowed(self) -> None:
        self.write("docs/contact.md", "Contact support@frameos.studio. Never " + "hello" + "@frameos.studio.\n")
        self.assertNoErrors()

    def test_price_in_skill(self) -> None:
        self.replace(CLIP_MD, "## Workflow\n", "## Workflow\n\nPlans start at $19 a month.\n")
        self.assertError(CLIP_MD, "states a price ($19)")

    def test_discount_code(self) -> None:
        self.write("docs/offer.md", "Use code " + "FRAMEOS" + "50 today.\n")
        self.assertError("docs/offer.md:1", "discount code")

    def test_dollar_skill_reference_is_not_a_price(self) -> None:
        self.write("docs/prompts.md", "Try: Use $frameos-clip to clip it. In awk use {print $1}.\n")
        self.assertNoErrors()

    def test_readme_too_short(self) -> None:
        self.write("README.md", "# FrameOS\n\nShort.\n")
        self.assertError("README.md", "words of prose")

    def test_license_missing(self) -> None:
        self.path("LICENSE").unlink()
        self.assertError("LICENSE", "missing")

    def test_icon_not_square(self) -> None:
        self.path("assets/icon.png").write_bytes(_png(1024, 512))
        self.assertError("assets/icon.png", "must be square")

    def test_icon_too_small(self) -> None:
        self.path("assets/icon.png").write_bytes(_png(256, 256))
        self.assertError("assets/icon.png", "at least 512x512")

    def test_missing_skill(self) -> None:
        shutil.rmtree(self.path("skills/frameos-library"))
        sync.sync(self.root)
        self.assertError("skills/frameos-library", "missing expected skill")

    def test_directory_without_skill_md(self) -> None:
        self.write("skills/_shared/notes.md", "shared\n")
        self.assertError("skills/_shared", "without SKILL.md")

    def test_missing_command(self) -> None:
        self.path("commands/frameos/moments.toml").unlink()
        self.assertError("commands/frameos/moments.toml", "missing", "frameos-find-moments")

    def test_command_must_name_skill(self) -> None:
        self.replace("commands/frameos/publish.toml", "frameos-publish", "the publishing")
        self.assertError("commands/frameos/publish.toml", "must name the frameos-publish skill")

    def test_gemini_context_file_missing(self) -> None:
        self.path("GEMINI.md").unlink()
        self.assertError("gemini-extension.json", "contextFileName")


class MirrorTest(fx.FixtureCase):
    def test_mirror_file_differs(self) -> None:
        rel = "agent-plugin/skills/frameos-clip/SKILL.md"
        self.write(rel, self.read(rel) + "\nextra\n")
        self.assertError(rel, "differs from skills/frameos-clip/SKILL.md")

    def test_mirror_stale_file(self) -> None:
        rel = "agent-plugin/skills/frameos-old/SKILL.md"
        self.write(rel, "old\n")
        self.assertError(rel, "stale")

    def test_mirror_missing(self) -> None:
        shutil.rmtree(self.path("agent-plugin/skills"))
        self.assertError("agent-plugin/skills/frameos-clip/SKILL.md", "missing from the mirror")


class MiscTest(fx.FixtureCase):
    def test_unpinned_workflow_action(self) -> None:
        self.write(".github/workflows/ci.yml", "jobs:\n  t:\n    steps:\n      - uses: actions/checkout@v4\n")
        self.assertError(".github/workflows/ci.yml:4", "full 40-character commit SHA")

    def test_pinned_workflow_action(self) -> None:
        self.write(".github/workflows/ci.yml", "jobs:\n  t:\n    steps:\n      - uses: actions/checkout@" + "a" * 40 + " # v9\n")
        self.assertNoErrors()

    def test_evals_unknown_tool(self) -> None:
        self.write("evals/case/graders/g.md", "tool_used: mcp__plugin_frameos_frameos__make_clip\n")
        self.assertError("evals/case/graders/g.md:1", "unknown tool 'make_clip'")

    def test_invalid_json_anywhere(self) -> None:
        self.write("evals/mocks/frameos/_tools.json", "{not json")
        self.assertError("evals/mocks/frameos/_tools.json", "invalid JSON")


class RealRepoCopyTest(unittest.TestCase):
    """The real checkout, copied and synced, validates; breaking the copy is caught.

    The agent-plugin/skills mirror is generated, so the copy is synced first;
    an unsynced checkout is reported by the 'sync --check' step of test.py.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="frameos-real-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "repo"
        shutil.copytree(fx.REPO, self.root, ignore=REAL_COPY_IGNORE)
        shutil.rmtree(self.root / "evals" / "results", ignore_errors=True)
        result = sync.sync(self.root)
        if not (self.root / "skills").is_dir():
            self.skipTest("skills/ not written yet")
        self.assertEqual(result.errors, [], "sync could not run on the real repo copy")

    def test_real_repo_copy_validates(self) -> None:
        errs = validate.run(self.root).errors
        self.assertEqual(errs, [], "validate.py errors on the real repo (after sync):\n  " + "\n  ".join(errs))

    def test_real_repo_copy_breakages_are_caught(self) -> None:
        (self.root / "bin").mkdir()
        (self.root / "VERSION").write_text("7.7.7\n", encoding="utf-8")
        errs = "\n".join(validate.run(self.root).errors)
        self.assertIn("bin: forbidden at the repo root", errs)
        self.assertIn(".claude-plugin/plugin.json: version is", errs)
        self.assertIn("VERSION is '7.7.7'", errs)


class MiniYamlTest(unittest.TestCase):
    def parse(self, text: str):
        return validate.parse_mini_yaml(text)[0]

    def test_nested_sequence_of_mappings(self) -> None:
        text = fx.OPENAI_YAML_TEMPLATE.format(name="frameos-clip", title="Clip")
        data = self.parse(text)
        self.assertEqual(data["dependencies"]["tools"][0]["url"], "https://frameos.studio/mcp")
        self.assertIs(data["policy"]["allow_implicit_invocation"], True)

    def test_flow_list_and_comments(self) -> None:
        data = self.parse('policy:\n  products: ["CHAT", "CODEX"]  # gating\n  n: 3\n')
        self.assertEqual(data, {"policy": {"products": ["CHAT", "CODEX"], "n": 3}})

    def test_block_scalars(self) -> None:
        data = self.parse("a: |\n  one\n  two\nb: >-\n  three\n  four\n")
        self.assertEqual(data, {"a": "one\ntwo\n", "b": "three four"})

    def test_plain_marked_and_quoted_unescaped(self) -> None:
        data = self.parse('a: plain words\nb: "q \\"x\\" \\u00e9"\nc: \'it\'\'s\'\n')
        self.assertIsInstance(data["a"], validate.PlainStr)
        self.assertEqual(data["b"], 'q "x" \u00e9')
        self.assertEqual(data["c"], "it's")

    def test_errors(self) -> None:
        for bad in ("a: b: c\n", "a: 1\na: 2\n", "a:\n\tb: 1\n", 'a: "open\n', "a: [1, [2]]\n"):
            with self.subTest(bad=bad), self.assertRaises(validate.MiniYAMLError):
                self.parse(bad)

    def test_comment_note(self) -> None:
        _, notes = validate.parse_mini_yaml("description: tips #1 and #2\n")
        self.assertTrue(any("YAML comment" in n for n in notes))

    def test_agrees_with_pyyaml_when_available(self) -> None:
        try:
            import yaml  # type: ignore
        except ImportError:
            self.skipTest("PyYAML not installed")
        samples = [
            fx.OPENAI_YAML_TEMPLATE.format(name="frameos-clip", title="Clip"),
            'name: x\ndescription: "Use when: always"\nlicense: MIT\n',
            "k: >\n  folded\n  text\n\n  para\n",
            "l:\n- a\n- b: 1\n  c: two\n",
        ]
        for s in samples:
            with self.subTest(s=s):
                self.assertEqual(json.dumps(self.parse(s)), json.dumps(yaml.safe_load(s)))


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="frameos-cli-")
        self.addCleanup(self._tmp.cleanup)
        self.root = fx.build_fixture_repo(Path(self._tmp.name) / "repo")

    def run_validate(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(fx.SCRIPTS / "validate.py"), "--root", str(self.root), *extra],
            capture_output=True, text=True, env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"},
        )

    def test_exit_zero_on_valid_repo(self) -> None:
        proc = self.run_validate()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("0 error(s)", proc.stdout)

    def test_exit_one_with_message_on_broken_repo(self) -> None:
        (self.root / "bin").mkdir()
        proc = self.run_validate()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("ERROR  bin: forbidden at the repo root", proc.stdout)

    def test_strict_fails_on_warnings(self) -> None:
        clip = self.root / CLIP_MD
        clip.write_text(clip.read_text(encoding="utf-8") + "\nAn em dash \u2014 here.\n", encoding="utf-8")
        sync.sync(self.root)
        self.assertEqual(self.run_validate().returncode, 0)
        self.assertEqual(self.run_validate("--strict").returncode, 1)


if __name__ == "__main__":
    unittest.main()
