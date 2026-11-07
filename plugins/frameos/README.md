# FrameOS for Claude

Turn a long video into captioned vertical shorts without leaving Claude. Paste a link to a podcast, stream, interview or webinar, and FrameOS finds the moments worth sharing, cuts them into clips that keep the speaker in frame, and adds captions people can read with the sound off. Then ask Claude to restyle the captions, export MP4s, make thumbnails from real frames of your video, draft a title and caption for each platform, or post a clip to an account you connected in FrameOS.

This folder is the whole Claude plugin: eight skills and the FrameOS connector.

## What's inside

- **Skills:** frameos-setup, frameos-clip, frameos-captions, frameos-find-moments, frameos-thumbnails, frameos-publish, frameos-library and frameos-repurpose, in [`skills/`](skills/).
- **Connector:** the hosted FrameOS MCP server at `https://frameos.studio/mcp`, set in [`.mcp.json`](.mcp.json). You sign in once with your FrameOS account in your browser.

## Install

- **claude.ai, Claude Desktop and Cowork:** add FrameOS from the Claude Directory, then connect your FrameOS account when asked.
- **Claude Code:** run `/plugin marketplace add theSatvik/frameos-plugins`, then `/plugin install frameos@frameos`, and sign in from `/mcp`.

Steps for other apps are at https://frameos.studio/plugin.

## What this plugin sends

- **Two addresses, nothing else.** The plugin points Claude at the FrameOS connector, `https://frameos.studio/mcp`, and at FrameOS sign-in, `https://clerk.frameos.studio`, which you see once when you connect your account. Upload and download links the connector hands back point at FrameOS's own file storage and expire.
- **No code of its own.** The plugin is written instructions (skills) and connection settings, with no hooks, scripts or binaries, and nothing runs on install. Claude makes every request. In apps with a terminal, Claude uses `curl` to upload a video file you name and, if you ask, to save finished MP4s.
- **No tracking.** No analytics or telemetry. The only extra detail is the plugin's version number, sent as an `X-FrameOS-Plugin-Version` header.
- **Nothing goes public without you.** The skills ask you to confirm every post, every time, before anything is published.

Making clips and thumbnails uses credits from your FrameOS account; plans are on https://frameos.studio/pricing.

[Privacy policy](https://frameos.studio/privacy) · [Terms](https://frameos.studio/terms) · [Support](https://frameos.studio/contact) · support@frameos.studio
