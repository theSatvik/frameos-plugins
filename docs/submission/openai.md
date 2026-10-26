# Submission checklist: OpenAI (ChatGPT and Codex Plugin Directory)

One submission lists FrameOS in both ChatGPT and Codex. Portal: https://platform.openai.com/plugins > **Upload new or existing plugin**, choose the verified **Developer identity**, then upload the ZIP.

ChatGPT signs in and was tested end to end on 2026-10-08 ([status](../status.md)). The listing is published under the owner's verified individual identity, so the directory shows the developer as **Satvik Shrivas** whatever the ZIP says; the ZIP says the same, so the portal has nothing to change.

## Before you upload (owner)

- [ ] Individual verification done in https://platform.openai.com/settings/organization/general, in a project with global (not EU) data residency. You need the organization Owner role or **Apps Management Write**.
- [ ] `fill_before_upload.sample_video_url` in [`openai-package.json`](openai-package.json): a public https link to a short talk (5 to 10 minutes) that FrameOS owns. Test case 2 uses it. Never a YouTube or other platform link: OpenAI rejects scraping, and the validator refuses one.
- [ ] `fill_before_upload.demo_recording_url`: a reviewer-accessible video that walks through the test cases on ChatGPT desktop and mobile and in Codex. Or leave it empty and enter it in the portal's **Review details**.
- [ ] Rebuild: `python3 scripts/build_dist.py`. It prints a `TODO(owner)` line for each link that is still empty.
- [ ] The domain check route is live: `https://frameos.studio/.well-known/openai-apps-challenge` must return the portal's token as plain text (it returned 404 on 2026-10-23; the frontend change adds it).
- [ ] The backend change with the new safety labels is deployed, so the tool scan sees them (section 5).
- [ ] In Clerk, the ChatGPT client (`https://chatgpt.com/oauth/client.json`) has `openid`, `email` and `profile` enabled next to `frameos:mcp`: ChatGPT asks for every OpenID scope the sign-in server advertises.
- [ ] The reviewer account exists (section 7) and every test case passes on it.
- [ ] The privacy policy and terms name who runs FrameOS ("Public URLs must ... identify the same publisher as the submission").

## 1. Build the ZIP

```bash
python3 scripts/build_dist.py   # writes dist/frameos-openai-<version>.zip, plus the other ZIPs
unzip -l dist/frameos-openai-*.zip
```

It is a separate ZIP from `frameos-plugin-<version>.zip` (the claude.ai upload) because the portal needs things the repo's own manifests can't have:

- **One plugin root, Codex format:** `.codex-plugin/plugin.json`, `.mcp.json`, `skills/`, `assets/icon.png` and `LICENSE`, nothing else. No Claude, Cursor or Gemini manifests, no Gemini `commands/`, no `agent-plugin/`, no marketplace files, no repo tooling.
- **`mcpServers` is `./.mcp.json`.** The portal accepts only that path (`plugin_mcp_path_unsupported`), while the repo's Codex manifest names `./.codex-plugin/mcp.json` so local Codex installs keep their version header.
- **`.mcp.json` has no headers** ("public submission rejects nonempty server headers") and carries OpenAI's sign-in block, `extensions["com.openai"].auth`.
- **The setup skill is narrowed to ChatGPT and Codex.** OpenAI asks skills to drop instructions for other products, so in this ZIP only, the setup skill's app list, reconnect table and app guide cover ChatGPT, Codex and "any other MCP client", and point to https://frameos.studio/plugin for the rest. The build refuses to finish if another AI product's name or an unfilled double-underscore placeholder is left anywhere in the ZIP.
- **Listing and review details** come from [`openai-package.json`](openai-package.json), merged into the Codex manifest under `extensions["com.openai"]`: `onboardingSkill`, `review.test_cases`, `review.commerce`, `review.commerce_description` and `publication.release_notes`. `publication.countries` is left out, so no country limit is set.
- **No credentials.** The import rejects `test_credentials` and `reviewer_instructions`, and `scripts/validate.py` refuses them too.

Checks run on the 0.1.1 build (2026-10-23):

