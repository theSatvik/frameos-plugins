# Submission checklist: Cursor Marketplace

Apply at https://cursor.com/marketplace/publish (sign in, then submit a plugin publisher application). Every plugin is reviewed by hand before it is listed, every update is reviewed again, and marketplace plugins must be open source in a public Git repo.

**Blocked until** the connector is live and sign-in works in Cursor ([status](../status.md)), and the plugin has been tested locally (last item).

## Checklist

Cursor's publishing checklist, and where this repo stands:

- [x] Valid manifest: [`.cursor-plugin/plugin.json`](../../.cursor-plugin/plugin.json). Cursor's schema allows no extra keys; the validator checks the key set.
- [x] Unique kebab-case `name`: `frameos`.
- [x] Valid frontmatter in every component (the skills; the validator checks them).
- [x] Logo committed and referenced by a relative path: `assets/icon.png`.
- [x] README: [README.md](../../README.md).
- [x] Every `${VAR}` used in an MCP config is declared in `variables`: none are used.
- [x] No `..` or absolute paths.
- [x] `minClientVersions.cursor` set to `3.13.0`, as Cursor's partner plugins do.
- [ ] Tested locally: clone into `~/.cursor/plugins/local/frameos`, reload, confirm the skills and the MCP server appear in **Customize**, sign in, and ask "What is my FrameOS credit balance?" ([install guide](../install/cursor.md)).

## Sign-in requirements in Cursor

- Cursor uses Dynamic Client Registration, or a static client ID in `auth.CLIENT_ID` (CIMD support is not documented). FrameOS's sign-in server needs DCR on.
- Without a static client ID, Cursor requests the scopes listed in the sign-in server's `/.well-known/oauth-authorization-server`, so `frameos:mcp` must be advertised there and granted by default.
- If FrameOS ever moves to a pre-registered client, register both Cursor redirect URIs: `https://www.cursor.com/agents/mcp/oauth/callback` (web and Cloud Agents) and `http://localhost:8787/callback` (desktop).

## Listing extras

- One-click install button for docs and the website. Cursor's own badge images are `https://cursor.com/deeplink/mcp-install-dark.svg` and `https://cursor.com/deeplink/mcp-install-light.svg`; the link is the one in [the install guide](../install/cursor.md#a-one-click-install-link).
- Community directory: https://cursor.directory lists community plugins and MCP servers. Its submission process is not yet verified.

## Team marketplaces (no review needed)

Teams (one team marketplace) and Enterprise (unlimited) can import a repo under **Dashboard > Plugins & MCPs > Team Marketplaces > Add Marketplace > Import from Repo**. Cursor documents `.cursor-plugin/marketplace.json` for multi-plugin repos; this repo has a single plugin at its root and no Cursor marketplace file, so whether **Import from Repo** accepts it is not yet verified.
