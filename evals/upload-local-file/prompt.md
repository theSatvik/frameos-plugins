---
description: "Local file path. The agent must take the upload route (create_upload_link with the real filename, then an HTTP PUT with curl), never pass a local path to submit_video, never show the signed upload link or the gs:// path, and report honestly when the upload cannot complete. Run with --scaffold and --allow-tools \"Bash(curl *)\"."
expected_outcome: "whoami, create_upload_link(filename episode-42.mp4), a curl PUT of the file; offline the PUT fails, so the reply says the upload did not go through and offers a next step. If a PUT ever succeeds, submit_uploaded_video must use the exact gs_path that create_upload_link returned (the mock aborts the run otherwise)."
tags: [clip, upload, needs-bash, needs-scaffold]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Bash]
---
I've got the raw recording of episode 42 in this folder as episode-42.mp4. Can you turn it into 3 vertical shorts?