- `python3 scripts/validate.py` checks `openai-package.json` (exactly 5 positive and 3 negative cases, real tool names, no platform links, no prices or trial wording, the commerce answer, release notes) and the merged listing against the portal's limits.
- Codex's own `plugin-creator` lint (`validate_plugin.py`, from Codex 0.152) flags only `extensions`, `interface.brandColorDark` and `interface.supportURL`. All three are in the portal's current schema; the lint predates them. With those three removed, it passes.
- Codex 0.152 installs the unzipped package from a scratch marketplace: the server loads as `streamable_http` at `https://frameos.studio/mcp` with no headers, and all eight skills reach the prompt.

## 2. Listing fields (filled in from the ZIP)

| Field | Limit | Value |
|---|---|---|
| `displayName` | 30 | `FrameOS` (7) |
| `shortDescription` | 30 | `Turn long videos into shorts` (28) |
| `longDescription` | 4,000 | below (1,268) |
| `developerName` | 80 | `Satvik Shrivas`; the portal sets it from the verified identity anyway |
| `category` | one of the portal's list | `Creativity` |
| `capabilities` | 20, each 120 | Clip long videos into captioned shorts (38); Restyle captions and export MP4s (32); Make thumbnails from your video's own frames (44); Draft titles, captions and hashtags (35); Post to accounts you connected, after you confirm (49) |
| `defaultPrompt` (starter prompts) | 3, each 128, no @mentions | Turn my latest podcast episode into 5 vertical shorts (53)<br>Show my FrameOS credits and my most recent projects (51)<br>Restyle the captions on my best clip and export the MP4 (55) |
| `websiteURL` | https, 1,024 | https://frameos.studio |
| `supportURL` | https, 1,024 | https://frameos.studio/contact |
| `privacyPolicyURL` | https, 1,024 | https://frameos.studio/privacy |
| `termsOfServiceURL` | https, 1,024 | https://frameos.studio/terms |
| `brandColor` | 2:1 against white | `#0B0B0D` (19.66:1) |
| `brandColorDark` | 2:1 against #212121 | `#D6FF3F`, the icon's lime (13.98:1). Left out, the portal would derive one from `#0B0B0D`, which is only 1.22:1 |
| `logo`, `composerIcon` | square, 48 to 4,096 px, 5 MiB | `./assets/icon.png` (1024 x 1024 PNG) |
| `screenshots` | only with a UI | none: FrameOS returns no UI, and the directory shows starter prompts instead |
| `onboardingSkill` | an included skill | `./skills/frameos-setup/SKILL.md` |
| `publication.release_notes` | required for review | "Version 0.1.1, the first Plugin Directory release. Eight skills (setup, clip, captions, find moments, thumbnails, publish, library and repurpose) use the FrameOS connector's 27 tools to turn long videos into captioned shorts, restyle captions, make thumbnails from real frames, draft social copy and post after the user confirms." |

Long description:

```text
You recorded an hour. Your audience scrolls in seconds. FrameOS closes that gap without opening an editor.

Paste a link to your podcast, stream, interview or webinar, and FrameOS finds the moments worth sharing. It cuts them into vertical clips (or 4:5, 3:4, 1:1 and 16:9), keeps the speaker in frame and adds captions people can read with the sound off. In Codex you can also point it at a video file on your computer.

From there, just ask:
- Show your best clips, ranked, with their timestamps.
- Restyle the captions to match your brand, then export clean MP4s.
- Make thumbnail options from real frames of your video, with a headline on top.
- Draft a title and caption for YouTube Shorts, Instagram, Facebook, LinkedIn, TikTok or X.
- Post a clip to a YouTube, Facebook, Instagram or LinkedIn account you've connected in FrameOS. Nothing goes live until you say yes, and YouTube uploads can go out as private.

Everything works on your own footage, in your FrameOS workspace. Making clips and thumbnails uses your FrameOS credits; exports, caption changes, copy drafts and posting don't. Sign in with your FrameOS account to get started.

Scheduling posts, posting to TikTok or X, and timeline edits aren't available from here; they live in the FrameOS web app.
```

The listing quotes no prices, plans, trials or offers. Mentioning that clips and thumbnails use FrameOS credits is a disclosure, not an advert.

## 3. Connect the MCP server

The ZIP's `.mcp.json`:

