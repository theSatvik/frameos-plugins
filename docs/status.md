# Status

Last checked: **2026-10-05**. Package version: see [`VERSION`](../VERSION).

## In one paragraph

The hosted FrameOS connector, `https://frameos.studio/mcp`, is **live**, and **Claude Code is the first app that can sign in**. On 2026-10-05 a real end-to-end test passed in Claude Code with the connector added directly: sign-in, consent, then `whoami` and `list_projects` returned the account's real data. Every other app (claude.ai and Claude Desktop, ChatGPT, Codex, Cursor, Gemini CLI, VS Code and Copilot, Perplexity) is **coming soon**: FrameOS's sign-in server only admits pre-registered apps for now, and so far only Claude Code is pre-registered. The packages in this repo load locally in Claude Code and Codex. Signing in through the Claude Code plugin's own connection has not been tested yet. Every install guide marks what is unverified, and the [mock server](../dev/README.md) still lets you try every workflow without spending credits.

## The hosted connector

Probed with `curl` on 2026-10-05:

| URL | Result |
|---|---|
| `https://frameos.studio/mcp` | 401 without a token. `WWW-Authenticate` carries `resource_metadata="https://frameos.studio/.well-known/oauth-protected-resource/mcp"` and `scope="frameos:mcp"` |
| `https://frameos.studio/.well-known/oauth-protected-resource/mcp` | 200. `resource` is `https://frameos.studio/mcp`; `authorization_servers` is `https://clerk.frameos.studio`, with no trailing slash |
| `https://clerk.frameos.studio/.well-known/oauth-authorization-server` | 200, see below |

The sign-in server (Clerk OAuth) is set up for agent sign-in, with one limit:

- Its `scopes_supported` lists `frameos:mcp`, the scope the connector requires on every token.
- It advertises `client_id_metadata_document_supported: true`, so Client ID Metadata Documents (CIMD) are on. Admission is set to **"Pre-registered clients only"**: an app can sign in only after its CIMD client has been registered with FrameOS. So far only Claude Code is.
- It has no `registration_endpoint`, so Dynamic Client Registration (DCR) is off.
- It advertises S256 PKCE, `none` among its token endpoint auth methods, and `authorization_response_iss_parameter_supported: true`, which several clients need.

### Fixed since the 2026-10-02 check

- The connector and its well-known route are served. Both returned 404 on 2026-10-02.
- Clerk advertises `frameos:mcp` and publishes CIMD.
- The 401 `WWW-Authenticate` header now carries `scope="frameos:mcp"`.
- The connector's sign-in server entry no longer has a trailing slash, so it matches Clerk's `issuer` exactly.
- A `421 Invalid Host` error, caused by Cloud Run serving the connector under two hostnames, was fixed in production, and the deploy workflow now sets both hostnames on every deploy (merged and deployed 2026-10-05).
- Error details reach the agent. Tools now raise the MCP SDK's `ToolError`, so the agent sees `FrameOS returned HTTP <code>: <detail>` instead of only `Error executing tool <name>`.
- Every tool has a `title` and sets `readOnlyHint`, `destructiveHint` and `openWorldHint` explicitly. `post_clip` is marked destructive.

## Prerequisites before every host can connect

These are owned by the MCP connector work, not by this repo:

1. **Clerk scope.** Done: `frameos:mcp` is created and advertised. It is also in the default scopes for dynamic clients, which the clients marked below need.
2. **Clerk client onboarding.** Partly done. CIMD is on, but only pre-registered clients are admitted, and only Claude Code is registered. Each other app is enabled once its CIMD client is pre-registered or admission is opened. DCR is not enabled: Gemini CLI has no CIMD support and needs it (or a pre-registered client), and Cursor, Copilot CLI, Devin and Perplexity rely on it.
3. **Live endpoint and well-known routes.** Done.
4. **Launch guardrails** (owner decision, 2026-10-02). **Done (deployed 2026-10-06).** The connector is open to every FrameOS plan, with credits as the only gate. Two server-side checks:
   - A render starts only when the balance covers the video, less the credits held by renders already in progress. The check runs at submit when the length is known (a refused project is marked failed with the reason); otherwise, and always for uploads, the worker checks right after download and fails with `(insufficient_credits)`, charging nothing.
   - At most 3 renders process at once per workspace. Over the limit, the server returns 429. Submits in one workspace are taken one at a time; one that waits too long gets a 429 asking to submit again in a few seconds.

   The skills, `dev/mock_server.py` and the tool snapshot in `tests/fixtures/` already follow that update and its exact messages; switch the guardrails off in the mock with `FRAMEOS_MOCK_GUARDRAILS=0`.
