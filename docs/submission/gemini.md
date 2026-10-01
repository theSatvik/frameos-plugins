# Submission checklist: Gemini CLI extension gallery

There is no submission form. The gallery at https://geminicli.com/extensions (registry: https://geminicli.com/extensions.json) is built by a crawler that runs daily and picks up public GitHub repos that meet the requirements below.

**Blocked until** the connector is live and the extension has been tested in Gemini CLI ([status](../status.md)). Listing earlier would show users an extension that can't sign in.

## Checklist

- [x] `gemini-extension.json` at the **absolute root** of the repo (and of any release archive): it is.
- [x] `name` `frameos` (lowercase, dashes allowed), `version`, and a `description`, which the gallery shows.
- [x] Connector entry uses `httpUrl` with `oauth.enabled` and `oauth.scopes: ["frameos:mcp"]`.
- [x] `contextFileName: "GEMINI.md"`, kept under 60 lines.
- [x] Commands in `commands/frameos/*.toml` (`/frameos:setup` and seven more) and skills in `skills/`.
- [ ] Repo is public.
- [ ] Repo has the GitHub topic `gemini-cli-extension`:

  ```bash
  gh repo edit theSatvik/frameos-plugins --add-topic gemini-cli-extension
  ```

- [ ] Tested locally: `gemini extensions link .` from a clone (or `gemini extensions install https://github.com/theSatvik/frameos-plugins`), restart Gemini CLI, run `/mcp auth frameos`, then `/frameos:setup` ([install guide](../install/gemini-cli.md)).

## Sign-in requirements in Gemini CLI

- Gemini CLI has no CIMD support, so FrameOS's sign-in server must offer Dynamic Client Registration (or FrameOS must ship a pre-registered public client with a fixed `redirectUri`).
- Gemini CLI enforces the issuer check (RFC 9207) strictly: the callback must carry an `iss` that matches the discovered issuer. Clerk advertises support; untested end to end.
- The connector's protected-resource metadata `resource` must exactly equal `https://frameos.studio/mcp`.

## Releases

- Users can pin a release with `--ref vX.Y.Z`; tag every release ([RELEASING.md](../../RELEASING.md)).
- If the repo ever moves, set `migratedTo` in `gemini-extension.json` so installed copies follow it.
