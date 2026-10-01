# Contributing

Thanks for helping. This repo is the FrameOS plugin for many agent hosts at once, so a small mistake in one file can break an install somewhere you didn't test. The rules below exist for that reason, and `scripts/validate.py` enforces most of them.

## Setup

- Python 3.9 or later for the scripts (standard library only). Python 3.11+ also lets the validator fully parse the Gemini command TOML files.
- Optional: [`uv`](https://docs.astral.sh/uv/) to run the mock server (`uv run --script dev/mock_server.py`), and Claude Code and the Codex CLI for host checks.

Before every pull request:

```bash
python3 scripts/sync.py
python3 scripts/test.py
claude plugin validate . --strict
claude plugin validate .claude-plugin/plugin.json --strict
```

## Repo layout

The repo root is the plugin. [README.md](README.md#packages-in-this-repo) has the table of which file serves which host. In short: one set of skills in `skills/`, one manifest per host, and an Agent Plugins copy in `agent-plugin/`.

## Hard rules

- **No hooks, no executables.** No `hooks/` folder, no `hooks` key in any manifest, no lifecycle scripts, and no top-level `bin/` (claude.ai and Cowork refuse a plugin that has one).
- **No `CLAUDE.md` or `AGENTS.md` at the root.** Claude's strict validation warns, and Devin would load `AGENTS.md` into every user's context.
- **No secrets** anywhere, including test fixtures and examples. The connector uses OAuth; nothing in this repo needs a key.
- **No `.DS_Store`**, and no file over 256 KiB unless it is an image.
- **Never hand-edit versions.** Use `python3 scripts/bump_version.py X.Y.Z` ([RELEASING.md](RELEASING.md)).
- **Never edit `agent-plugin/skills/`.** It is a byte-for-byte copy of `skills/` written by `python3 scripts/sync.py` (hosts reject symlinks that leave the plugin folder).
- **Contact address:** use only support@frameos.studio and https://frameos.studio/contact. Do not add any other FrameOS email address.

## Writing skills

Each skill is `skills/<name>/SKILL.md`, optional `references/*.md`, and a required `agents/openai.yaml`.

- **Portable frontmatter only:** `name`, `description`, `license`. No other keys (`allowed-tools`, `argument-hint`, `metadata`, `compatibility` and the rest are host-specific and break somewhere).
  - `name` equals the folder name: lowercase letters, digits and single hyphens, at most 64 characters.
  - `description` is at most 1,024 characters (aim for 300 to 600), contains no `<` or `>`, and says what the skill does, when to use it, and which sibling skill owns the neighbouring job.
  - `license: MIT`.
- **Length:** aim for 250 lines or fewer per `SKILL.md`; 500 is the hard limit. Keep each reference under 200 lines, linked directly from `SKILL.md` (one level deep).
- **Ground rules:** every skill starts with the block between `<!-- ground-rules:start -->` and `<!-- ground-rules:end -->`. Edit [`scripts/ground_rules.md`](scripts/ground_rules.md), never the copies, then run `python3 scripts/sync.py`.
- **Tool names:** write bare names in backticks (`submit_video`, not a host-prefixed name), because every host prefixes differently. Only the 27 tools in [`tests/fixtures/mcp-snapshot.json`](tests/fixtures/mcp-snapshot.json) exist; the validator fails on anything that looks like an unknown tool.
- **User-facing language:** "your clips", "the render", "your FrameOS credits". No raw IDs, storage paths, tool names or HTTP codes in what the agent says, unless the user asks.
- **Facts:** every product behaviour must match what the connector actually does. Never quote prices, plan allotments, trial offers or discount codes (the validator rejects prices and codes); link https://frameos.studio/pricing and use the account tools for the live balance. Don't promise features that aren't available through the tools.
- **`agents/openai.yaml`:** `interface.display_name`, `short_description` (25 to 64 characters), `default_prompt` (128 characters or fewer, naming the skill as `$frameos-...`), `policy.allow_implicit_invocation`, and the `frameos` MCP dependency. Quote every string value.

## When the connector changes

1. Capture a fresh `tools/list` (and `initialize`) response from the real server into [`tests/fixtures/mcp-snapshot.json`](tests/fixtures/mcp-snapshot.json).
2. Update [`dev/mock_server.py`](dev/mock_server.py) to match; a test checks that its tools, parameters and annotations equal the snapshot.
3. Update the skills, the eval mocks in [`evals/`](evals/), and any doc that names a changed tool or behaviour.

## Docs

- Install steps must be exact and come from the host's own documentation or a real run. Mark anything you haven't checked on a real account as "not yet verified".
- Keep [docs/status.md](docs/status.md) honest about what has been verified on which host.
- Keep the README written for creators: what they can say to their agent, then how to install.

## Testing without touching your own setup

- Mock server: see [dev/README.md](dev/README.md).
- Use throwaway profiles for install tests: `CLAUDE_CONFIG_DIR=$(mktemp -d)` for Claude Code and `CODEX_HOME=$(mktemp -d)` for Codex. A `frameos` server in your own `~/.codex/config.toml` hides the plugin's server of the same name.
- When you run Claude Code inside this repo, it also offers the root `.mcp.json` as a project MCP server (shown as pending approval). That is the plugin's own connection file; approve it only if you mean to test against it.

## License

By contributing you agree that your contributions are licensed under the [MIT License](LICENSE).
