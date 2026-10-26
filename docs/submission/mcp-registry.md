# Submission checklist: official MCP Registry

The MCP Registry (https://registry.modelcontextprotocol.io, still marked preview) lists the hosted **connector**, not this plugin. Other directories read from it: the GitHub MCP Registry and VS Code's `@mcp` gallery start from it ([copilot.md](copilot.md)), and Glama, PulseMCP and several smaller sites import from it ([community.md](community.md)). Searching the registry for `studio.frameos` returned nothing on 2026-10-23.

Who does it: the owner. A publish is public at once and a published version can never be changed, so it needs your go-ahead every time.

## What `server.json` does

[`server.json`](../../server.json) at the repo root is the registry entry, exactly as it will be published:

| Field | Value | Why |
|---|---|---|
| `name` | `studio.frameos/frameos` | The namespace. `studio.frameos` is `frameos.studio` reversed, so only whoever controls that domain can publish under it. It can't be changed later. |
| `title`, `description` | `FrameOS`; 84 characters | What directories show (description limit 100). |
| `version` | `1.0.0` | The listing's own version, separate from the plugin's `VERSION`. Raise it by hand on every publish. |
| `websiteUrl` | https://frameos.studio/plugin | Setup and docs page. |
| `repository` | `theSatvik/frameos-plugins`, GitHub ID `1400829488` | The public repo with the install guides. |
| `icons` | https://frameos.studio/frameos/frameos-favicon.png (256 x 256 PNG) | Shown next to the listing. |
| `remotes` | one `streamable-http` remote, `https://frameos.studio/mcp`, no headers | The connector; people sign in with OAuth, so no keys or headers. |

It validates against `https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json` (checked 2026-10-23), and `python3 scripts/validate.py` checks the FrameOS-specific fields.

## Before the first publish

- [ ] `https://frameos.studio/.well-known/mcp-registry-auth` serves this one line as plain text (it returned 404 on 2026-10-23; the frontend change adds the route):

  ```text
  v=MCPv1; k=ed25519; p=75t4Zu1Y3jkQ0kt15/dA6WjGKX7UH3cb3rwNju+l0Z8=
  ```

  That is the public half of the key at `~/.config/frameos/mcp-registry-ed25519.pem`. The private key never goes in a repo, a chat or a form.
- [ ] `version` in `server.json` is one the registry hasn't published yet (`1.0.0` for the first publish).

## Publish: the exact commands

Run from the repo root on macOS. macOS's own LibreSSL can't read Ed25519 keys, so OpenSSL 3 is called by its full path. These are the same steps as [RELEASING.md step 7](../../RELEASING.md#7-publish-to-the-mcp-registry).

```bash
# 1. Tools
brew install mcp-publisher openssl@3
OPENSSL=/opt/homebrew/opt/openssl@3/bin/openssl
KEY=~/.config/frameos/mcp-registry-ed25519.pem

# 2. Check the listing file
SCHEMA="$(mktemp)"
curl -sS -o "$SCHEMA" https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json
uv run --no-project --with jsonschema python -c "import json, sys, jsonschema; jsonschema.validate(json.load(open('server.json')), json.load(open(sys.argv[1]))); print('server.json is valid')" "$SCHEMA"
python3 scripts/test.py

# 3. The key on your machine must match what the website serves (the two lines must be identical)
echo "v=MCPv1; k=ed25519; p=$("$OPENSSL" pkey -in "$KEY" -pubout -outform DER | tail -c 32 | base64)"
curl -s https://frameos.studio/.well-known/mcp-registry-auth

# 4. Sign in with the domain and publish (reads server.json in this folder)
mcp-publisher login http --domain frameos.studio \
  --private-key "$("$OPENSSL" pkey -in "$KEY" -noout -text | grep -A3 'priv:' | tail -n +2 | tr -d ' :\n')"
mcp-publisher publish

# 5. Confirm: expect one server, studio.frameos/frameos, at the new version
curl -s "https://registry.modelcontextprotocol.io/v0.1/servers?search=studio.frameos" | python3 -m json.tool
```

The sign-in signs a timestamp that must be within about 15 seconds of the registry's clock; if it is refused, sync your clock and run step 4 again.

## Later publishes

Publish again only when the listing itself changes (description, icon, website or repository): raise `version` (`1.0.1` and so on), then repeat steps 2 to 5. A plugin release on its own needs no publish, and tool changes on the server show up without one.

## Other namespace option (not used)

`io.github.theSatvik/frameos` would prove ownership by GitHub sign-in instead of the domain key. The domain namespace matches the brand, and `server.json` already uses it, so keep it.
