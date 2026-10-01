# Submission checklist: official MCP Registry

The MCP Registry (https://registry.modelcontextprotocol.io, still marked preview) lists the **connector**, not this plugin. Publishing there, and owning its `server.json`, belongs to the FrameOS MCP connector work, so this repo deliberately ships no `server.json`. This page records what the listing needs so the two stay consistent. Searching the registry for "frameos" returned no results on 2026-10-02.

**Blocked until** the connector is live ([status](../status.md)).

## Choose the namespace

The namespace proves ownership and can't be changed later:

| Namespace | How you prove it | Notes |
|---|---|---|
| `studio.frameos/frameos` | Domain: a TXT record on the apex of `frameos.studio`, or a file served at `https://frameos.studio/.well-known/mcp-registry-auth` | Matches the brand. The HTTP option needs a frontend route. |
| `io.github.theSatvik/frameos` | GitHub sign-in as `theSatvik` | Simplest. The exact letter case the registry expects for `theSatvik` is not yet verified. |

Both the DNS record and the HTTP file contain `v=MCPv1; k=ed25519; p=<base64 public key>`.

## `server.json`

Validate against the published schema `https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`. Required: `name`, `description` (100 characters or fewer) and `version`. A starting point:

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "studio.frameos/frameos",
  "title": "FrameOS",
  "description": "Turn long videos into captioned short clips: submit, track, caption, export and post.",
  "version": "0.1.0",
  "websiteUrl": "https://frameos.studio",
  "remotes": [
    { "type": "streamable-http", "url": "https://frameos.studio/mcp" }
  ]
}
```

- `version` is the connector's version (its `initialize` response reports `0.1.0` today), not this plugin's.
- Add `icons` only with a public HTTPS image URL; add `repository` only if the connector's source is public.
- Re-publishing changed metadata needs a new version; the registry docs suggest a semver pre-release for metadata-only updates.

## Publish

```bash
brew install mcp-publisher
mcp-publisher login github                 # for io.github.theSatvik/*
# or, for studio.frameos/*, with an Ed25519 key (macOS LibreSSL can't make one; use OpenSSL 3):
#   brew install openssl@3
#   mcp-publisher login http --domain frameos.studio --private-key "<hex private key>"   # .well-known file
#   mcp-publisher login dns  --domain frameos.studio --private-key "<hex private key>"   # TXT record
mcp-publisher validate
mcp-publisher publish
curl "https://registry.modelcontextprotocol.io/v0/servers?search=frameos"
```

Keep the private key out of every repo and out of chat logs.

## Related directories

- **GitHub MCP Registry / VS Code `@mcp`:** onboarding starts from the official registry ([copilot.md](copilot.md)).
- **Smithery (optional):** publish by URL at https://smithery.ai/new. Smithery registers clients through CIMD, so Clerk's CIMD must be on. Its scanner needs a 401 (not 403) for unauthenticated requests and is often blocked by firewalls; if it can't get past sign-in it reads a static card at `/.well-known/mcp/server-card.json`.
