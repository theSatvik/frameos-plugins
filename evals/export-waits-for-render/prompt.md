---
description: "Export that has to render first. export_clip answers \"rendering\" with a job; the agent must poll get_job until it completes and only then call export_clip once more for the URL. A second export_clip while the job is still rendering aborts the run (stateful agent mocks in this case's mocks/)."
expected_outcome: "export_clip (rendering) -> get_job (processing) -> get_job (completed) -> export_clip (ready); exactly two export_clip calls, on the top-ranked clip; the reply gives the download link and says it expires."
tags: [core, export, agent-mock]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep]
---
Give me a captioned MP4 download of the top clip from my latest FrameOS project.
