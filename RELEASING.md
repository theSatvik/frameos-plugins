# Releasing

Every release ships one version number everywhere: [`VERSION`](VERSION), every manifest and marketplace entry, and every `X-FrameOS-Plugin-Version` header. Never edit those by hand; the bump script does it and the validator fails on any drift.

## Checklist

### 1. Prepare

- [ ] Start from an up-to-date `main` with a clean working tree and green CI.
- [ ] Pick the version ([semver](https://semver.org/)):
  - **patch** (0.1.1): wording fixes in skills or docs, no new behaviour.
  - **minor** (0.2.0): new skills, new hosts, new workflows, or behaviour changes in existing skills.
  - **major** (1.0.0): anything that breaks installs or saved references: renaming the plugin, a skill, the `frameos` server key or a Gemini command.

### 2. Bump and record

```bash
python3 scripts/bump_version.py X.Y.Z --dry-run   # shows every file it will change
python3 scripts/bump_version.py X.Y.Z
```

It updates `VERSION`, every manifest and marketplace `version`, every `X-FrameOS-Plugin-Version` header, and header values quoted in docs. It refuses non-semver versions and downgrades (unless `--allow-downgrade`).

- [ ] Add the release to [CHANGELOG.md](CHANGELOG.md) by hand: move items from **Unreleased** under `## [X.Y.Z] - YYYY-MM-DD`.
- [ ] If anything changed what has been verified on which host, update [docs/status.md](docs/status.md).

### 3. Check

```bash
python3 scripts/sync.py         # ground rules into every skill, skills/ into agent-plugin/skills/
python3 scripts/test.py         # sync --check, validate.py, unit tests
```

The mock-server tests skip themselves unless the `mcp` package is importable. To include them, run the same script with Python 3.10 or later and `mcp==2.2.0`, for example:

```bash
uv run --python 3.11 --with mcp==2.2.0 python scripts/test.py
```

Host validators (no credentials needed):

```bash
claude plugin validate . --strict
claude plugin validate .claude-plugin/plugin.json --strict
claude plugin eval . --trust-plugin --max-cost-usd 0 --ablation none --no-publish
```

The eval command with `--max-cost-usd 0` only loads and checks every case and mock, then stops; exit code 2 with `partialReason: cost_ceiling` is the expected result. Run the full suite (it costs API usage) before minor and major releases:

```bash
claude plugin eval . --trust-plugin --json results.json --threshold 0.8 --no-publish --max-cost-usd 20
```

Codex install check in a throwaway profile, so your own `~/.codex` is untouched:

```bash
export CODEX_HOME="$(mktemp -d)"
codex plugin marketplace add "$PWD"
codex plugin add frameos@frameos
codex debug prompt-input "hi" | grep -o 'frameos:frameos-[a-z-]*' | sort -u   # expect all eight skills
unset CODEX_HOME
```

### 4. Build the ZIPs

```bash
python3 scripts/build_dist.py
```

This writes, into `dist/` (git-ignored):

- `dist/frameos-plugin-X.Y.Z.zip`: the plugin for claude.ai **Upload plugin** and the OpenAI plugin portal.
- `dist/claude-ai/<skill>.zip`: one per skill, folder at the top level, for claude.ai skill upload.
- `dist/perplexity/<skill>.zip`: one per skill, `SKILL.md` at the root, for Perplexity Computer.
- `dist/SHA256SUMS`.

Spot-check the layouts with `unzip -l`.

### 5. Merge, tag, publish

- [ ] Commit (`Release vX.Y.Z`), open a PR, and merge once CI passes.
- [ ] Tag the merge commit and push the tag:

  ```bash
  git tag -a vX.Y.Z -m "FrameOS plugins vX.Y.Z"
  git push origin vX.Y.Z
  ```

  `vX.Y.Z` is the tag users pin with `--ref` (Codex, Gemini CLI) or `#vX.Y.Z` (Claude Code).
- [ ] Optionally add Claude Code's own tag, which also checks that `plugin.json` and the marketplace entry agree. It is only needed if other plugins declare a version range on FrameOS:

  ```bash
  claude plugin tag --dry-run
  claude plugin tag --push
  ```

  This creates `frameos--vX.Y.Z`.
- [ ] Create the GitHub release with the ZIPs. Release asset names must be unique, and the claude.ai and Perplexity skill ZIPs share file names, so rename them first:

  ```bash
  mkdir -p dist/release
  cp dist/frameos-plugin-X.Y.Z.zip dist/SHA256SUMS dist/release/
  for f in dist/claude-ai/*.zip;  do cp "$f" "dist/release/$(basename "$f" .zip)-claude-ai.zip"; done
  for f in dist/perplexity/*.zip; do cp "$f" "dist/release/$(basename "$f" .zip)-perplexity.zip"; done
  awk '/^## \[X.Y.Z\]/{f=1; next} /^## \[/{f=0} f' CHANGELOG.md > dist/release-notes.md
  gh release create vX.Y.Z dist/release/* --title "vX.Y.Z" --notes-file dist/release-notes.md
  ```

  `SHA256SUMS` lists the original paths under `dist/`, not the renamed copies.

### 6. Directories

Do only the ones where FrameOS is listed (see [docs/submission/](docs/submission/)):

- [ ] **Anthropic:** the plugin listing picks up new versions from GitHub automatically; check the portal for scan results.
- [ ] **OpenAI (ChatGPT and Codex):** upload the new `frameos-plugin-X.Y.Z.zip` when metadata or skills changed (connector-only changes go live without a new ZIP).
- [ ] **Cursor Marketplace:** every update is re-reviewed after you push.
- [ ] **Gemini CLI gallery:** nothing to do; it re-crawls daily.
- [ ] **awesome-copilot / Devin marketplace:** if listed, update the pinned tag or commit SHA through their process.
- [ ] Tell users who uploaded skill ZIPs to claude.ai or Perplexity that new ZIPs are on the release page.
