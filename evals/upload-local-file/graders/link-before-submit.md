---
type: regex
target: mock_calls
# submit_uploaded_video must never come before create_upload_link
match: not_contains
---
^(?:(?!create_upload_link)[\s\S])*submit_uploaded_video
