# Mock FrameOS MCP server

`dev/mock_server.py` is a single-file, stateful stand-in for the FrameOS MCP server. Use it to demo the skills end to end, develop new ones, or run the test suite without a FrameOS account, without credentials and without spending credits.

It exposes the same 27 tools as the real server, with identical names, parameters, defaults, enums, annotations and descriptions (`tests/test_mock_server.py` checks this against `tests/fixtures/mcp-snapshot.json`). Behind the tools is an in-memory fake of the FrameOS API that returns the real response shapes and error strings: jobs move through the real progress messages, renders charge credits, exports start burn jobs, and posts finish with a link.

Nothing leaves your machine. Media, preview, thumbnail and post links all point at `https://mock.frameos.invalid/...`, a reserved domain that never resolves. Upload links point at the mock itself, so the local-file flow works with `curl`.

## Run it

You need [uv](https://docs.astral.sh/uv/). The script declares its own dependency (`mcp==2.2.0`, the SDK the real server uses) inline, so there is nothing to install. Run these from the repo root:

```bash
uv run --script dev/mock_server.py                     # stdio
uv run --script dev/mock_server.py --http              # Streamable HTTP at http://127.0.0.1:8790/mcp
uv run --script dev/mock_server.py --http --port 9000  # another port
```

Without uv, use Python 3.10+ with `pip install mcp==2.2.0`, then `python dev/mock_server.py`.

HTTP mode is stateless JSON at `/mcp` with no auth, like the real server's transport minus OAuth. It binds to `127.0.0.1` by default and keeps the SDK's DNS-rebinding protection. All state lives in memory, so restarting the server resets the account.

## Demo it in Claude Code

From the repo root:

```bash
claude --plugin-dir . --mcp-config dev/mock.mcp.json --strict-mcp-config
```

- `--plugin-dir .` loads this repo as the `frameos` plugin, including the eight skills.
- `dev/mock.mcp.json` starts the mock over stdio as a server named `frameos`. It uses a relative path, so launch `claude` from the repo root.
- `--strict-mcp-config` keeps only the mock. Without it, Claude Code also loads the plugin's own server and the root `.mcp.json`, which both point at the real endpoint and fail to connect.

For a headless run, put the prompt before `--mcp-config`. That flag takes several files, so anything after it that isn't another flag is read as a file name:

```bash
claude -p "Clip https://www.youtube.com/watch?v=demo123 into 3 TikToks about pricing" \
  --plugin-dir . --mcp-config dev/mock.mcp.json --strict-mcp-config \
  --allowedTools "mcp__frameos__*"
```

Verified on 2026-10-02 with Claude Code 2.1.282. The session's init event listed the 8 `frameos:` skills and one MCP server, `frameos`, connected with 27 tools. No other MCP servers were loaded.

## Demo it in Codex

Use HTTP mode. In one terminal:

```bash
uv run --script dev/mock_server.py --http
```

Then, with the plugin installed (see `docs/install/codex.md`), start Codex with the server URL overridden:

```bash
codex -c 'mcp_servers.frameos.url="http://127.0.0.1:8790/mcp"'
```

A user-level `mcp_servers.frameos` entry shadows the plugin's server of the same name, so the skills talk to the mock. The override also works when your `~/.codex/config.toml` already has a URL-based `frameos` entry. Add `exec "<prompt>"` for a headless run.

Stdio works only if no `frameos` entry in your config sets a `url`. Otherwise Codex refuses with "url is not supported for stdio".

```bash
codex -c 'mcp_servers.frameos.command="uv"' \
      -c "mcp_servers.frameos.args=[\"run\",\"--script\",\"$PWD/dev/mock_server.py\"]"
```

What was checked with codex-cli 0.152.0 against a scratch `CODEX_HOME`: `codex mcp list` accepts both overrides. A full Codex session against the mock has not been run.

## Demo it in Cursor, VS Code / Copilot and other clients

Start HTTP mode (`uv run --script dev/mock_server.py --http`), install the plugin for the skills (`docs/install/`), then add the mock as its own server. Use a different name (`frameos-mock`) so it can't clash with the plugin's `frameos` server. The skills call tools by bare name, so they use whichever server is connected.

- Cursor: add this to `.cursor/mcp.json` in the project, or to `~/.cursor/mcp.json`.

  ```json
  { "mcpServers": { "frameos-mock": { "url": "http://127.0.0.1:8790/mcp" } } }
  ```

- VS Code / GitHub Copilot: add this to `.vscode/mcp.json`. If you open this repo itself, VS Code also picks up the root `.mcp.json` (the real endpoint); stop that server or ignore its connection error.

  ```json
  { "servers": { "frameos-mock": { "type": "http", "url": "http://127.0.0.1:8790/mcp" } } }
  ```

- Any other MCP client: point it at stdio (`uv run --script /absolute/path/to/dev/mock_server.py`) or at `http://127.0.0.1:8790/mcp`.

The Cursor and VS Code snippets follow those hosts' documented formats but have not been run against the mock.

## Things to try

1. "What's my FrameOS credit balance?" Returns a fixture workspace with 120 credits.
2. "Clip https://www.youtube.com/watch?v=demo123 into 3 TikToks about pricing." The render finishes after about three status checks. Clips come from a fictional podcast, *The Build Room*, and a focus on pricing puts the pricing clip first.
3. "Export the top clip with captions." The first export call starts a burn job. Once that finishes, a second call returns a download link.
4. "Make the captions bigger and move them up, Beasty style, then export again."
5. "Make 3 YouTube thumbnails for that clip." Costs 30 mock credits.
6. "Draft an Instagram caption for it, then post it to my YouTube as unlisted." The post job finishes with a mock link.
7. "Clip ./episode.mp4." This tests the local-file path: upload link, `curl -X PUT` to the mock, then submit.
8. "Show my older projects and recaption one of them." A seeded 40-day-old project has burned-in captions, which exercises the `recaption_clip` path.

## Error triggers

Errors surface as tool errors with the real server's text, `FrameOS returned HTTP <code>: <detail>`. The MCP SDK puts `Error executing tool <name>: ` in front of it.

| Trigger | Result |
|---|---|
| `FRAMEOS_MOCK_CREDITS=0` | `submit_video` / `submit_uploaded_video`: 402 `Out of credits. Upgrade your plan or add credits to keep processing.` Thumbnails return 402 below 10 credits. |
| Source URL containing `too-short` | 422 `This video is only 12 seconds long, which is too short to pull a highlight out of. ...` The project is left `failed` with `(source_too_short)`. |
| Source URL containing `no-clips` | The render job fails at the scoring step with the real `(no_clips_found)` message, and no credits are charged. |
| Unknown UUID | 404 with the route's own detail: `Video not found`, `Clip not found`, `Project not found`, `Collection not found`, `Job not found`. |
| Not a UUID, or a parameter out of range | 422 with FastAPI's list-shaped detail, e.g. `[{'type': 'uuid_parsing', 'loc': ['path', 'project_id'], ...}]` |
| Unknown caption style, font or animation | 422 `Unknown caption style: X` / `Unknown caption font: X` / `Unknown caption animation: X` |
| `set_caption_style` on a burned (legacy) clip | 409 `This clip has burned-in captions — use POST /clips/{id}/recaption.` |
| `recaption_clip` on an overlay clip | 409 `This clip uses overlay captions — set the style via PATCH /clips/{id}/captions (instant); burning happens on export.` |
| `post_clip` before exporting the saved style | 409 `Captions for this clip aren't rendered yet. Export the clip first, then post.` |
| `submit_uploaded_video` before the PUT / twice | 409 `Video upload has not completed` / 404 `Upload link was not issued to this workspace or expired` |
| 31st `generate_social_copy` call in an hour | 429 `Social copy limit reached; try again in an hour` |
| Duplicate collection name | 409 `A collection with that name already exists` |

## Settings

| Variable | Default | Effect |
|---|---|---|
| `FRAMEOS_MOCK_CREDITS` | `120` | Starting credit balance. |
| `FRAMEOS_MOCK_PLAN` | `starter` | `plan` reported by `whoami` (`free`, `starter` or `pro`). It changes nothing else. |
| `FRAMEOS_MOCK_SPEED` | `fast` | `fast`: jobs advance on each status check. A render completes on the 3rd check (also counting `get_project` and `list_projects`), exports, re-captions and thumbnails on the 2nd, posts on the 3rd. A number N: jobs advance by wall-clock time instead, with a render taking N seconds, exports and re-captions N/4, thumbnails 0.4N, posts 0.3N. |
| `FRAMEOS_MOCK_SEED` | `1` | `0` starts with no projects. By default there is one older project with burned-in captions, no stored transcript, and one stale clip. |
| `FRAMEOS_MOCK_SOCIAL` | `1` | `0` starts with no connected social accounts. By default there is one each for YouTube, Instagram, LinkedIn and Facebook. |
| `FRAMEOS_MOCK_BRAND_LOGO` | `0` | `1` makes `get_brand` return a logo. |
| `FRAMEOS_MOCK_ERRORS` | `detailed` | `opaque` reproduces what today's real server shows (see below). |
| `FRAMEOS_MOCK_UPLOAD_PORT` | `0` | stdio mode only: the port for the upload receiver (`0` = any free port). In HTTP mode, uploads go to the same port as `/mcp`. |
| `FRAMEOS_MOCK_QUIET` | unset | `1` drops the one-line startup message on stderr. |

## Real backend quirks the mock reproduces on purpose

The skills have to cope with these, so the mock keeps them:

- **Progress units.** `progress` runs 0-100 in `list_projects`, but 0-1 in `get_project` and `get_job`.
- **ETA.** For YouTube links, `eta_seconds` stays `null` until the worker has downloaded the source. Vimeo links get an ETA at submit.
- **Job IDs.**
  - The formats are `clip:render:<video>`, `export:<clip>:<unix_s>`, `recap:<clip>:<unix_s>`, `social:post:<clip>:<unix_s>` and `thumb:<org>:<unix_ms>`.
  - Thumbnails return a camelCase `jobId`.
  - An owned job ID with no state polls as `pending` forever.
- **Exports.**
  - New clips are `overlay` clips with `exportRequired: true` and a `null` `downloadUrl`. Their `url` and `previewUrl` are caption-free.
  - Each `export_clip` call made before the export exists starts another burn job.
- **Captions.**
  - `recaption_clip` does not validate the style.
  - Calling `set_caption_style` without `appearance` clears any saved overrides.
- **Stale clips.** `list_clips` and `get_project` still count a soft-deleted clip from an earlier run, which then returns 404 on `describe_clip`.
- **Stray project on 402.** A 402 at submit leaves a stray `pending` project with no job. After 30 minutes it is marked failed as "Processing crashed before it could report".
- **Resubmitting.** Resubmitting a link that is still rendering returns `status: "already_running"` and ignores the new settings. A failed link re-runs in the same project. A completed link creates a new project, which is charged in full again, because the record of paid minutes belongs to the project, not the link.
- **Uploads.** Uploaded sources are deleted after a successful render, so a thumbnail job by `video_id` for that project fails. Making it by `clip_id` works.
- **Transcripts.** `get_transcript` takes milliseconds and returns seconds.
- **Focus prompt.** `focus_prompt` is silently cut to 400 characters and matched on words.

## Error text: an open issue in the real server

The real server raises `RuntimeError("FrameOS returned HTTP ...")`. The mcp 2.2.0 SDK treats any exception other than `ToolError` as a crash and shows the client only `Error executing tool <name>`, so the FrameOS detail never reaches the agent. This was reproduced against a scratch copy of the real `server.py` on 2026-10-02.

The mock raises `ToolError` by default, which is what the real server would do once it switches to `ToolError`. Set `FRAMEOS_MOCK_ERRORS=opaque` to see today's real behaviour.

## What the mock does not simulate

- **OAuth.** The mock has no auth at all, so it never returns 401 or 403, has no `frameos:mcp` scope, no `WWW-Authenticate` challenge and no protected-resource metadata. To try the frameos-setup troubleshooting paths you need the real server.
- **Real media and real clipping.** Links don't resolve.
  - Clips are cut from a fixed script for a fictional podcast. They are not picked by AI from your video.
  - Durations are made up from a hash of the URL (6 to 62 minutes), and titles are made up too.
  - Social copy is filled into a template. No model writes it.
- **Failures beyond the triggers above.** That includes:
  - bot-check and download errors, and the automatic "retrying automatically" re-run;
  - the 45-minute capacity retry and the processing timeout;
  - `cancelled` jobs;
  - 503s ("Render queue unreachable", "Export requires the Cloud Run worker", "FrameOS API is unavailable");
  - partial publishes, and Instagram's long processing.
- **Caching and timing.** The real API caches the account (60 s) and the project list (20 s), and its tool calls time out after 45 s. The mock does neither.
- **Language.** Transcripts are English only. Translation, missing word timings and speaker fields are not simulated.
- **Visual effects.** There is no watermark, brand-logo, plan or pack behaviour. `plan` is just a label.
- **Multiple workspaces.** There is one workspace, so cross-workspace 404s only show up as "unknown ID".
- **Persistence.** State is lost when the process exits.

## Tests

`tests/test_mock_server.py` checks:

- schema parity with the snapshot;
- the full flow over the MCP protocol: submit, poll, list clips, export (rendering), poll, export (ready), then a bad caption style;
- the 402, 404, 409 and 422 paths, uploads, thumbnails, posting and collections;
- both transports, stdio and HTTP.

The tests are skipped when `mcp` is not installed, so `python3 scripts/test.py` stays stdlib-only. To run them:

```bash
uv run --with mcp==2.2.0 python -m unittest discover -s tests -p test_mock_server.py
```

When the real server changes, refresh `tests/fixtures/mcp-snapshot.json` and copy the changed tool signatures into `create_server()` in `mock_server.py`. They are copied verbatim from `FrameOS-Backend/mcp_server/frameos_mcp/server.py`.
