---
description: "Platform words map to the right shape and a topic becomes a word-level focus prompt. \"Instagram feed\" must become 4:5, \"2 clips\" max_clips 2, and \"the parts about pricing\" a focus_prompt containing the word the speaker says."
expected_outcome: "one submit_video with aspect_ratio 4:5, max_clips 2 and a focus_prompt that contains \"pricing\" (or \"price\"); the reply says other topics can still appear."
tags: [core, clip]
max_turns: 25
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep]
---
Make 2 clips for our Instagram feed from https://vimeo.com/912345678 - only the parts where we talk about pricing.
