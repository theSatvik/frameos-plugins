#!/usr/bin/env bash
# Scaffold for the upload-local-file case: a placeholder "recording" in the run's workspace.
# The bytes do not matter; the PUT cannot reach storage from the eval sandbox anyway.
set -euo pipefail
dd if=/dev/zero of=episode-42.mp4 bs=1024 count=256 2>/dev/null