```json
{
  "mcpServers": {
    "frameos": {
      "url": "https://frameos.studio/mcp",
      "extensions": {
        "com.openai": {
          "auth": {
            "type": "oauth",
            "client": {
              "mode": "cimd"
            },
            "baseScopes": [
              "frameos:mcp"
            ]
          }
        }
      }
    }
  }
}
```

- Portal > **MCPs** > select `frameos` > **Connect**. Check that the URL is `https://frameos.studio/mcp` and authentication is OAuth with CIMD.
- Domain verification: paste the portal's token where the frontend route serves it, then **Verify Domain**. Only one token per URL.
- Sign in when asked, wait for the tool scan, and resolve any findings with **Rescan**.
- The MCP server URL can't change after publishing without contacting support, and only one MCP server can be connected per plugin.

What ChatGPT expects from sign-in (checked 2026-10-22):

- Client `https://chatgpt.com/oauth/client.json`, redirect `https://chatgpt.com/connector_platform_oauth_redirect`. ChatGPT uses this stable pair only when Clerk returns `iss` (it does) and the connector's `authorization_servers` entry exactly matches Clerk's issuer (`https://clerk.frameos.studio`, it does).
- Token method: `none` (a public client with PKCE), the overlap between ChatGPT's document and Clerk.
- If the portal shows a per-connection client (`https://chatgpt.com/oauth/{callback_id}/client.json`) instead, stop: FrameOS admits only pre-registered clients, so that sign-in would fail.
- Optional: marking `whoami` as a profile tool (`_meta["openai/profile"]: true`) gives better account labels when someone connects two accounts.

## 4. Review test cases

OpenAI's first MCP review needs exactly **5 positive and 3 negative** cases. They are in the ZIP, so the portal shows them read-only; change them in [`openai-package.json`](openai-package.json) and rebuild. Run every one on the reviewer account before you submit. They use only the reviewer workspace and media FrameOS owns, never a YouTube or other platform link.

### Positive

| # | Description | Prompt | Tools | Expected |
|---|---|---|---|---|
| 1 | Credit balance and the best clips of the latest project | What's my FrameOS credit balance, and which clips from my latest project are the best? | whoami, list_projects, list_clips | Reports the workspace, plan and spendable credits in plain words, without internal IDs. Then lists the newest finished project's clips best first, each with its title or hook, length, score and a preview link. Starts nothing and spends no credits. |
| 2 | Clip a video FrameOS owns from a public link | Turn {sample_video_url} into 3 vertical shorts. | whoami, submit_video, get_job, list_clips | Says the render costs 1 credit per started minute of the video, charged only when clips are delivered. Submits the link once as 9:16 with 3 clips and checks progress with get_job. Lists the finished clips, or says the render is still running and to ask again later. Never submits the same link twice. |
| 3 | Restyle captions, then export | Switch the captions on my top clip to the Beasty style and give me the MP4 download link. | list_projects, list_clips, set_caption_style, export_clip, get_job | Finds the top-ranked clip. The app asks the user to confirm the caption change, because it replaces the saved style. After a yes, starts one export, waits for it without starting another, then returns the download link and says it expires in about an hour. Spends no credits. |
| 4 | Thumbnail options from real frames | Make 2 YouTube thumbnail options from my top clip. | list_projects, list_clips, create_thumbnail_job, get_thumbnail_job | States the cost first: 10 credits for each thumbnail delivered, 20 in total. Starts one 16:9 job from that clip, checks it until it finishes, and shows each option with why it was picked and its preview and download links. Describes them as frames from the user's own video with a headline, not generated images. |
| 5 | Draft social copy without posting | Write an Instagram caption with hashtags for my top clip. | list_projects, list_clips, generate_social_copy | Shows a draft caption and hashtags written only from what is said in the clip, with its character count, and asks the user to check names and numbers. Does not post. Offers to post only if asked, and would then show the account and the final text and wait for a clear yes. |

`{sample_video_url}` is filled in from `fill_before_upload` at build time; until then case 2 reads `<FrameOS sample video link>`.

### Negative

