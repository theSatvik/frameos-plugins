# Install FrameOS in Codex

You get the eight FrameOS skills plus the FrameOS connector in the Codex CLI.

> **Not yet verified on a live account.** The FrameOS connector is not live as of 2026-10-02 ([status](../status.md)). Installing works today (checked locally with codex-cli 0.152.0, in an isolated `CODEX_HOME`); `codex mcp login frameos` fails until the connector launches.

## Requirements

- Codex CLI with plugin support. The steps below were checked with 0.152.0.
- `git` on your machine.
- A FrameOS account. Signing in for the first time creates your workspace.

## Install

```bash
codex plugin marketplace add theSatvik/frameos-plugins
codex plugin add frameos@frameos
```

To pin a release, add `--ref v0.1.0` to the first command (or write `theSatvik/frameos-plugins@v0.1.0`). You can also browse and toggle plugins inside Codex: run `codex`, then `/plugins`, and press Space on FrameOS.

Plugin skills and tools load in a **new** session.

## Sign in

```bash
codex mcp login frameos
```

This opens your browser. If sign-in succeeds but FrameOS later reports a missing permission, log in again and ask for the scope explicitly:

```bash
codex mcp login frameos --scopes frameos:mcp
```

`--oauth-client-registration cimd` or `dcr` forces one registration method for that login only. The plugin's marketplace entry uses on-use sign-in, so Codex does not ask you to sign in at install time.

## Check it works

```bash
codex mcp list
```

FrameOS should be listed. Then, in a new Codex session, ask:

```text
What is my FrameOS credit balance?
```

You should see your workspace name and a credit number. The skills show up to the model as `frameos:frameos-clip`, `frameos:frameos-setup` and so on; you can mention one directly with `$frameos-clip` (the pattern OpenAI's own plugins use; not yet verified for FrameOS).

## Sign in again or fix the connection

```bash
codex mcp logout frameos
codex mcp login frameos
```

**Name clash:** a server named `frameos` in your own `~/.codex/config.toml` (`[mcp_servers.frameos]`) hides the plugin's server with the same name. Remove or rename your entry if the plugin's connection doesn't appear.

## Ask before posting

Codex can ask for approval before FrameOS tools that change things. To always be asked before a post, add this to `~/.codex/config.toml` (documented Codex settings; not yet tried with FrameOS):

```toml
[plugins."frameos@frameos".mcp_servers.frameos]
default_tools_approval_mode = "writes"

[plugins."frameos@frameos".mcp_servers.frameos.tools.post_clip]
approval_mode = "prompt"
```

The skills already require your explicit confirmation for every post; this adds a second check in Codex itself.

## Update or remove

```bash
codex plugin marketplace upgrade frameos
codex plugin add frameos@frameos
codex plugin remove frameos@frameos
```

Start a new session after updating.

## Connector only, without the skills

```bash
codex mcp add frameos --url https://frameos.studio/mcp
codex mcp login frameos --scopes frameos:mcp
```

Or in `~/.codex/config.toml`:

```toml
[mcp_servers.frameos]
url = "https://frameos.studio/mcp"
scopes = ["frameos:mcp"]
oauth_resource = "https://frameos.studio/mcp"
```

Don't combine this with the plugin: a user-level `frameos` server hides the plugin's one.

## Good to know

- Codex can upload a local video file for you, because it can run commands.
- The plugin's connection sends the `frameos:mcp` scope and an `X-FrameOS-Plugin-Version` header on every request.
- The same plugin format is used by the ChatGPT plugin directory; see [chatgpt.md](chatgpt.md).
