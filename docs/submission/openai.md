# Submission checklist: OpenAI (ChatGPT and Codex plugin directory)

One submission lists FrameOS in both ChatGPT and Codex. Portal: https://platform.openai.com/plugins > **Upload new or existing plugin**.

**Blocked until** ChatGPT can sign in and the domain-verification route exists. The connector is live, but only pre-registered clients are admitted and only Claude Code is registered so far, so ChatGPT is not enabled yet ([status](../status.md)). Every tool now declares all three annotations (below).

## 1. Access and identity

- [ ] Use the organization and project that will own the plugin. Organization owners can submit; others need the **Apps Management Write** permission.
- [ ] Complete individual or business verification; the directory shows that verified name.
- [ ] Use a project **without** EU data residency (those can't submit MCP plugins).

## 2. The ZIP

- [ ] Build it: `python3 scripts/build_dist.py` writes `dist/frameos-plugin-<version>.zip` and `dist/SHA256SUMS`. The ZIP leaves out repo tooling (`tests/`, `dev/`, `evals/`, `scripts/`, `docs/submission/`, `.github/`) and the `agent-plugin/` copy, and the build refuses to run if the skills are out of sync.
- [ ] Exactly one plugin root; at most 100 MB compressed, 512 MiB extracted and 5,000 entries.
- [ ] No `.app.json` and no lifecycle hooks (neither exists in this repo).
- [ ] The MCP server is in the **first** upload. A skills-only plugin can't gain an MCP server later.
- [ ] No credentials anywhere in the ZIP. Reviewer credentials go in the dashboard only.
- Not yet verified: whether the portal accepts a ZIP that also contains the Claude, Cursor and Gemini manifests. The portal normalises Claude and Agent Plugins manifests to `.codex-plugin/plugin.json`, and this ZIP already has one.

## 3. Manifest (`.codex-plugin/plugin.json`)

Already in place: `name`, semver `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, `skills`, `mcpServers` (declared, so the portal doesn't ignore `.mcp.json`), and an `interface` with:

- [x] `displayName` "FrameOS" (30 characters or fewer for submission)
- [x] `shortDescription` "Turn long videos into shorts" (28 of 30 characters)
- [x] `longDescription` (under 4,000 characters), `developerName`, `category` "Creativity", `capabilities`
- [x] `websiteURL`, `supportURL` (https://frameos.studio/contact), `privacyPolicyURL`, `termsOfServiceURL` - all four are required for MCP review
- [x] `defaultPrompt`: 3 entries, each 128 characters or fewer (longer ones are silently dropped)
- [x] `brandColor`, `composerIcon`, `logo` (`./assets/icon.png`, square, 1024 px)

Still to add before submitting, in a top-level `extensions` object of `.codex-plugin/plugin.json`, under `"com.openai"` (next to `interface`, not inside it). The portal imports these when you upload the ZIP:

- [ ] `onboardingSkill`: `"./skills/frameos-setup/SKILL.md"`
- [ ] `review.test_cases`: the 5 positive and 3 negative cases below
- [ ] `review.demo_recording_url`: a reviewer-accessible video that walks through the test cases
- [ ] `review.commerce`: `false`, with `commerce_description` "FrameOS does not sell products or take payments in ChatGPT; plans are managed on frameos.studio."
- [ ] `publication.release_notes`, and optionally `publication.countries`

Note: Codex's bundled `validate_plugin.py` lint predates the portal schema and rejects `extensions` and `interface.supportURL`. Codex 0.152 installs the manifest anyway; treat the portal as the source of truth.

## 4. Connect and scan the MCP server

- [ ] Portal > **MCPs** > **Connect**: URL `https://frameos.studio/mcp`, authentication OAuth.
- [ ] Domain verification: serve the portal's token as plain text at `https://frameos.studio/.well-known/openai-apps-challenge` (a frontend route; not served today).
- [ ] Run the tool scan and resolve findings.

ChatGPT's OAuth expectations:

- ChatGPT prefers CIMD with client ID `https://chatgpt.com/oauth/client.json` (redirect `https://chatgpt.com/connector_platform_oauth_redirect`). Its document defaults to `private_key_jwt` but also supports `none`; Clerk's overlap is `none` (public client with PKCE). DCR is used when a `registration_endpoint` exists.
- ChatGPT uses the stable redirect above only if the sign-in server returns `iss` and the connector's `authorization_servers` entry **exactly** matches Clerk's `issuer`. Otherwise ChatGPT falls back to `https://chatgpt.com/connector/oauth/{callback_id}`. The trailing slash that used to break the match is fixed: as of 2026-10-05 the connector publishes `https://clerk.frameos.studio`, the same as Clerk's `issuer`.
- ChatGPT requests the OpenID scopes the sign-in server advertises, so `frameos:mcp` must be a Clerk default scope.
- Optional: marking `whoami` as a profile tool (`_meta["openai/profile"]: true`) improves account labels when users connect more than one account.

## 5. Tool annotations

The portal requires explicit `readOnlyHint`, `openWorldHint` and `destructiveHint` on **every** tool, each with a justification. Current values come from [`tests/fixtures/mcp-snapshot.json`](../../tests/fixtures/mcp-snapshot.json) (the backend's main branch, 2026-10-03), where every tool now sets all three and has a `title`. The proposal is for the MCP connector owner to confirm (annotations live in the connector, not in this repo). Three proposals still differ from the current values: `set_caption_style` and `recaption_clip` (`destructiveHint` is false today) and `generate_social_copy` (`readOnlyHint` is false today).

Key: RO = readOnlyHint, D = destructiveHint, OW = openWorldHint.

| Tool | Current RO / D / OW | Proposed RO / D / OW | Justification |
|---|---|---|---|
| `whoami`, `get_usage`, `get_brand`, `list_projects`, `get_project`, `get_job`, `get_transcript`, `list_clips`, `describe_clip`, `list_collections`, `list_clips_in_collection`, `get_thumbnail_job`, `list_thumbnails`, `list_social_accounts` | true / false / false | true / false / false | Only read data in the connected FrameOS workspace. |
| `submit_video` | false / false / true | false / false / true | Creates a project and spends credits; fetches the public link the user gave. Changes no existing data. |
| `submit_uploaded_video` | false / false / false | false / false / false | Creates a project from the user's own upload and spends credits. |
| `create_upload_link` | false / false / false | false / false / false | Issues a one-hour upload URL; changes no existing data. |
| `export_clip`, `export_collection` | false / false / false | false / false / false | Render a captioned copy; the clip itself is unchanged. |
| `duplicate_clip`, `create_collection`, `add_clip_to_collection` | false / false / false | false / false / false | Add records only (adding to a collection is idempotent). |
| `set_caption_style` | false / false / false | false / true / false | Replaces the clip's saved caption style and appearance; omitting appearance clears earlier overrides. |
| `recaption_clip` | false / false / false | false / true / false | Re-renders a legacy clip and points it at the new file. |
| `generate_social_copy` | false / false / false | true / false / false | Returns draft text and changes nothing (rate-limited to 30 per hour per workspace). |
| `create_thumbnail_job` | false / false / true | false / false / true | Creates thumbnails and spends credits; can fetch a public video or style-reference URL. |
| `post_clip` | false / true / true | false / true / true | Publishes publicly on a third-party platform; cannot be undone from FrameOS. |

## 6. Review test cases

OpenAI requires exactly **5 positive and 3 negative** cases for the initial MCP review. Run every case on the reviewer account before submitting.

Before using them, replace `<SAMPLE_VIDEO_URL>` with a public video FrameOS owns, at least 30 seconds long (a 5 to 10 minute talk keeps the render short).

### Positive

| # | description | prompt | tools_triggered | expected_behavior |
|---|---|---|---|---|
| 1 | Account status and credits | What's my FrameOS credit balance, and what plan am I on? | `whoami` | Reports the workspace name, plan and current credit balance in plain language, without raw IDs. Does not quote prices; links https://frameos.studio/pricing if asked. |
| 2 | Review the best clips of the latest project | Show me the best clips from my most recent FrameOS project. | `whoami`, `list_projects`, `list_clips` | Finds the newest completed project and lists its clips best first, each with a title or hook, length (mm:ss), score out of 10, timestamps in the source video and a preview link. |
| 3 | Start a render from a public link | Turn `<SAMPLE_VIDEO_URL>` into 3 vertical shorts. | `whoami`, `submit_video`, `get_job` | Notes that rendering costs 1 credit per started minute of source video, submits the video as 9:16 with 3 clips, and reports that processing started with an estimated time. Checks progress with `get_job`; presents the clips when done or tells the user to ask later. Never submits the same video twice. |
| 4 | Restyle captions and export | Switch the captions on my top clip to the Beasty style and give me the download link. | `list_projects`, `list_clips`, `set_caption_style`, `export_clip`, `get_job` | Sets the Beasty style on the top-ranked clip, starts one export, waits for the export job without starting another, then returns the download link and says it expires in about an hour. |
| 5 | Draft social copy without posting | Write an Instagram caption with hashtags for my top clip. | `list_projects`, `list_clips`, `generate_social_copy` | Shows a draft title, caption and hashtags based only on what is said in the clip. Does not post. Offers to post only if the user asks, and would confirm account and text first. |

### Negative

| # | description | prompt |
|---|---|---|
| 1 | "Prepare" is not "post". The plugin must not call `post_clip`. It may export the clip and draft copy, then ask whether the user wants it posted. | Get my top clip ready for Instagram. |
| 2 | FrameOS cannot post to TikTok. The plugin should say so, not call `post_clip`, and offer TikTok copy plus the exported file to upload manually. | Post my top clip to TikTok. |
| 3 | Scheduling is not available through FrameOS's tools. The plugin should say so and must not post immediately instead. | Schedule my top clip to go out on YouTube next Friday at 9am. |

### Ready to paste into `extensions["com.openai"].review`

```json
{
  "test_cases": {
    "positive": [
      {
        "description": "Account status and credits",
        "prompt": "What's my FrameOS credit balance, and what plan am I on?",
        "tools_triggered": "whoami",
        "expected_behavior": "Reports the workspace name, plan and current credit balance in plain language, without raw IDs. Does not quote prices; links https://frameos.studio/pricing if asked."
      },
      {
        "description": "Review the best clips of the latest project",
        "prompt": "Show me the best clips from my most recent FrameOS project.",
        "tools_triggered": "whoami, list_projects, list_clips",
        "expected_behavior": "Finds the newest completed project and lists its clips best first, each with a title or hook, length (mm:ss), score out of 10, timestamps in the source video and a preview link."
      },
      {
        "description": "Start a render from a public link",
        "prompt": "Turn <SAMPLE_VIDEO_URL> into 3 vertical shorts.",
        "tools_triggered": "whoami, submit_video, get_job",
        "expected_behavior": "Notes that rendering costs 1 credit per started minute of source video, submits the video as 9:16 with 3 clips, and reports that processing started with an estimated time. Checks progress with get_job; presents the clips when done or tells the user to ask later. Never submits the same video twice."
      },
      {
        "description": "Restyle captions and export",
        "prompt": "Switch the captions on my top clip to the Beasty style and give me the download link.",
        "tools_triggered": "list_projects, list_clips, set_caption_style, export_clip, get_job",
        "expected_behavior": "Sets the Beasty style on the top-ranked clip, starts one export, waits for the export job without starting another, then returns the download link and says it expires in about an hour."
      },
      {
        "description": "Draft social copy without posting",
        "prompt": "Write an Instagram caption with hashtags for my top clip.",
        "tools_triggered": "list_projects, list_clips, generate_social_copy",
        "expected_behavior": "Shows a draft title, caption and hashtags based only on what is said in the clip. Does not post. Offers to post only if the user asks, and would confirm account and text first."
      }
    ],
    "negative": [
      {
        "description": "Prepare is not post: must not call post_clip; may export and draft copy, then ask whether to post.",
        "prompt": "Get my top clip ready for Instagram."
      },
      {
        "description": "TikTok posting is not supported: must not call post_clip; should offer TikTok copy and the exported file instead.",
        "prompt": "Post my top clip to TikTok."
      },
      {
        "description": "Scheduling is not available: should say so and must not post immediately instead.",
        "prompt": "Schedule my top clip to go out on YouTube next Friday at 9am."
      }
    ]
  }
}
```

## 7. Reviewer materials

- [ ] Reviewer account: a dedicated FrameOS account with sample data (not a real user's workspace), no MFA, email codes or magic links, usable immediately. It needs a completed project with several clips and enough credits for case 3. Enter the credentials in **Review details** only.
- [ ] Demo video URL covering the test cases.
- [ ] Release notes for the package version.

## 8. After approval

- You choose when to publish.
- The hosted connector is scanned daily; tool changes go live after automated checks without a new ZIP.
- Changes to metadata or skills need a new ZIP with a new `version` (`scripts/bump_version.py`, see [RELEASING.md](../../RELEASING.md)).
- Changing the connector URL requires contacting OpenAI support.
