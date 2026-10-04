# Install FrameOS in Claude.ai, Claude Desktop and Cowork

There are three ways in. Pick one:

| Route | You get | Best for |
|---|---|---|
| [A. Plugin](#a-add-the-plugin) | The eight skills and the connector | Most people |
| [B. Custom connector](#b-add-a-custom-connector-by-url) | The FrameOS tools only | Free plan, or when plugins are not available to you |
| [C. Skill upload](#c-upload-individual-skills) | One or more skills, no connector | Adding skills next to route B |

> **Coming soon: claude.ai, Claude Desktop and Cowork can't sign in to FrameOS yet.** The FrameOS connector is live as of 2026-10-05, but its sign-in server only admits pre-registered apps for now, and so far only Claude Code is pre-registered ([status](../status.md)). None of these routes has been tested on claude.ai yet. Menu names below come from Anthropic's documentation.

Everything you add on claude.ai is saved to your account, so it also works in Claude Desktop and Cowork.

## A. Add the plugin

1. Go to **Customize > Plugins** (https://claude.ai/customize/plugins) in claude.ai or the desktop app.
2. Select **Add > Add marketplace** and enter `theSatvik/frameos-plugins` (or `https://github.com/theSatvik/frameos-plugins`).
3. FrameOS now appears alongside your other plugins. Select it, then select **Add** (in Cowork the button is **Install**).
4. Adding a plugin does not sign you in. Open the FrameOS plugin, go to its **Connectors** tab and connect FrameOS. Skills load either way, but they can't reach FrameOS until the connector shows **Connected**.

Not yet verified: whether **Add marketplace** accepts this repo, whose root is the plugin. If it does not, use **Add > Upload plugin** with the plugin ZIP instead:

- Build it with `python3 scripts/build_dist.py` (it writes `dist/frameos-plugin-<version>.zip`), or download it from the repo's GitHub releases once one is published.
- The archive must contain exactly one `.claude-plugin/plugin.json`. Upload accepts up to 200 MB and 5,000 files.

To pick up new versions, select **Check for updates** on the marketplace, or turn on **Sync automatically**.

What loads where: skills and the remote connector work in chat and Cowork. You can add up to 25 marketplaces yourself per organization. Browsing the public directory (**Discover**) needs Pro, Max, Team or Enterprise; FrameOS is not in the directory yet.

## B. Add a custom connector by URL

Works on Free, Pro, Max, Team and Enterprise. On the Free plan you can add one custom connector.

**Free, Pro or Max:**

1. Go to **Customize > Connectors** and click **Add custom connector**.
2. **MCP server URL:** `https://frameos.studio/mcp`
3. **Authentication:** **Sign in now** (or **Sign in when needed**).
4. **OAuth client:** **Use Claude's published identity**. If sign-in later fails with a registration error, remove the connector and add it again with **Register automatically**.
5. Leave **Request headers** and **Advanced > Transport** alone. Click **Add**, then **Connect**.

**Team or Enterprise:** an Owner adds the connector for everyone under **Organization settings > Connectors** (https://claude.ai/admin-settings/connectors): select **Add**, then **Custom**, choose **Web** if asked, enter `https://frameos.studio/mcp`, and click **Add**. Each member then goes to **Customize > Connectors**, finds FrameOS with the **Custom** label, and clicks **Connect**.

Authentication settings can't be edited after you add a connector. To change them, remove the connector and add it again.

## C. Upload individual skills

Needs Pro, Max, Team or Enterprise, with **Code execution and file creation** turned on.

1. Build the skill ZIPs: `python3 scripts/build_dist.py` writes one per skill to `dist/claude-ai/<skill>.zip`. Each ZIP has the skill folder at the top level (`frameos-clip.zip` contains `frameos-clip/SKILL.md`), which is what claude.ai expects. A ZIP with `SKILL.md` at its root is not recognised.
2. Go to **Customize > Skills** and upload the ZIP. Turn the skill on.
3. Skills need the connector to do anything, so add it with route B.

To zip one by hand: `cd skills && zip -r ../frameos-clip.zip frameos-clip/`, then check with `unzip -l ../frameos-clip.zip` that every entry starts with `frameos-clip/`.

## Check it works

Start a new chat and ask:

```text
What is my FrameOS credit balance?
```

You should get your workspace name and a credit number. A "Connected" label alone is not proof.

## Sign in again or fix the connection

- Sign-in expired or failed: go to **Customize > Connectors**, open FrameOS, disconnect it and click **Connect** again. For the plugin's connector you can also use the plugin's **Connectors** tab.
- A "missing permission" (403) error: remove the FrameOS connector and add it again, so the new permission is requested at sign-in.

## Known limitations

- Each tool call in claude.ai and Desktop has a time limit of about 4 minutes, so FrameOS never waits for a render inside one call. A render usually takes 10 to 30 minutes: start it, then come back and ask "check my FrameOS render".
- Uploading a file from your computer needs an agent that can run commands. In chat, share a public link instead (YouTube, Vimeo, Twitch, Kick, a public Google Drive file, or a direct video URL), or upload in the web app at https://frameos.studio/dashboard.
- A plugin you add here appears in Claude Code as `frameos@synced` at its next session start.
