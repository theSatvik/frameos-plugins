---
expect:
  gs_path: ["gs://frameos-mock-media/inputs/3f9c2a7e5b1d4c8f9a0e6b2d7c4f1a3e.mp4"]
---
{
  "project": {
    "id": "d2a6f8b4-1c9e-4b57-a3d0-7e4c1f9b2a86",
    "status": "pending",
    "url": "{{input.gs_path}}",
    "filename": "episode-42.mp4",
    "clips_count": 0,
    "progress": 0.0
  },
  "job": {
    "message": "Processing queued",
    "video_id": "d2a6f8b4-1c9e-4b57-a3d0-7e4c1f9b2a86",
    "job_id": "clip:render:d2a6f8b4-1c9e-4b57-a3d0-7e4c1f9b2a86",
    "max_clips": 3,
    "eta_seconds": 1418,
    "source_duration_seconds": 2843.0
  }
}