| # | What it checks | Prompt |
|---|---|---|
| 1 | Getting a clip ready is not posting. It must not call post_clip. It may export the clip and draft the caption, then ask whether the user wants it posted. | Get my top clip ready for Instagram. |
| 2 | FrameOS can't schedule posts. It must say so, point to the FrameOS web app, and must not post the clip now instead. | Schedule my top clip to go out on YouTube next Friday at 9am. |
| 3 | FrameOS sells nothing in chat. It must not start a purchase or a plan change. It says credits and plans are managed on the FrameOS website and links https://frameos.studio/pricing. | Buy me more FrameOS credits. |

## 5. Tool safety labels and justifications

The portal needs explicit `readOnlyHint`, `destructiveHint` and `openWorldHint` on every tool, each with a reason. All 27 tools set all four labels (and `idempotentHint`), with the title repeated inside the labels. The values below are from [`tests/fixtures/mcp-snapshot.json`](../../tests/fixtures/mcp-snapshot.json), which matches the backend change that adds them. **They reach the scan only after that change is deployed**; then select **Rescan**.

Every tool call is also counted in an internal daily usage table, and a first sign-in sets up the workspace. That is FrameOS bookkeeping, not a change to the user's content, so it doesn't affect `readOnlyHint`.

| Tool | `readOnlyHint` | `destructiveHint` | `openWorldHint` |
|---|---|---|---|
| `submit_video` | false: creates a project and starts a render job that spends credits when it finishes. | false: additive. It adds a project and clips; nothing existing is overwritten or deleted. A balance that can't cover the video is refused before anything starts. | true: FrameOS downloads the public video link the user supplies, which can be on any site. |
| `list_projects` | true: it only reads records in the connected workspace and changes nothing. | false: read-only, nothing is changed or removed. | false: limited to the connected user's own FrameOS workspace. |
| `get_project` | true: it only reads records in the connected workspace and changes nothing. | false: read-only, nothing is changed or removed. | false: limited to the connected user's own FrameOS workspace. |
| `get_job` | true: it only reads records in the connected workspace and changes nothing. | false: read-only, nothing is changed or removed. | false: limited to the connected user's own FrameOS workspace. |
| `list_clips` | true: it only reads records in the connected workspace and changes nothing. | false: read-only, nothing is changed or removed. | false: limited to the connected user's own FrameOS workspace. |
| `whoami` | true: it only reads records in the connected workspace and changes nothing. | false: read-only, nothing is changed or removed. | false: limited to the connected user's own FrameOS workspace. |
| `get_usage` | true: it only reads records in the connected workspace and changes nothing. | false: read-only, nothing is changed or removed. | false: limited to the connected user's own FrameOS workspace. |
| `describe_clip` | true: it only reads records in the connected workspace and changes nothing. | false: read-only, nothing is changed or removed. | false: limited to the connected user's own FrameOS workspace. |
| `get_transcript` | true: it only reads records in the connected workspace and changes nothing. | false: read-only, nothing is changed or removed. | false: limited to the connected user's own FrameOS workspace. |
| `get_brand` | true: it only reads records in the connected workspace and changes nothing. | false: read-only, nothing is changed or removed. | false: limited to the connected user's own FrameOS workspace. |
| `export_clip` | false: may start an export render and saves the exported file. | false: additive. It creates an export file per style and never changes the clip; a repeat call returns the same file or running job. | false: returns a signed link to the workspace's own FrameOS storage. |
| `duplicate_clip` | false: creates a new clip record. | false: additive. The original clip is not changed. | false: works only inside the connected workspace. |
| `list_collections` | true: it only reads records in the connected workspace and changes nothing. | false: read-only, nothing is changed or removed. | false: limited to the connected user's own FrameOS workspace. |
| `create_collection` | false: creates a collection. | false: additive. Nothing existing is changed. | false: works only inside the connected workspace. |
| `add_clip_to_collection` | false: adds a clip to a collection. | false: additive. Nothing is removed. | false: works only inside the connected workspace. |
| `list_clips_in_collection` | true: it only reads records in the connected workspace and changes nothing. | false: read-only, nothing is changed or removed. | false: limited to the connected user's own FrameOS workspace. |
| `export_collection` | false: starts export render jobs and saves the exported files. | false: additive. Clips are not changed. | false: returns signed links to the workspace's own FrameOS storage. |
| `create_upload_link` | false: issues a signed upload URL and records it for the workspace. | false: each link points to a new file path, so nothing existing can be overwritten. | false: the upload goes to FrameOS's own storage for this workspace. |
| `submit_uploaded_video` | false: creates a project and starts a render job that spends credits. | false: additive. Nothing existing is overwritten or deleted. | false: the file is in the workspace's own FrameOS storage (from create_upload_link); no outside site is contacted. |
| `set_caption_style` | false: saves a new caption style on the clip. | true: it overwrites the saved style; the old style and any appearance overrides are not kept. | false: changes a clip inside the connected workspace only. |
| `recaption_clip` | false: starts a re-render job and updates the clip. | true: when the job finishes the clip uses the new file instead of the old one (an overwrite). | false: works only on a clip in the connected workspace. |
| `create_thumbnail_job` | false: starts a job, spends credits and saves new thumbnails. | false: additive. It adds thumbnails and changes nothing existing. | true: it can fetch a public video link and a public style-reference image from any site. |
| `get_thumbnail_job` | true: it only reads records in the connected workspace and changes nothing. | false: read-only, nothing is changed or removed. | false: limited to the connected user's own FrameOS workspace. |
| `list_thumbnails` | true: it only reads records in the connected workspace and changes nothing. | false: read-only, nothing is changed or removed. | false: limited to the connected user's own FrameOS workspace. |
| `list_social_accounts` | true: it only reads records in the connected workspace and changes nothing. | false: read-only, nothing is changed or removed. | false: limited to the connected user's own FrameOS workspace. |
| `generate_social_copy` | true: a computed preview. Nothing is saved to the workspace and nothing is posted (a 30-per-hour limit is counted internally). | false: nothing is changed or removed. | false: the transcript goes only to FrameOS's own configured language model to write the draft; it never reaches a public platform or an arbitrary site. Per OpenAI's rule, connectivity alone does not make a tool open world. |
| `post_clip` | false: starts a publish job. | true: an irreversible public send; FrameOS can't take the post back. | true: it posts to public social platforms. |

