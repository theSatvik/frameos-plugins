# Status

Last checked: **2026-10-02**. Package version: see [`VERSION`](../VERSION).

## In one paragraph

The packages in this repo are written and load locally in Claude Code and Codex. The hosted FrameOS connector they point at, `https://frameos.studio/mcp`, is **not live yet**, so no host can sign in or run a FrameOS action today. Nothing has been tested against a live FrameOS account on any host. Every install guide marks what is unverified. Until the connector launches, use the [mock server](../dev/README.md) to try the workflows.

## The hosted connector

Probed with `curl` on 2026-10-02:

| URL | Result |
|---|---|
| `https://frameos.studio/mcp` | 404 |
| `https://frameos.studio/.well-known/oauth-protected-resource/mcp` | 404 |
| `https://clerk.frameos.studio/.well-known/oauth-authorization-server` | 200, but see below |

The connector itself (27 tools) is implemented as part of the FrameOS MCP connector work, but it is not deployed. The sign-in server (Clerk) answers, but it is not ready for agent sign-in yet:

- Its `scopes_supported` does not list `frameos:mcp`, the scope the connector requires on every token.
- It has no `registration_endpoint`, so Dynamic Client Registration (DCR) is off.
- It does not advertise `client_id_metadata_document_supported`, so Client ID Metadata Documents (CIMD) are off.
- It does advertise S256 PKCE and `authorization_response_iss_parameter_supported: true`, which several clients need.

## Prerequisites before any host can connect

These are owned by the MCP connector work, not by this repo:

1. **Clerk scope.** Create the `frameos:mcp` scope, advertise it, assign it to the OAuth applications that may request it, and add it to the default scopes for dynamic clients. Several clients only request scopes the sign-in server advertises (table below).
2. **Clerk client onboarding.** Turn on CIMD (used by Claude's apps, Claude Code, Codex, VS Code and ChatGPT when offered) and DCR (needed by Gemini CLI, which has no CIMD support, and relied on by Cursor, Copilot CLI, Devin and Perplexity).
3. **Live endpoint and well-known routes.** `https://frameos.studio/mcp` and `https://frameos.studio/.well-known/oauth-protected-resource/mcp` must be served (the frontend rewrite merged and the connector origin configured).
4. **End-to-end check** on at least one host with a real account.

Which clients ask for `frameos:mcp` on their own (from client source and docs; not yet confirmed against the live server):

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
| Claude Code 2.1.282 | Yes, locally: `claude plugin validate --strict` passes for the marketplace and the plugin; marketplace add and install in an isolated config load all 8 skills and the connector | Request shape only: against a local fake server, Claude Code asked for `frameos:mcp offline_access` | Not yet |
| Codex CLI 0.152.0 | Yes, locally: marketplace add and plugin add in an isolated `CODEX_HOME`; all 8 skills reach the model's prompt | Not yet (`codex mcp login` fails while the endpoint is 404) | Not yet |
| Claude.ai, Desktop, Cowork | Not yet verified. Whether **Add marketplace** accepts a repo whose root is the plugin is unconfirmed | Not yet | Not yet |
| ChatGPT | Not yet verified | Not yet | Not yet |
| Cursor | Not yet verified | Not yet | Not yet |
| Gemini CLI | Not yet verified (not installed on the test machine) | Not yet | Not yet |
| VS Code and GitHub Copilot | Not yet verified | Not yet | Not yet |
| Perplexity | Not yet verified | Not yet | Not yet |
| Devin and Windsurf | Not yet verified | Not yet | Not yet |
| `npx skills` | Not yet verified | n/a | n/a |

## Open issues in the MCP connector

These were found while building the packages and are for the owner of the FrameOS MCP connector to fix. This repo does not change the connector. The skills already work around the agent-visible ones where they can.

**Sign-in and directory readiness**

- The connector publishes its sign-in server with a trailing slash (`https://clerk.frameos.studio/`), while Clerk's issuer has none. ChatGPT compares them exactly and would fall back to per-connection redirects.
- The 401 `WWW-Authenticate` header carries no `scope="frameos:mcp"`, so clients that read the scope from the challenge cannot find it there.
- No tool has a `title`, and write tools do not all declare `destructiveHint` (and `openWorldHint`) explicitly. Claude's and OpenAI's directories require these. Posting a clip is marked non-destructive even though a public post cannot be undone.
- Clerk: create and advertise the scope, make it a default, enable CIMD and DCR, and test loopback redirect matching on random ports (Claude Code, Codex, VS Code).
- Frontend: serve the connector routes, and later `/.well-known/openai-apps-challenge` (OpenAI portal domain check) and possibly `/.well-known/mcp-registry-auth` (MCP Registry) and `/.well-known/oauth-authorization-server` (Perplexity's documented discovery path).

**Behaviour an agent can see**

1. Listing a project's clips can include clips from an earlier run that no longer exist; opening or exporting those returns "not found".
2. Calling export again before an export finishes starts another render each time; exporting a whole collection can start up to 50 renders in one call, close to the per-call time limit.
3. Re-captioning a legacy clip does not check the style name; a bad name is saved and later exports fail until the style is set again.
4. Clips that need an export still expose caption-free preview links.
5. The transcript tool takes milliseconds but returns seconds, and does not say so.
6. The focus prompt accepts 1,000 characters but only the first 400 are used.
7. Posting is described as immediate but is a background job; privacy is ignored on Instagram and LinkedIn, and "unlisted" posts publicly on Facebook.
8. Units and field names drift between tools: progress is 0-100 in the project list but 0-1 elsewhere, thumbnails return `jobId` while other tools return `job_id`, and the single-project view has no error message.
9. The upload link accepts a content type it never uses.
10. Re-submitting a link whose earlier run failed or was cancelled quietly reuses that run's clip-length band and content profile.
11. If the same link is already processing, new settings (clip count, aspect, focus) are dropped without saying so.
12. A submit refused for zero credits still leaves an empty project, which is marked failed about 30 minutes later.
13. Asking for 0 thumbnails produces 3; the count is silently reduced to what the balance affords; the "include face" option does nothing yet.
14. Thumbnails made from an uploaded project fail after its render, because the uploaded source is deleted; making them from a clip works.
15. Any positive balance lets a full render through, and the balance stops at zero.
16. A job ID that does not exist but looks valid reads as "pending" forever.
17. Error details do not reach the agent today: the connector raises a generic exception, so the MCP SDK shows only `Error executing tool <name>` instead of the `FrameOS returned HTTP <code>: <detail>` text the skills read. The fix is to raise the SDK's tool-error type. The [mock server](../dev/README.md) shows the intended text by default and today's behaviour with `FRAMEOS_MOCK_ERRORS=opaque`.

**Security.** Three security findings in the connector are handled privately with its owner. Details stay out of this public file until they are fixed; see [SECURITY.md](../SECURITY.md) for how to report issues.

**Operations.** Each connector request verifies the token with Clerk twice and re-resolves the workspace without caching, which adds database load per tool call.

## How to re-check

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://frameos.studio/mcp
curl -s -o /dev/null -w '%{http_code}\n' https://frameos.studio/.well-known/oauth-protected-resource/mcp
curl -s https://clerk.frameos.studio/.well-known/oauth-authorization-server | python3 -m json.tool | grep -E 'scopes_supported|registration_endpoint|client_id_metadata' -A8
```

When the first two return something other than 404, `frameos:mcp` appears in the scopes, and either `registration_endpoint` or `client_id_metadata_document_supported` is present, run each install guide's "Check it works" step and update the table above.
