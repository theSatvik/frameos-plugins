# FrameOS for AI agents

Turn your long videos into short clips by asking the AI agent you already use. Paste a podcast, stream, interview or webinar link into Claude Code today (Claude, ChatGPT, Codex, Cursor, Gemini CLI, GitHub Copilot and Perplexity are coming soon), and FrameOS finds the strongest moments, reframes them for your format, adds captions and hands you back a ranked list of clips. You stay in charge of what gets exported, captioned, thumbnailed and posted.

This repo holds the official FrameOS plugin, skills and extension packages. They connect your agent to the hosted FrameOS connector (an MCP server at `https://frameos.studio/mcp`) and teach it how to use FrameOS well: when to check your credits, how long to wait for a render, which caption styles exist, and never to post anything without your go-ahead.

> **Status, 2026-10-09: the hosted connector is live, and every listed app can sign in.** `https://frameos.studio/mcp` is up. Claude Code, Claude (web, Desktop, mobile), ChatGPT, Codex, Cursor and VS Code with GitHub Copilot are tested end to end against a real account; Gemini CLI and Perplexity are enabled and being tested. See [docs/status.md](docs/status.md) for what is left, and [try the whole workflow against the mock server](#try-it-without-credits-mock-server) without spending credits.

## What you can say to your agent

You don't need to learn any commands. Talk to your agent the way you'd brief an editor:

- "Turn this episode into 5 vertical shorts for TikTok: https://youtube.com/watch?v=..."
- "Make 3 square clips for LinkedIn from this interview, focusing on what we say about pricing."
- "Show me my clips from yesterday's stream, best first."
- "Make the captions on clip 2 bigger, move them up a bit and use the Beasty style. Then give me the MP4."
- "Where in last week's podcast do we talk about hiring? Give me quotes with timestamps."
- "Make 2 YouTube thumbnails for my best clip."
- "Write an Instagram caption for that clip." Then, when you're happy: "Post it to my Instagram."
- "Turn this webinar into a week of content: 5 clips, captions, thumbnails and copy for YouTube and LinkedIn."
- "How many FrameOS credits do I have left, and what did I spend them on this month?"

More ready-to-use prompts, grouped by job, are in [docs/workflows.md](docs/workflows.md).

### What happens when you ask for clips

1. Your agent checks you're signed in and have credits.
2. It sends the link (or uploads your file, if your agent can run commands) to FrameOS with your settings: how many clips, which format, and what to focus on.
3. A render usually takes 10 to 30 minutes. Your agent tells you roughly how long and checks back on its own, or, in chat apps that can't wait, tells you to ask "check my FrameOS render" later.
4. You get a ranked list: title or hook, length, score, where it sits in the original video, and a preview link.
5. You pick what happens next: restyle captions, export MP4s, make thumbnails, draft copy, or post.

### How credits work

- It works on every FrameOS plan. All you need is credits.
- A render costs 1 credit per started minute of source video, and you're only charged when clips are delivered.
- Thumbnails cost 10 credits each.
- Exports, caption changes, copy drafts, collections and posting are free.
- A render only starts when your balance covers the whole video, so you never end up with a half-paid render.
- Up to 3 videos can be processing at once in a workspace. Your agent queues the rest and submits them as renders finish.
- The server enforces both of these rules (live since 2026-10-06), and the skills follow them too.
- Ask your agent "What is my FrameOS credit balance?" any time. Plans and prices live on https://frameos.studio/pricing; your agent won't quote them.

## Install

Pick your app. Each guide has the exact steps, how to check it worked, how to sign in again, and known limits. Claude Code, Claude (web, Desktop, mobile), ChatGPT, Codex, Cursor and VS Code are tested end to end; Gemini CLI and Perplexity can sign in since 2026-10-08 and are being tested ([status](docs/status.md)).

| Where you use AI | Quickest path | Full guide |
|---|---|---|
| Claude Code | `claude mcp add --transport http -s user frameos https://frameos.studio/mcp` then `claude mcp login frameos` (tested). Or, with the skills: `claude plugin marketplace add theSatvik/frameos-plugins` then `claude plugin install frameos@frameos` (signing in through the plugin's own connection is not tested yet) | [docs/install/claude-code.md](docs/install/claude-code.md) |
| Claude.ai, Claude Desktop, Cowork | **Customize > Plugins > Add > Add marketplace**, enter `theSatvik/frameos-plugins`; or add a custom connector with `https://frameos.studio/mcp` | [docs/install/claude-ai.md](docs/install/claude-ai.md) |
| Codex | `codex plugin marketplace add theSatvik/frameos-plugins` then `codex plugin add frameos@frameos` | [docs/install/codex.md](docs/install/codex.md) |
| ChatGPT | Turn on developer mode, then add `https://frameos.studio/mcp` under ChatGPT Plugins | [docs/install/chatgpt.md](docs/install/chatgpt.md) |
| Cursor | One-click install link, or the plugin as a local plugin | [docs/install/cursor.md](docs/install/cursor.md) |
| Gemini CLI | `gemini extensions install https://github.com/theSatvik/frameos-plugins` | [docs/install/gemini-cli.md](docs/install/gemini-cli.md) |
| VS Code and GitHub Copilot | `copilot plugin install theSatvik/frameos-plugins:agent-plugin`, or **Chat: Install Plugin From Source** in VS Code | [docs/install/vscode-copilot.md](docs/install/vscode-copilot.md) |
| Perplexity | **Account settings > Connectors > + Custom connector > Remote** with `https://frameos.studio/mcp` | [docs/install/perplexity.md](docs/install/perplexity.md) |
| Devin and Windsurf | `devin plugins install theSatvik/frameos-plugins` | [docs/install/devin-windsurf.md](docs/install/devin-windsurf.md) |
| Any other agent | `npx skills add theSatvik/frameos-plugins`, plus the connector URL `https://frameos.studio/mcp` | [docs/install/other-agents.md](docs/install/other-agents.md) |

**Check it worked.** In a new conversation, ask: "What is my FrameOS credit balance?" You should get your workspace name and a credit number. A "connected" badge on its own isn't proof; only a real answer is.

**Let your agent do the install.** Agents that can run commands (Claude Code, Codex, Gemini CLI and similar) can install FrameOS for you. Paste this:

```text
Install FrameOS by following https://github.com/theSatvik/frameos-plugins/blob/main/docs/install-protocol.md
```

## What it can and can't do

**Your agent can:**

- Clip a video from a link - YouTube, Vimeo, Twitch, Kick, public Google Drive files or a direct video file URL - or from a file on your computer when your agent can run commands. Sources need to be at least 30 seconds long.
- Make up to 20 clips per video (3 by default). The number is a maximum, so you may get fewer.
- Frame clips as 9:16 (Shorts, Reels, TikTok), 4:5 or 3:4 (feeds), 1:1 (square) or 16:9 (landscape).
- Steer clipping toward a topic. Use the words the speaker actually says ("pricing", "hiring"), because the focus is matched on words; it's a preference, not a filter.
- Restyle captions with 22 caption styles (or none), 16 fonts, size, position and 17 animations, then export a captioned MP4. Download links last about an hour, and your agent fetches fresh ones when needed.
- Search the full transcript of videos processed since the connector launched (older projects may only have per-clip transcripts) and pull quotes with timestamps.
- Make up to 3 thumbnails per request from real frames of your video with text layout (not AI-generated images).
- Draft a title, caption and hashtags for YouTube, Instagram, Facebook, LinkedIn, TikTok or X.
- Post to YouTube (Shorts), a Facebook Page, an Instagram Business account (Reels) or a LinkedIn personal profile that you connected in FrameOS - only after you confirm each post.
- Organise clips into collections, duplicate clips to experiment, and show your credit usage for the last 30 days.

**Not available through your agent** (use the FrameOS web app at https://frameos.studio/dashboard, or it's not available yet):

- Scheduling posts, share links, censoring or bleeping, dubbing, or free-form timeline edits.
- Choosing the clip length, or rendering a whole video without clipping.
- Cancelling a render that has started.
- Posting to TikTok or X (your agent can still write the copy).
- Connecting social accounts or uploading a brand logo (both are done once, in the web app).
- Renaming or deleting collections, or removing a clip from one.

Clips made on the free plan carry a FrameOS watermark.

## Try it without credits (mock server)

The repo ships a local mock FrameOS server with the same 27 tools and inputs as the real one, and errors in the same format. It needs no account, no sign-in and no credits, so you can watch the whole flow - submit, poll, clips, captions, export, thumbnails, copy and a fake post - without touching a real account.

```bash
git clone https://github.com/theSatvik/frameos-plugins
cd frameos-plugins
uv run --script dev/mock_server.py                        # stdio
uv run --script dev/mock_server.py --http --port 8790     # Streamable HTTP at http://127.0.0.1:8790/mcp
claude --plugin-dir . --mcp-config dev/mock.mcp.json --strict-mcp-config   # Claude Code: these skills + the mock only
```

Mock links point at `mock.frameos.invalid`, so nothing real is created. [dev/README.md](dev/README.md) has the full walkthrough and the inputs that trigger each error.

## Packages in this repo

The repo root is the plugin. One set of skills serves every host; each host reads its own manifest.

| File or folder | What it is | Read by |
|---|---|---|
| [`skills/`](skills/) | The eight skills: [frameos-setup](skills/frameos-setup/SKILL.md), [frameos-clip](skills/frameos-clip/SKILL.md), [frameos-captions](skills/frameos-captions/SKILL.md), [frameos-find-moments](skills/frameos-find-moments/SKILL.md), [frameos-thumbnails](skills/frameos-thumbnails/SKILL.md), [frameos-publish](skills/frameos-publish/SKILL.md), [frameos-library](skills/frameos-library/SKILL.md), [frameos-repurpose](skills/frameos-repurpose/SKILL.md). Each has `references/` and `agents/openai.yaml`. | Every host; `npx skills`; skill ZIP uploads |
| [`.claude-plugin/`](.claude-plugin/) | Claude plugin manifest and marketplace | Claude Code; claude.ai, Claude Desktop and Cowork; Devin falls back to it |
| [`.mcp.json`](.mcp.json) | The FrameOS connection, written so both Claude and Codex read it | Claude Code, Codex |
| [`.codex-plugin/`](.codex-plugin/), [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json) | Codex plugin manifest and marketplace | Codex CLI and app; ChatGPT plugin directory submission |
| [`.cursor-plugin/plugin.json`](.cursor-plugin/plugin.json) | Cursor plugin, connection included | Cursor |
| [`gemini-extension.json`](gemini-extension.json), [`GEMINI.md`](GEMINI.md), [`commands/frameos/`](commands/frameos/) | Gemini CLI extension, its always-on context and the `/frameos:*` commands | Gemini CLI |
| [`agent-plugin/`](agent-plugin/) | Agent Plugins 1.0 package (its `skills/` is a synced copy) | VS Code and GitHub Copilot (IDE, CLI, app), Devin, Cursor |
| [`.github/plugin/marketplace.json`](.github/plugin/marketplace.json) | Copilot marketplace pointing at `agent-plugin/` | Copilot CLI, VS Code |
| [`assets/icon.png`](assets/icon.png) | 1024 px icon | Codex, Cursor, directories |
| [`dev/`](dev/README.md) | Mock FrameOS server for demos and tests | You, maintainers |
| [`docs/`](docs/) | Install guides, prompt library, status, submission checklists | Everyone |
| [`scripts/`](scripts/), [`tests/`](tests/), [`evals/`](evals/) | Validator, sync, version bump, ZIP builder, tests, Claude plugin evals | Maintainers |

Skill ZIPs for claude.ai and Perplexity uploads, and the plugin ZIP for **Upload plugin**, are built with `python3 scripts/build_dist.py` into `dist/`.

## Links

- FrameOS: https://frameos.studio - web app: https://frameos.studio/dashboard - pricing: https://frameos.studio/pricing
- Help: https://frameos.studio/contact or support@frameos.studio
- Privacy: https://frameos.studio/privacy - Terms: https://frameos.studio/terms
- [Status](docs/status.md) - [Prompt library](docs/workflows.md) - [Agent install protocol](docs/install-protocol.md) - [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md) - [Releasing](RELEASING.md) - [Security](SECURITY.md) - [License (MIT)](LICENSE)
