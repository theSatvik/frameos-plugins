---
description: "Caption restyle on an overlay clip. \"MrBeast style\" maps to the beasty style, \"a bit bigger\" to an appearance scale above 1, set_caption_style comes before export_clip, recaption_clip (legacy burned clips only) is never used, and the reply hands over the exported URL."
expected_outcome: "set_caption_style(clip \"Why we killed our free plan\", style beasty, appearance with scale about 1.25), then export_clip, then the reply links the beasty export."
tags: [smoke, core, captions]
max_turns: 25
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep]
---
On my latest FrameOS project, switch the captions on the "Why we killed our free plan" clip to a MrBeast-style look and make the text a bit bigger, then send me the captioned MP4.
