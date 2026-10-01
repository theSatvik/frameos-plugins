---
type: tool_used
tool: Bash
# Needs --allow-tools "Bash(curl *)"; without it Bash does not exist in the run.
input_match: 'curl[\s\S]*(?:--upload-file|\s-T\s)[\s\S]*episode-42\.mp4'
min: 1
weight: 0.5
---
