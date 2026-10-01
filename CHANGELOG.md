# Changelog

All notable changes to the FrameOS plugin, skills and extension packages. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/). The canonical version is in [`VERSION`](VERSION).

## [Unreleased]

## [0.1.0] - not yet released

First version. The hosted FrameOS connector (`https://frameos.studio/mcp`) is not live yet, so nothing in this release has been verified against a live FrameOS account ([status](docs/status.md)).

### Added

- Eight skills: frameos-setup, frameos-clip, frameos-captions, frameos-find-moments, frameos-thumbnails, frameos-publish, frameos-library and frameos-repurpose. Each has on-demand `references/` and an `agents/openai.yaml` for Codex and ChatGPT. They share one ground-rules block kept in sync from `scripts/ground_rules.md`.
- One repo that installs on every host it targets:
  - Claude plugin and marketplace (`.claude-plugin/`) for Claude Code, claude.ai, Claude Desktop and Cowork.
  - Codex plugin and marketplace (`.codex-plugin/`, `.agents/plugins/marketplace.json`) for Codex and the ChatGPT plugin directory.
  - Cursor plugin (`.cursor-plugin/plugin.json`).
  - Gemini CLI extension (`gemini-extension.json`, `GEMINI.md`) with eight `/frameos:*` commands.
  - Agent Plugins 1.0 package (`agent-plugin/`) and a Copilot marketplace (`.github/plugin/marketplace.json`) for VS Code, GitHub Copilot and Devin.
- Connection settings that request the `frameos:mcp` scope wherever a host allows it, and send an `X-FrameOS-Plugin-Version` header.
- A local mock FrameOS MCP server (`dev/`) with the same 27 tools, for demos and tests without credits.
- Maintainer scripts: `validate.py`, `sync.py`, `bump_version.py`, `build_dist.py` and `test.py`, plus unit tests and a Claude plugin eval suite.
- Docs: install guides for ten hosts, an agent-executable install protocol, a prompt library with 30 prompts, a status page and directory submission checklists.

### Known issues

- The hosted connector returns 404, and the sign-in server does not yet advertise the `frameos:mcp` scope or offer client registration. See [docs/status.md](docs/status.md) for the full list of open items for the MCP connector owner.
