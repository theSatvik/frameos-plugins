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
- Restyle the captions to match your brand, then export captioned MP4s.
- Make thumbnail options from real frames of your video, with a headline on top.
- Draft a title and caption for YouTube Shorts, Instagram, Facebook, LinkedIn, TikTok or X.
- Post a clip to a YouTube, Facebook, Instagram or LinkedIn account you've connected in FrameOS. Nothing goes live until you say yes, and YouTube uploads can go out as private.

Everything works on your own footage, in your FrameOS workspace. Sign in with your FrameOS account to get started.

Scheduling posts and timeline edits aren't available here; they live in the FrameOS web app. FrameOS can't post to TikTok or X: it writes the caption and gives you the MP4 to upload yourself.
```

The listing quotes no prices, plans, trials, offers or credits: OpenAI's metadata check (2026-10-30) flagged a sentence about which actions use FrameOS credits as pricing, so the cost is stated in chat before anything is spent instead.

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

Every tool sets `readOnlyHint`, `destructiveHint` and `openWorldHint` (and `idempotentHint`) to explicit booleans, with the title repeated inside the labels. OpenAI's first review (2026-11-13) found labels that didn't match what the tools do. The connector update of 2026-11-14 follows OpenAI's current rules: credits are never refunded, so spending them is an irreversible transaction, and every description now states what its labels rest on (credit spend, overwrites, public posts, and what a retry repeats). What changed:

- `submit_video`, `submit_uploaded_video` and `create_thumbnail_job`: `destructiveHint` false to true (they spend credits that are never refunded; `submit_uploaded_video` also deletes the uploaded file after a successful render).
- `set_caption_style` and `create_collection`: `idempotentHint` false to true (a repeat with the same arguments changes nothing).
- `list_projects` no longer settles stalled renders while it lists (the web dashboard's own list still does), and the job tools don't read reframe jobs, so every read-only tool changes nothing.

The pre-resubmission audit (connector 0.1.3, 2026-11-15) also changed what tools return and say:

- `whoami` no longer returns the user or workspace ID, and `list_projects` and `get_project` show `uploadedFile` instead of an uploaded file's storage path. Job results leave out the raw start time and, for thumbnails, internal scoring (OpenAI's response-minimization rule).
- A short balance is explained ("This workspace has no credits left to process this video") with a link to the informational plans page, never "upgrade".
- The server instructions add that `post_clip` posts right away and that scheduling, timeline edits and connecting accounts are done in the FrameOS web app. They carry no links and nothing about buying: OpenAI's scan marked a version with both "needs further review" (2026-11-17), so the pricing link stays in the 402 message and the skills, and the rights line in the `submit_video` and `create_thumbnail_job` descriptions. Descriptions state the input limits (`max_clips` 1 to 20, `focus_prompt` up to 1000 characters, transcript pages up to 500, `tone` up to 100 characters).
- The unused `content_type` and `include_face` inputs are gone.

The values below are from [`tests/fixtures/mcp-snapshot.json`](../../tests/fixtures/mcp-snapshot.json). **They reach the scan only after the connector is deployed**; then select **Rescan**.

Every tool call is also counted in an internal daily usage table, and a first sign-in sets up the workspace. That is FrameOS bookkeeping, not a change to the user's content, so it doesn't affect `readOnlyHint`.

| Tool | `readOnlyHint` | `destructiveHint` | `openWorldHint` |
|---|---|---|---|
| `submit_video` | false: it creates a project in the user's workspace (or re-runs a failed one) and starts a render job that saves new clips and spends credits. | true: when the clips are saved it spends the workspace's credits (1 per source minute), and FrameOS never refunds credits, so each run is an irreversible transaction. Resubmitting a link whose last run failed, stopped or stalled also re-runs that project in place, replacing its settings and, on success, its clips. | true: it fetches the video from the public http(s) link the user provides, an outside destination the user chooses rather than their FrameOS workspace. |
| `list_projects` | true: it reads one page of the connected workspace's projects (status, progress, clip count) and changes nothing; it starts no job and charges nothing. | false: it is read-only, so nothing is written, deleted or spent. | false: it is confined to the connected user's own FrameOS workspace and contacts no outside site. |
| `get_project` | true: it reads one project's status, progress, source link (null for an uploaded file) and clip count from the connected workspace and changes nothing. | false: it is read-only, so nothing is written, deleted or spent. | false: it is confined to the connected user's own FrameOS workspace and contacts no outside site. |
| `get_job` | true: it reads the stored state, progress, message, ETA and result of a job owned by the connected workspace. Polling never starts, changes, cancels or charges anything. | false: it is read-only, so nothing is written, deleted or spent. | false: it reads only FrameOS's own job records for the user's workspace and contacts no outside site. |
| `list_clips` | true: it reads the clips of one owned project and returns them; nothing is created, changed, queued or sent. The media links are signed for about an hour at call time and never stored. | false: it is read-only, so nothing is written, deleted or spent. | false: it stays inside the user's own workspace and FrameOS's private storage, and fetches no outside URL. |
| `whoami` | true: it reads the workspace's name, plan and credit balance; it never spends, holds or changes credits or settings. | false: it is read-only, so nothing is written, deleted or spent. | false: it reads only the connected FrameOS account and contacts no outside site. |
| `get_usage` | true: it reads the workspace's last 30 days of credit charges and its current balance, and never spends, holds or refunds anything. Preview links are signed per call and never stored. | false: it is read-only, so nothing is written, deleted or spent. | false: it reads only the connected workspace's own records and FrameOS's own storage, and contacts no third party. |
| `describe_clip` | true: it reads one clip the connected workspace owns and returns it; nothing is created, changed, queued or sent. The media links are signed for about an hour at call time and never stored. | false: it is read-only, so nothing is written, deleted or spent. | false: it stays with one clip in the user's own workspace and FrameOS's private storage, and contacts no outside site. |
| `get_transcript` | true: it reads the transcript FrameOS saved when the project rendered and returns a page or time range of it. Nothing is created, changed or sent. | false: it is read-only, so nothing is written, deleted or spent. | false: it reads only the user's own project from FrameOS's private storage, and does not re-fetch the source video or call any outside service. |
| `get_brand` | true: it reads the workspace's saved default brand template and signs a one-hour preview link to its logo; no template or setting is created, changed or deleted. | false: it is read-only, so nothing is written, deleted or spent. | false: it reads only the workspace's own brand settings and the logo file in that workspace's own folder in FrameOS storage. |
| `export_clip` | false: when the captioned file for that style isn't in storage yet, it starts a background render job that saves a new MP4 in the user's FrameOS storage. | false: it only adds an export file at a name the API first checks is free; the clip, its saved style and its existing files are never changed or deleted, and no credits are spent. A repeat returns the same running job or the finished file. | false: it acts only on a clip in the user's own workspace, using FrameOS's own storage and render workers. The download link is a one-hour signed URL to the user's own file, given only to the caller. |
| `duplicate_clip` | false: it saves a new clip record in the user's project. | false: purely additive; the copy points at the original's existing media, and the original clip, its media and its settings are not changed or deleted. No credits are spent. | false: it stays inside the user's own FrameOS project; nothing is fetched from or sent outside FrameOS. |
| `list_collections` | true: it runs one query over the workspace's collections and returns id, name, creation time and clip count; it creates, changes, starts and charges nothing. | false: it is read-only, so nothing is written, deleted or spent. | false: the query is limited to the signed-in user's private FrameOS workspace and reaches no outside site. |
| `create_collection` | false: it saves one new collection record in the workspace. | false: purely additive; it inserts one empty, private collection and never edits or removes anything. A duplicate name is refused and the existing collection is left as it was. | false: it writes only inside the user's own private FrameOS workspace; nothing is published or sent outside FrameOS. |
| `add_clip_to_collection` | false: it saves a link between a clip and a collection in the workspace. | false: additive only; it adds one membership entry, or nothing if the clip is already there, and never changes, moves or deletes the clip, the collection or other entries. No credits are spent. | false: the clip and the collection must both belong to the signed-in user's workspace, and nothing leaves FrameOS. |
| `list_clips_in_collection` | true: it reads which clips are in the collection and signs short-lived links to them on each call; nothing is stored, started, changed or charged. | false: it is read-only, so nothing is written, deleted or spent. | false: it reads only the user's private workspace; the links point at the user's own files and go only to the caller. |
| `export_collection` | false: for clips whose captioned file isn't ready, it starts background render jobs (at most 10 rendering per call) that save new MP4s in the user's FrameOS storage. | false: it only adds export files at names the API checks are free and returns links; it never changes or deletes the clips, their saved styles, the collection or existing files, and spends no credits. | false: it is limited to clips in a collection the user's workspace owns, and nothing is fetched from or posted outside FrameOS. The links are one-hour signed URLs to the user's own files. |
| `create_upload_link` | false: each call opens a new upload slot, records an upload claim for the workspace, and returns a signed URL that grants write access to that slot for one hour. | false: every slot is a new, randomly named file, so the link can't overwrite or delete anything that exists, and no credits are spent. An unused link simply expires. | false: the link points only at the connected workspace's private FrameOS storage, and the call contacts no public site, social platform or AI service. |
| `submit_uploaded_video` | false: it creates a project and starts a render job that saves new clips, spends credits and then deletes the uploaded file. | true: it spends credits (1 per source minute) that FrameOS never refunds, and after a successful render it deletes the uploaded source file, which FrameOS can't restore. A repeat after a failed, stopped or stalled run also re-runs that project in place, replacing its saved settings. | false: it only processes a file already uploaded to the connected workspace's private FrameOS storage (the gs:// path is ownership-checked) and fetches no web link. Transcription and clip picking use FrameOS's fixed AI processors, not destinations chosen by the user or the model. |
| `set_caption_style` | false: it saves a new caption style, and optionally an appearance, on the clip. | true: it overwrites the clip's saved caption style, and when appearance is left out it erases earlier font, size, position and animation overrides; FrameOS keeps no copy of the old settings. That is an overwrite even though the user could type the old values in again. | false: it is one database update on the user's own clip in their private FrameOS workspace; no job, file, link or outside service is involved. |
| `recaption_clip` | false: for an overlay clip it saves a new caption style at once; for an older burned-caption clip it starts a re-render job that then changes the clip. | true: for a burned-caption clip the finished job points the clip at the new render, keeps no link to the old file and switches the clip to overlay captions; for an overlay clip it overwrites the saved style and clears omitted appearance overrides. Calling again with the old style would not bring the old video back. | false: it touches only the user's own clip and FrameOS's own database, storage and render workers; no user-supplied link, social platform or AI provider is involved. |
| `create_thumbnail_job` | false: it starts a background job that saves new thumbnail images and records to the workspace and deducts credits. | true: each successful job takes 10 credits per thumbnail off the balance for good (FrameOS never refunds credits), an irreversible transaction, and every call, retries included, charges again. The host should confirm with the user before each call. | true: it fetches the public http(s) video link and optional style-reference image the user provides, outside destinations the user chooses; with video_id it re-downloads a link-sourced project's original from its link. |
| `get_thumbnail_job` | true: it reads the stored status and result images of a thumbnail job the workspace owns; it never starts, finishes, bills or re-signs anything. | false: it is read-only, so nothing is written, deleted or spent. | false: it reads FrameOS's own job store for the user's own job and contacts no outside site. |
| `list_thumbnails` | true: it reads the workspace's saved thumbnail records and signs short-lived view and download links on each call; nothing is stored, changed or charged. | false: it is read-only, so nothing is written, deleted or spent. | false: it reads only the user's private workspace; the links point at the user's own images and go only to the caller. |
| `list_social_accounts` | true: it reads the workspace's saved records of connected accounts (id, platform, name, picture, whether it needs reconnecting) and never returns sign-in tokens. It connects, disconnects or changes nothing. | false: it is read-only, so nothing is written, deleted or spent. | false: it reads only FrameOS's own database for the user's workspace and never contacts YouTube, Facebook, Instagram, LinkedIn or any other service. |
| `generate_social_copy` | true: it computes a draft title, caption and hashtags from the clip's transcript and returns them; nothing is saved, the clip is unchanged, nothing is posted and no credits are spent. The only trace is an internal counter that caps drafts at 30 per workspace per hour. | false: it is read-only, so nothing is overwritten, deleted, published or charged. | false: it works on one clip in the user's private workspace and sends the transcript only to the third-party AI provider FrameOS has set up to write the reply, never to a destination the user or model chooses. Nothing is published or made public. |
| `post_clip` | false: it publishes a video to the user's social account and records the post and its upload job in FrameOS. | true: publishing is an irreversible public send; once started FrameOS can't cancel it or take the post down, and each call publishes another copy. Being able to delete the post later on the platform doesn't make it non-destructive. | true: it posts to public third-party platforms (YouTube, Facebook, Instagram, LinkedIn), where people outside FrameOS can see it. |

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
