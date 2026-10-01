---
expect:
  job_id: ["thumb:c4e1a9b2-5f3d-4a8e-b6c7-1d0f2e3a4b5c:1759382345678", "thumb:c4e1a9b2-5f3d-4a8e-b6c7-1d0f2e3a4b5c:1758711002345"]
---
{
  "id": "{{input.job_id}}",
  "state": "completed",
  "progress": 1.0,
  "message": "",
  "eta_seconds": 120,
  "eta_remaining_seconds": 0,
  "started_at_ms": 1759382345678,
  "source_duration_seconds": null,
  "result": {
    "thumbnails": [
      {
        "url": "https://mock.frameos.invalid/thumbs/free-plan-1.jpg?Expires=1759424400&Signature=mock",
        "downloadUrl": "https://mock.frameos.invalid/thumbs/free-plan-1.jpg?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Expires=3600&X-Goog-SignedHeaders=host&X-Goog-Signature=mock",
        "template": "headline-left",
        "role": "primary",
        "reason": "Speaker mid-gesture with a clear eye line and space for the headline.",
        "fit_score": 0.86,
        "width": 1080,
        "height": 1920
      },
      {
        "url": "https://mock.frameos.invalid/thumbs/free-plan-2.jpg?Expires=1759424400&Signature=mock",
        "downloadUrl": "https://mock.frameos.invalid/thumbs/free-plan-2.jpg?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Expires=3600&X-Goog-SignedHeaders=host&X-Goog-Signature=mock",
        "template": "headline-bottom",
        "role": "alternate",
        "reason": "Tighter crop on the speaker; headline sits under the face.",
        "fit_score": 0.79,
        "width": 1080,
        "height": 1920
      },
      {
        "url": "https://mock.frameos.invalid/thumbs/free-plan-3.jpg?Expires=1759424400&Signature=mock",
        "downloadUrl": "https://mock.frameos.invalid/thumbs/free-plan-3.jpg?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Expires=3600&X-Goog-SignedHeaders=host&X-Goog-Signature=mock",
        "template": "split",
        "role": "alternate",
        "reason": "Two-shot of host and guest; works as a series cover.",
        "fit_score": 0.71,
        "width": 1080,
        "height": 1920
      }
    ],
    "title": "Why we killed our free plan",
    "hook": {
      "topic": "free plan",
      "kicker": "PRICING",
      "line1": "WE KILLED",
      "line2": "OUR FREE PLAN",
      "rationale": "The clip's strongest claim, short enough to read at phone size.",
      "source": "transcript",
      "template_family": "bold"
    }
  }
}
