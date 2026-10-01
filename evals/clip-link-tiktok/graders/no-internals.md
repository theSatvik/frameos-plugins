---
type: regex
target: last_message
match: not_contains
---
mcp__|\b(?:submit_video|get_job|list_clips|whoami)\b|clip:render:|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}
