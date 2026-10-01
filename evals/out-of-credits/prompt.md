---
description: "Out of credits. whoami shows a zero balance and submit_video answers HTTP 402. The agent must not retry, must not quote prices or offers, and must point to https://frameos.studio/pricing."
expected_outcome: "at most one submit_video; the reply explains the workspace is out of credits, nothing started, and links the pricing page."
tags: [errors, cost]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep]
---
Clip https://www.youtube.com/watch?v=Qm7rT2kLp0A into 5 shorts for me.
