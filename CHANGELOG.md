# Changelog

All notable changes to the FrameOS plugin, skills and extension packages. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/). The canonical version is in [`VERSION`](VERSION).

## [Unreleased]

## [0.1.1] - not yet released

### Added

- `server.json`, the connector's listing for the Official MCP Registry (`studio.frameos/frameos`, schema 2025-12-11). Its `version` (1.0.0) is the listing's own and is independent of the plugin version; `bump_version.py` leaves it alone. `validate.py` checks it, the plugin ZIP leaves it out, and RELEASING.md has the publish steps.
- README: a "What this plugin sends" section (the two FrameOS addresses, no code of its own, no tracking, nothing posted without your go-ahead) with the privacy, terms and support links.
- Brand keywords `frameos` and `frameos-studio` in every manifest, next to the generic ones.
- `dist/frameos-openai-<version>.zip`, the OpenAI Plugin Directory upload for ChatGPT and Codex, built by `scripts/build_dist.py`. It holds one Codex-format plugin root: `.codex-plugin/plugin.json` pointed at a root `.mcp.json` with OpenAI's CIMD sign-in block and no headers, the skills (with the setup skill narrowed to ChatGPT and Codex), the icon and the licence. No Claude, Cursor or Gemini files. The build stops if another AI product's name or an unfilled client-ID placeholder would ship.
- `docs/submission/openai-package.json`: the OpenAI listing text and review details the build merges into that ZIP (5 positive and 3 negative test cases on FrameOS-owned media, the commerce answer, release notes, and two links the owner fills in before upload). `validate.py` checks it.
- `brandColorDark` `#D6FF3F` in the Codex manifest (13.98:1 against `#212121`; OpenAI derives an unreadable dark colour otherwise). The validator now checks both brand colours' contrast.
- Paste-ready listing docs: `docs/submission/grok-cursor.md` (the x.ai form for Grok, Grok Bot and Cursor), `docs/submission/community.md` (ranks 6 to 29 of the directory research), and fresh `anthropic.md`, `openai.md` and `mcp-registry.md`.
- The GitHub Copilot CLI can sign in to FrameOS through its own published client document (`https://github.com/copilot/cli/client-metadata.json`, pre-registered on 2026-10-23; needs Copilot CLI 1.0.83 or newer), so there is no client ID or port to set: add the server URL, then `/mcp auth frameos`. It is in beta: a sign-in probe reaches the FrameOS sign-in page, but it is not tested end to end yet. The VS Code and Copilot guide (new route D), the setup skill's host reference, the agent install protocol, the README and the status page carry the steps.

### Changed