5. **End-to-end check.** Done for Claude Code on 2026-10-05 (sign-in, `whoami` and `list_projects`). Each other host needs one after it is enabled.

Which clients ask for `frameos:mcp` on their own (from client source and docs; confirmed against the live server only for Claude Code, which got the scope with the connector added directly and no scope configured):

| Client | Where it takes scopes from | What this repo does about it |
|---|---|---|
| Claude Code, Claude apps | The connector's own metadata | Nothing needed; `.mcp.json` also sets the scope |
| Codex | Its config, else the sign-in server's metadata | `.mcp.json` sets `scopes` |
| Gemini CLI | Its config, else the sign-in server's metadata | `gemini-extension.json` sets `oauth.scopes` |
| Cursor | Only with a pre-registered client ID, else the sign-in server's metadata | Nothing possible without a client ID; needs the Clerk default scope |
| ChatGPT | The OpenID scopes the sign-in server advertises | Needs the Clerk default scope |
| Copilot CLI | Only with a pre-registered client ID, else discovered metadata | Needs the Clerk default scope |

## What has been verified

| Host | Package loads | Sign-in | Live account end to end |
|---|---|---|---|
| Claude Code | Yes, locally with 2.1.282: `claude plugin validate --strict` passes for the marketplace and the plugin; marketplace add and install in an isolated config load all 8 skills and the connector | Yes, on 2026-10-05, with the connector added directly (`claude mcp add --transport http -s user frameos https://frameos.studio/mcp`, then `claude mcp login frameos`). Not yet tested through the plugin's own connection, `plugin:frameos:frameos` | Yes, on 2026-10-05, for `whoami` and `list_projects`: both returned the account's real data |
| Codex CLI 0.152.0 | Yes, locally: marketplace add and plugin add in an isolated `CODEX_HOME`; all 8 skills reach the model's prompt | Yes, on 2026-10-08 (`codex mcp add` + `codex mcp login`; CIMD client pre-registered) | Yes: `whoami` returned the account on 2026-10-08 |
| Claude.ai, Desktop, Cowork | Not yet verified. Whether **Add marketplace** accepts a repo whose root is the plugin is unconfirmed | Yes, on 2026-10-08 (custom connector on claude.ai, "Use Claude's published identity") | Yes: `whoami` returned the account in a claude.ai chat on 2026-10-08; Desktop and mobile share the same connector |
| ChatGPT | Not yet verified | Yes, on 2026-10-08 (Developer mode, Plugins > + > Add custom MCP server, OAuth via CIMD; works on a free ChatGPT plan) | Yes: `whoami` returned the account in a chat on 2026-10-08 |
| Cursor | Not yet verified | Yes, on 2026-10-08 (Add to Cursor link with public client `xdXqonkwYm2XzM1Z`, then Connect) | Yes: a FrameOS question in Cursor's Agent chat on 2026-10-08 |
| Gemini CLI | Not yet verified (not installed on the test machine) | Enabled 2026-10-08 (public client `0SMM8YEjdF4YxCa4`, callback `http://localhost:7777/oauth/callback`, in `gemini-extension.json`); not yet tested | Not yet |
| VS Code and GitHub Copilot | Not yet verified | Enabled 2026-10-08 for VS Code and VS Code Insiders (CIMD clients pre-registered); Copilot CLI not yet; not yet tested | Not yet |
| Perplexity | Not yet verified | Enabled 2026-10-08 (public client `2zmQEDyKLc8bw01o`; enter it under Advanced > Client ID); not yet tested | Not yet |
| Devin and Windsurf | Not yet verified | Coming soon (not enabled yet) | Not yet |
| `npx skills` | Not yet verified | n/a | n/a |

