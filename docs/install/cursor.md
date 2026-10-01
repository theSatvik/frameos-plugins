# Install FrameOS in Cursor

| Route | You get |
|---|---|
| [A. One-click install link](#a-one-click-install-link) | The FrameOS connector |
| [B. Local plugin](#b-local-plugin) | The eight skills and the connector |
| [C. Cursor Marketplace](#c-cursor-marketplace) | The eight skills and the connector, once FrameOS is listed |
| [D. Edit mcp.json by hand](#d-edit-mcpjson-by-hand) | The FrameOS connector |

> **Not yet verified on a live account.** The FrameOS connector is not live as of 2026-10-02 ([status](../status.md)), and none of these routes has been tested in Cursor yet. Steps come from Cursor's documentation.

## Requirements

- Cursor. The plugin manifest asks for Cursor 3.13.0 or later.
- A FrameOS account. Signing in for the first time creates your workspace.

## A. One-click install link

Open this link in your browser (paste it into the address bar if clicking it does nothing):

```text
cursor://anysphere.cursor-deeplink/mcp/install?name=frameos&config=eyJ0eXBlIjoiaHR0cCIsInVybCI6Imh0dHBzOi8vZnJhbWVvcy5zdHVkaW8vbWNwIn0=
```

The `config` part is base64 for `{"type":"http","url":"https://frameos.studio/mcp"}`. Cursor asks you to confirm the install, then follow the sign-in prompt.

## B. Local plugin

1. Clone the repo straight into Cursor's local plugin folder (a symlink to a clone elsewhere is skipped):

   ```bash
   git clone https://github.com/theSatvik/frameos-plugins ~/.cursor/plugins/local/frameos
   ```

2. Restart Cursor, or run **Developer: Reload Window**.
3. Open **Customize** and check that the FrameOS skills and MCP server are listed.

Cursor reads `.cursor-plugin/plugin.json` at the repo root, which includes the connector. On Teams and Enterprise, local plugins need **Allow Local Plugin Imports** (under **Dashboard > Settings > Security & Identity > Marketplace and Plugins**), which is off by default on Enterprise. If a marketplace copy of FrameOS is installed, it takes precedence over the local one. To update, run `git -C ~/.cursor/plugins/local/frameos pull` and reload.

## C. Cursor Marketplace

FrameOS is not in the Cursor Marketplace yet. Once it is, open **Customize**, search for FrameOS and select **Install**.

## D. Edit mcp.json by hand

Add this to `~/.cursor/mcp.json` (all projects) or `.cursor/mcp.json` (one project), then restart Cursor:

```json
{
  "mcpServers": {
    "frameos": { "url": "https://frameos.studio/mcp" }
  }
}
```

## Check it works

In a new Agent chat, ask:

```text
What is my FrameOS credit balance?
```

You should see your workspace name and a credit number.

## Sign in again or fix the connection

- Open **Customize**, find the FrameOS MCP server, and use its toggle or sign-in prompt. (The exact re-authentication controls are not yet verified.)
- To see what went wrong: open the Output panel (Cmd+Shift+U), choose **MCP Logs**, and look for connection or authentication errors.
- A "missing permission" (403) error: remove FrameOS and add it again.

## Known limitations

- Cursor asks FrameOS's sign-in server for the permissions that server advertises, unless a pre-registered client ID is configured. Until the FrameOS permission is advertised and on by default, sign-in can succeed but FrameOS will answer with a missing-permission error ([status](../status.md#prerequisites-before-any-host-can-connect)).
- Cursor registers itself automatically (Dynamic Client Registration), which FrameOS's sign-in server does not offer yet.
- Cursor can upload a local video file for you, because its agent can run commands.
