---
description: Video link to clips, happy path. Checks the connection first, submits once with TikTok settings, polls the render, lists the clips and presents them ranked with scores and source timestamps, without leaking tool names or IDs.
expected_outcome: whoami, then one submit_video (3 clips, 9:16 or default), then get_job, then list_clips; the reply lists the clips with "8.7/10" style scores, mm:ss times and preview links.
tags: [smoke, core, clip]
max_turns: 25
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep]
---
Can you turn https://www.youtube.com/watch?v=Rk4vT9wQe2M into 3 short clips for TikTok? It's the latest episode of our podcast.