- Devin and Windsurf (now Devin Desktop) are marked "coming soon". No sign-in client is registered with FrameOS for the Devin CLI, Devin Desktop or the Devin web app, so none of them can sign in yet. The Devin guide now says so in a short note (use another app; email support@frameos.studio to hear when Devin works), and the setup skill, install protocol, README, status page and submission notes follow. Every placeholder client ID is gone from the repo, and `tests/test_build_dist.py` now fails if one appears anywhere in it (the OpenAI ZIP build still refuses any unfilled double-underscore placeholder).
- The root `.mcp.json` now holds only Claude Code's MCP keys (`type`, `url`, `oauth.scopes` as one string, `headers`), so the Claude directory's schema check passes. Codex reads its own `.codex-plugin/mcp.json`, named by `.codex-plugin/plugin.json`, which keeps the `scopes`, `oauth_resource` and `http_headers` Codex used before (checked with codex-cli 0.152.0 in a throwaway profile). The validator enforces both shapes.
- The Claude marketplace description no longer calls the plugin "official", and neither does the README.
- Docs: the Anthropic and OpenAI submission checklists no longer say they are blocked on sign-in (Claude and ChatGPT were tested end to end on 2026-10-08); the MCP Registry checklist points at `server.json`; the README install table marks which Claude.ai and Cursor routes are tested.
- Synced with the FrameOS connector's listing update (backend branch `claude/mcp-directory-ready`, not deployed yet): the snapshot, the mock server and `evals/mocks/frameos/_tools.json` carry server version 0.1.1 with its title, website link and icon; every tool's title repeated inside its safety labels; `idempotentHint` on the 15 read-only tools; `set_caption_style` and `recaption_clip` marked destructive; `generate_social_copy` marked read-only; and the current `get_brand` description. Out-of-credits errors now end with a link to the plans page, in the mock and the out-of-credits eval too.
- The setup skill's ChatGPT guide mentions installing from the Plugin Directory once FrameOS is listed.
- Install guides: the old "Coming soon: can't sign in yet" banners in the Claude.ai, ChatGPT, Codex, Cursor, Gemini CLI, Perplexity and other-agents guides now say what was tested and what wasn't, as in the status page. The Claude Code guide no longer says it is the only app that can sign in, and the Gemini, Copilot and Perplexity submission checklists are blocked on testing only. The ChatGPT and Gemini CLI guides' known limitations now match their banners, and Gemini CLI's connector-only route (the guide and the setup skill) carries the public client ID it needs to sign in. The Cursor submission checklist records Cursor's client document as pre-registered on 2026-10-23.
- Perplexity: the install guide and the setup skill now give the public client ID (`2zmQEDyKLc8bw01o`, under Advanced) that the status page lists. Without it Perplexity tries to register itself, which FrameOS doesn't allow.
- The setup skill names the plan the way the FrameOS site does: `starter` is Pro and `pro` is Max.
- README: "What this plugin sends" says the repo's `dev/`, `scripts/`, `tests/` and `evals/` folders are maintainer tooling the plugin never runs.
- `docs/submission/anthropic.md` says the read-only and destructive counts assume the backend label update is deployed, and lists bundled image paths in backticks as a possible reviewer hold.
- Synced with the FrameOS connector's launch-hardening update (deployed 2026-10-06). The tool snapshot (`tests/fixtures/mcp-snapshot.json`) and `evals/mocks/frameos/_tools.json` carry its new descriptions for `submit_video`, `submit_uploaded_video`, `get_transcript`, `export_clip`, `export_collection`, `create_thumbnail_job` and `post_clip`; tool names, parameters, titles and annotations are unchanged.
- The mock server follows the update: the credit check with holds for renders in flight, a refused project marked failed with `(insufficient_credits)`, no credit check at submit for uploads, upload paths under the workspace's own folder, repeat exports returning the running job, collection exports in batches of 10 with `not_started`, public-link checks on video links and thumbnail inputs, `max_thumbnails` of at least 1, `recaption_clip` style checks, replaced clips left out of `list_clips` and `get_project`, and the post-title fallback to the clip's own title.
- Skills: updated for the same behaviour (exports, collection batches, thumbnail inputs, post titles, upload resubmits, the new 400 and 429 messages, and re-captioning).
- Docs: Windsurf's Cascade agent is marked as removed from Devin Desktop (8 Sep 2026); it only supports Dynamic Client Registration, so it can't sign in. The docs no longer say the Copilot CLI needs a `tools` list; it is optional and defaults to all tools. Signing in through the Copilot CLI plugin's own server is not tested yet, so the guide falls back to adding the connector separately.

## [0.1.0] - not yet released

First version. The hosted FrameOS connector (`https://frameos.studio/mcp`) is live as of 2026-10-05. A real end-to-end test passed that day with Claude Code connected directly: sign-in, then `whoami` and `list_projects` returned a real account's data. Nothing else in this release has been verified against a live FrameOS account yet ([status](docs/status.md)).

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

- Every listed app except Devin can sign in: Claude Code, Claude (web, Desktop, mobile), ChatGPT, Codex, VS Code and the Copilot CLI through their published client documents (the Copilot CLI's since 2026-10-23), and Cursor, Gemini CLI and Perplexity through public client IDs shipped in their configs or install steps (since 2026-10-08). Devin (including Windsurf) has no registered client yet, so it can't sign in. Only pre-registered apps are admitted and Dynamic Client Registration stays off, so Windsurf's old Cascade agent can't sign in either. Claude Code, Claude, ChatGPT, Codex, Cursor and VS Code are tested end to end; Gemini CLI, Perplexity and the Copilot CLI are not yet.
- Signing in through the Claude Code plugin's own connection (`plugin:frameos:frameos`) has not been tested yet; connecting the connector directly has.
- See [docs/status.md](docs/status.md) for the full list of open items.
