# FrameOS install protocol (for AI agents)

A user pasted something like "Install FrameOS by following this page". You are the agent doing the install. Follow these steps in order and report back in plain language. The human-readable guides are in [docs/install/](install/).

## Rules

- Install FrameOS only into the app you are running in. Don't change other apps' settings.
- Show the user each command before you run it and ask once for a go-ahead for the whole install.
- Never ask for, print or store passwords, tokens or API keys. FrameOS signs in through the browser; you never handle credentials.
- Don't edit config files by hand when a CLI command exists for the job.
- Bound every wait. Never loop forever.
- A "connected" status is not proof. Only a successful `whoami` call counts.
- **As of 2026-10-05 the FrameOS connector is live, but only Claude Code can sign in** ([status](status.md)). Every other app is coming soon: its sign-in is not enabled yet. In any other app, install if the user wants the packages ready, then stop before sign-in and tell the user clearly that sign-in for their app is not enabled yet. Don't keep retrying.
- In Claude Code, the path tested end to end is connecting the connector directly ([install/claude-code.md](install/claude-code.md), route A). Signing in through the plugin's own connection, `plugin:frameos:frameos`, has not been tested yet. If it fails, tell the user and point them to route A, which means uninstalling the plugin first so the tools aren't duplicated.

## Step 1. Identify the host

Work out which app you are running in, then follow its column below.

| You are | Can you run shell commands? | Path |
|---|---|---|
| Claude Code (terminal, IDE, or the desktop app's Code tab) | Yes | [Claude Code](#claude-code) |
| Codex CLI | Yes | [Codex](#codex) |
| Gemini CLI | Yes | [Gemini CLI](#gemini-cli) |
| Copilot CLI | Yes | [Copilot CLI](#copilot-cli) |
| Devin CLI or Devin Desktop | Yes | [Devin](#devin) |
| Cursor agent | Yes | [Cursor](#cursor) |
| Claude.ai chat, Claude Desktop chat, Cowork, ChatGPT, Perplexity, VS Code chat without a terminal | No, or not for app settings | [Chat apps](#chat-apps) |

If you can't tell, ask the user which app they are using.

## Step 2. Inspect before installing

Check whether FrameOS is already installed, so you don't install it twice.

### Claude Code

```bash
claude plugin marketplace list --json
claude plugin list --json
claude mcp list
```

FrameOS is installed if `frameos@frameos` appears in the plugin list. Also note any MCP server already pointing at `https://frameos.studio/mcp` that is not `plugin:frameos:frameos`; tell the user it duplicates the plugin.

### Codex

```bash
codex plugin marketplace list
codex plugin list --json
codex mcp list --json
```

If `~/.codex/config.toml` already defines `[mcp_servers.frameos]`, that entry hides the plugin's server. Tell the user and ask before changing it.

### Gemini CLI

```bash
gemini extensions list
```

## Step 3. Install

### Claude Code

```bash
claude plugin marketplace add theSatvik/frameos-plugins
claude plugin install frameos@frameos
```

Skip the first command if the `frameos` marketplace is already listed; run `claude plugin marketplace update frameos` instead.

### Codex

```bash
codex plugin marketplace add theSatvik/frameos-plugins
codex plugin add frameos@frameos
```

If the marketplace already exists, run `codex plugin marketplace upgrade frameos` before `codex plugin add`.

### Gemini CLI

```bash
gemini extensions install https://github.com/theSatvik/frameos-plugins
```

### Copilot CLI

```bash
copilot plugin install theSatvik/frameos-plugins:agent-plugin
```

### Devin

```bash
devin plugins install theSatvik/frameos-plugins
```

### Cursor

Ask the user before cloning into their Cursor folder, then:

```bash
git clone https://github.com/theSatvik/frameos-plugins ~/.cursor/plugins/local/frameos
```

Ask the user to restart Cursor or run **Developer: Reload Window**.

### Chat apps

You can't install from here. Give the user the steps for their app and stop:

- Claude.ai, Desktop, Cowork: [install/claude-ai.md](install/claude-ai.md)
- ChatGPT: [install/chatgpt.md](install/chatgpt.md)
- Perplexity: [install/perplexity.md](install/perplexity.md)
- VS Code: [install/vscode-copilot.md](install/vscode-copilot.md)

## Step 4. Sign in

Sign-in opens a browser and waits for the user, so ask the user to run it in their own terminal or session rather than running it yourself:

| Host | What the user runs |
|---|---|
| Claude Code | `/mcp` in a Claude Code session, select `plugin:frameos:frameos`, sign in (`claude mcp login` does not see plugin connections) |
| Codex | `codex mcp login frameos` |
| Gemini CLI | Restart Gemini CLI, then `/mcp auth frameos` |
| Copilot CLI | `/mcp auth frameos` in a session |
| Devin | `devin mcp login frameos` |
| Cursor | The sign-in prompt for FrameOS in **Customize** |

New plugins load in a new session: in Claude Code run `/reload-plugins` (or start a new session); in Codex and Gemini CLI start a new session.

## Step 5. Prove it works

Call the FrameOS `whoami` tool once.

- **Success:** you get a workspace name, a plan and a credit balance. Installation is done.
- **Sign-in error (401):** the user hasn't signed in, or the sign-in expired. Repeat step 4 once.
- **Missing permission (403):** the sign-in didn't include FrameOS access. Ask the user to clear the FrameOS sign-in and sign in again (Claude Code: **Clear authentication** in `/mcp`; Codex: `codex mcp logout frameos` then log in). If it still fails, stop: the FrameOS permission may not be available yet ([status](status.md)).
- **Not found (404) or "unavailable":** the FrameOS connector is not reachable. Stop and report it; don't retry in a loop.
- **The tool doesn't exist yet:** the plugin hasn't loaded in this session. Ask the user to start a new session and try once more.

## Step 6. Report

Tell the user, in plain words:

1. Which app you installed FrameOS into and how (plugin, extension or connector).
2. Whether sign-in worked.
3. The `whoami` result: workspace name and credit balance. Don't show raw IDs.
4. What to try next, for example: "Turn this video into 3 vertical shorts: [your video link]", or "What can FrameOS do?". More prompts: [workflows.md](workflows.md).
5. If anything failed, the exact step, the error in one sentence, and the matching guide in [docs/install/](install/).