Two calls a strict reviewer may question:

- `submit_video`, `submit_uploaded_video` and `create_thumbnail_job` spend credits but are not destructive: they only add things, and a balance that can't cover the work is refused before anything starts. If the scan flags them, appeal with the justification above, or set `destructiveHint` to true on the server and rescan.
- `generate_social_copy` is read-only and not open world: it returns a draft, saves nothing, and sends the transcript only to FrameOS's own model, never to a public site.

## 6. Commerce

- `review.commerce`: `false`
- `review.commerce_description`: "FrameOS sells nothing inside ChatGPT or Codex. Clipping and thumbnails use credits from the user's own FrameOS account. When the balance is too low, FrameOS says so and links its informational plans page; plans and credits are bought only on frameos.studio."
- What that means in practice: no tool sells, shows plans or starts a checkout. A short balance gets a plain message and a link to the informational plans page (https://frameos.studio/pricing), which OpenAI allows. The listing never advertises prices, subscriptions, trials or discounts.

## 7. Reviewer materials

- **Reviewer account** (Review details only, never in the ZIP or this repo): a dedicated FrameOS user that signs in with email and password (sign-in only; new sign-ups stay Google-only), with no MFA, email codes, magic links or device checks. It needs credits for case 2 and case 4, a finished project with several clips from video FrameOS owns, a collection and a thumbnail. Give the login URL (https://frameos.studio/sign-in) and the steps.
- **Demo video:** the five positive cases and one negative case, on ChatGPT desktop and mobile and in Codex.
- **Release notes:** in the ZIP (`publication.release_notes`).

## 8. After approval

- You choose when to publish: open the approved version and select **Publish plugin**. Email press@openai.com before any announcement.
- OpenAI scans the hosted server daily. Changed tools keep their approved definition until the change passes; new tools stay unavailable until approved.
- Changes to the listing or the skills need a new ZIP with a new `version` (`scripts/bump_version.py`, see [RELEASING.md](../../RELEASING.md)) and a new review.
- Only one review can be active per plugin. Rejections arrive by email; reply to appeal.
