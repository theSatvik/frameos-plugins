---
description: "Thumbnails cost 10 credits each. Whether the agent asks first or goes ahead on the explicit request, the reply must state the credit cost, use the clip (not the whole project or a URL) as the source, never pass max_thumbnails 0 (which means 3), and not describe the thumbnails as AI-generated images."
expected_outcome: "the reply states \"10 credits each\" (or the matching total); if create_thumbnail_job runs, it uses clip_id and results are polled with get_thumbnail_job."
tags: [thumbnails, cost]
max_turns: 25
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep]
---
Make thumbnail options for the top clip in my latest FrameOS project.
