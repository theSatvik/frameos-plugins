# Community directories (ranks 6 to 29)

The research pass of 2026-10-22 ranked 31 places to list FrameOS. Ranks 1 to 5 have their own pages: [Anthropic](anthropic.md) (connector and plugin), [MCP Registry](mcp-registry.md), [Grok, Grok Bot and Cursor](grok-cursor.md) and [OpenAI](openai.md). This page covers ranks 6 to 29 in order. Ranks 30 and 31 are partner-only or closed catalogs, so they are left out.

Each block says where to submit, what to paste and who does it:

- **Owner:** you do it (accounts, forms, payments, public posts and anything that accepts terms).
- **Claude, then owner:** Claude prepares the files, pull request or field text in a repo; you submit or approve it.
- **Claude (with your OK):** Claude can do it, but only after you say yes, because it runs a third-party package or makes something public.

A sign-in caveat applies everywhere: FrameOS only admits apps whose sign-in client is pre-registered in Clerk (Dynamic Client Registration is off). A directory whose app registers itself won't be able to sign in until its client is added. The blocks say where that applies.

## Paste kit

Use these everywhere below unless a block says otherwise.

| Field | Value |
|---|---|
| Name | `FrameOS`. Where "FrameOS" or "Frameo" is already taken (Product Hunt, Smithery, Glama), `FrameOS Studio` |
| Tagline (60 max) | `Turn long videos into captioned short clips` |
| MCP server | `https://frameos.studio/mcp`, Streamable HTTP, OAuth 2.1 sign-in with your FrameOS account (no API key) |
| Website | https://frameos.studio |
| Docs and setup | https://frameos.studio/plugin |
| Source (skills and plugin manifests) | https://github.com/theSatvik/frameos-plugins (MIT) |
| Privacy / terms | https://frameos.studio/privacy, https://frameos.studio/terms |
| Support | support@frameos.studio |
| Logo | `https://frameos.studio/frameos/frameos-logo-1024-plate.png` (1:1 with a background plate) or `https://frameos.studio/frameos/frameos-logo-512.png`, once the frontend change that adds them is live. Live today: https://raw.githubusercontent.com/theSatvik/frameos-plugins/main/assets/icon.png (1024 x 1024) |
| Categories | Video, Content creation, Social media, Marketing |
| Pricing model | Paid |

Short description (154 of 160 characters):

```text
Turn podcasts, streams and webinars into captioned, reframed short clips. Restyle captions, make thumbnails, draft posts and share them from your AI chat.
```

Long description:

```text
You recorded an hour. Your audience scrolls in seconds. FrameOS closes that gap without opening an editor.

Paste a link to your podcast, stream or webinar, or upload the file, and FrameOS finds the moments worth sharing. It cuts them into vertical clips, keeps the speaker in frame and adds captions people can read with the sound off. You stay in the chat the whole time.

From there, just ask:
- Restyle the captions to match your brand, then export clean MP4s.
- Pull thumbnail options from the best frames, with a headline on top.
- Draft a title and caption for YouTube Shorts, Instagram, Facebook or LinkedIn.
- Post a clip to an account you've connected. Your assistant asks before anything goes live, and YouTube uploads can go out as private.

Everything works on your own footage, in your FrameOS workspace. Making clips and thumbnails uses FrameOS credits; exports, caption changes, copy drafts and posting don't. Sign in with your FrameOS account to get started.
```

Price line, for community directories only (never in the Claude, OpenAI, Cursor or Grok listings). Copy it from the top strip of https://frameos.studio/pricing on the day you submit; on 2026-10-23 it read:

```text
Plans from $4.50/mo · cancel anytime
```

Never write "free trial": the trial has been off since 2026-10-08.

Keywords:

```text
frameos, frameos studio, frameos clips, frameos mcp, video clips, short clips, podcast clips, stream clips, captions, reframe, vertical video, youtube shorts, instagram reels, thumbnails, social media posting, video repurposing
```

Example prompts:

