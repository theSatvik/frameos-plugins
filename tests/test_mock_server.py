"""Tests for dev/mock_server.py, the stateful mock FrameOS MCP server.

1. Schema parity: the mock's tools/list (names, parameters, required lists, enums,
   defaults, annotations, descriptions, output schemas) and server instructions
   equal tests/fixtures/mcp-snapshot.json, the snapshot of the real server.
2. Behaviour, driven over the MCP protocol with the SDK's in-memory client
   (JSON-RPC framing, `mode="legacy"`): submit -> poll -> clips -> export, the
   error strings, the caption 409 rules, uploads, thumbnails, posting.
3. Transports: the real entry point over stdio and over Streamable HTTP.

Needs the `mcp` package (2.2.0, the SDK the real server uses). Without it every
test here is skipped, so `python3 scripts/test.py` stays stdlib-only. To run them:

    uv run --with mcp==2.2.0 python -m unittest discover -s tests -p test_mock_server.py
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
import uuid
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parent.parent
MOCK_PATH = REPO / "dev" / "mock_server.py"
SNAPSHOT = json.loads((REPO / "tests" / "fixtures" / "mcp-snapshot.json").read_text(encoding="utf-8"))

try:
    from mcp import Client, StdioServerParameters
except ImportError:  # the stdlib-only CI job has no mcp
    Client = StdioServerParameters = None
    mock = None
else:
    _spec = importlib.util.spec_from_file_location("frameos_mock_server", MOCK_PATH)
    mock = importlib.util.module_from_spec(_spec)
    sys.modules[_spec.name] = mock
    _spec.loader.exec_module(mock)

SKIP_REASON = "needs mcp==2.2.0: uv run --with mcp==2.2.0 python -m unittest discover -s tests -p test_mock_server.py"
TERMINAL = {"completed", "failed", "cancelled"}


def _data(result):
    """The tool's JSON payload: structuredContent.result for list tools, else the text block."""
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict) and "result" in structured:
        return structured["result"]
    return json.loads(result.content[0].text)


def _new_server(**config):
    state = mock.MockState(mock.MockConfig(**config))
    return mock.create_server(state), state


@unittest.skipIf(mock is None, SKIP_REASON)
class SchemaParityTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        server, _ = _new_server()
        async with Client(server, mode="legacy") as client:
            self.server_info = client.server_info
            self.instructions = client.instructions
            tools = (await client.list_tools()).tools
        self.mine = {t.name: t.model_dump(by_alias=True, exclude_none=True, mode="json") for t in tools}
        self.order = [t.name for t in tools]
        self.real = {t["name"]: t for t in SNAPSHOT["tools_list"]["tools"]}

    def test_same_tool_names_in_the_same_order(self):
        self.assertEqual(self.order, [t["name"] for t in SNAPSHOT["tools_list"]["tools"]])
        self.assertEqual(len(self.order), 27)

    def test_input_schemas_match(self):
        for name, real in self.real.items():
            with self.subTest(tool=name):
                mine = self.mine[name]["inputSchema"]
                real_schema = real["inputSchema"]
                self.assertEqual(list(mine.get("properties", {})), list(real_schema.get("properties", {})))
                self.assertEqual(mine.get("required"), real_schema.get("required"))
                for prop, spec in real_schema.get("properties", {}).items():
                    got = mine["properties"][prop]
                    self.assertEqual(got.get("enum"), spec.get("enum"), f"{name}.{prop} enum")
                    self.assertEqual("default" in got, "default" in spec, f"{name}.{prop} has default")
                    self.assertEqual(got.get("default"), spec.get("default"), f"{name}.{prop} default")
                    self.assertEqual(got.get("type"), spec.get("type"), f"{name}.{prop} type")
                    self.assertEqual(got.get("anyOf"), spec.get("anyOf"), f"{name}.{prop} anyOf")
                self.assertEqual(mine, real_schema)

    def test_annotations_descriptions_and_output_schemas_match(self):
        for name, real in self.real.items():
            with self.subTest(tool=name):
                mine = self.mine[name]
                self.assertEqual(mine.get("annotations"), real.get("annotations"))
                self.assertEqual(mine.get("description"), real.get("description"))
                self.assertEqual(mine.get("outputSchema"), real.get("outputSchema"))
                self.assertEqual(mine, real)  # nothing else differs either

    def test_server_identity_and_instructions(self):
        self.assertEqual(self.instructions, SNAPSHOT["initialize"]["instructions"])
        self.assertEqual(self.server_info.name, SNAPSHOT["initialize"]["serverInfo"]["name"])
        self.assertEqual(self.server_info.version, SNAPSHOT["initialize"]["serverInfo"]["version"])


