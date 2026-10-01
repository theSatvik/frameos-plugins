# Submission checklist: Anthropic (Claude directory)

Portal: https://claude.ai/directory/manage. Submit **both** kinds below, pointing at the same connector URL, so the plugin's connector and the directory connector are the same thing.

Who can submit: Pro and Max users from their own account; on Team and Enterprise, an Owner (Enterprise can also grant a **Directory** permission). Free accounts can't submit. Limit: 10 submissions per organization per 24 hours.

**Blocked until** the connector is live and sign-in works ([status](../status.md)), and until tool titles exist (below).

## 1. Plugin bundle (this GitHub repo)

The repo can stay private while under review but must be public before the listing goes live. New versions are picked up by GitHub webhook or a scheduled check, and every version gets a security scan.

Blocking checks, and where this repo stands:

- [x] README of at least 40 words of prose (code blocks don't count): [README.md](../../README.md)
- [x] `LICENSE` file and a `license` field: MIT
- [x] Plugin `name` is lowercase `a-z0-9-`, at most 64 characters: `frameos` (availability is checked at submission)
- [x] No `.DS_Store` files (`.gitignore` excludes them)
- [x] Repo under 50 MiB, no file over 5 MiB
- [x] No secrets in the repo
- [x] Remote MCP `url` is a literal absolute `https://` URL: `https://frameos.studio/mcp`
- [x] No package launchers to pin, no `hooks.json`, no top-level `bin/` (claude.ai refuses plugins with `bin/`)
- [x] Skill frontmatter is valid YAML with a string `description` (`python3 scripts/validate.py`)
- [ ] `claude plugin validate . --strict` and `claude plugin validate .claude-plugin/plugin.json --strict` pass on the release commit

Held for a human reviewer (avoid if possible): any non-image file over 256 KiB, more than 512 files, binaries, `.mcpb` bundles, lockfile installs.

## 2. MCP connector (`https://frameos.studio/mcp`)

Requirements from Anthropic's review criteria, and the current state:

- [ ] **Every tool has a `title`.** None of the 27 tools sets one today. For the MCP connector owner to fix.
- [ ] **Every tool has the applicable `readOnlyHint` or `destructiveHint`.** Read tools set `readOnlyHint`; write tools set `destructiveHint: false`, including posting, which publishes publicly. For the MCP connector owner to fix.
- [x] Tool names of 64 characters or fewer; read and write tools are separate.
- [x] OAuth 2.0 for sign-in (Clerk). Prerequisites still open: scope, CIMD/DCR, live routes ([status](../status.md#prerequisites-before-any-host-can-connect)).
- [ ] Actionable error messages: errors are meant to reach the agent as `FrameOS returned HTTP <code>: <detail>`, which the skills translate for users. Today the MCP SDK hides that text behind a generic `Error executing tool <name>` ([status](../status.md#open-issues-in-the-mcp-connector), item 17).
- [ ] Documentation URL: this repo's README, or a page on frameos.studio.
- [x] Privacy policy: https://frameos.studio/privacy
- [x] Support contact: support@frameos.studio, https://frameos.studio/contact
- [x] Icon: [`assets/icon.png`](../../assets/icon.png) (1024 x 1024)
- [ ] Test credentials for a fully populated reviewer account (see below).
- [ ] Listing text within limits: name 100 characters, one-liner 200, description 2,000, 1 to 5 categories. The slug is permanent.
- [ ] Seven compliance acknowledgments, including the one on AI media generation (see the policy note).

### OAuth details Claude expects

- Redirect URI for Claude's apps (web, Desktop, mobile, Cowork): `https://claude.ai/api/mcp/auth_callback`.
- Claude Code uses a loopback redirect (`http://localhost/callback` or `http://127.0.0.1/callback`) on a random port.
- Claude's apps use CIMD only when the sign-in server advertises `client_id_metadata_document_supported: true` and `none` among its token endpoint auth methods; otherwise they fall back to DCR, which needs a `registration_endpoint`. The hosted apps' client metadata document is `https://claude.ai/oauth/mcp-oauth-client-metadata` (found by probing, not documented).
- An unauthenticated request must get a 401 with `WWW-Authenticate: Bearer resource_metadata="..."`. The protected-resource metadata `resource` must equal `https://frameos.studio/mcp` exactly, and only the first `authorization_servers` entry is used.
- The sign-in server must be reachable from `160.79.104.0/21`.
- Per tool call on claude.ai and Desktop: about 150,000 characters of output and 240 seconds. FrameOS returns quickly and never blocks on a render.

### Policy note: FrameOS is not AI media generation

The directory does not accept connectors that generate images, video or audio through AI models. Describe FrameOS precisely in the listing and the acknowledgments:

- FrameOS **cuts, reframes and captions the user's own footage**. AI ranks moments from the transcript; it does not generate video.
- **Thumbnails are frame grabs** from the user's own video (sampled with ffmpeg) plus text layout drawn with Pillow. They are not AI-generated images.
- Social copy is AI-drafted **text** from the clip's transcript, shown to the user before anything is posted.

### Reviewer account

Prepare a dedicated FrameOS account (no MFA) with sample data, not a real user's workspace:

- At least one completed project with several clips, made from a video FrameOS owns.
- Enough credits for one more short render and a thumbnail.
- Optional: a connected test YouTube channel, so posting can be shown with privacy set to private.

## Draft listing text

Name: `FrameOS`

One-liner:

> Turn long videos into captioned short clips: submit a link, follow the render, restyle captions, export MP4s, make thumbnails and draft social copy.

Description:

> FrameOS turns long videos you own - podcasts, streams, interviews, webinars - into short clips. Paste a link (YouTube, Vimeo, Twitch, Kick, a public Google Drive file or a direct video URL) or upload a file, and FrameOS finds the strongest moments in the transcript, reframes them for 9:16, 4:5, 3:4, 1:1 or 16:9, and adds captions. Claude can then show you the ranked clips with scores and timestamps, restyle captions from 22 styles, export captioned MP4s, make thumbnails from real frames of your video, organise clips into collections, and draft titles and captions for YouTube, Instagram, Facebook, LinkedIn, TikTok and X. When you explicitly ask, it posts to YouTube, a Facebook Page, an Instagram Business account or a LinkedIn profile you connected in FrameOS, confirming every post with you first. Renders use your FrameOS credits; check your balance any time.

Categories: pick 1 to 5 from the portal's list.

## Other routes

- Anthropic's official marketplace (`claude-plugins-official`) does not take portal submissions.
- The community marketplace is `anthropics/claude-plugins-community` (install name `claude-community`).