```text
Turn this podcast episode into 5 captioned short clips: [paste link]
Which clips from my latest project are ready? Show me the top three.
Switch the captions on my newest clips to the Beasty style and give me the MP4 links.
Make three YouTube thumbnail options from my best clip.
Write a YouTube Shorts title and a LinkedIn post for clip 2 of my last project.
Post my best clip to my YouTube channel as private.
```

Tool summary, for directories that ask what the server does:

```text
FrameOS gives your assistant 27 tools over one secure sign-in. Create: submit_video (public link) or create_upload_link + submit_uploaded_video (your own file) start a clipping job, and get_job tracks it. Browse: list_projects, get_project, list_clips, describe_clip, get_transcript, get_brand, whoami and get_usage are read-only. Edit and export: set_caption_style and recaption_clip change captions, export_clip and export_collection return MP4 links, duplicate_clip copies a clip, and list_collections, create_collection, add_clip_to_collection and list_clips_in_collection organise your library. Thumbnails: create_thumbnail_job makes options from real frames of your video with text on top, and get_thumbnail_job / list_thumbnails fetch them. Share: generate_social_copy drafts titles and captions as text only, list_social_accounts shows connected accounts, and post_clip publishes to YouTube, Facebook, Instagram or LinkedIn after you confirm.
```

## The directories

### Gemini CLI Extensions gallery

Rank 6 · Who: owner (one command) · Cost: free · Review: automatic daily crawl

- **Where:** no form. The gallery at https://geminicli.com/extensions crawls public repos that carry the GitHub topic `gemini-cli-extension` ([how it works](https://geminicli.com/docs/extensions/releasing/)).
- **What to paste:** nothing. The listing comes from `gemini-extension.json` and the README.
- **Do:** first test `gemini extensions install https://github.com/theSatvik/frameos-plugins` and one tool call (Gemini CLI is enabled but not tested end to end). Then set the topics and homepage, prepared and not run:

  ```bash
  gh repo edit theSatvik/frameos-plugins --homepage https://frameos.studio/plugin --add-topic gemini-cli-extension --add-topic mcp --add-topic mcp-server --add-topic claude-code-plugin --add-topic codex-plugin --add-topic video-editing --add-topic ai-video
  ```

- **Check:** search the gallery for "frameos" about a day later.

### Smithery

Rank 7 · Who: owner · Cost: free · Review: automated scan

- **Where:** https://smithery.ai/new
- **What to paste:** namespace `frameos`, display name `FrameOS Studio` (an unrelated "frameo" exists), server URL `https://frameos.studio/mcp`, the short description and logo.
- **Before:** Smithery's sign-in client, `https://connect.smithery.ai/.well-known/oauth-client`, was pre-registered in Clerk on 2026-10-23; sign in through Smithery once before listing (not tested end to end yet). Sign-in tokens pass through Smithery's gateway; say so in the privacy policy before listing.
- **After:** complete the OAuth scan, then Settings > Verification. Claim the namespace early.

### GitHub MCP Registry and VS Code's `@mcp` gallery

Rank 8 · Who: Claude, then owner · Cost: free · Review: hand-picked, no time frame

- **Where:** a comment on https://github.com/github/github-mcp-server/discussions/1257
- **Before:** the official MCP Registry entry must be live first ([mcp-registry.md](mcp-registry.md)). VS Code signs in today (its client is pre-registered); Copilot in JetBrains, Xcode and Eclipse registers itself, so it won't sign in.
- **What to paste** (post it from the `theSatvik` account; it is public):

  ```text
  Requesting onboarding for FrameOS.
  - Registry name: studio.frameos/frameos (version 1.0.0)
  - Endpoint: https://frameos.studio/mcp, Streamable HTTP, OAuth 2.1 (CIMD; VS Code's client is pre-registered)
  - Source: https://github.com/theSatvik/frameos-plugins (MIT)
  - What it does: turns long videos into captioned short clips, restyles captions, exports MP4s, makes thumbnails from real frames and posts to connected accounts after the user confirms.
  - Check: curl -s "https://registry.modelcontextprotocol.io/v0.1/servers?search=studio.frameos"
  ```