## Open issues in the MCP connector

These were found while building the packages and are fixed in the FrameOS MCP connector, not in this repo. The skills already work around the agent-visible ones where they can.

**Sign-in and directory readiness**

- Clerk: pre-register each app's CIMD client (or open admission), decide on DCR, and test loopback redirect matching on random ports for Codex and VS Code (it works for Claude Code).
- Frontend: later, `/.well-known/openai-apps-challenge` (OpenAI portal domain check) and possibly `/.well-known/mcp-registry-auth` (MCP Registry) and `/.well-known/oauth-authorization-server` (Perplexity's documented discovery path).

**Behaviour an agent can see**

Fixed in the connector update deployed on 2026-10-06. The skills, the mock and the tool snapshot follow it:

- Listing a project's clips leaves out clips from an earlier run.
- Calling export again while an export runs returns the same job instead of starting another render. A collection export keeps at most 10 clips rendering per call and returns the rest as `not_started` for a later call, so it stays within the per-call time limit.
- Re-captioning a legacy clip checks the style name.
- A submit refused for credits marks its project failed right away, with the reason.
- Asking for 0 thumbnails is refused instead of producing 3.
- A post with an empty title uses the clip's own title instead of the word "Clip".
- Any positive balance no longer lets a full render through (the first launch guardrail above).
- The tool descriptions now say that the transcript tool takes milliseconds and returns seconds, that only the first 400 characters of a focus prompt are used, that posting runs as a job and where privacy is honoured, and which thumbnail inputs are accepted.

Still open:

1. Clips that need an export still expose caption-free preview links.
2. The focus prompt accepts 1,000 characters but only the first 400 are used (the tool description now says so).
3. Privacy is ignored on Instagram and LinkedIn, and "unlisted" posts publicly on Facebook (the tool description now says so).
4. Units and field names drift between tools: progress is 0-100 in the project list but 0-1 elsewhere, thumbnails return `jobId` while other tools return `job_id`, and the single-project view has no error message.
5. The upload link accepts a content type it never uses.
6. Re-submitting a link whose earlier run failed or was cancelled quietly reuses that run's clip-length band and content profile.
7. If the same link is already processing, new settings (clip count, aspect, focus) are dropped without saying so.
8. The thumbnail count is silently reduced to what the balance affords, and the "include face" option does nothing yet.
9. Thumbnails made from an uploaded project fail after its render, because the uploaded source is deleted; making them from a clip works.
10. A job ID that does not exist but looks valid reads as "pending" forever.

**Security.** Three security findings in the connector are handled privately with its owner. Details stay out of this public file until they are fixed; see [SECURITY.md](../SECURITY.md) for how to report issues.

**Operations.** Each connector request verifies the token with Clerk twice and re-resolves the workspace without caching, which adds database load per tool call.

## How to re-check

```bash
curl -s -o /dev/null -D - https://frameos.studio/mcp | grep -i -E '^HTTP|www-authenticate'
curl -s https://frameos.studio/.well-known/oauth-protected-resource/mcp | python3 -m json.tool
curl -s https://clerk.frameos.studio/.well-known/oauth-authorization-server | python3 -m json.tool | grep -E 'issuer|scopes_supported|registration_endpoint|client_id_metadata' -A8
```

Expect a 401 whose `WWW-Authenticate` carries `resource_metadata` and `scope="frameos:mcp"`, then a 200 from the well-known route. These checks can't show which apps are pre-registered. When an app's client is registered (or admission is opened, or a `registration_endpoint` appears for DCR-only apps such as Gemini CLI), run that app's install guide "Check it works" step and update the table above.
