---
type: agent
expect:
  job_id: string
---
You play the FrameOS `get_job` tool. The only active job is the caption export job export:5b0e8f3a-7c1d-4e92-b6a4-3d8f1e2c9a07:1759381800, which started when export_clip answered "rendering".

Decide the answer from the history of this run:
1. job_id is export:5b0e8f3a-7c1d-4e92-b6a4-3d8f1e2c9a07:1759381800 and the history has no earlier get_job answer for it: reply exactly
{"id": "export:5b0e8f3a-7c1d-4e92-b6a4-3d8f1e2c9a07:1759381800", "state": "processing", "progress": 0.5, "message": "", "eta_seconds": null, "eta_remaining_seconds": null, "started_at_ms": 1759381800000, "source_duration_seconds": null, "result": null}
2. job_id is export:5b0e8f3a-7c1d-4e92-b6a4-3d8f1e2c9a07:1759381800 and the history already has a get_job answer for it: reply exactly
{"id": "export:5b0e8f3a-7c1d-4e92-b6a4-3d8f1e2c9a07:1759381800", "state": "completed", "progress": 1.0, "message": "export ready · karaoke", "eta_seconds": null, "eta_remaining_seconds": 0, "started_at_ms": 1759381800000, "source_duration_seconds": null, "result": null}
3. Any other job_id (FrameOS reads job ids it has no state for as pending): reply exactly this, with the job_id that was sent in place of JOB_ID
{"id": "JOB_ID", "state": "pending", "progress": 0.0, "message": "", "eta_seconds": null, "eta_remaining_seconds": null, "started_at_ms": null, "source_duration_seconds": null, "result": null}