### Grok Connectors catalog (grok.com)

Rank 9 · Who: owner · Cost: free · Review: unknown (the destination is "coming soon")

- **Where:** the same x.ai form as rank 4; tick **Grok (coming soon)** ([grok-cursor.md](grok-cursor.md)).
- **Before:** `https://grok.com/oauth/mcp-client.json` was pre-registered in Clerk on 2026-10-23. Test grok.com > Connectors > New Connector > Custom > `https://frameos.studio/mcp` (not tested end to end yet).
- **Later (Claude):** add a Grok tab to https://frameos.studio/plugin.

### awesome-copilot external plugins (Copilot CLI's default marketplace)

Rank 10 · Who: Claude, then owner · Cost: free · Review: 1 day to about 2 months, about a quarter rejected

- **Where:** https://github.com/github/awesome-copilot/issues/new/choose > External Plugin form.
- **What to paste:** name `frameos`, repository `theSatvik/frameos-plugins`, path `agent-plugin`, the release tag and its full 40-character commit SHA, the short description.
- **Before:** cut a release tag (none exists yet). The Copilot CLI's client `https://github.com/copilot/cli/client-metadata.json` was pre-registered in Clerk on 2026-10-23, so the install guides need no client ID; run one sign-in and a credit question in the Copilot CLI end to end first (a sign-in probe reaches the FrameOS sign-in page, nothing more is tested).

### Glama connectors (and the awesome-remote-mcp-servers list)

Rank 11 · Who: Claude, then owner · Cost: free · Review: automatic; searchable once the server shows as healthy

- **Where:** https://glama.ai/mcp/connectors. It imports from the official registry, or use Add MCP Server > Connector. Name it `FrameOS Studio` if "FrameOS" is taken.
- **Do:** sign in and copy the claim token (owner); serve it at `https://frameos.studio/.well-known/glama.json` (Claude, frontend); run the HTTP check; add a test profile under Admin > Test Profile so Glama can sign in, since it can't register itself (owner).
- **Then:** the Glama badge unlocks https://github.com/punkpeye/awesome-remote-mcp-servers. Claude prepares the pull request entry; you approve it.

### Raycast Model Context Protocol Registry

Rank 12 · Who: Claude, then owner · Cost: free · Review: about 1 day

- **Where:** a pull request to https://github.com/raycast/extensions/tree/main/extensions/model-context-protocol-registry
- **Before:** Raycast can't sign in on its own here, so create a public Clerk client with redirect `http://localhost:36933/oauth/callback` and scope `frameos:mcp` (owner).
- **Claude:** adds the entry (through `mcp-remote` with that fixed client), the README row and changelog line, builds and tests. You approve the pull request titled "[Model Context Protocol Registry] Add FrameOS MCP server".

### skills.sh

Rank 13 · Who: Claude (with your OK) · Cost: free · Review: automatic

- **Where:** no form. A repo appears after someone installs it with `npx skills add theSatvik/frameos-plugins` (telemetry on).
- **What to paste:** nothing. Optionally add a `skills.sh.json` that groups the eight skills, and put the install command on https://frameos.studio/plugin.
- **Why it needs your OK:** it runs an npm package.

### mcp.so, mcpservers.org and MCP Market

Rank 14 · Who: owner · Cost: free queues, or a paid fast review with a followed link (39, 39 and 29 US dollars) · Review: unstated / up to 2 weeks / 4 to 6 weeks free

- **Where:** https://mcp.so/submit, https://mcpservers.org/submit, https://mcpmarket.com/submit
- **What to paste:** submit as a remote server: name, short description, `https://frameos.studio/mcp`, the repo, a category and the logo. mcpservers.org also takes a website URL. On MCP Market, also submit the eight skills as "Agent Skill" (the repo URL).
- **Decide:** free queue or paid fast lane, per site.

### Kiro Powers