@unittest.skipIf(mock is None, SKIP_REASON)
class FlowTest(unittest.IsolatedAsyncioTestCase):
    async def call(self, client, _tool, **args):
        result = await client.call_tool(_tool, args)
        self.assertFalse(result.is_error, f"{_tool} failed: {result.content[0].text if result.content else ''}")
        return _data(result)

    async def error(self, client, _tool, **args) -> str:
        result = await client.call_tool(_tool, args)
        self.assertTrue(result.is_error, f"{_tool} unexpectedly succeeded: {result.content[0].text}")
        return result.content[0].text

    async def poll(self, client, job_id, tool="get_job", limit=10):
        seen = []
        for _ in range(limit):
            view = await self.call(client, tool, job_id=job_id)
            seen.append(view)
            if view["state"] in TERMINAL:
                return seen
        self.fail(f"{job_id} never finished: {seen[-1]}")

    async def put(self, upload_url, data):
        request = urllib.request.Request(upload_url, data=data, method="PUT", headers={"Content-Type": "video/mp4"})
        status = await asyncio.to_thread(lambda: urllib.request.urlopen(request, timeout=5).status)
        self.assertEqual(status, 200)

    async def submit_and_finish(self, client, url="https://www.youtube.com/watch?v=mockFlow01", **args):
        submitted = await self.call(client, "submit_video", source_url=url, **args)
        await self.poll(client, submitted["job"]["job_id"])
        return submitted, await self.call(client, "list_clips", project_id=submitted["project"]["id"])

    async def test_clip_export_flow(self):
        server, state = _new_server(credits=120)
        async with Client(server, mode="legacy") as client:
            me = await self.call(client, "whoami")
            self.assertEqual(set(me), {"user_id", "organization_id", "organization_name", "account"})
            self.assertEqual(set(me["account"]), {"plan", "credits", "paid_credits", "trial_credits",
                                                  "trial_credits_expires_at", "trial_credits_expired"})
            self.assertEqual(me["account"]["credits"], 120)

            submitted = await self.call(client, "submit_video",
                                        source_url="https://www.youtube.com/watch?v=mockFlow01",
                                        max_clips=3, aspect_ratio="9:16")
            project, job = submitted["project"], submitted["job"]
            self.assertEqual(set(project), {"id", "status", "url", "filename", "clips_count", "progress"})
            self.assertEqual(project["status"], "pending")
            self.assertEqual(job["job_id"], f"clip:render:{project['id']}")
            self.assertEqual(job["message"], "Processing queued")
            self.assertIsNone(job["eta_seconds"])  # YouTube: unknown until the worker measures the source

            seen = await self.poll(client, job["job_id"])
            self.assertEqual(len(seen), 3)  # default fast mode completes on the third poll
            self.assertEqual(set(seen[0]), {"id", "state", "progress", "message", "eta_seconds",
                                            "eta_remaining_seconds", "started_at_ms",
                                            "source_duration_seconds", "result"})
            self.assertEqual(seen[0]["message"], "transcribing")
            self.assertIsInstance(seen[0]["eta_seconds"], int)
            self.assertTrue(all(0.0 <= v["progress"] <= 1.0 for v in seen))
            self.assertEqual(seen[-1]["state"], "completed")
            self.assertEqual(seen[-1]["message"], "3 clips ready")
            self.assertEqual(seen[-1]["eta_remaining_seconds"], 0)
            self.assertIsNone(seen[-1]["result"])  # render jobs carry no result; read list_clips

            listed = await self.call(client, "list_projects")
            self.assertEqual(listed[0]["id"], project["id"])
            self.assertEqual(listed[0]["progress"], 100)  # 0-100 here, 0-1 everywhere else
            self.assertEqual((await self.call(client, "get_project", project_id=project["id"]))["progress"], 1.0)

            clips = await self.call(client, "list_clips", project_id=project["id"])
            self.assertEqual(len(clips), 3)
            self.assertEqual([c["rank"] for c in clips], [0, 1, 2])
            first = clips[0]
            for c in clips:
                self.assertTrue(0.0 <= c["score"] <= 1.0)
                self.assertLess(c["startTime"], c["endTime"])
                self.assertEqual(c["startTimeMs"], int(round(c["startTime"] * 1000)))
                self.assertEqual((c["captionMode"], c["captionStyle"]), ("overlay", "shorts_default"))
                self.assertTrue(c["exportRequired"])
                self.assertIsNone(c["downloadUrl"])
                self.assertTrue(c["previewUrl"].startswith("https://mock.frameos.invalid/"))
                self.assertEqual(c["aspectRatio"], "9:16")
                self.assertEqual(c["title"], c["hook"])
            spent = 120 - (await self.call(client, "whoami"))["account"]["credits"]
            self.assertEqual(spent, -(-state.projects[project["id"]].sim_duration // 60))

            rendering = await self.call(client, "export_clip", clip_id=first["id"])
            self.assertEqual(rendering["status"], "rendering")
            self.assertEqual(rendering["style"], "karaoke")  # shorts_default resolves to karaoke
            self.assertTrue(rendering["job_id"].startswith(f"export:{first['id']}:"))
            export_job = await self.poll(client, rendering["job_id"])
            self.assertEqual(export_job[-1]["message"], "export ready · karaoke")
            ready = await self.call(client, "export_clip", clip_id=first["id"])
            self.assertEqual(ready["status"], "ready")
            self.assertTrue(ready["url"].startswith("https://mock.frameos.invalid/"))
            self.assertIn("attachment", ready["url"])

            text = await self.error(client, "set_caption_style", clip_id=first["id"], style="mrbeast")
            self.assertIn("FrameOS returned HTTP 422: Unknown caption style: mrbeast", text)
            text = await self.error(client, "set_caption_style", clip_id=first["id"], style="beasty",
                                    appearance={"font": "Comic Sans"})
            self.assertIn("FrameOS returned HTTP 422: Unknown caption font: Comic Sans", text)

    async def test_out_of_credits_returns_402(self):
        state = mock.MockState(mock.MockConfig.from_env({"FRAMEOS_MOCK_CREDITS": "0"}))
        async with Client(mock.create_server(state), mode="legacy") as client:
            self.assertEqual((await self.call(client, "whoami"))["account"]["credits"], 0)
            text = await self.error(client, "submit_video", source_url="https://www.youtube.com/watch?v=broke1")
            self.assertIn("FrameOS returned HTTP 402: Out of credits. Upgrade your plan or add credits to keep "
                          "processing.", text)
            # The row made before the credit check is failed with the reason at once
            # (mcp_routes._settle_refused_row), not left pending for the 30-minute reaper.
            refused = (await self.call(client, "list_projects"))[0]
            self.assertEqual((refused["status"], refused["clipCount"]), ("failed", 0))
            self.assertEqual(refused["errorMessage"], "Out of credits. Upgrade your plan or add credits to keep "
                                                      "processing. (insufficient_credits)")
            view = await self.call(client, "get_job", job_id=f"clip:render:{refused['id']}")
            self.assertEqual((view["state"], view["message"]), ("pending", ""))  # no job was queued
            # Thumbnails need 10 credits each.
            text = await self.error(client, "create_thumbnail_job", url="https://example.com/v.mp4")
            self.assertIn("FrameOS returned HTTP 402: Out of credits. Thumbnails cost 10 credits each", text)

    async def test_real_error_strings(self):
        server, _ = _new_server()
        async with Client(server, mode="legacy") as client:
            text = await self.error(client, "submit_video", source_url="https://vimeo.com/too-short-clip")
            self.assertIn("FrameOS returned HTTP 422: This video is only 12 seconds long, which is too short to "
                          "pull a highlight out of. FrameOS needs at least 30 seconds of video to work with.", text)
            failed = (await self.call(client, "list_projects"))[0]
            self.assertEqual(failed["status"], "failed")
            self.assertTrue(failed["errorMessage"].endswith("(source_too_short)"))

            missing = str(uuid.uuid4())
            self.assertIn("FrameOS returned HTTP 404: Video not found",
                          await self.error(client, "get_project", project_id=missing))
            self.assertIn("FrameOS returned HTTP 404: Clip not found",
                          await self.error(client, "describe_clip", clip_id=missing))
            self.assertIn("FrameOS returned HTTP 404: Job not found",
                          await self.error(client, "get_job", job_id=f"clip:render:{missing}"))
            text = await self.error(client, "get_project", project_id="not-a-uuid")
            self.assertIn("FrameOS returned HTTP 422: [{'type': 'uuid_parsing', 'loc': ['path', 'project_id']", text)
            text = await self.error(client, "submit_video", source_url="https://youtu.be/x", max_clips=25)
            self.assertIn("FrameOS returned HTTP 422: [{'type': 'less_than_equal', 'loc': ['body', 'max_clips']", text)
            text = await self.error(client, "list_projects", limit=51)
            self.assertIn("'loc': ['query', 'limit']", text)
            text = await self.error(client, "create_collection", name="   ")
            self.assertIn("Collection name cannot be blank", text)

    async def test_resubmitting_a_link(self):
        server, state = _new_server(credits=500)
        url = "https://www.youtube.com/watch?v=again01"
        async with Client(server, mode="legacy") as client:
            first = await self.call(client, "submit_video", source_url=url, max_clips=2)
            running = await self.call(client, "submit_video", source_url=url, max_clips=9)
            self.assertEqual(running["job"], {"job_id": first["job"]["job_id"], "status": "already_running"})
            self.assertEqual(running["project"]["id"], first["project"]["id"])
            await self.poll(client, first["job"]["job_id"])
            cost = -(-state.projects[first["project"]["id"]].sim_duration // 60)
            self.assertEqual((await self.call(client, "whoami"))["account"]["credits"], 500 - cost)
            # A completed link starts a NEW project, and the paid-minutes ledger is per project.
            second = await self.call(client, "submit_video", source_url=url)
            self.assertNotEqual(second["project"]["id"], first["project"]["id"])
            await self.poll(client, second["job"]["job_id"])
            self.assertEqual((await self.call(client, "whoami"))["account"]["credits"], 500 - 2 * cost)

    async def test_caption_409_rules_and_legacy_clips(self):
        server, state = _new_server()
        async with Client(server, mode="legacy") as client:
            legacy = next(p for p in await self.call(client, "list_projects") if p["status"] == "completed")
            clips = await self.call(client, "list_clips", project_id=legacy["id"])
            # A clip an earlier run left behind (soft-deleted) is not listed or counted anywhere.
            self.assertEqual(len(clips), 2)
            self.assertEqual((await self.call(client, "get_project", project_id=legacy["id"]))["clips_count"], 2)
            self.assertEqual(legacy["clipCount"], 2)
            replaced = [c for c in state.clips.values() if c.video_id == legacy["id"] and c.deleted]
            self.assertEqual(len(replaced), 1)
            self.assertNotIn(replaced[0].id, {c["id"] for c in clips})
            self.assertIn("HTTP 404: Clip not found", await self.error(client, "describe_clip", clip_id=replaced[0].id))
            burned = [c for c in clips if c["captionMode"] == "burned"]
            self.assertEqual(len(burned), 2)
            self.assertFalse(burned[0]["exportRequired"])
            self.assertIsNotNone(burned[0]["downloadUrl"])
            self.assertIn("HTTP 404: Source transcript unavailable for this project",
                          await self.error(client, "get_transcript", project_id=legacy["id"]))

            live = clips[0]
            text = await self.error(client, "set_caption_style", clip_id=live["id"], style="beasty")
            self.assertIn("FrameOS returned HTTP 409: This clip has burned-in captions — use POST "
                          "/clips/{id}/recaption.", text)
            ready = await self.call(client, "export_clip", clip_id=live["id"])
            self.assertEqual(ready["status"], "ready")  # burned clips are already final

            # recaption_clip checks the style against the catalogue first (422), like set_caption_style.
            self.assertIn("FrameOS returned HTTP 422: Unknown caption style: mrbeast",
                          await self.error(client, "recaption_clip", clip_id=live["id"], style="mrbeast"))
            self.assertIn("HTTP 422: Unknown caption style: mrbeast",
                          await self.error(client, "recaption_clip", clip_id=str(uuid.uuid4()), style="mrbeast"))
            recap = await self.call(client, "recaption_clip", clip_id=live["id"], style="Bounce")
            self.assertEqual(recap["style"], "beasty")  # the canonical id, not what was sent
            self.assertTrue(recap["job_id"].startswith(f"recap:{live['id']}:"))
            done = await self.poll(client, recap["job_id"])
            self.assertEqual(done[-1]["message"], "re-captioned · beasty")
            after = await self.call(client, "describe_clip", clip_id=live["id"])
            self.assertEqual((after["captionMode"], after["captionStyle"]), ("overlay", "beasty"))
            self.assertNotEqual(after["url"].split("?")[0], live["url"].split("?")[0])
            self.assertEqual(after["layout"], {})

            _, fresh = await self.submit_and_finish(client)
            text = await self.error(client, "recaption_clip", clip_id=fresh[0]["id"], style="beasty")
            self.assertIn("FrameOS returned HTTP 409: This clip uses overlay captions — set the style via PATCH "
                          "/clips/{id}/captions (instant); burning happens on export.", text)
            saved = await self.call(client, "set_caption_style", clip_id=fresh[0]["id"], style="BOUNCE",
                                    appearance={"font": "Anton", "scale": 1.234, "yPct": 0.2, "unknown": 1})
            self.assertEqual(saved, {"clip_id": fresh[0]["id"], "mode": "overlay", "style": "beasty",
                                     "appearance": {"font": "Anton", "scale": 1.23, "yPct": 0.2}})
            cleared = await self.call(client, "set_caption_style", clip_id=fresh[0]["id"], style="beasty")
            self.assertIsNone(cleared["appearance"])  # omitting appearance clears saved overrides

    async def test_posting_needs_the_saved_style_exported_first(self):
        server, state = _new_server()
        async with Client(server, mode="legacy") as client:
            _, clips = await self.submit_and_finish(client)
            clip = clips[0]
            accounts = await self.call(client, "list_social_accounts")
            self.assertEqual({a["platform"] for a in accounts}, {"youtube", "instagram", "linkedin", "facebook"})
            youtube = next(a for a in accounts if a["platform"] == "youtube")
            self.assertEqual(set(youtube), {"id", "platform", "accountRef", "displayName", "avatarUrl", "status",
                                            "connectedAt"})

            draft = await self.call(client, "generate_social_copy", clip_id=clip["id"], platform="tiktok")
            self.assertEqual(set(draft), {"clip_id", "platform", "title", "caption", "hashtags", "posted"})
            self.assertFalse(draft["posted"])
            self.assertLessEqual(len(draft["hashtags"]), 10)

            await self.call(client, "set_caption_style", clip_id=clip["id"], style="beasty")
            text = await self.error(client, "post_clip", clip_id=clip["id"], account_id=youtube["id"])
            self.assertIn("FrameOS returned HTTP 409: Captions for this clip aren't rendered yet. Export the clip "
                          "first, then post.", text)
            self.assertEqual(state.posts, [])

            rendering = await self.call(client, "export_clip", clip_id=clip["id"])
            await self.poll(client, rendering["job_id"])
            posted = await self.call(client, "post_clip", clip_id=clip["id"], account_id=youtube["id"],
                                     title="We tripled the price", privacy="unlisted")
            self.assertEqual((posted["platform"], posted["account"]), ("youtube", youtube["displayName"]))
            self.assertTrue(posted["job_id"].startswith(f"social:post:{clip['id']}:"))
            done = await self.poll(client, posted["job_id"])
            self.assertEqual(done[-1]["state"], "completed")
            self.assertTrue(done[-1]["message"].startswith("https://mock.frameos.invalid/posts/youtube/shorts/"))
            self.assertEqual(len(state.posts), 1)

            self.assertIn("HTTP 404: Social account not found",
                          await self.error(client, "post_clip", clip_id=clip["id"], account_id=str(uuid.uuid4())))

    async def test_a_blank_post_title_uses_the_clips_own_title(self):
        server, state = _new_server()
        async with Client(server, mode="legacy") as client:
            _, clips = await self.submit_and_finish(client)
            clip = clips[0]
            await self.poll(client, (await self.call(client, "export_clip", clip_id=clip["id"]))["job_id"])
            accounts = {a["platform"]: a for a in await self.call(client, "list_social_accounts")}

            job = await self.call(client, "post_clip", clip_id=clip["id"], account_id=accounts["youtube"]["id"],
                                  title="   ", description="Second line\nmore")
            await self.poll(client, job["job_id"])
            youtube = state.posts[-1]
            self.assertEqual(youtube["title"], clip["title"])  # never the word "Clip"
            self.assertNotEqual(youtube["title"], "Clip")

            # Instagram and LinkedIn post one text built only from what was sent.
            job = await self.call(client, "post_clip", clip_id=clip["id"], account_id=accounts["instagram"]["id"],
                                  description="The whole caption, hashtags and all. #pricing")
            await self.poll(client, job["job_id"])
            self.assertEqual(state.posts[-1]["body"], "The whole caption, hashtags and all. #pricing")
            job = await self.call(client, "post_clip", clip_id=clip["id"], account_id=accounts["linkedin"]["id"],
                                  title="Opening line", description="The rest.")
            await self.poll(client, job["job_id"])
            self.assertEqual(state.posts[-1]["body"], "Opening line\n\nThe rest.")
            self.assertEqual(state.posts[-1]["title"], "Opening line")

    async def test_export_while_rendering_returns_the_same_job(self):
        server, _ = _new_server()
        async with Client(server, mode="legacy") as client:
            _, clips = await self.submit_and_finish(client)
            clip = clips[0]
            first = await self.call(client, "export_clip", clip_id=clip["id"])
            again = await self.call(client, "export_clip", clip_id=clip["id"], filename="other-name")
            self.assertEqual(again, first)  # no second burn of the same artifact
            await self.poll(client, first["job_id"])
            self.assertEqual((await self.call(client, "export_clip", clip_id=clip["id"]))["status"], "ready")
            # A new look is a new artifact, so it gets a burn of its own.
            await self.call(client, "set_caption_style", clip_id=clip["id"], style="beasty")
            restyled = await self.call(client, "export_clip", clip_id=clip["id"])
            self.assertEqual((restyled["status"], restyled["style"]), ("rendering", "beasty"))
            self.assertEqual(restyled, await self.call(client, "export_clip", clip_id=clip["id"]))

    async def test_collection_export_keeps_ten_rendering_per_call(self):
        server, _ = _new_server(credits=5000)
        async with Client(server, mode="legacy") as client:
            made = await self.call(client, "create_collection", name="Big pack")
            ids = []
            n = 0
            while len(ids) < 12:
                _, clips = await self.submit_and_finish(client, url=f"https://www.youtube.com/watch?v=batch{n}",
                                                        max_clips=5)
                ids += [c["id"] for c in clips]
                n += 1
            for clip_id in ids[:12]:
                await self.call(client, "add_clip_to_collection", collection_id=made["id"], clip_id=clip_id)

            first = await self.call(client, "export_collection", collection_id=made["id"])
            statuses = [c["status"] for c in first["clips"]]
            self.assertEqual(statuses, ["rendering"] * 10 + ["not_started"] * 2)
            self.assertEqual(first["not_started"], 2)
            waiting = first["clips"][10]
            self.assertEqual(set(waiting), {"clip_id", "status", "style", "reason"})
            self.assertEqual(waiting["reason"], "Not started yet, to keep this call short. Call export_collection "
                                                "again after the rendering clips finish.")
            # Calling again while they render starts nothing new: same jobs, same two waiting.
            second = await self.call(client, "export_collection", collection_id=made["id"])
            self.assertEqual([c.get("job_id") for c in second["clips"]], [c.get("job_id") for c in first["clips"]])
            self.assertEqual(second["not_started"], 2)

            for entry in first["clips"][:10]:
                await self.poll(client, entry["job_id"])
            third = await self.call(client, "export_collection", collection_id=made["id"])
            self.assertEqual([c["status"] for c in third["clips"]], ["ready"] * 10 + ["rendering"] * 2)
            self.assertEqual(third["not_started"], 0)
            for entry in third["clips"][10:]:
                await self.poll(client, entry["job_id"])
            last = await self.call(client, "export_collection", collection_id=made["id"])
            self.assertEqual([c["status"] for c in last["clips"]], ["ready"] * 12)

    async def test_thumbnail_inputs(self):
        server, state = _new_server(credits=500)
        async with Client(server, mode="legacy") as client:
            _, clips = await self.submit_and_finish(client)
            clip_id = clips[0]["id"]
            for bad in (0, -2):
                text = await self.error(client, "create_thumbnail_job", clip_id=clip_id, max_thumbnails=bad)
                self.assertIn("FrameOS returned HTTP 422: [{'type': 'greater_than_equal', "
                              "'loc': ['body', 'max_thumbnails']", text)
            # Body validation comes first, before the link checks.
            text = await self.error(client, "create_thumbnail_job", url="gs://x/y.mp4", max_thumbnails=0)
            self.assertIn("'loc': ['body', 'max_thumbnails']", text)

            url_message = ("FrameOS returned HTTP 422: url must be a public http(s) video link. Use clip_id or "
                           "video_id for media in this workspace.")
            for bad in (f"gs://{mock.BUCKET}/inputs/a.mp4", "  gs://other/b.mp4", "/Users/me/episode.mp4",
                        "file:///tmp/a.mp4", "http://localhost:8000/v.mp4", "http://169.254.169.254/latest",
                        "http://10.0.0.7/v.mp4", "http://[::1]/v.mp4", "http://metadata.google.internal/x",
                        "HTTPS://example.com/v.mp4"):
                with self.subTest(url=bad):
                    self.assertIn(url_message, await self.error(client, "create_thumbnail_job", url=bad))
            for bad in ("gs://bucket/ref.png", "file:///tmp/ref.png", "https://localhost/ref.png", "ref.png"):
                with self.subTest(style_ref=bad):
                    self.assertIn("FrameOS returned HTTP 422: style_ref must be a public http(s) image link.",
                                  await self.error(client, "create_thumbnail_job", clip_id=clip_id, style_ref=bad))
            self.assertEqual(state.thumbnails, [])

            # More than 3 makes 3; a public style reference is used.
            before = (await self.call(client, "whoami"))["account"]["credits"]
            created = await self.call(client, "create_thumbnail_job", clip_id=clip_id, max_thumbnails=7,
                                      style_ref=" https://i.ytimg.com/vi/abc/maxresdefault.jpg ")
            done = await self.poll(client, created["jobId"], tool="get_thumbnail_job")
            self.assertIn("matching your style", [st.message for st in state.jobs[created["jobId"]].stages])
            self.assertEqual(len(done[-1]["result"]["thumbnails"]), 3)
            self.assertEqual(before - (await self.call(client, "whoami"))["account"]["credits"], 30)
            one = await self.call(client, "create_thumbnail_job", url="https://www.youtube.com/watch?v=abc",
                                  max_thumbnails=1)
            done = await self.poll(client, one["jobId"], tool="get_thumbnail_job")
            self.assertEqual(len(done[-1]["result"]["thumbnails"]), 1)

    async def test_focus_prompt_limits(self):
        server, state = _new_server(credits=500)
        receiver = mock.start_upload_receiver(state)
        self.addCleanup(receiver.server_close)
        self.addCleanup(receiver.shutdown)
        async with Client(server, mode="legacy") as client:
            focus = "pricing,   price " * 58 + "x" * 14  # 1000 characters, with runs of spaces
            self.assertEqual(len(focus), 1000)
            submitted = await self.call(client, "submit_video", source_url="https://www.youtube.com/watch?v=f1000",
                                        focus_prompt=focus)
            kept = state.projects[submitted["project"]["id"]].focus_prompt
            self.assertEqual(kept, " ".join(focus.split())[:400])  # whitespace collapsed, first 400 used
            for tool, args in (("submit_video", {"source_url": "https://www.youtube.com/watch?v=f1001"}),
                               ("submit_uploaded_video", {"gs_path": f"gs://{mock.BUCKET}/inputs/x.mp4"})):
                with self.subTest(tool=tool):
                    text = await self.error(client, tool, focus_prompt="a" * 1001, **args)
                    self.assertIn("FrameOS returned HTTP 422: [{'type': 'string_too_long', "
                                  "'loc': ['body', 'focus_prompt']", text)
            link = await self.call(client, "create_upload_link", filename="talk.mp4")
            await self.put(link["upload_url"], b"\0" * 64)
            started = await self.call(client, "submit_uploaded_video", gs_path=link["gs_path"], focus_prompt=focus)
            self.assertEqual(state.projects[started["project"]["id"]].focus_prompt, kept)

    async def test_private_and_internal_links_are_refused_at_submit(self):
        server, state = _new_server()
        async with Client(server, mode="legacy") as client:
            before = len(state.projects)
            for bad in ("http://localhost:8000/v.mp4", "http://192.168.1.4/v.mp4", "https://metadata/computeMetadata"):
                with self.subTest(url=bad):
                    self.assertIn("FrameOS returned HTTP 400: Paste a public video link (http:// or https://), "
                                  "or upload the file.", await self.error(client, "submit_video", source_url=bad))
            self.assertEqual(len(state.projects), before)  # refused before any project is made

    async def test_upload_flow(self):
        server, state = _new_server()
        receiver = mock.start_upload_receiver(state)
        self.addCleanup(receiver.server_close)
        self.addCleanup(receiver.shutdown)
        async with Client(server, mode="legacy") as client:
            org = (await self.call(client, "whoami"))["organization_id"]
            link = await self.call(client, "create_upload_link", filename="Episode 12.mov")
            # gs://<bucket>/inputs/<workspace id>/<hex>.<ext>
            self.assertRegex(link["gs_path"], rf"^gs://{mock.BUCKET}/inputs/{org}/[0-9a-f]{{32}}\.mov$")
            odd = await self.call(client, "create_upload_link", filename="take two.M P4!")
            self.assertTrue(odd["gs_path"].endswith(".mp4"))  # the extension keeps [a-z0-9] only
            self.assertIn("HTTP 409: Video upload has not completed",
                          await self.error(client, "submit_uploaded_video", gs_path=link["gs_path"]))
            await self.put(link["upload_url"], b"\0" * 4096)
            started = await self.call(client, "submit_uploaded_video", gs_path=link["gs_path"])
            self.assertEqual(started["project"]["filename"], "Episode 12.mov")
            # The API cannot measure an upload, so there is no length or ETA at submit.
            self.assertIsNone(started["job"]["eta_seconds"])
            self.assertIsNone(started["job"]["source_duration_seconds"])
            # The claim is spent, but the path is in this workspace's folder: a resubmit
            # while it renders is answered with the running job, not a 404.
            again = await self.call(client, "submit_uploaded_video", gs_path=link["gs_path"])
            self.assertEqual(again["job"], {"job_id": started["job"]["job_id"], "status": "already_running"})
            self.assertIn("HTTP 422: Invalid uploaded video path",
                          await self.error(client, "submit_uploaded_video", gs_path="gs://elsewhere/inputs/a.mp4"))
            self.assertIn("HTTP 404: Upload link was not issued to this workspace or expired",
                          await self.error(client, "submit_uploaded_video",
                                           gs_path=f"gs://{mock.BUCKET}/inputs/{uuid.uuid4()}/a.mp4"))
            self.assertIn("HTTP 409: Video upload has not completed",
                          await self.error(client, "submit_uploaded_video",
                                           gs_path=f"gs://{mock.BUCKET}/inputs/{org}/{uuid.uuid4().hex}.mp4"))
            await self.poll(client, started["job"]["job_id"])
            # A successful render deletes the uploaded source.
            self.assertIn("HTTP 409: Video upload has not completed",
                          await self.error(client, "submit_uploaded_video", gs_path=link["gs_path"]))
            # The uploaded source is deleted after a successful render, so a
            # thumbnail job from the project (video_id) fails; clip_id works.
            thumb = await self.call(client, "create_thumbnail_job", video_id=started["project"]["id"])
            failed = await self.poll(client, thumb["jobId"], tool="get_thumbnail_job")
            self.assertEqual(failed[-1]["state"], "failed")

    async def test_thumbnails_cost_and_shape(self):
        server, _ = _new_server(credits=200)
        async with Client(server, mode="legacy") as client:
            _, clips = await self.submit_and_finish(client)
            before = (await self.call(client, "whoami"))["account"]["credits"]
            created = await self.call(client, "create_thumbnail_job", clip_id=clips[0]["id"], aspect="16:9")
            self.assertEqual(set(created), {"jobId", "status"})  # camelCase jobId, unlike every other job
            self.assertEqual(created["status"], "queued")
            done = await self.poll(client, created["jobId"], tool="get_thumbnail_job")
            result = done[-1]["result"]
            self.assertEqual(len(result["thumbnails"]), 3)
            self.assertEqual({(t["width"], t["height"]) for t in result["thumbnails"]}, {(1280, 720)})
            self.assertEqual(set(result["hook"]), {"topic", "kicker", "line1", "line2", "rationale", "source",
                                                   "template_family"})
            after = (await self.call(client, "whoami"))["account"]["credits"]
            self.assertEqual(before - after, 30)
            listed = await self.call(client, "list_thumbnails", limit=5)
            self.assertEqual(len(listed), 3)
            self.assertEqual(listed[0]["jobId"], created["jobId"])
            self.assertIn("HTTP 422: Provide clip_id, video_id, or url, not more than one",
                          await self.error(client, "create_thumbnail_job", clip_id=clips[0]["id"],
                                           url="https://example.com/v.mp4"))

    async def test_collections(self):
        server, _ = _new_server()
        async with Client(server, mode="legacy") as client:
            _, clips = await self.submit_and_finish(client)
            made = await self.call(client, "create_collection", name="Ep 75 pack")
            self.assertEqual(made["clip_count"], 0)
            self.assertIn("HTTP 409: A collection with that name already exists",
                          await self.error(client, "create_collection", name="Ep 75 pack"))
            first = await self.call(client, "add_clip_to_collection", collection_id=made["id"], clip_id=clips[0]["id"])
            again = await self.call(client, "add_clip_to_collection", collection_id=made["id"], clip_id=clips[0]["id"])
            self.assertEqual((first["added"], again["added"]), (True, False))
            await self.call(client, "add_clip_to_collection", collection_id=made["id"], clip_id=clips[1]["id"])
            self.assertEqual((await self.call(client, "list_collections"))[0]["clip_count"], 2)
            exported = await self.call(client, "export_collection", collection_id=made["id"])
            self.assertEqual(set(exported), {"collection_id", "clips", "not_started"})
            self.assertEqual([c["status"] for c in exported["clips"]], ["rendering", "rendering"])
            self.assertEqual(exported["not_started"], 0)
            copy = await self.call(client, "duplicate_clip", clip_id=clips[0]["id"])
            self.assertTrue(copy["title"].endswith("(Copy)"))
            self.assertEqual(copy["rank"], 3)

    async def test_transcript_takes_milliseconds_and_returns_seconds(self):
        server, _ = _new_server()
        async with Client(server, mode="legacy") as client:
            submitted, clips = await self.submit_and_finish(client)
            clip = clips[0]
            page = await self.call(client, "get_transcript", project_id=submitted["project"]["id"],
                                   start_ms=clip["startTimeMs"], end_ms=clip["endTimeMs"], include_words=True)
            self.assertGreater(page["total"], 0)
            segment = page["segments"][0]
            self.assertLessEqual(segment["start"], clip["endTime"])  # seconds, not milliseconds
            self.assertGreaterEqual(segment["end"], clip["startTime"])
            self.assertIn("words", segment)
            self.assertIn("HTTP 422: end_ms must be greater than start_ms",
                          await self.error(client, "get_transcript", project_id=submitted["project"]["id"],
                                           start_ms=5000, end_ms=5000))

    async def test_focus_prompt_steers_the_top_clip(self):
        server, _ = _new_server()
        async with Client(server, mode="legacy") as client:
            _, clips = await self.submit_and_finish(client, url="https://www.youtube.com/watch?v=focus1",
                                                    focus_prompt="the newsletter part")
            self.assertIn("newsletter", clips[0]["transcript"].lower())
            self.assertEqual(clips, sorted(clips, key=lambda c: -c["score"]))

    async def test_opaque_error_mode_reproduces_the_legacy_bare_error(self):
        """Legacy option: the bare error the real server showed before it switched to ToolError."""
        server, _ = _new_server(credits=0, errors="opaque")
        async with Client(server, mode="legacy") as client:
            with self.assertLogs("mcp.server.mcpserver.server", level="ERROR"):  # the SDK logs the crash
                text = await self.error(client, "submit_video", source_url="https://www.youtube.com/watch?v=x1")
            self.assertEqual(text, "Error executing tool submit_video")

    async def test_wall_clock_speed(self):
        now = [1_000_000.0]
        state = mock.MockState(mock.MockConfig(speed=60.0), clock=lambda: now[0])
        async with Client(mock.create_server(state), mode="legacy") as client:
            job_id = (await self.call(client, "submit_video", source_url="https://vimeo.com/123456"))["job"]["job_id"]
            for _ in range(3):  # polling alone does not move a wall-clock job
                self.assertEqual((await self.call(client, "get_job", job_id=job_id))["state"], "pending")
            now[0] += 61
            self.assertEqual((await self.call(client, "get_job", job_id=job_id))["state"], "completed")
            project_id = job_id.rsplit(":", 1)[-1]
            clip = (await self.call(client, "list_clips", project_id=project_id))[0]
            self.assertEqual((await self.call(client, "export_clip", clip_id=clip["id"]))["status"], "rendering")
            now[0] += 16  # an export takes a quarter of a render; no get_job poll needed in this mode
            self.assertEqual((await self.call(client, "export_clip", clip_id=clip["id"]))["status"], "ready")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@unittest.skipIf(mock is None, SKIP_REASON)
class GuardrailTest(unittest.IsolatedAsyncioTestCase):
    """Launch guardrails agreed on 2026-10-02: balance covers the video, at most 3 renders at once."""

    call, error, poll, put = FlowTest.call, FlowTest.error, FlowTest.poll, FlowTest.put

    @staticmethod
    def needed(url):
        return -(-int(mock.MockState._sim_duration(url)) // 60)

    async def test_three_renders_at_once_then_429(self):
        server, _ = _new_server(credits=1000)
        async with Client(server, mode="legacy") as client:
            jobs = []
            for i in range(3):
                submitted = await self.call(client, "submit_video", source_url=f"https://www.youtube.com/watch?v=cap{i}")
                jobs.append(submitted["job"]["job_id"])
            text = await self.error(client, "submit_video", source_url="https://www.youtube.com/watch?v=cap3")
            self.assertIn("FrameOS returned HTTP 429: 3 videos are already processing in this workspace (limit 3). "
                          "Wait for one to finish, then submit again.", text)
            # Re-submitting a link that is already rendering is still answered, not refused.
            again = await self.call(client, "submit_video", source_url="https://www.youtube.com/watch?v=cap0")
            self.assertEqual(again["job"]["status"], "already_running")
            await self.poll(client, jobs[0])
            await self.call(client, "submit_video", source_url="https://www.youtube.com/watch?v=cap3")

    async def test_stray_rows_from_a_failed_start_do_not_count(self):
        server, state = _new_server(credits=0)
        async with Client(server, mode="legacy") as client:
            for i in range(4):
                text = await self.error(client, "submit_video", source_url=f"https://www.youtube.com/watch?v=stray{i}")
                self.assertIn("HTTP 402: Out of credits", text)
            refused = [p for p in state.projects.values() if p.source.endswith(tuple(f"stray{i}" for i in range(4)))]
            self.assertEqual({p.status for p in refused}, {"failed"})

    async def test_known_length_must_be_covered_at_submit(self):
        server, state = _new_server(credits=5)
        async with Client(server, mode="legacy") as client:
            text = await self.error(client, "submit_video", source_url="https://vimeo.com/76979871")
            project = next(p for p in state.projects.values() if p.source.endswith("76979871"))
            needed = -(-int(project.sim_duration) // 60)
            message = (f"This video is {needed} minutes long and needs {needed} credits, but your workspace "
                       f"has 5. Add credits or use a shorter video.")
            self.assertIn(f"FrameOS returned HTTP 402: {message}", text)
            self.assertEqual((await self.call(client, "whoami"))["account"]["credits"], 5)
            # The refused row is failed with that reason, not left pending.
            row = next(p for p in await self.call(client, "list_projects") if p["id"] == project.id)
            self.assertEqual((row["status"], row["errorMessage"]), ("failed", f"{message} (insufficient_credits)"))

    async def test_unknown_length_fails_after_download_without_charge(self):
        server, state = _new_server(credits=5)
        async with Client(server, mode="legacy") as client:
            submitted = await self.call(client, "submit_video", source_url="https://www.youtube.com/watch?v=long01")
            seen = await self.poll(client, submitted["job"]["job_id"])
            self.assertEqual(seen[-1]["state"], "failed")
            self.assertTrue(seen[-1]["message"].endswith("Nothing was charged. (insufficient_credits)"))
            self.assertIn("but your workspace has 5.", seen[-1]["message"])
            self.assertNotIn("transcribing", [v["message"] for v in seen])
            listed = (await self.call(client, "list_projects"))[0]
            self.assertTrue(listed["errorMessage"].endswith("(insufficient_credits)"))
            self.assertEqual((await self.call(client, "whoami"))["account"]["credits"], 5)
            # The worker saved the length it measured, so a resubmit is refused at submit.
            text = await self.error(client, "submit_video", source_url="https://www.youtube.com/watch?v=long01")
            self.assertIn("FrameOS returned HTTP 402: This video is", text)
            self.assertIn("Add credits or use a shorter video.", text)
            listed = (await self.call(client, "list_projects"))[0]
            self.assertEqual(listed["id"], submitted["project"]["id"])  # the same row, failed again
            self.assertEqual(listed["status"], "failed")
            self.assertTrue(listed["errorMessage"].endswith("Add credits or use a shorter video. (insufficient_credits)"))

    async def test_uploads_are_checked_after_download_not_at_submit(self):
        server, state = _new_server(credits=5)
        receiver = mock.start_upload_receiver(state)
        self.addCleanup(receiver.server_close)
        self.addCleanup(receiver.shutdown)
        async with Client(server, mode="legacy") as client:
            link = await self.call(client, "create_upload_link", filename="long-episode.mp4")
            await self.put(link["upload_url"], b"\0" * 128)
            submitted = await self.call(client, "submit_uploaded_video", gs_path=link["gs_path"])  # no 402 here
            project = state.projects[submitted["project"]["id"]]
            needed = -(-int(project.sim_duration) // 60)
            self.assertGreater(needed, 5)
            seen = await self.poll(client, submitted["job"]["job_id"])
            self.assertEqual(seen[-1]["state"], "failed")
            self.assertEqual(seen[-1]["message"], f"This video is {needed} minutes long and needs {needed} credits, "
                                                  f"but your workspace has 5. Nothing was charged. (insufficient_credits)")
            self.assertEqual((await self.call(client, "whoami"))["account"]["credits"], 5)
            # The upload is kept for a retry, and now its length is known: refused at submit.
            text = await self.error(client, "submit_uploaded_video", gs_path=link["gs_path"])
            self.assertIn(f"FrameOS returned HTTP 402: This video is {needed} minutes long and needs {needed} "
                          f"credits, but your workspace has 5. Add credits or use a shorter video.", text)
            self.assertEqual((project.status, project.filename), ("failed", "long-episode.mp4"))
            self.assertTrue(project.error_message.endswith("shorter video. (insufficient_credits)"))
            state.paid_credits = 500  # credits added
            again = await self.call(client, "submit_uploaded_video", gs_path=link["gs_path"])
            self.assertEqual(again["project"]["id"], project.id)
            self.assertEqual((await self.poll(client, again["job"]["job_id"]))[-1]["state"], "completed")

    async def test_known_length_holds_credits_while_it_renders(self):
        a, b = "https://vimeo.com/no-clips-hold1", "https://vimeo.com/hold2"
        credits = self.needed(a) + self.needed(b) - 1
        server, state = _new_server(credits=credits)
        async with Client(server, mode="legacy") as client:
            first = await self.call(client, "submit_video", source_url=a)
            # The first render holds what it needs, so the second sees only the rest.
            text = await self.error(client, "submit_video", source_url=b)
            self.assertIn(f"needs {self.needed(b)} credits, but your workspace has {self.needed(b) - 1}.", text)
            # The first ends without clips (not charged), which frees its hold.
            self.assertEqual((await self.poll(client, first["job"]["job_id"]))[-1]["state"], "failed")
            self.assertEqual((await self.call(client, "whoami"))["account"]["credits"], credits)
            second = await self.call(client, "submit_video", source_url=b)
            self.assertEqual((await self.poll(client, second["job"]["job_id"]))[-1]["state"], "completed")

    async def test_unknown_length_holds_credits_once_measured(self):
        c, d = "https://www.youtube.com/watch?v=hold3", "https://www.youtube.com/watch?v=hold4"
        credits = self.needed(c) + self.needed(d) - 1
        server, _ = _new_server(credits=credits)
        async with Client(server, mode="legacy") as client:
            first = await self.call(client, "submit_video", source_url=c)
            second = await self.call(client, "submit_video", source_url=d)  # neither length is known yet
            view = await self.call(client, "get_job", job_id=first["job"]["job_id"])
            self.assertEqual(view["message"], "transcribing")  # measured, checked and holding
            seen = await self.poll(client, second["job"]["job_id"])
            self.assertEqual(seen[-1]["state"], "failed")
            self.assertIn(f"needs {self.needed(d)} credits, but your workspace has {self.needed(d) - 1}. "
                          f"Nothing was charged. (insufficient_credits)", seen[-1]["message"])
            self.assertEqual((await self.poll(client, first["job"]["job_id"]))[-1]["state"], "completed")

    async def test_guardrails_can_be_switched_off(self):
        state = mock.MockState(mock.MockConfig.from_env({"FRAMEOS_MOCK_GUARDRAILS": "0", "FRAMEOS_MOCK_CREDITS": "1000"}))
        async with Client(mock.create_server(state), mode="legacy") as client:
            for i in range(4):
                await self.call(client, "submit_video", source_url=f"https://www.youtube.com/watch?v=off{i}")


@unittest.skipIf(mock is None, SKIP_REASON)
class TransportTest(unittest.IsolatedAsyncioTestCase):
    """The real entry point as a subprocess, over stdio and Streamable HTTP."""

    def env(self, **extra):
        env = {k: v for k, v in os.environ.items() if not k.startswith("FRAMEOS_MOCK_")}
        env.update(PYTHONDONTWRITEBYTECODE="1", FRAMEOS_MOCK_QUIET="1", **extra)
        return env

    async def test_stdio(self):
        params = StdioServerParameters(command=sys.executable, args=[str(MOCK_PATH)],
                                       env=self.env(FRAMEOS_MOCK_CREDITS="7"))
        async with Client(params) as client:
            self.assertEqual(len((await client.list_tools()).tools), 27)
            me = _data(await client.call_tool("whoami", {}))
            self.assertEqual(me["account"]["credits"], 7)
            link = _data(await client.call_tool("create_upload_link", {"filename": "a.mp4"}))
            self.assertTrue(link["upload_url"].startswith("http://127.0.0.1:"))

    async def test_http(self):
        port = _free_port()
        proc = subprocess.Popen([sys.executable, str(MOCK_PATH), "--http", "--port", str(port)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=self.env())
        self.addCleanup(proc.wait, 10)
        self.addCleanup(proc.terminate)
        deadline = time.monotonic() + 20
        while True:
            try:
                socket.create_connection(("127.0.0.1", port), 0.2).close()
                break
            except OSError:
                if time.monotonic() > deadline or proc.poll() is not None:
                    self.fail("mock HTTP server did not start")
                await asyncio.sleep(0.1)
        async with Client(f"http://127.0.0.1:{port}/mcp") as client:
            self.assertEqual(len((await client.list_tools()).tools), 27)
            link = _data(await client.call_tool("create_upload_link", {"filename": "b.mp4"}))
            self.assertTrue(link["upload_url"].startswith(f"http://127.0.0.1:{port}/upload/inputs/"))
            request = urllib.request.Request(link["upload_url"], data=b"\0" * 10, method="PUT")
            status = await asyncio.to_thread(lambda: urllib.request.urlopen(request, timeout=5).status)
            self.assertEqual(status, 200)
            started = _data(await client.call_tool("submit_uploaded_video", {"gs_path": link["gs_path"]}))
            # state survives across stateless HTTP requests
            projects = _data(await client.call_tool("list_projects", {}))
            self.assertEqual(projects[0]["id"], started["project"]["id"])


if __name__ == "__main__":
    unittest.main()
