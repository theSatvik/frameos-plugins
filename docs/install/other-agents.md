# Use FrameOS with other agents

Any agent that supports remote MCP servers with OAuth sign-in can use the FrameOS connector, and any agent that reads Agent Skills (`SKILL.md` folders) can use the FrameOS skills.

> **Coming soon for other agents.** The FrameOS connector is live as of 2026-10-05, but its sign-in server only admits pre-registered apps for now, and so far only Claude Code is pre-registered ([status](../status.md)). FrameOS has not been tested with the agents on this page. Use the host-specific guides where one exists: [Claude Code](claude-code.md), [Claude.ai](claude-ai.md), [Codex](codex.md), [ChatGPT](chatgpt.md), [Cursor](cursor.md), [Gemini CLI](gemini-cli.md), [VS Code and Copilot](vscode-copilot.md), [Perplexity](perplexity.md), [Devin and Windsurf](devin-windsurf.md).

## 1. Add the skills with `npx skills`

```bash
npx skills add theSatvik/frameos-plugins
```

The `skills` CLI finds the eight skills in this repo and installs them where your agent looks for skills. Useful options: `-g` installs for your user instead of the current project, `-a <agent>` targets one agent, `-s <skill>` picks one skill, `--list` shows what's available, `-y` skips prompts.

You can also copy the folders from [`skills/`](../../skills/) yourself. `.agents/skills/` in a project is read by Cursor, Gemini CLI, VS Code and Copilot, Devin Desktop and Codex.

The skills only describe how to use FrameOS. Your agent also needs the connector (step 2).

## 2. Add the connector

| Setting | Value |
|---|---|
| URL | `https://frameos.studio/mcp` |
| Transport | Streamable HTTP |
| Authentication | OAuth 2.1 with PKCE, discovered from the server (no API key, no client secret) |
| Permission (scope) | `frameos:mcp` |

Most MCP clients take a JSON entry like this one. Field names vary by client: some want `"type": "http"`, some `"streamable-http"`, some `httpUrl` or `serverUrl`.

```json
{
  "mcpServers": {
    "frameos": { "type": "http", "url": "https://frameos.studio/mcp" }
  }
}
```

If your client lets you set OAuth scopes, set `frameos:mcp`.

## 3. Check it works

Ask your agent:

```text
What is my FrameOS credit balance?
```

You should see your workspace name and a credit number.

## Agents that can't sign in with OAuth

The FrameOS connector only accepts OAuth sign-in. There are no API keys, so agents that only support fixed tokens or headers can't connect.

## Good to know

- Agent Skills is an open format. The agentskills.io client list includes OpenCode, Goose, Amp, Kiro, Roo Code, TRAE and Junie among others; FrameOS has not been tested with them, so there are no specific steps here.
- Agents that can run commands can upload a local video file to FrameOS. Chat-only agents need a public link (YouTube, Vimeo, Twitch, Kick, a public Google Drive file, or a direct video URL).
- No FrameOS listing exists yet in the MCP Registry or other MCP directories.