Rank 15 · Who: Claude, then owner · Cost: free · Review: "we will reach out"

- **Where:** https://kiro.dev/powers/submit/
- **Before:** Kiro registers itself by default, so create a Kiro public client in Clerk with a fixed local redirect (owner). Claude then adds that client to the Kiro config, and tests an install from GitHub in Kiro.
- **What to paste:** the paste kit, the repo and the docs link. The README already has privacy and support links.

### Devin plugin marketplace

Rank 16 · Who: Claude, then owner · Cost: free (sign the CLA) · Review: about 5 to 11 days

- **Where:** a pull request to https://github.com/CognitionAI/devin-marketplace
- **Before:** Devin can't sign in yet, and its install guide says "coming soon". Register Devin's sign-in clients in Clerk (owner): a public client for the Devin CLI and Devin Desktop (callback `http://localhost:8765/callback`), and one with redirect `https://api.devin.ai/mcp/oauth/callback` and no secret for the web app. Then Claude writes the real client IDs back into the Devin guide, the setup skill and the install protocol, and you test a sign-in.
- **Claude:** adds `plugins/frameos/.devin-plugin/plugin.json` (short description of 40 characters or fewer, logo checked in), runs their validator and a local install. You approve the pull request.

### Cursor Directory (cursor.directory)

Rank 17 · Who: owner · Cost: free · Review: about 2 weeks

