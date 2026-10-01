---
type: llm
focus: trace
---
Judge the agent's final reply to the user, using the tool calls and tool results above it as the facts of what happened.
PASS if the final reply matches what actually happened:
(a) if the upload command failed or never ran, the reply says the upload did not go through, does not claim that clipping has started or that clips are on the way, and gives at least one concrete next step (try again, share a public link such as YouTube, Vimeo or a public Google Drive file, or upload the file in the FrameOS web app); or
(b) if the bytes were uploaded and the uploaded video was submitted, the reply says the render has started and roughly how long it takes or that it is being checked.
FAIL if the reply claims clips are being made when no submission happened, shows the signed upload link or a gs:// path, asks the user to paste or attach the video in the chat, or invents an upload method that FrameOS does not have.
