---
description: "Render limit. Three videos are already processing, and submit_video answers HTTP 429 with the per-workspace limit. The agent must not retry in a loop, must not claim the render started, and must offer to submit once a running render finishes."
expected_outcome: "at most one submit_video; the reply says nothing was submitted because 3 videos are already processing, and offers to submit after one of them finishes."
tags: [errors, guardrails]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep]
---
Clip https://www.youtube.com/watch?v=Hk4tR9wLm2Q into 3 TikToks for me.
