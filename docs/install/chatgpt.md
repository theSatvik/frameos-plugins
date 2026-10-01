# Use FrameOS in ChatGPT

Today the way in is **developer mode**: you add the FrameOS connector to ChatGPT yourself. A listing in the ChatGPT plugin directory, which would also bring the FrameOS skills, needs OpenAI's review first and has not been submitted yet ([checklist](../submission/openai.md)).

> **Not yet verified on a live account.** The FrameOS connector is not live as of 2026-10-02 ([status](../status.md)), and nothing here has been tested in ChatGPT yet. Steps come from OpenAI's developer documentation.

## Requirements

- A ChatGPT **Pro, Plus, Business, Enterprise or Education** account, on the web. Developer mode can also depend on your workspace's policy.
- A FrameOS account. Signing in for the first time creates your workspace.

## Add FrameOS in developer mode

1. In ChatGPT, open **Settings > Security and login** and turn on **Developer mode**.
2. Go to **ChatGPT Plugins** (https://chatgpt.com/plugins) and select the **plus** button.
3. Enter a name (`FrameOS`) and a short description, for example "Turn long videos into captioned short clips".
4. Under **Connection**, enter the MCP server URL `https://frameos.studio/mcp`.
5. For authentication choose **OAuth**, create the connection, and sign in to FrameOS when asked.
6. Review the tools ChatGPT found. The app is listed under **Drafts**.

## Use it

Start a new conversation, open the **Plus** menu, choose **Developer mode**, and select FrameOS. Then talk normally:

```text
What is my FrameOS credit balance?
```

You should get your workspace name and a credit number. That is the check that the connection works.

ChatGPT asks you to confirm write actions by default, and it treats every tool that is not marked read-only as a write. Expect a confirmation before FrameOS starts a render, exports, changes captions, makes thumbnails or posts. You can remember a choice per conversation.

## Sign in again or refresh

- Open the app at **ChatGPT Plugins**, go to its details page, and select **Refresh** to pull new tools and descriptions after FrameOS updates.
- If sign-in expires or FrameOS reports a missing permission (403), remove the app and add it again so ChatGPT signs in from scratch. (The exact reconnect controls on the details page are not yet verified.)

## Known limitations

- **No skills in developer mode.** A developer-mode app carries the connector only, so ChatGPT works from the tools' own descriptions. You can paste prompts from [workflows.md](../workflows.md) to get the same behaviour. The skills arrive with the directory listing.
- **Renders take time.** A render usually takes 10 to 30 minutes, and a chat can't wait that long. Start it, then come back and ask "check my FrameOS render".
- **Links, not files.** ChatGPT can't upload a file from your computer to FrameOS. Share a public link instead (YouTube, Vimeo, Twitch, Kick, a public Google Drive file, or a direct video URL), or upload in the web app at https://frameos.studio/dashboard.
- **Sign-in prerequisites.** ChatGPT needs FrameOS's sign-in server to offer client registration and the FrameOS permission by default. Both are still pending ([status](../status.md#prerequisites-before-any-host-can-connect)).

## For workspace admins

OpenAI documents two ways for Business and Enterprise admins to share a plugin with a workspace. Neither has been tried with FrameOS yet:

- **Publish a developer-mode app to the workspace** from **Plugins > Personal**, using the app's menu and **Publish**.
- **Import a marketplace from GitHub** under **Admin > Plugins > Import marketplace**. It accepts `.agents/plugins/marketplace.json` or `.claude-plugin/marketplace.json`, both of which this repo has (`theSatvik/frameos-plugins`), and syncs daily.

## Codex

Codex uses the same plugin package and installs from this repo today. See [codex.md](codex.md).
