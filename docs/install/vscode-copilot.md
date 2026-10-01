# Install FrameOS in VS Code and GitHub Copilot

FrameOS ships an [Agent Plugins](https://agent-plugins.org) package in [`agent-plugin/`](../../agent-plugin/) (the skills plus the connector). GitHub Copilot in VS Code, the Copilot CLI and the Copilot app all read that format.

| Route | You get |
|---|---|
| [A. Copilot CLI plugin](#a-copilot-cli-plugin) | Skills and connector, in the CLI and in VS Code |
| [B. VS Code plugin](#b-vs-code-plugin) | Skills and connector |
| [C. Connector only](#c-connector-only) | The FrameOS tools |

> **Not yet verified on a live account.** The FrameOS connector is not live as of 2026-10-02 ([status](../status.md)), and none of these routes has been tested in VS Code or Copilot yet. Steps come from the VS Code and GitHub Copilot documentation.

## Requirements

- VS Code with GitHub Copilot, or the Copilot CLI.
- For plugins in VS Code: the `chat.plugins.enabled` setting turned on.
- **Copilot Business or Enterprise:** the "MCP servers in Copilot" policy is off by default; an organization admin has to turn it on. Copilot Free, Pro, Pro+ and Max are not governed by it.
- A FrameOS account. Signing in for the first time creates your workspace.

## A. Copilot CLI plugin

```bash
copilot plugin install theSatvik/frameos-plugins:agent-plugin
```

Or through the repo's Copilot marketplace (`.github/plugin/marketplace.json`, named `frameos`):

```bash
copilot plugin marketplace add theSatvik/frameos-plugins
copilot plugin install frameos@frameos
```

Not yet verified: that the Copilot CLI reads `.github/plugin/marketplace.json` (which points at `agent-plugin/`) rather than `.claude-plugin/marketplace.json` (which points at the repo root); the first command above avoids the question.

VS Code picks up plugins installed by the Copilot CLI automatically: they appear in the **Agent Plugins - Installed** view.

## B. VS Code plugin

**From source:** run **Chat: Install Plugin From Source** from the Command Palette and enter `https://github.com/theSatvik/frameos-plugins`. VS Code clones the repo and installs the plugin at its root. The root holds the Claude-format manifest (`.claude-plugin/plugin.json` plus `.mcp.json`), which VS Code also supports. Not yet verified: that VS Code picks that manifest here, and how it treats the Codex and Claude specific keys in `.mcp.json`. If it misbehaves, use the local Agent Plugins package instead:

```bash
git clone https://github.com/theSatvik/frameos-plugins
```

```json
// settings.json
"chat.pluginLocations": {
  "/path/to/frameos-plugins/agent-plugin": true
}
```

**From a marketplace:** add the repo as a marketplace, then search `@agentPlugins` in the Extensions view and install FrameOS. Not yet verified: which of the repo's two marketplace files VS Code reads.

```json
// settings.json
"chat.plugins.marketplaces": ["theSatvik/frameos-plugins"]
```

## C. Connector only

One-click (VS Code handles the `vscode:` link; paste it into your browser if clicking does nothing):

```text
vscode:mcp/install?%7B%22name%22%3A%22frameos%22%2C%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A%2F%2Fframeos.studio%2Fmcp%22%7D
```

For VS Code Insiders, use the same link starting with `vscode-insiders:`. From a terminal:

```bash
code --add-mcp '{"name":"frameos","type":"http","url":"https://frameos.studio/mcp"}'
```

Or add it to `.vscode/mcp.json` in a workspace:

```json
{
  "servers": {
    "frameos": { "type": "http", "url": "https://frameos.studio/mcp" }
  }
}
```

**Copilot CLI only:**

```bash
copilot mcp add --transport http frameos https://frameos.studio/mcp
```

If you edit `~/.copilot/mcp-config.json` yourself, note that the Copilot CLI requires a `tools` list:

```json
{
  "mcpServers": {
    "frameos": { "type": "http", "url": "https://frameos.studio/mcp", "tools": ["*"] }
  }
}
```

## Sign in

VS Code prompts you to sign in when it connects to FrameOS. In the Copilot CLI, run `/mcp auth frameos` in a session; it opens your browser.

## Check it works

In Copilot Chat (agent mode) or a Copilot CLI session, ask:

```text
What is my FrameOS credit balance?
```

You should see your workspace name and a credit number.

## Sign in again or fix the connection

- **VS Code:** run **MCP: List Servers**, select frameos, and choose **Restart** or **Show Output** to see errors. **MCP: Reset Cached Tools** clears an old tool list. (The exact controls for signing out and back in are not yet verified.)
- **Copilot CLI:** when the server shows `needs-auth`, run `/mcp auth frameos` to sign in again or switch accounts.

## Known limitations

- **Copilot cloud agent and Copilot code review do not support remote MCP servers that use OAuth**, so FrameOS works in VS Code, the Copilot CLI and the Copilot app, but not there.
- VS Code tries Client ID Metadata Documents first, then Dynamic Client Registration. FrameOS's sign-in server offers neither yet ([status](../status.md#prerequisites-before-any-host-can-connect)).
- Copilot can upload a local video file for you only where its agent can run commands.
