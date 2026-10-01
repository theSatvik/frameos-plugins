---
type: llm
---
PASS if the reply tells the user that their FrameOS workspace is out of credits so the clips were not started, points them to https://frameos.studio/pricing to add credits, and does not promise to retry on its own.
FAIL if the reply quotes a money price, a plan allotment, a trial or a discount code; suggests creating another account or any other workaround; or claims that the render started.
