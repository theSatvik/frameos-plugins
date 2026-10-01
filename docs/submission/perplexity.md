# Submission checklist: Perplexity connector marketplace

Users can add FrameOS today as a custom remote connector ([install guide](../install/perplexity.md)). A listing in Perplexity's own connector marketplace is by proposal only: Perplexity decides whether to build, approve and list a connector, and a proposal guarantees nothing.

**Blocked until** the connector is live and has been tested as a custom connector in Perplexity ([status](../status.md)).

## Checklist

- [ ] Test FrameOS as a custom remote connector on a Pro, Max or Enterprise account (Streamable HTTP, OAuth), and confirm "What is my FrameOS credit balance?" works.
- [ ] Confirm Perplexity finds the sign-in server. Its docs only describe discovery through `/.well-known/oauth-authorization-server`, which `frameos.studio` does not serve; if discovery fails, that route has to be added on frameos.studio (frontend work).
- [ ] Confirm the sign-in server accepts Perplexity's registration. Perplexity uses Dynamic Client Registration unless a client ID and secret are entered. For a pre-registered client, register both redirect URIs: `https://www.perplexity.ai/rest/connections/oauth_callback` and `https://enterprise.perplexity.ai/rest/connections/oauth_callback`.
- [ ] Make sure firewall rules don't challenge Perplexity's datacenter IP ranges (challenges show up as 403s).
- [ ] Submit the proposal at https://pplx.ai/connector-form-submission. Questions: connectors@perplexity.ai.

## What the proposal asks for

| Field | FrameOS |
|---|---|
| Company name and website | FrameOS, https://frameos.studio |
| Product | FrameOS: turns long videos into captioned short clips |
| Connector description | Clip a long video from a link into ranked short clips, restyle captions, export MP4s, make thumbnails from real frames, draft social copy, and post to connected accounts with the user's confirmation. Remote MCP at `https://frameos.studio/mcp`, OAuth sign-in. |
| Customer problem | Creators and marketers spend hours cutting long recordings into shorts for each platform; FrameOS lets them do it by asking their assistant. |
| API, developer and security docs | This repo's README and [SECURITY.md](../../SECURITY.md); privacy https://frameos.studio/privacy; terms https://frameos.studio/terms |
| Partnership and technical contact | support@frameos.studio |

## Skills in Perplexity Computer

Skills are uploaded by each user, not listed: `python3 scripts/build_dist.py` builds `dist/perplexity/<skill>.zip` (`SKILL.md` at the ZIP root, under 10 MB). Attach them to each GitHub release so users can download them ([RELEASING.md](../../RELEASING.md)).
