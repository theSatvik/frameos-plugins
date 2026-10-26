# Submission checklist: Cursor Marketplace

**Submit through the x.ai form instead:** it lists FrameOS in the Cursor Marketplace and Grok Bot at once, and the field-by-field answers are in [grok-cursor.md](grok-cursor.md). Don't also apply at https://cursor.com/marketplace/publish; it is the same catalog. Every plugin is reviewed by hand before it is listed, every update is reviewed again, and marketplace plugins must be open source in a public Git repo.

Cursor desktop signs in and was tested end to end on 2026-10-08 ([status](../status.md)). Cursor's own client document, used by Cursor web, Cloud Agents and Grok Bot, was pre-registered in Clerk on 2026-10-23; none of those is tested end to end yet (see [grok-cursor.md](grok-cursor.md)).

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

- Cursor signs in with the public client ID in `.cursor-plugin/plugin.json` (`auth.CLIENT_ID` `xdXqonkwYm2XzM1Z`), because FrameOS's sign-in server has Dynamic Client Registration off.
- That client allows `http://localhost:8787/callback` (desktop, working). Whether it also needs `https://www.cursor.com/agents/mcp/oauth/callback` (web and Cloud Agents) and `https://www.cursor.com/bot/mcp/oauth/callback` (Grok Bot), now that Cursor's client document is registered, is still to confirm ([grok-cursor.md](grok-cursor.md)).
- Cursor's own client metadata document, `https://cursor.com/oauth/mcp-client.json`, was pre-registered in Clerk on 2026-10-23 (Cursor web, Cloud Agents and Grok Bot); not tested end to end yet.
- `cursor.directory` reportedly reads the root `.mcp.json`, which has no Cursor client ID; test an install from there after listing.

## Listing extras

- One-click install button for docs and the website. Cursor's own badge images are `https://cursor.com/deeplink/mcp-install-dark.svg` and `https://cursor.com/deeplink/mcp-install-light.svg`; the link is the one in [the install guide](../install/cursor.md#a-one-click-install-link).
- Community directory: https://cursor.directory lists community plugins and MCP servers; see [community.md](community.md#cursor-directory-cursordirectory).

## Team marketplaces (no review needed)

Teams (one team marketplace) and Enterprise (unlimited) can import a repo under **Dashboard > Plugins & MCPs > Team Marketplaces > Add Marketplace > Import from Repo**. Cursor documents `.cursor-plugin/marketplace.json` for multi-plugin repos; this repo has a single plugin at its root and no Cursor marketplace file, so whether **Import from Repo** accepts it is not yet verified.
