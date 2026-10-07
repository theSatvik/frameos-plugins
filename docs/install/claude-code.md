# Install FrameOS in Claude Code

Claude Code is the first app that can sign in to FrameOS. Connect it and you can ask Claude Code things like "turn this episode into 5 shorts" or "restyle the captions on my best clip".

| Route | You get | Status |
|---|---|---|
| [A. Connect FrameOS directly](#a-connect-frameos-directly) | The FrameOS tools | Works: tested end to end with a real account on 2026-10-05 |
| [B. Install the plugin](#b-install-the-plugin) | The eight FrameOS skills plus the connector | Installs (checked locally with Claude Code 2.1.282); signing in through the plugin's connection is not tested yet |

Pick one. Using both gives you two copies of every FrameOS tool.

> **Status, 2026-10-05.** The FrameOS connector is live, and Claude Code is the only app that can sign in so far ([status](../status.md)). Route A passed a real end-to-end test: sign-in, consent, then `whoami` and `list_projects` returned the account's real data. Route B points at the same connector, but its sign-in has not been tested yet.

## Requirements

- Claude Code. For route B you need plugin support: the plugin steps were checked with 2.1.282, and the one-step plugin install needs 2.1.275 or later.
- For route B, `git` on your machine (Claude Code clones the marketplace repo).
- A FrameOS account. Signing in for the first time creates your workspace.

## A. Connect FrameOS directly

From your shell:

```bash
claude mcp add --transport http -s user frameos https://frameos.studio/mcp
claude mcp login frameos
```

`-s user` makes FrameOS available in all your projects. `claude mcp login frameos` opens your browser: sign in to FrameOS and approve Claude Code's access. Over SSH, add `--no-browser`; it prints a link to open on your own machine, then you paste the redirect URL back.

You can also sign in from inside a session: run `/mcp`, select `frameos`, and follow the steps in your browser.

This route gives you the FrameOS tools without the skills, so Claude Code works from the tools' own descriptions. If you want the skills too, use route B instead.

## B. Install the plugin

The plugin adds the eight FrameOS skills (when to check your credits, how long to wait for a render, which caption styles exist, never to post without your go-ahead) and its own connection to the same connector, named `plugin:frameos:frameos`. If you already connected FrameOS with route A, remove that first: `claude mcp remove frameos -s user`.

From your shell:

```bash
claude plugin marketplace add theSatvik/frameos-plugins
claude plugin install frameos@frameos
```

Or inside a Claude Code session:

```text
/plugin marketplace add theSatvik/frameos-plugins
/plugin install frameos@frameos
```

On 2.1.275 or later you can do both in one step:

```text
/plugin install frameos --marketplace theSatvik/frameos-plugins
```

`claude plugin install` takes `--scope user|project|local` (default `user`). If the install summary says `Run /reload-plugins to activate.`, run `/reload-plugins`, or start a new session.

### Sign in through the plugin

- In a session: run `/mcp`, select `plugin:frameos:frameos`, and follow the steps in your browser.
- `claude mcp login` from your shell does not work here: it only sees connections you added yourself, not a plugin's. Use `/mcp` inside a session.

Not tested yet: this uses the same connector and sign-in server as route A, but no one has signed in through the plugin's connection so far. If it fails, uninstall the plugin (`claude plugin uninstall frameos@frameos`) and use route A for now.

### For a team repository

Commit this to the repository's `.claude/settings.json` so everyone working in it gets FrameOS offered:

```json
{
  "extraKnownMarketplaces": {
    "frameos": { "source": { "source": "github", "repo": "theSatvik/frameos-plugins" } }
  },
  "enabledPlugins": { "frameos@frameos": true }
}
```

Each person still runs `claude plugin install frameos@frameos --scope project` once.

## Non-interactive runs

`claude -p` and the Agent SDK cannot sign in on their own. Sign in once interactively first, with either route.

## Check it works

In a new conversation, ask:

```text
What is my FrameOS credit balance?
```

You should see your workspace name and a credit number. `claude mcp list` should list `frameos` (route A) or `plugin:frameos:frameos` (route B), but a "connected" status on its own isn't proof; only a real answer is.

With the plugin, the skills are also available as slash commands, for example `/frameos:frameos-clip` and `/frameos:frameos-setup`.

## Sign in again or fix the connection

The server is `frameos` with route A and `plugin:frameos:frameos` with route B.

- "Needs authentication", or a sign-in error in the middle of a task: run `/mcp`, select the FrameOS server, then **Re-authenticate**.
- A "missing permission" (403) error: in `/mcp`, choose **Clear authentication** for the FrameOS server (or run `claude mcp logout frameos`, or `claude mcp logout plugin:frameos:frameos`), then sign in again so the new permission is requested.
- Connection errors: `claude mcp get frameos` (or `claude mcp get plugin:frameos:frameos`) shows the HTTP status and the server's error text.
- FrameOS's own errors reach Claude as `FrameOS returned HTTP <code>: <detail>`, so Claude can tell you what went wrong.

## Update or remove

Route A:

```bash
claude mcp remove frameos -s user
```

Route B:

```bash
claude plugin marketplace update frameos
claude plugin update frameos@frameos
claude plugin uninstall frameos@frameos
```

Auto-update is off by default for third-party marketplaces. Turn it on in `/plugin` > **Marketplaces** > `frameos` > **Enable auto-update**.

## Good to know

- Tool names in permission rules look like `mcp__frameos__whoami` with route A and `mcp__plugin_frameos_frameos__whoami` with route B. `mcp__frameos__*` or `mcp__plugin_frameos_frameos__*` covers all FrameOS tools.
- Claude Code can upload a local video file for you, because it can run commands (the upload is an HTTP PUT with `curl`).
- If you also add FrameOS as a connector on claude.ai with the same URL, the plugin's connection takes precedence in Claude Code and the claude.ai one is hidden in `/mcp`.
- A plugin you add on claude.ai shows up in Claude Code as `frameos@synced`. Plugins installed from the CLI are not pushed to your claude.ai account.
- With the plugin, every request carries an `X-FrameOS-Plugin-Version` header with the plugin version.
