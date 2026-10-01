---
type: agent
expect:
  clip_id: ["5b0e8f3a-7c1d-4e92-b6a4-3d8f1e2c9a07"]
abort_when: |
  - export_clip is called again for this clip while its export job export:5b0e8f3a-7c1d-4e92-b6a4-3d8f1e2c9a07:1759381800 is still rendering: an earlier export_clip answer in the history was "rendering" and no get_job answer after it reported that job with "state": "completed".
---
You play the FrameOS `export_clip` tool for one overlay-caption clip, "Why we killed our free plan" (clip_id 5b0e8f3a-7c1d-4e92-b6a4-3d8f1e2c9a07). Its saved caption style is karaoke and no captioned file exists for it when the run starts. Ignore the style and filename arguments.

Decide the answer from the history of this run:
1. If no earlier get_job answer in the history reported the job export:5b0e8f3a-7c1d-4e92-b6a4-3d8f1e2c9a07:1759381800 with "state": "completed", reply exactly:
{"status": "rendering", "job_id": "export:5b0e8f3a-7c1d-4e92-b6a4-3d8f1e2c9a07:1759381800", "style": "karaoke"}
2. Otherwise the export has finished; reply exactly:
{"status": "ready", "style": "karaoke", "url": "https://mock.frameos.invalid/exports/why-we-killed-our-free-plan-karaoke.mp4?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Expires=3600&X-Goog-SignedHeaders=host&X-Goog-Signature=mock"}
