# Submission checklist: Anthropic (Claude directory)

Portal: https://claude.ai/directory/manage. Submit **both** entries below from the same organization, pointing at the same connector URL. Then pair them, so people who install both see one set of tools.

Who can submit: Pro and Max users from their own account; on Team and Enterprise, an Owner (Enterprise can also grant a **Directory** permission). Free accounts can't submit. Limit: 10 submissions per organization per 24 hours, drafts included. The listing belongs to the organization that submits it.

Claude (web, Desktop and mobile) signs in through its pre-registered client and was tested end to end on 2026-10-08, as was Claude Code on 2026-10-05 ([status](../status.md)). Every tool has a title and explicit safety labels.

Before you submit, deploy the backend update that refines those labels (backend branch `claude/mcp-directory-ready`; see [openai.md section 5](openai.md#5-tool-safety-labels-and-justifications)). The read-only and destructive counts below assume it. Until it ships, the live server marks 14 tools read-only and only `post_clip` destructive.

Everything below is ready to paste. Nothing here is a credential: the reviewer login goes only into the portal's **Test & launch** step.

## 1. MCP connector entry

**Submit new > MCP connector**

| Field | Value |
|---|---|
| Connection | Universal URL `https://frameos.studio/mcp` |
| Authentication | Client ID metadata documents (CIMD) |
| Name (100 max) | `FrameOS` |
| Slug (permanent) | `frameos` |
| Documentation URL | https://frameos.studio/plugin |
| Privacy policy URL | https://frameos.studio/privacy |
| Support contact | support@frameos.studio |
| Icon | Upload [`assets/icon.png`](../../assets/icon.png) (1024 x 1024 PNG). If the portal wants a URL: `https://frameos.studio/frameos/frameos-logo-512.png` once the frontend change that adds it is live; `https://frameos.studio/frameos/frameos-favicon.png` (256 x 256) is live today |
| Company | FrameOS, https://frameos.studio, primary contact support@frameos.studio |

Categories (pick 1 to 5 from the portal's list): the closest matches to **Video**, **Content creation**, **Social media** and **Marketing**.

One-liner (154 of 200 characters):

```text
Turn podcasts, streams and webinars into captioned, reframed short clips. Restyle captions, make thumbnails, draft posts and share them from your AI chat.
```

Description (1,481 of 2,000 characters):

```text
You recorded an hour. Your audience scrolls in seconds. FrameOS closes that gap without opening an editor.

Paste a link to your podcast, stream, interview or webinar, and FrameOS finds the moments worth sharing. It cuts your footage into vertical clips (or 4:5, 3:4, 1:1 and 16:9), keeps the speaker in frame and adds captions people can read with the sound off. In Claude Code you can also point it at a video file on your computer.

From there, just ask Claude:
- Show your best clips, ranked, with scores and timestamps.
- Restyle the captions from 22 styles to match your brand, then export clean MP4s.
- Make thumbnail options from real frames of your video, with a headline on top.
- Draft a title and caption for YouTube Shorts, Instagram, Facebook, LinkedIn, TikTok or X.
- Post a clip to a YouTube channel, Facebook Page, Instagram Business account or LinkedIn profile you've connected in FrameOS. Claude asks before anything goes live, and YouTube uploads can go out as private.

FrameOS works on your own footage, in your FrameOS workspace. It cuts, reframes and captions what you recorded; it doesn't generate video, images or voices. Thumbnails are frames from your video with a headline on top, and post copy is a text draft you approve.

Making clips and thumbnails uses your FrameOS credits; exports, caption changes, copy drafts and posting don't. Scheduling posts and timeline edits live in the FrameOS web app.

Sign in with your FrameOS account to get started.
```

Example prompts (the policy asks for at least three that work; each of these maps to a real tool path, so don't promise caption colours, words per line or a chosen thumbnail headline, which the tools can't set):

```text
Turn this podcast episode into 5 captioned short clips: [paste link]
Which clips from my latest project are ready? Show me the top three.
Switch the captions on my newest clips to the Beasty style and give me the MP4 links.
Make three YouTube thumbnail options from my best clip.
Write a YouTube Shorts title and a LinkedIn post for clip 2 of my last project.
Post my best clip to my YouTube channel as private.
```

### Use cases step

- **Primary use cases:** turn a long recording into ranked, captioned short clips; restyle captions and export MP4s; make thumbnails from real frames; draft titles and captions; post a clip to a connected account after the user confirms.
- **Prerequisites:** a FrameOS account. New clips and thumbnails need FrameOS credits; browsing, exports, caption changes, copy drafts and posting don't. Posting needs a social account connected in the FrameOS web app.
- **Reads or writes:** both. 15 tools only read; 12 change something (they start renders, save caption styles, create collections or post), and `post_clip`, `set_caption_style` and `recaption_clip` are marked destructive.

### Data handling step

| Question | Answer |
|---|---|
| Whose API does the connector call? | Our own. `https://frameos.studio/mcp` calls only the FrameOS API, and the domain matches the service. |
| Personal health data? | No. |
| Sponsored content? | No. |

### Test & launch step

- Reviewer account: a dedicated FrameOS test user that signs in with **email and password** (sign-in only; new sign-ups stay Google-only). No MFA, no email codes. Enter the email, password and sign-in steps in the portal only, never in this repo.
- What the account holds: credits for one more short render and a thumbnail; one finished project with several clips, made from a video FrameOS owns; a collection; a thumbnail; ideally a connected test YouTube channel so posting can be shown with privacy set to private.
- Suggested order for the reviewer: `whoami`, `list_projects`, `get_project`, `list_clips`, `describe_clip`, `export_clip` (returns an MP4 link), `set_caption_style`, `generate_social_copy`. A new render: `submit_video` with the FrameOS-owned sample link, then `get_job` for a few minutes.
- Before you tick the box: run every tool once yourself in a custom connector or MCP Inspector, as the portal asks.

### Compliance step: the seven acknowledgements

All seven are required. What each one means for FrameOS:

1. **Directory guidelines:** read and followed; tool descriptions are plain and don't promote anything.
2. **First-party API usage:** the connector calls only FrameOS's own API.
3. **Financial transactions:** no tool moves money or sells anything. Renders spend credits from the user's existing balance; a short balance is refused with a plain message and a link to the plans page.
4. **AI media generation:** FrameOS doesn't generate images, video or audio with AI. It cuts, reframes and captions the user's own footage. AI only ranks moments from the transcript and drafts post text. Thumbnails are frames from the video (ffmpeg) with text laid out on top (Pillow).
5. **Prompt injection:** tool descriptions tell Claude only how each tool works, and the skills treat transcripts, titles and captions as data, never as instructions.
6. **Conversation data:** the connector receives only each tool's arguments. It never asks for chat history, memory or files.
7. **Public documentation:** https://frameos.studio/plugin, live and indexed, with setup, tools, example prompts and troubleshooting.

## 2. Plugin bundle entry

**Submit new > Plugin bundle**

| Field | Value |
|---|---|
| Repository | `theSatvik/frameos-plugins` (connect the `theSatvik` GitHub account to claude.ai first) |
| Plugin path | leave empty (the plugin is the repo root) |
| Branch | `main` |
| Updates | keep the GitHub push webhook; set Auto-publish as you prefer |

The portal validates what is on GitHub, not your local copy, so push the release commit first. Listing details come from `.claude-plugin/plugin.json` and the README; edit them in the repo, not in the portal.

### Data handling step

| Question | Answer |
|---|---|
| Does the plugin read or store personal data? | The plugin is instructions only and stores nothing. Through the FrameOS connector it reads the user's workspace name, plan, credit balance, projects, clips, transcripts and connected social account names, to answer the user's request. |
| Does it send data anywhere other than the declared connector? | No. Only `https://frameos.studio/mcp`, with sign-in at `https://clerk.frameos.studio`. The README's "What this plugin sends" section says the same. |
| How long is data kept? | The plugin keeps nothing. FrameOS keeps clips, transcripts and thumbnails in the user's workspace, and deletes uploaded source videos within 7 days ([privacy policy](https://frameos.studio/privacy)). |
| Is it meant for people under 18? | No. (Owner to confirm: the terms don't state a minimum age today.) |
| Contact email | support@frameos.studio |

Then tick the four acknowledgements and submit for review. A plugin is installable only once its status is **Published**, not just Approved.

### Repo checks (Blocking in the portal)

- [x] README with at least 40 words of prose, `LICENSE` file and `license` field (MIT)
- [x] Plugin `name` `frameos`: lowercase, at most 64 characters, nothing presenting it as official
- [x] No `.DS_Store`, no secrets, repo under 50 MiB, no file over 5 MiB
- [x] Root `.mcp.json` uses only Claude Code's keys (`type`, `url`, `oauth.scopes` as one string, `headers`); Codex's keys live in `.codex-plugin/mcp.json`
- [x] Remote MCP `url` is a literal `https://` URL; no `hooks.json`, no top-level `bin/`, no package launchers
- [x] Skill frontmatter is valid YAML with a string `description` (`python3 scripts/validate.py`)
- [ ] `claude plugin validate . --strict` and `claude plugin validate .claude-plugin/plugin.json --strict` pass on the pushed release commit

Held for a human reviewer (avoid if possible): any non-image file over 256 KiB, more than 512 files, binaries, `.mcpb` bundles, lockfile installs. The checklist also holds bundled image paths written in backticks or code blocks instead of Markdown image syntax; the README files table and a few docs name the icon that way, so expect a possible hold there (a first submission gets a human review anyway).

## OAuth details Claude expects

- Redirect URI for Claude's apps (web, Desktop, mobile, Cowork): `https://claude.ai/api/mcp/auth_callback`. Client metadata document: `https://claude.ai/oauth/mcp-oauth-client-metadata`.
- Claude Code uses a loopback redirect (`http://localhost/callback` or `http://127.0.0.1/callback`) on a random port.
- Claude uses CIMD only when the sign-in server advertises `client_id_metadata_document_supported: true` and `none` among its token endpoint auth methods. Clerk advertises both, and Claude's clients are pre-registered.
- An unauthenticated request gets a 401 with `WWW-Authenticate: Bearer resource_metadata="..."`, and the protected-resource `resource` is exactly `https://frameos.studio/mcp`.
- The sign-in server must be reachable from `160.79.104.0/21`.
- Per tool call on claude.ai and Desktop: about 150,000 characters of output and 240 seconds. FrameOS returns quickly and never blocks on a render.

## After publishing

- Link the listing (`https://claude.ai/directory/connectors/frameos`) from https://frameos.studio/plugin.
- Tool changes deploy on the server without resubmitting; renamed tools on the listing need a listing edit.
- Anthropic's official marketplace (`claude-plugins-official`) takes no portal submissions. Approved plugins can also appear in `anthropics/claude-plugins-community` (install name `claude-community`); once FrameOS is there, add `/plugin install frameos@claude-community` to the install guides.
