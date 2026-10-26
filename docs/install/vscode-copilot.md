# Install FrameOS in VS Code and GitHub Copilot

FrameOS ships an [Agent Plugins](https://agent-plugins.org) package in [`agent-plugin/`](../../agent-plugin/) (the skills plus the connector). GitHub Copilot in VS Code, the Copilot CLI and the Copilot app all read that format.

| Route | You get |
|---|---|
| [A. Copilot CLI plugin](#a-copilot-cli-plugin) | Skills and connector, in the CLI and in VS Code |
| [B. VS Code plugin](#b-vs-code-plugin) | Skills and connector |
| [C. Connector only, VS Code](#c-connector-only-vs-code) | The FrameOS tools |
| [D. Connector only, Copilot CLI](#d-connector-only-copilot-cli) | The FrameOS tools |

> **Tested in VS Code on 2026-10-09** with route C: the connector in the user `mcp.json`, sign-in, then a credit question in Copilot Chat ([status](../status.md)). Routes A and B (the plugins) are not tested yet. The Copilot CLI signs in with its own published client document, which FrameOS registered on 2026-10-23 (route D); it is not tested end to end yet.

## Requirements

- VS Code with GitHub Copilot, or the Copilot CLI.
- For the Copilot CLI: version 1.0.83 or newer, the first that signs in with a published client document. Older versions can't sign in to FrameOS.
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

Not yet verified: signing in through the plugin's own connection. It should sign in the same way as route D, since there is no client ID to set. If it doesn't, add the connector from [route D](#d-connector-only-copilot-cli) as well and sign in through it. Also not yet verified: how the Copilot CLI lists the plugin's server next to yours.

## B. VS Code plugin

**From source:** run **Chat: Install Plugin From Source** from the Command Palette and enter `https://github.com/theSatvik/frameos-plugins`. VS Code clones the repo and installs the plugin at its root. The root holds the Claude-format manifest (`.claude-plugin/plugin.json` plus `.mcp.json`), which VS Code also supports. Not yet verified: that VS Code picks that manifest here, and how it treats the Claude-format `.mcp.json`. If it misbehaves, use the local Agent Plugins package instead:

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

## C. Connector only, VS Code

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

## D. Connector only, Copilot CLI

The Copilot CLI signs in to FrameOS with its own published client document (a Client ID Metadata Document), which FrameOS has registered. There is no client ID, client secret or port to set: add the server address, then sign in.

1. Install the Copilot CLI (1.0.83 or newer) and sign in to GitHub:

   ```bash
   npm install -g @github/copilot
   ```

2. Add FrameOS:

   ```bash
   copilot mcp add --transport http frameos https://frameos.studio/mcp
   ```

   Or add it to `~/.copilot/mcp-config.json` (or `$COPILOT_HOME/mcp-config.json` if you set it) yourself, next to any servers already there:

   ```json
   {
     "mcpServers": {
       "frameos": {
         "type": "http",
         "url": "https://frameos.studio/mcp"
       }
     }
   }
   ```

   A `tools` list is optional; without one the Copilot CLI uses all FrameOS tools.

3. Start `copilot` and sign in (below).

## Sign in

VS Code asks whether the frameos server may authenticate to `clerk.frameos.studio`. Click **Allow**, then sign in to FrameOS and approve access in your browser.

If no prompt appears and the server's output ends with `Found 0 sessions for scopes: frameos:mcp` and `Connection state: Stopped`, start it by hand: in the Extensions view, under **MCP Servers - Installed**, open the gear menu next to frameos and choose **Start Server**. The prompt then appears.

In the Copilot CLI, run `/mcp auth frameos` in a session; it opens your browser. Sign in to FrameOS and approve access.

## Check it works

In Copilot Chat (agent mode) or a Copilot CLI session, ask:

```text
What is my FrameOS credit balance?
```

You should see your workspace name and a credit number.

## Sign in again or fix the connection

- **VS Code:** run **MCP: List Servers**, select frameos, and choose **Restart** or **Show Output** to see errors. **MCP: Reset Cached Tools** clears an old tool list. (The exact controls for signing out and back in are not yet verified.)
- **Copilot CLI:** when the server shows `needs-auth`, run `/mcp auth frameos` to sign in again or switch accounts. If sign-in fails with a registration error, check that the Copilot CLI is 1.0.83 or newer (`copilot version`; `copilot update` updates it), then try again.

## Known limitations

- **Copilot cloud agent and Copilot code review do not support remote MCP servers that use OAuth**, so FrameOS works in VS Code and the Copilot CLI, but not there. The Copilot app is not verified.
- VS Code tries Client ID Metadata Documents first, then Dynamic Client Registration. FrameOS's sign-in server accepts Client ID Metadata Documents only from pre-registered apps; VS Code's and VS Code Insiders' are registered, and Dynamic Client Registration is off ([status](../status.md#prerequisites-before-every-host-can-connect)). The Copilot CLI's own client document is registered too (route D).
- A chat that VS Code hands to the Copilot CLI agent does not see servers from VS Code's `mcp.json`, so it reports the FrameOS tools as unavailable. VS Code's documentation says those sessions can only use local servers that need no sign-in. Use a regular Copilot Chat in agent mode.
- Not yet verified: whether the Copilot CLI stays signed in after its first sign-in expires. If the server shows `needs-auth`, run `/mcp auth frameos` again.
- Copilot can upload a local video file for you only where its agent can run commands.
