# Install FrameOS in Gemini CLI

The repo is a Gemini CLI extension: you get the eight skills, the FrameOS connector, a short always-on context file and eight `/frameos:*` commands.

> **Gemini CLI can sign in to FrameOS** through the public client ID in `gemini-extension.json`, but it is not tested end to end yet ([status](../status.md)). Gemini CLI was not installed on the machine these packages were built on, so this extension has not been loaded in Gemini CLI yet. Steps come from Gemini CLI's documentation and source.

## Requirements

- Gemini CLI with extension support, and `git`.
- A local browser for sign-in. Sign-in does not work in a headless or SSH session without browser forwarding.
- A FrameOS account. Signing in for the first time creates your workspace.

## Install

Run this in your terminal, not inside a Gemini CLI session (extension commands don't work in interactive mode):

```bash
gemini extensions install https://github.com/theSatvik/frameos-plugins
```

Useful options: `--ref v0.1.0` to pin a release, `--auto-update` to follow new versions, `--consent` to skip the confirmation prompt. Restart Gemini CLI afterwards.

## Sign in

Inside Gemini CLI:

```text
/mcp auth frameos
```

The extension already asks for the FrameOS permission (`frameos:mcp`). Gemini CLI keeps its tokens in `~/.gemini/mcp-oauth-tokens.json`.

## Check it works

```text
/extensions list
```

FrameOS should be listed. Then ask:

```text
What is my FrameOS credit balance?
```

You should see your workspace name and a credit number. Or run `/frameos:setup`.

## Commands

| Command | What it does |
|---|---|
| `/frameos:setup` | Check the connection and your credits, or fix sign-in |
| `/frameos:clip <link or file>` | Turn a long video into short clips |
| `/frameos:captions <what to change>` | Restyle a clip's captions and export it |
| `/frameos:moments <topic>` | Search a processed video's transcript |
| `/frameos:thumbnails <clip>` | Make thumbnails (asks before spending credits) |
| `/frameos:publish <clip and platform>` | Draft copy, or post after you confirm |
| `/frameos:library <what to find>` | Past projects, clips, collections, credit usage |
| `/frameos:repurpose <link>` | Plan and run a content pack |

Anything you type after the command is passed along, for example `/frameos:clip https://youtube.com/watch?v=... 5 clips for TikTok`.

## Sign in again or fix the connection

- Tokens expired: run `/mcp auth frameos` again.
- A "missing permission" (403) error: run `/mcp auth frameos` again after the FrameOS permission is available ([status](../status.md#prerequisites-before-every-host-can-connect)).

## Update or remove

```bash
gemini extensions update frameos
gemini extensions uninstall frameos
```

## Connector only, without the extension

```bash
gemini mcp add --transport http frameos https://frameos.studio/mcp
```

This writes to `.gemini/settings.json` (add `-s user` for `~/.gemini/settings.json`). Then edit the `frameos` entry so it signs in with FrameOS's public Gemini CLI client and asks for the FrameOS permission, as the extension does:

```json
{
  "mcpServers": {
    "frameos": {
      "httpUrl": "https://frameos.studio/mcp",
      "oauth": {
        "enabled": true,
        "clientId": "0SMM8YEjdF4YxCa4",
        "redirectUri": "http://localhost:7777/oauth/callback",
        "scopes": ["frameos:mcp", "offline_access"]
      }
    }
  }
}
```

## Known limitations

- Gemini CLI does not support Client ID Metadata Documents, and FrameOS's sign-in server has Dynamic Client Registration off, so Gemini CLI signs in only with the public client ID above (in `gemini-extension.json`, or added by hand as shown). A `frameos` entry without it can't sign in ([status](../status.md#prerequisites-before-every-host-can-connect)).
- Gemini CLI checks the sign-in server's issuer strictly; this has not been tested against FrameOS's sign-in server yet.
- Gemini CLI can upload a local video file for you, because it can run commands.
