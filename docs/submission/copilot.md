# Submission checklist: GitHub Copilot and VS Code

Two separate listings matter here:

1. **Agent plugin marketplaces.** VS Code and the Copilot CLI discover plugins from `github/copilot-plugins` and `github/awesome-copilot` by default.
2. **The GitHub MCP Registry**, which feeds VS Code's `@mcp` gallery in the Extensions view.

Users can install from this repo without either ([install guide](../install/vscode-copilot.md)).

**Blocked until** the connector is live and the plugin has been tested in VS Code and the Copilot CLI ([status](../status.md)).

## awesome-copilot (external plugin)

Use the repo's **external plugin issue form**. Don't open a pull request that edits `plugins/external.json`.

- [ ] Public GitHub repo: `theSatvik/frameos-plugins`.
- [ ] Source of type `github`, pointing at the Agent Plugins package path `agent-plugin`.
- [ ] An immutable `ref` (a release tag such as `v0.1.0`) and/or the full 40-character commit `sha`.
- [x] Semver `version`, `license` (MIT), `author.name` (FrameOS) and lowercase, hyphenated `keywords`, all in [`.github/plugin/marketplace.json`](../../.github/plugin/marketplace.json) and [`agent-plugin/plugin.json`](../../agent-plugin/plugin.json).
- [ ] After each release, update the pinned `ref`/`sha` through the same process.

`github/copilot-plugins`: the submission process is not yet verified.

## GitHub MCP Registry (VS Code `@mcp` gallery)

Per GitHub staff (May 2026), onboarding a server is a manual curation process:

1. Publish FrameOS to the official MCP Registry first ([mcp-registry.md](mcp-registry.md)).
2. Request onboarding. An October 2025 GitHub blog post named partnerships@github.com as the channel; whether that still applies is not yet verified.
3. After onboarding, new registry versions sync automatically.

## Things reviewers and users will hit

- Copilot cloud agent and Copilot code review don't support remote MCP servers that use OAuth, so FrameOS can't work there. Say so in the listing.
- Copilot code review only uses tools marked `readOnlyHint: true`.
- For Copilot Business and Enterprise, the "MCP servers in Copilot" policy is off by default and an admin must enable it.
- VS Code tries CIMD first (client metadata `https://vscode.dev/oauth/client-metadata.json`, redirects `http://127.0.0.1:33418/` and `https://vscode.dev/redirect`), then DCR. For a pre-registered client, register `http://127.0.0.1:33418` and `https://vscode.dev/redirect`.
- Copilot CLI's own MCP config requires a `tools` list; without a pre-registered client ID it can't be told to request `frameos:mcp`, so the sign-in server must grant it by default.
