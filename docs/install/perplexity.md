# Use FrameOS in Perplexity

Add FrameOS as a custom remote connector, and optionally upload the FrameOS skills to Perplexity Computer.

> **Coming soon: Perplexity can't sign in to FrameOS yet.** The FrameOS connector is live as of 2026-10-05, but its sign-in server only admits pre-registered apps for now, and so far only Claude Code is pre-registered ([status](../status.md)). Nothing here has been tested in Perplexity yet. Steps come from Perplexity's help center.

## Requirements

- **Perplexity Pro, Max or Enterprise.** Custom connectors are not on the Free plan.
- **Enterprise:** members can add custom connectors only if an admin turned on **Allow members to add custom connectors** (off by default). Admins can also add FrameOS for the whole organization.
- Perplexity notes that some custom connectors work only on certain surfaces (web, desktop, mobile). Which surfaces support FrameOS is not yet verified.
- A FrameOS account. Signing in for the first time creates your workspace.

## Add the connector

1. Open **Account settings > Connectors**. (Enterprise admins adding it for everyone: **Enterprise settings > Permissions > Connectors permissions**.)
2. Click **+ Custom connector** in the top-right corner and choose **Remote**.
3. Fill in:

   | Field | Value |
   |---|---|
   | Name | `FrameOS` |
   | MCP Server URL | `https://frameos.studio/mcp` |
   | Description | `Turn long videos into captioned short clips` |
   | Authentication | **OAuth** (leave client ID and secret empty) |
   | Transport | **Streamable HTTP** |
   | Icon | optional; [`assets/icon.png`](../../assets/icon.png) fits the 128 KB limit |

4. Tick the acknowledgement box and click **Add**.
5. Click the FrameOS card on the Connectors screen to sign in.

## Check it works

In a new thread with the FrameOS connector on, ask:

```text
What is my FrameOS credit balance?
```

You should see your workspace name and a credit number.

## Add the skills to Perplexity Computer (optional)

Computer accepts uploaded skills on every plan that includes Computer.

1. Build the ZIPs: `python3 scripts/build_dist.py` writes one per skill to `dist/perplexity/<skill>.zip`, with `SKILL.md` at the root of the ZIP, which is the layout Perplexity expects. Each must be under 10 MB.
2. In Perplexity, go to **Computer > Skills > Create skill > Upload a skill** and upload a ZIP. Repeat for each skill you want; start with frameos-setup and frameos-clip.

## Sign in again or refresh

- Click the FrameOS card on the Connectors screen to sign in again.
- To pick up new FrameOS tools after an update, or after a "missing permission" (403) error, remove the connector and add it again.

## Known limitations

- Perplexity's documentation describes discovering sign-in settings from `/.well-known/oauth-authorization-server` and does not mention the protected-resource metadata FrameOS publishes. Whether Perplexity finds FrameOS's sign-in server on its own is not yet verified.
- Perplexity registers itself automatically (Dynamic Client Registration) when no client ID is entered; FrameOS's sign-in server does not offer that yet ([status](../status.md#prerequisites-before-every-host-can-connect)).
- Perplexity connects from datacenter IP ranges. If a firewall challenges those requests, they show up as 403 errors.
- Renders take 10 to 30 minutes. Start one, then come back and ask "check my FrameOS render".
- Uploading a file from your computer needs an agent that can run commands. In a normal Perplexity thread, share a public link instead (YouTube, Vimeo, Twitch, Kick, a public Google Drive file, or a direct video URL). Whether Perplexity Computer can do the upload is not yet verified.
