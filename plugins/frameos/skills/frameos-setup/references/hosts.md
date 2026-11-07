# Connecting FrameOS, app by app

Reference for the frameos-setup skill. Every app connects to the same server:

- URL: `https://frameos.studio/mcp`
- Transport: Streamable HTTP (some apps call it "HTTP" or "streamable-http")
- Sign-in: OAuth in the user's browser, requesting the `frameos:mcp` access scope
- Server name used below: `frameos` (in Claude Code the plugin's copy is `plugin:frameos:frameos`)

The proof in every app is the same: ask "What is my FrameOS credit balance?" and the agent should answer with the workspace name and credits from `whoami`. Menu names come from each app's documentation and can move between versions; if a label differs, look in the app's MCP, Connectors or Plugins settings.

This copy covers Claude Code, claude.ai, Claude Desktop and Cowork. Steps for every other app are at https://frameos.studio/plugin.

## Claude Code (terminal and the Desktop Code tab)

- Install the plugin (skills plus server):
  `claude plugin marketplace add theSatvik/frameos-plugins`
  `claude plugin install frameos@frameos`
  Inside a session the same steps are `/plugin marketplace add theSatvik/frameos-plugins` and `/plugin install frameos@frameos`.
- Server only, without the plugin: `claude mcp add --transport http frameos https://frameos.studio/mcp` (the server name is then `frameos`).
- Is it connected: `claude mcp list` shows each server's state; "Failed to connect" means the service could not be reached. In a session, `/mcp` lists the servers.
- Sign in or re-authenticate: `/mcp`, select `plugin:frameos:frameos`, choose to authenticate. `claude mcp login` does not see plugin connections, so sign in from `/mcp`.
- Sign out: `claude mcp logout plugin:frameos:frameos`. For a 403 permission error, sign out this way and then sign in again.
- Notes: non-interactive runs (`claude -p`, the SDK) cannot sign in, so sign in once interactively first. If FrameOS was also added as a claude.ai connector with the same URL, Claude Code uses its own server and hides the connector. Start a new session if the tools do not appear after installing.

## Claude.ai web, Claude Desktop, Cowork

- Option A, plugin: Customize > Plugins > Add > Add marketplace, enter `theSatvik/frameos-plugins`, install FrameOS, then open the plugin's Connectors tab and connect the FrameOS server.
- Option B, connector only: Customize > Connectors > Add custom connector, URL `https://frameos.studio/mcp`, sign in when asked. The Free plan allows one custom connector.
- Team and Enterprise: an Owner adds it under Organization settings > Connectors > Add > Custom > Web; then each member clicks Connect.
- Is it connected: the connector shows as connected in Customize > Connectors; then ask for the credit balance.
- Re-authenticate: Customize > Connectors > FrameOS > Connect. Sign-in settings cannot be edited after adding: for a 403 permission error, remove the connector and add it again.
- Notes: chat apps usually cannot send local video files to FrameOS; use public links, or upload in the web app at https://frameos.studio/dashboard. Uploading a skill on its own (Customize > Skills) needs code execution turned on.

## Any other MCP client

- Add a remote server named `frameos` with URL `https://frameos.studio/mcp`, transport Streamable HTTP, OAuth sign-in. If the client lets you set scopes, use `frameos:mcp`.
- Prove it with the credit-balance question.
