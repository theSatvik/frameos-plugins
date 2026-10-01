---
description: "get_transcript takes milliseconds but returns seconds. \"Minute 12 to minute 15\" must be sent as start_ms 720000 and end_ms 900000, and the returned seconds must be shown to the user as mm:ss."
expected_outcome: "get_transcript(latest project, start_ms 720000, end_ms 900000); quotes shown with mm:ss timestamps such as 12:11 or 14:31."
tags: [smoke, core, moments]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep]
---
In my latest FrameOS project, what do they say between minute 12 and minute 15? Give me a few quotes with timestamps.
