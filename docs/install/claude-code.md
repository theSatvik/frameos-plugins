# Install FrameOS in Claude Code

You get the eight FrameOS skills plus the FrameOS connector, so you can ask Claude Code things like "turn this episode into 5 shorts" or "restyle the captions on my best clip".

> **Not yet verified on a live account.** The FrameOS connector is not live as of 2026-10-02 ([status](../status.md)). Installing works today (checked locally with Claude Code 2.1.282); signing in will fail until the connector launches.

## Requirements

- Claude Code with plugin support. The steps below were checked with 2.1.282. The one-step install needs 2.1.275 or later.
- `git` on your machine (Claude Code clones the marketplace repo).
- A FrameOS account. Signing in for the first time creates your workspace.

## Install

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

## Sign in

The connector shows up as `plugin:frameos:frameos`. Sign in once:

- In a session: run `/mcp`, select `plugin:frameos:frameos`, and follow the steps in your browser.
- From your shell: `claude mcp login plugin:frameos:frameos`. Over SSH, add `--no-browser`; it prints a link to open on your own machine, then you paste the redirect URL back.

Non-interactive runs (`claude -p`, the Agent SDK) cannot sign in on their own. Sign in once interactively first.

## Check it works

In a new conversation, ask:

```text
What is my FrameOS credit balance?
```

You should see your workspace name and a credit number. You can also run `claude mcp list` and look for `plugin:frameos:frameos`. Today it shows `Failed to connect` because the endpoint returns 404.

The skills are also available as slash commands, for example `/frameos:frameos-clip` and `/frameos:frameos-setup`.

## Sign in again or fix the connection

- "Needs authentication", or a sign-in error in the middle of a task: run `/mcp`, select `plugin:frameos:frameos`, then **Re-authenticate**.
- A "missing permission" (403) error: in `/mcp`, choose **Clear authentication** for `plugin:frameos:frameos` (or run `claude mcp logout plugin:frameos:frameos`), then sign in again so the new permission is requested.
- Connection errors: `claude mcp get plugin:frameos:frameos` shows the HTTP status and the server's error text.

## Update or remove

```bash
claude plugin marketplace update frameos
claude plugin update frameos@frameos
claude plugin uninstall frameos@frameos
```

Auto-update is off by default for third-party marketplaces. Turn it on in `/plugin` > **Marketplaces** > `frameos` > **Enable auto-update**.

## Connector only, without the skills

If you only want the tools:

```bash
claude mcp add --transport http frameos https://frameos.studio/mcp
```

Then run `/mcp` and sign in. Don't use this together with the plugin, or you'll have two copies of every FrameOS tool.

## Good to know

- Tool names in permission rules look like `mcp__plugin_frameos_frameos__whoami`. `mcp__plugin_frameos_frameos__*` covers all FrameOS tools.
- Claude Code can upload a local video file for you, because it can run commands (the upload is an HTTP PUT with `curl`).
- If you also add FrameOS as a connector on claude.ai with the same URL, the plugin's connection takes precedence in Claude Code and the claude.ai one is hidden in `/mcp`.
- A plugin you add on claude.ai shows up in Claude Code as `frameos@synced`. Plugins installed from the CLI are not pushed to your claude.ai account.
- Every request carries an `X-FrameOS-Plugin-Version` header with the plugin version.
