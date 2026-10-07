# Changelog

All notable changes to the FrameOS plugin, skills and extension packages. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/). The canonical version is in [`VERSION`](VERSION).

## [Unreleased]

### Changed

- Synced with the FrameOS connector's launch-hardening update (deployed 2026-10-06). The tool snapshot (`tests/fixtures/mcp-snapshot.json`) and `evals/mocks/frameos/_tools.json` carry its new descriptions for `submit_video`, `submit_uploaded_video`, `get_transcript`, `export_clip`, `export_collection`, `create_thumbnail_job` and `post_clip`; tool names, parameters, titles and annotations are unchanged.
- The mock server follows the update: the credit check with holds for renders in flight, a refused project marked failed with `(insufficient_credits)`, no credit check at submit for uploads, upload paths under the workspace's own folder, repeat exports returning the running job, collection exports in batches of 10 with `not_started`, public-link checks on video links and thumbnail inputs, `max_thumbnails` of at least 1, `recaption_clip` style checks, replaced clips left out of `list_clips` and `get_project`, and the post-title fallback to the clip's own title.
- Skills: updated for the same behaviour (exports, collection batches, thumbnail inputs, post titles, upload resubmits, the new 400 and 429 messages, and re-captioning).

## [0.1.0] - not yet released

First version. The hosted FrameOS connector (`https://frameos.studio/mcp`) is live as of 2026-10-05, and so far only Claude Code can sign in to it. A real end-to-end test passed that day with Claude Code connected directly: sign-in, then `whoami` and `list_projects` returned a real account's data. Nothing else in this release has been verified against a live FrameOS account yet ([status](docs/status.md)).

### Added

- Eight skills: frameos-setup, frameos-clip, frameos-captions, frameos-find-moments, frameos-thumbnails, frameos-publish, frameos-library and frameos-repurpose. Each has on-demand `references/` and an `agents/openai.yaml` for Codex and ChatGPT. They share one ground-rules block kept in sync from `scripts/ground_rules.md`.
- One repo that installs on every host it targets:
  - Claude plugin and marketplace (`.claude-plugin/`) for Claude Code, claude.ai, Claude Desktop and Cowork.
  - Codex plugin and marketplace (`.codex-plugin/`, `.agents/plugins/marketplace.json`) for Codex and the ChatGPT plugin directory.
  - Cursor plugin (`.cursor-plugin/plugin.json`).
  - Gemini CLI extension (`gemini-extension.json`, `GEMINI.md`) with eight `/frameos:*` commands.
  - Agent Plugins 1.0 package (`agent-plugin/`) and a Copilot marketplace (`.github/plugin/marketplace.json`) for VS Code, GitHub Copilot and Devin.
- Connection settings that request the `frameos:mcp` scope wherever a host allows it, and send an `X-FrameOS-Plugin-Version` header.
- A local mock FrameOS MCP server (`dev/`) with the same 27 tools, titles and annotations as the real one, for demos and tests without credits. The tool snapshot it is checked against comes from the backend's main branch (2026-10-03).
- Maintainer scripts: `validate.py`, `sync.py`, `bump_version.py`, `build_dist.py` and `test.py`, plus unit tests and a Claude plugin eval suite.
- Docs: install guides for ten hosts, an agent-executable install protocol, a prompt library with 30 prompts, a status page and directory submission checklists.

### Known issues

- Only Claude Code can sign in. FrameOS's sign-in server admits only pre-registered apps for now, and Claude Code is the only one registered; the other hosts (claude.ai and Claude Desktop, ChatGPT, Codex, Cursor, Gemini CLI, VS Code and Copilot, Perplexity) are coming soon. Dynamic Client Registration is off.
- Signing in through the Claude Code plugin's own connection (`plugin:frameos:frameos`) has not been tested yet; connecting the connector directly has.
- See [docs/status.md](docs/status.md) for the full list of open items.
