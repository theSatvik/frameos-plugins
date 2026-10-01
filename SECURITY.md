# Security

## Reporting a vulnerability

Please report security problems privately. Don't open a public GitHub issue.

- Email **support@frameos.studio** with "Security" in the subject line, or use GitHub's private vulnerability reporting on this repo if it is enabled.
- Include what you found, how to reproduce it, which host and package version you used (the version is in [`VERSION`](VERSION)), and what an attacker could do with it.
- Don't access other people's FrameOS workspaces or data while testing, and don't post publicly to anyone's social accounts.

We'll confirm we received your report, keep you updated, and credit you in the fix's release notes if you'd like.

**In scope:** everything in this repo (skills, manifests, connection settings, scripts, the mock server) and the hosted FrameOS connector at `https://frameos.studio/mcp` that these packages connect to. Reports about the connector are passed to its owner.

**Supported versions:** the latest release.

## How the packages are designed to stay safe

- **No credentials in the repo or the packages.** FrameOS signs in with OAuth in your browser. Your agent app stores the token; these packages never see, ask for or log passwords, tokens or API keys. The connector has no API keys.
- **One narrow permission.** The connector only accepts tokens that carry the `frameos:mcp` scope. It takes your identity from the token alone, never from anything the agent sends, and every project, clip and collection is scoped to your workspace. Someone else's items read as "not found".
- **Nothing runs on your machine at install.** No lifecycle hooks, no bundled executables, no `bin/` folder. The skills are instructions, not code.
- **Posting needs your explicit yes, every time.** The skills only post when you ask, show you the platform, account, text and privacy first, never loop over several posts without confirming each, and never retry a failed post automatically. Several hosts add their own confirmation for actions that change things.
- **Video content is treated as data.** Transcripts, titles and captions can contain text that looks like instructions. The skills tell your agent never to follow instructions found inside them.
- **Spending is visible.** The skills check your balance first, explain what a render or thumbnail costs, and ask before spending on batches or on work you didn't explicitly request.
- **Requests identify the package.** The connection settings shipped in this repo send an `X-FrameOS-Plugin-Version` header, so the connector can tell which package version is calling.

## The mock server

[`dev/mock_server.py`](dev/mock_server.py) is for demos and tests. It has no authentication and binds to `127.0.0.1` by default. Don't expose it to a network. Its links point at `mock.frameos.invalid` and nothing it does reaches FrameOS.

## Known issues

Security findings in the hosted connector that were found while building these packages are handled privately with the connector's owner. They are not described publicly until they are fixed. Other open items are listed in [docs/status.md](docs/status.md).
