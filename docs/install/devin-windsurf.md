# Install FrameOS in Devin and Windsurf

Windsurf became **Devin Desktop** on 2 June 2026. Its default agent, Devin Local, uses the Devin CLI's plugins and MCP settings, so the steps below cover Devin Desktop and the Devin CLI. The older Cascade agent is covered at the end.

> **Not yet verified.** The FrameOS connector is not live as of 2026-10-02 ([status](../status.md)), and none of these steps has been tested in Devin or Windsurf yet. Steps come from Devin's documentation.

## Requirements

- Devin Desktop or the Devin CLI.
- A FrameOS account. Signing in for the first time creates your workspace.

## Install the plugin

```bash
devin plugins install theSatvik/frameos-plugins
```

Devin looks for `.devin-plugin/plugin.json` first, then `.claude-plugin/plugin.json`, then an Agent Plugins `plugin.json`. This repo has no `.devin-plugin/`, so Devin uses the Claude-format plugin at the repo root (skills plus `.mcp.json`). To use the Agent Plugins package instead:

```bash
devin plugins install theSatvik/frameos-plugins#agent-plugin
```

## Connector only

```bash
devin mcp add -s user frameos https://frameos.studio/mcp
```

Or edit the config yourself: `~/.config/devin/mcp_config.json` (Windows: `%APPDATA%\devin\mcp_config.json`) for all projects, or `.devin/mcp_config.json` for one project:

```json
{
  "mcpServers": {
    "frameos": { "url": "https://frameos.studio/mcp", "transport": "http" }
  }
}
```

## Sign in

```bash
devin mcp login frameos
```

This opens your browser. Devin registers itself with Dynamic Client Registration when no client ID is configured, which FrameOS's sign-in server does not offer yet ([status](../status.md#prerequisites-before-any-host-can-connect)).

## Check it works

Ask Devin:

```text
What is my FrameOS credit balance?
```

You should see your workspace name and a credit number.

## Sign in again

Run `devin mcp login frameos` again.

## Legacy Cascade agent

Windsurf's Cascade agent was kept available after the rename, at least through July 2026; whether it is still available is not yet verified. It reads `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "frameos": { "serverUrl": "https://frameos.studio/mcp" }
  }
}
```

Cascade has no MCP marketplace or one-click install, and allows 100 MCP tools in total across servers (FrameOS has 27).

## Known limitations

- FrameOS is not listed in Devin's plugin marketplace yet.
- Devin can upload a local video file for you, because it can run commands.