- **Where:** https://cursor.directory/plugins/new (sign in with GitHub, paste the repo URL).
- **Watch:** it reportedly reads the root `.mcp.json`, which has no Cursor client ID (that file follows Claude's format). Install from the listing once it is live and confirm sign-in works; the Cursor Marketplace route ([grok-cursor.md](grok-cursor.md)) uses `.cursor-plugin/plugin.json`, which does have it.

### Composio toolkit partnership

Rank 18 · Who: owner · Cost: not published · Review: not published

- **Where:** https://composio.dev/partnerships#apply (work email `support@frameos.studio`).
- **What to paste:** the MCP server URL and the short description.
- **Later:** if they accept, they will need a Clerk client for `https://backend.composio.dev/api/v3/toolkits/auth/callback`.

### There's An AI For That

Rank 19 · Who: owner · Cost: about 49 US dollars once (secondary source), or free through their monthly X thread · Review: 1 to 2 days

- **Where:** https://theresanaiforthat.com/submit/
- **What to paste:** submit FrameOS twice, as an AI tool (website, tagline, long description, price line, categories) and as an MCP server (`https://frameos.studio/mcp`).
- **Decide:** paid or free route.

### Claude Code Templates (aitmpl.com) and Awesome Codex Plugins

Rank 20 · Who: Claude, then owner · Cost: free · Review: frequent merges

- **Where:** pull requests to https://github.com/davila7/claude-code-templates and https://github.com/hashgraph-online/awesome-codex-plugins
- **Claude:** adds `cli-tool/components/mcps/marketing/frameos.json` (type `http`, the server URL) to the first, and a README line to the second. You approve both.
- **Note:** the Codex list needs a plugin-scanner score of 80 or more; running the scanner installs a third-party package, so it needs your OK.

### n8n

Rank 21 · Who: Claude, then owner · Cost: free · Review: templates about 1 to 4 weeks

- **Where:** the n8n Creator Hub for a template now; https://creators.n8n.io/nodes for a verified node later.
- **Before:** a Clerk client for n8n cloud's redirect, `https://oauth.n8n.cloud/oauth2/callback` (owner). Self-hosted n8n would need an API key, which FrameOS doesn't offer.
- **Claude:** builds a "long video to clips to captions to social posts" template with the MCP Client Tool; you publish it.

### xAI Grok Build plugin marketplace

Rank 22 · Who: Claude, then owner · Cost: free · Review: median about 13 days, but few outside pull requests merge

- **Where:** a pull request to https://github.com/xai-org/plugin-marketplace (follow its CONTRIBUTING.md). Separate from the Grok Bot form.
- **Before:** they want the source in an organization, not a personal account: create a `frameos-studio` GitHub organization, or vendor the plugin under their `external_plugins/`. Keywords must be specific (`frameos`, `frameos studio`, `frameos clips`, `frameos mcp`). Grok Build registers itself or needs a configured client ID, so it needs a Clerk client too.
- **Claude:** tests `grok mcp add`, prepares the entry pinned to a full commit SHA and runs their scripts. You open the pull request.

### Directories that copy from the registry

Rank 23 · Who: Claude checks, owner claims · Cost: free · Review: automatic

- **Where:** PulseMCP (its submissions are paused), mcp.directory, Unyly, claudemarketplaces.com and claude-plugins.dev fill themselves from the official MCP Registry and GitHub.
- **Do:** nothing until the registry entry is live. One to two weeks later, Claude checks each one; you email mcp.directory (https://mcp.directory/submit) to claim the listing.

### Microsoft 365 Copilot connectors and Microsoft's MCP certification

Rank 24 · Who: owner · Cost: no fee · Review: weeks

- **Where:** https://partner.microsoft.com/dashboard/home
- **Decision:** wait. It needs a verified business, a business email, a confidential sign-in client kept in Azure Key Vault, and response-time targets. Revisit when there is enterprise demand or a registered company.

### HubSpot, Slack, Zapier, Pipedream and Activepieces

Rank 25 · Who: owner · Cost: free · Review: up to 60 days (HubSpot), up to 10 weeks (Slack), about a week plus a 90-day beta (Zapier)

- **Decision:** wait. HubSpot needs 3 unaffiliated installs and its own Clerk client; Slack needs 10 active workspaces and tools that answer within 60 seconds; Zapier, Pipedream and Activepieces need a REST API or a native integration. Revisit once the main listings bring users.

### Partner requests: Perplexity, Mistral Le Chat and Kimi

Rank 26 · Who: owner · Cost: free · Review: unknown

- **Where:** api@perplexity.ai; https://mistral.ai/partners/; Kimi's in-app "Apply for official marketplace publication".
- **When:** once the Claude and ChatGPT listings are live. One short email each, with the tagline, the server URL and the docs link.
- **Note:** Perplexity's custom connector wants a client ID and secret (whether a blank secret works is unverified), and Le Chat needs self-registration or a non-empty secret.

### Agensi skills marketplace

Rank 27 · Who: Claude, then owner · Cost: free to list · Review: 24 to 48 hours

- **Where:** https://www.agensi.io/sell
- **What to paste:** one ZIP per skill. `python3 scripts/build_dist.py` already writes them to `dist/claude-ai/`.
- **Rule:** list every skill as Free. Never sell them.

### Product Hunt relaunch

Rank 28 · Who: owner · Cost: free · Review: relaunch request reviewed

- **Where:** https://www.producthunt.com/products/frameos-2 (listed as "FrameOS Studio" since about June 2026).
- **Now:** the page still says "free 1-week trial", stale since 2026-10-08. Replace it with the price line above.
- **Later:** relaunch as "FrameOS for AI agents" around December, when the directory listings are live (the 6-month relaunch window ends then).

### The long tail

Rank 29 · Who: Claude, then owner · Cost: free, except Claude Market (10 US dollars) · Review: varies; Cline and Kilo are slow

- **Where:** https://www.claudemarket.ai/submit, https://lobehub.com/publish-mcp/skill.md, https://github.com/cline/marketplace, https://github.com/Kilo-Org/kilo-marketplace, the awesome-claude-code issue form, and a pull request to VoltAgent's awesome-agent-skills. SkillsMP already lists the eight skills.
- **When:** after the main listings, once the repo has some stars and installs: awesome-claude-code and VoltAgent look for adoption.
- **Sign-in:** Cline and LobeHub register themselves, so their users can't sign in today. Kilo's CLI client, `https://kilo.ai/docs/oauth/kilo/client.json`, was pre-registered on 2026-10-23 (not tested end to end yet).
