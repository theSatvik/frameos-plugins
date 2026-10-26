# Submission checklist: Grok, Grok Bot and the Cursor Marketplace

One form lists FrameOS in all three: https://x.ai/bot/marketplace/submit-a-plugin. Grok Bot's "Connect apps" list comes from the Cursor Marketplace, so a single submission covers Cursor and Grok Bot now, and Grok (grok.com) once that destination opens.

**Use this form only.** Don't also apply at https://cursor.com/marketplace/publish: it is the same catalog, and two applications for one plugin just slow review. Later updates are a re-index request, not a new application (Publisher Terms 2.1).

Submitting means accepting the [Cursor Marketplace Publisher Terms](https://cursor.com/marketplace-publisher-terms): the plugin is free to install (a paid FrameOS account behind it is fine), the privacy policy and terms are public, and plugin data is never sold or used for training.

## Before you submit (owner)

- [x] In Clerk, done 2026-10-23: the CIMD clients for Cursor (web, cloud agents and Grok Bot) and Grok are pre-registered. Neither is tested end to end yet.
- [ ] Confirm whether Cursor's public client `xdXqonkwYm2XzM1Z` still needs `https://www.cursor.com/agents/mcp/oauth/callback` and `https://www.cursor.com/bot/mcp/oauth/callback` now that the CIMD clients are registered.
- [ ] Test in Cursor web or a Cloud Agent: install, sign in, ask "What's my FrameOS credit balance?".
- [ ] Test in Grok Bot: tell a bot "Add this MCP server: https://frameos.studio/mcp", approve the sign-in card, then run a clip, a thumbnail and a private YouTube post. Tick **Grok Bot** below only once this works.
- [ ] The logo URL below returns the image (it returned 404 on 2026-10-23; the frontend change that adds it must ship first).
- [ ] The reviewer account exists (email and password sign-in, no MFA, credits and a finished project). Its login goes only to x.ai (privately, or in the form itself), never in this repo.

## The form, field by field

Limits are the form's own `maxlength` values (read 2026-10-23).

| Field | Limit | Answer |
|---|---|---|
| First Name | 40 | `Satvik` |
| Last Name | 40 | `Shrivas` |
| Work Email | 254 | `support@frameos.studio` |
| Organization Name | 100 | `FrameOS` |
| Organization Handle | 40, lowercase, no spaces | `frameos` (if taken, `frameos-studio`) |
| Website URL | 200 | `https://frameos.studio` |
| Logotype URL | 200, 1:1 SVG or PNG with a background plate | `https://frameos.studio/frameos/frameos-logo-1024-plate.png` |
| Where do you want to be listed? | | Tick **Grok (coming soon)**, **Grok Bot** and **Cursor** |
| MCP Server URL or Public GitHub Repository | 200 | `https://github.com/theSatvik/frameos-plugins` |
| Brief Description | 600 | below |
| Testing Instructions | 600 | below |
| "I've tested this plugin locally and in-app" | | Tick only after both tests above pass |

Why the repository rather than the bare server URL: the repo carries the Cursor plugin manifest with FrameOS's Cursor client ID and sign-in scopes, plus the eight skills, and names the server `https://frameos.studio/mcp` inside it. The description gives the server URL too, for Grok.

Brief Description (506 of 600 characters):

```text
FrameOS turns long videos into captioned short clips, right from your chat. Paste a link to a podcast, stream or webinar and FrameOS finds the moments worth sharing, cuts vertical clips that keep the speaker in frame, and adds captions people can read with the sound off. Then restyle captions, export MP4s, make thumbnails from real frames, draft titles and captions, and post to YouTube, Facebook, Instagram or LinkedIn after you confirm. Works on your own footage. MCP server: https://frameos.studio/mcp
```

Testing Instructions (558 of 600 characters):

```text
Sign in with our test account: email and password, no MFA. We share the login privately; email support@frameos.studio and we'll send it. The account has credits and a finished project. Try:
1. What's my FrameOS credit balance?
2. Show the best clips from my latest project.
3. Switch the captions on my top clip to Beasty and give me the MP4 link.
4. Make 2 YouTube thumbnail options from my top clip.
5. Write an Instagram caption for my top clip.
Posting always asks for a yes first. Server: https://frameos.studio/mcp (OAuth). Help: support@frameos.studio
```

Reviewers move faster when they can sign in straight away. If you'd rather not wait for their email, swap the second sentence for the test login itself when you fill in the form (the form goes only to x.ai), keeping the field under 600 characters. Never put the login in this repo.

## After you submit

- Review has no published time frame. Expect an email to support@frameos.studio.
- Once listed, add the Cursor Marketplace and Grok Bot links to https://frameos.studio/plugin and to [install/cursor.md](../install/cursor.md).
- The Grok Build CLI has a separate catalog, `xai-org/plugin-marketplace`, opened by pull request: see [community.md](community.md#xai-grok-build-plugin-marketplace).
