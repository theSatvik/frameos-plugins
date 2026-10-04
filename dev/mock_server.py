#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp==2.2.0"]
# ///
"""Stateful mock of the FrameOS MCP server, for demos and tests that spend no credits.

It exposes the same 27 tools as the real server (FrameOS-Backend
`mcp_server/frameos_mcp/server.py`): identical names, titles, parameters, types,
defaults, enums, annotations and descriptions. `tests/test_mock_server.py` checks this against
`tests/fixtures/mcp-snapshot.json`. Behind the tools sits an in-memory fake of the
FrameOS API that returns the real response shapes and the real error strings.

Run it from the repo root:

    uv run --script dev/mock_server.py                        # stdio
    uv run --script dev/mock_server.py --http --port 8790     # Streamable HTTP at /mcp

Nothing leaves your machine and nothing is billed. Every media, preview and post
link it hands out is on https://mock.frameos.invalid/ (a reserved domain that never
resolves). Upload links point at this process, so the upload flow can be tried with
curl. See dev/README.md for the environment knobs and what is not simulated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Annotated, Any, Callable, Literal, Optional
from urllib.parse import quote, urlparse

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field, TypeAdapter, ValidationError, field_validator

# The real server's instructions, verbatim.
INSTRUCTIONS = (
    "Create clips with submit_video, then poll get_job and call list_clips after completion. "
    "Processing consumes FrameOS credits. Use only projects the connected account owns."
)

MOCK_HOST = "https://mock.frameos.invalid"

# Launch guardrail messages. Keep them identical to the spec handed to the MCP
# connector owner (FrameOS-Backend task file, section 1, owner decision 2026-10-02).
SHORTFALL_SUBMIT_MESSAGE = (
    "This video is {minutes} minutes long and needs {needed} credits, but your workspace has "
    "{balance}. Add credits or use a shorter video."
)
SHORTFALL_WORKER_MESSAGE = (
    "This video is {minutes} minutes long and needs {needed} credits, but your workspace has "
    "{balance}. Nothing was charged. (insufficient_credits)"
)
CONCURRENCY_MESSAGE = (
    "{active} videos are already processing in this workspace (limit {limit}). "
    "Wait for one to finish, then submit again."
)
BUCKET = "frameos-mock-bucket"
DEFAULT_HTTP_PORT = 8790

MIN_SOURCE_SECONDS = 30
THUMBNAIL_CREDITS_PER = 10
THUMBNAIL_MAX = 3
THUMBNAIL_ASPECTS = {"auto", "16:9", "9:16", "1:1", "4:5", "3:4"}
THUMB_CANVAS = {
    "16:9": (1280, 720),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "3:4": (1080, 1440),
}
SIGNED_GET_SECONDS = 6 * 3600  # CDN-signed plain GETs last 6-12 h
SIGNED_ATTACHMENT_SECONDS = 3600  # attachment (download) links last 1 h
UPLOAD_CLAIM_SECONDS = 3600
STRAY_ROW_REAP_SECONDS = 30 * 60
SOCIAL_COPY_LIMIT_PER_HOUR = 30

# Caption contract (backend/api/routes.py, core/caption_appearance.py, core/caption_anim.py).
CAPTION_STYLE_ALIASES = {
    "shorts-default": "karaoke", "float": "karaoke", "default": "karaoke",
    "bounce": "beasty", "type": "deep-diver",
}
CAPTION_STYLES = {
    "none", "karaoke", "beasty", "deep-diver", "pod-p", "instagram",
    "youshaei", "mozi", "popline", "glitch-infinite", "seamless-bounce",
    "baby-earthquake", "blur-switch", "highlighter-box", "simple",
    "think-media", "focus", "blur-in", "with-backdrop", "soft-landing",
    "baby-steps", "grow", "breathe",
}
CAPTION_FONTS = frozenset({
    "Montserrat", "Poppins", "Roboto", "Anton", "Bebas Neue", "Oswald",
    "Archivo", "Heebo", "Kanit", "Lilita One", "Spline Sans",
    "Poltawski Nowy", "Lemon", "Luckiest Guy", "Marcellus", "Roboto Mono",
})
CAPTION_ANIMS = frozenset({
    "pop", "scale", "scale-in", "hover", "blur-in", "blur-switch",
    "deep-diver", "individual-focus", "seamless-bounce", "baby-earthquake",
    "glitch-infinite-zoom", "simple-words-pop", "slide-in-from-top",
    "breathe-scale-wiggle", "word-level_karaoke_fill-pop",
    "word-level_karaoke_bg-highlight", "word-level_simple_bg-highlight",
})
SOCIAL_COPY_PLATFORMS = {"youtube", "instagram", "facebook", "linkedin", "tiktok", "x"}

NO_CLIPS_MESSAGE = (
    "We couldn't find a moment strong enough to turn into a clip. This usually "
    "means there isn't much clear speech to work with — try a longer video, or "
    "one with more talking. (no_clips_found)"
)
THUMBNAIL_FAILED_MESSAGE = "Thumbnail generation failed. Please try another link."
STRAY_ROW_MESSAGE = "Processing crashed before it could report. Please try again."

# How many get_job polls a job needs in the default "fast" mode, and how long it
# takes (as a fraction of FRAMEOS_MOCK_SPEED seconds) in wall-clock mode.
FAST_POLLS = {"render": 3, "export": 2, "recap": 2, "thumb": 2, "post": 3}
TIME_SCALE = {"render": 1.0, "export": 0.25, "recap": 0.25, "thumb": 0.4, "post": 0.3}

# ---------------------------------------------------------------------------
# Synthetic content: a fictional creator-business podcast. Clips, hooks and the
# source transcript are all built from these blocks, so focus_prompt words that
# appear here (pricing, newsletter, burnout, editor, hook, sponsor, retention,
# shorts ...) steer which clips come back, the way the real word matcher does.
# ---------------------------------------------------------------------------
SHOW_NAME = "The Build Room"
INTRO = [
    "Welcome back to The Build Room, the show about turning a channel into a real business.",
    "Today we are talking through the decisions that actually moved the numbers this year.",
    "Some of these worked, a couple were expensive lessons, and we will be honest about both.",
]
BRIDGES = [
    "Okay, let me move on to the next thing, because this one surprised me.",
    "That connects to something else we changed around the same time.",
    "Before we get to that, a quick story from behind the scenes.",
    "I want to come back to this later, but first something related.",
]
BLOCKS: list[dict[str, Any]] = [
    {
        "key": "pricing",
        "hook": "We tripled the price and lost almost nobody",
        "tags": ["#pricing", "#creatorbusiness", "#onlinecourses"],
        "lines": [
            "Our first course was priced low because we were scared nobody would buy it.",
            "The pricing felt safe, but it attracted people who never opened the second lesson.",
            "So we tripled the price and rewrote the sales page around one specific outcome.",
            "Honestly, I expected refunds and angry emails the week we changed the pricing.",
            "What actually happened is that sales barely dipped and completion rates doubled.",
            "People who pay more show up, do the work, and then tell their friends about it.",
            "The lesson for me is that a low price is not kindness if nobody finishes.",
            "If you are nervous about raising prices, test it on the next launch, not the last one.",
        ],
    },
    {
        "key": "newsletter",
        "hook": "The newsletter mistake that cost us a year",
        "tags": ["#newsletter", "#emailmarketing", "#audiencegrowth"],
        "lines": [
            "For a whole year we treated the newsletter like an afterthought.",
            "We sent it whenever a video came out, which made it a worse notification.",
            "Open rates kept sliding and we told ourselves email was dead.",
            "Then we started writing one useful idea per issue that was not in the videos.",
            "Replies went from almost zero to dozens every single week.",
            "The newsletter became the place where our best viewers actually talked back.",
            "If I could redo it, I would have started writing it properly on day one.",
            "Your email list is the only audience no algorithm can take away from you.",
        ],
    },
    {
        "key": "burnout",
        "hook": "Posting every day almost ended the channel",
        "tags": ["#burnout", "#contentcreator", "#consistency"],
        "lines": [
            "There was a stretch where we posted a short every single day for four months.",
            "The views went up, but I stopped enjoying any of it after the first month.",
            "I was editing at midnight and recording again at eight the next morning.",
            "Burnout does not arrive as one bad day, it shows up as a slow loss of curiosity.",
            "We cut back to three posts a week and the channel did not collapse.",
            "Retention actually improved because each video had time to be good.",
            "Consistency matters, but consistency you can keep for years matters more.",
            "Protect the part of you that thinks this work is fun, because that is the real asset.",
        ],
    },
    {
        "key": "hiring",
        "hook": "Hire an editor before you think you can afford one",
        "tags": ["#hiring", "#videoediting", "#creatorbusiness"],
        "lines": [
            "Hiring our first editor was the scariest expense we had ever signed up for.",
            "I kept saying we would hire once the channel made more money.",
            "The problem is that editing was eating twenty hours of my week.",
            "Those were hours I could have spent writing, filming, or talking to sponsors.",
            "Within two months of hiring, we were publishing more and earning more.",
            "Write down every task you do in a week and price your own hour honestly.",
            "If an editor costs less than your hour, you are already paying for not hiring.",
            "Start with a short paid trial project so both sides can see if it fits.",
        ],
    },
    {
        "key": "hooks",
        "hook": "The first three seconds decide everything",
        "tags": ["#hooks", "#retention", "#youtubetips"],
        "lines": [
            "Most people lose the viewer before they even get to the point.",
            "We used to open with a greeting, a logo, and a long setup.",
            "Now the first line of every video is the most surprising thing we say in it.",
            "If the hook does not work out loud in three seconds, it does not work.",
            "Write five versions of the first sentence and read each one to someone else.",
            "The version that makes them ask a question is almost always the right one.",
            "A strong hook is a promise, and the rest of the video has to keep it.",
            "The retention graph showed the drop at second four disappearing almost overnight.",
        ],
    },
    {
        "key": "sponsors",
        "hook": "How to say no to a sponsor without burning the bridge",
        "tags": ["#sponsorships", "#brandDeals", "#creatoreconomy"],
        "lines": [
            "Turning down a sponsor felt impossible when we were just getting started.",
            "We said yes to a product we did not use and the audience noticed immediately.",
            "The comments were polite, but trust takes a long time to rebuild.",
            "Now every sponsor gets the same simple test: would I recommend this for free?",
            "When the answer is no, we say thank you and explain exactly why.",
            "Two of those brands came back a year later with something we genuinely loved.",
            "Saying no clearly is what makes your yes worth something to the next sponsor.",
            "Your audience is not a billboard, it is a relationship you are borrowing from.",
        ],
    },
    {
        "key": "analytics",
        "hook": "Stop checking views, watch retention instead",
        "tags": ["#analytics", "#retention", "#youtubegrowth"],
        "lines": [
            "I used to refresh the view count every hour after we published.",
            "Views tell you how many people clicked, not whether the video was any good.",
            "Retention tells you exactly where people got bored and left.",
            "We now review the retention graph of every video before we plan the next one.",
            "If there is a cliff, we go back and watch that exact moment out loud.",
            "Almost every cliff was a moment where we repeated ourselves or explained too much.",
            "Fixing those moments did more for growth than any thumbnail experiment.",
            "Look at the shape of the graph, not the size of the number.",
        ],
    },
    {
        "key": "repurposing",
        "hook": "One long episode, a week of shorts",
        "tags": ["#repurposing", "#shorts", "#contentstrategy"],
        "lines": [
            "Every long episode we record now becomes at least five short clips.",
            "The trick is to find moments that make sense without any context.",
            "A good short has a clear question, a tension, and an answer inside a minute.",
            "We look for places where the guest suddenly gets animated or tells a story.",
            "Each clip gets its own caption style and a title written for that platform.",
            "Shorts brought in more new subscribers than the full episodes this year.",
            "The long episode is the library, and the shorts are the doors into it.",
            "Repurposing is not lazy, it is how one good conversation reaches more people.",
        ],
    },
]
BLOCK_BY_KEY = {b["key"]: b for b in BLOCKS}
_FOCUS_STOPWORDS = {
    "that", "this", "with", "about", "part", "when", "they", "what", "from", "have",
    "more", "into", "where", "their", "there", "talk", "talks", "talking", "clip",
    "clips", "video", "moments", "moment", "find", "some", "make", "best",
}


class FrameOSHTTPError(Exception):
    """A non-2xx answer from the fake FrameOS API (status + FastAPI `detail`)."""

    def __init__(self, status: int, detail: Any) -> None:
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


# ---------------------------------------------------------------------------
# Request validation that mirrors FastAPI's 422s (list-shaped `detail`).
# ---------------------------------------------------------------------------
def _fastapi_detail(exc: ValidationError, *prefix: str) -> list:
    items = []
    for err in exc.errors(include_url=False):
        item = dict(err)
        item["loc"] = [*prefix, *err.get("loc", ())]
        if "ctx" in item:
            item["ctx"] = {
                key: (value if value is None or isinstance(value, (str, int, float, bool)) else {})
                for key, value in item["ctx"].items()
            }
        items.append(item)
    return json.loads(json.dumps(items, default=str))


def _body(model: type[BaseModel], data: dict) -> Any:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise FrameOSHTTPError(422, _fastapi_detail(exc, "body")) from None


_UUID = TypeAdapter(uuid.UUID)


def _path_uuid(name: str, value: Any) -> str:
    try:
        return str(_UUID.validate_python(value))
    except ValidationError as exc:
        raise FrameOSHTTPError(422, _fastapi_detail(exc, "path", name)) from None


def _query_int(name: str, value: Any, *, ge: int | None = None, le: int | None = None) -> int:
    adapter = TypeAdapter(Annotated[int, Field(ge=ge, le=le)])
    try:
        return adapter.validate_python(str(value))
    except ValidationError as exc:
        raise FrameOSHTTPError(422, _fastapi_detail(exc, "query", name)) from None


class _SubmitVideo(BaseModel):
    source_url: str = Field(min_length=8, max_length=2048)
    max_clips: int = Field(default=3, ge=1, le=20)
    aspect_ratio: str = "9:16"
    focus_prompt: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("source_url")
    @classmethod
    def valid_source_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("source_url must be an HTTP or HTTPS URL")
        return value


class _SubmitUploadedVideo(BaseModel):
    gs_path: str
    max_clips: int = Field(default=3, ge=1, le=20)
    aspect_ratio: str = "9:16"
    focus_prompt: Optional[str] = Field(default=None, max_length=1000)


class _SignedUpload(BaseModel):
    filename: str
    content_type: Optional[str] = None


class _CaptionStyle(BaseModel):
    style: str = "karaoke"
    appearance: Optional[dict] = None


class _Export(BaseModel):
    style: Optional[str] = None
    filename: Optional[str] = None


class _NewCollection(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Collection name cannot be blank")
        return value


class _AddCollectionClip(BaseModel):
    clip_id: uuid.UUID


class _SocialCopy(BaseModel):
    platform: str
    tone: str = Field(default="clear and natural", max_length=100)

    @field_validator("platform")
    @classmethod
    def supported_platform(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in SOCIAL_COPY_PLATFORMS:
            raise ValueError("Unsupported social platform")
        return value


class _SocialPost(BaseModel):
    clip_id: uuid.UUID
    account_id: uuid.UUID
    title: str = ""
    description: str = ""
    privacy: str = "public"


class _Thumbnails(BaseModel):
    url: str = ""
    video_id: Optional[uuid.UUID] = None
    include_face: bool = False
    max_thumbnails: Optional[int] = None
    style_ref: str = ""
    aspect: str = "auto"
    clip_id: Optional[uuid.UUID] = None


# ---------------------------------------------------------------------------
# Caption helpers (same rules as the backend).
# ---------------------------------------------------------------------------
def _normalize_caption_style(value: Optional[str]) -> str:
    key = (value or "").strip().lower().replace("_", "-")
    key = CAPTION_STYLE_ALIASES.get(key, key)
    if key not in CAPTION_STYLES:
        raise FrameOSHTTPError(422, f"Unknown caption style: {value}")
    return key


def _normalize_appearance(value: Any) -> Optional[dict]:
    if not isinstance(value, dict):
        return None
    out: dict[str, Any] = {}
    font = value.get("font")
    if isinstance(font, str) and font.strip():
        font = font.strip()
        if font not in CAPTION_FONTS:
            raise ValueError(f"Unknown caption font: {font}")
        out["font"] = font
    scale = value.get("scale")
    if isinstance(scale, (int, float)) and not isinstance(scale, bool):
        scale = round(min(2.0, max(0.5, float(scale))), 2)
        if abs(scale - 1.0) >= 0.01:
            out["scale"] = scale
    y_pct = value.get("yPct")
    if isinstance(y_pct, (int, float)) and not isinstance(y_pct, bool):
        out["yPct"] = round(min(0.95, max(0.05, float(y_pct))), 3)
    anim = value.get("anim")
    if isinstance(anim, str) and anim.strip():
        key = anim.strip()
        if key not in CAPTION_ANIMS and key != "none":
            raise ValueError(f"Unknown caption animation: {anim}")
        out["anim"] = key
    return out or None


def _appearance_or_422(value: Any) -> Optional[dict]:
    try:
        return _normalize_appearance(value)
    except ValueError as exc:
        raise FrameOSHTTPError(422, str(exc)) from None


def _appearance_slug(appearance: Optional[dict]) -> str:
    if not appearance:
        return ""
    canon = json.dumps(appearance, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(canon.encode("utf-8")).hexdigest()[:8]


def _clean_text(value: object, *, limit: int = 180) -> str:
    return " ".join(str(value or "").split())[:limit]


def _derived_headline(transcript: str) -> str:
    first = re.split(r"(?<=[.!?])\s+", (transcript or "").strip(), maxsplit=1)[0]
    words = first.rstrip(".!?").split()
    return " ".join(words[:12])


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).replace(tzinfo=None).isoformat()


def _seed_of(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:12], 16)


def _eta_seconds(duration_seconds: Optional[float], max_clips: int) -> Optional[int]:
    if not duration_seconds or duration_seconds <= 0:
        return None
    raw = 180.0 + 0.2 * float(duration_seconds) + 180.0 * max(1, int(max_clips)) * 1.0
    return int(math.ceil(raw * 1.1))


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
@dataclass
class MockConfig:
    credits: int = 120
    plan: str = "starter"
    speed: Any = "fast"  # "fast" (poll-driven) or seconds (float) for a full render
    seed_projects: bool = True
    social_accounts: bool = True
    brand_logo: bool = False
    errors: str = "detailed"  # "detailed" or "opaque"
    # Launch guardrails (owner decision 2026-10-02): a render must be covered by
    # the balance, and at most `max_concurrent` renders run per workspace.
    guardrails: bool = True
    max_concurrent: int = 3

    @classmethod
    def from_env(cls, env: Optional[dict] = None) -> "MockConfig":
        env = os.environ if env is None else env

        def flag(name: str, default: bool) -> bool:
            raw = str(env.get(name, "")).strip().lower()
            return default if not raw else raw not in {"0", "false", "no", "off"}

        speed_raw = str(env.get("FRAMEOS_MOCK_SPEED", "fast")).strip().lower() or "fast"
        speed: Any = "fast"
        if speed_raw != "fast":
            try:
                speed = max(1.0, float(speed_raw))
            except ValueError:
                speed = "fast"
        try:
            credits = int(env.get("FRAMEOS_MOCK_CREDITS", "120"))
        except ValueError:
            credits = 120
        plan = str(env.get("FRAMEOS_MOCK_PLAN", "starter")).strip().lower()
        errors = str(env.get("FRAMEOS_MOCK_ERRORS", "detailed")).strip().lower()
        try:
            max_concurrent = int(env.get("FRAMEOS_MOCK_MAX_CONCURRENT", "3"))
        except ValueError:
            max_concurrent = 3
        return cls(
            credits=max(0, credits),
            plan=plan if plan in {"free", "starter", "pro"} else "starter",
            speed=speed,
            seed_projects=flag("FRAMEOS_MOCK_SEED", True),
            social_accounts=flag("FRAMEOS_MOCK_SOCIAL", True),
            brand_logo=flag("FRAMEOS_MOCK_BRAND_LOGO", False),
            errors=errors if errors in {"detailed", "opaque"} else "detailed",
            guardrails=flag("FRAMEOS_MOCK_GUARDRAILS", True),
            max_concurrent=max(1, max_concurrent),
        )


@dataclass
class Stage:
    at: float  # fraction of the job timeline where this stage is reached
    state: str  # pending | processing | completed | failed
    progress: float
    message: str
    db_progress: Optional[int] = None


@dataclass
class Job:
    id: str
    kind: str  # render | export | recap | thumb | post
    stages: list
    created_at: float
    started_at_ms: int
    eta_seconds: Optional[int] = None
    source_duration_seconds: Optional[float] = None
    result: Optional[dict] = None
    polls: int = 0
    applied: int = 0
    on_stage: Optional[Callable[["Job", Stage], None]] = None

    @property
    def current(self) -> Stage:
        return self.stages[self.applied]


@dataclass
class Project:
    id: str
    title: str
    source: str
    source_type: str
    filename: Optional[str]
    created_at: float
    sim_duration: float
    known_duration: Optional[float] = None
    status: str = "pending"
    progress: int = 0
    duration_sec: Optional[int] = None
    thumbnail_url: Optional[str] = None
    error_message: Optional[str] = None
    max_clips: int = 3
    aspect_ratio: str = "9:16"
    focus_prompt: Optional[str] = None
    credits_charged_minutes: Optional[int] = None
    transcript: Optional[list] = None
    uploaded: bool = False
    source_deleted: bool = False
    run: int = 0
    job_id: Optional[str] = None


@dataclass
class Clip:
    id: str
    video_id: str
    filename: str
    start_ms: int
    end_ms: int
    score: Optional[float]
    rank: int
    transcript: str
    media: str  # object key of the clip file, e.g. outputs/<video>/<run>/clip_0.mp4
    caption: Any  # dict (JSON meta) for new clips, a bare string for legacy burned clips
    size_bytes: int
    aspect_ratio: str
    created_at: float
    render_metadata: dict = field(default_factory=dict)
    topic: str = ""
    deleted: bool = False


class MockState:
    """In-memory fake of the account-scoped FrameOS API behind the MCP tools."""

    def __init__(self, config: Optional[MockConfig] = None, *, clock: Callable[[], float] = time.time,
                 upload_base: str = f"{MOCK_HOST}/upload") -> None:
        self.config = config or MockConfig.from_env()
        self.clock = clock
        self.upload_base = upload_base.rstrip("/")
        self.user_id = str(uuid.uuid4())
        self.org_id = str(uuid.uuid4())
        self.org_name = "Mock Creator's workspace"
        self.paid_credits = int(self.config.credits)
        self.trial_credits = 0
        self.projects: dict[str, Project] = {}
        self.clips: dict[str, Clip] = {}
        self.jobs: dict[str, Job] = {}
        self.collections: dict[str, dict] = {}
        self.thumbnails: list[dict] = []
        self.social_accounts: list[dict] = []
        self.posts: list[dict] = []
        self.exported: set = set()  # export artifact keys that exist
        self.upload_claims: dict[str, tuple] = {}  # gs_path -> (filename, expires_at)
        self.issued_uploads: dict[str, float] = {}  # object key -> expires_at
        self.uploaded_objects: dict[str, int] = {}  # object key -> bytes received
        self.social_copy_calls: list[float] = []
        self.lock = threading.Lock()
        if self.config.social_accounts:
            self._seed_social_accounts()
        if self.config.seed_projects:
            self._seed_legacy_project()

    # ----- helpers --------------------------------------------------------
    def now(self) -> float:
        return float(self.clock())

    def _balance(self) -> int:
        return max(0, self.paid_credits + self.trial_credits)

    def _spend(self, amount: int) -> None:
        amount = max(0, int(amount))
        from_trial = min(self.trial_credits, amount)
        self.trial_credits -= from_trial
        self.paid_credits = max(0, self.paid_credits - (amount - from_trial))

    def _signed(self, key: str, *, attachment: Optional[str] = None) -> str:
        seconds = SIGNED_ATTACHMENT_SECONDS if attachment else SIGNED_GET_SECONDS
        url = f"{MOCK_HOST}/media/{quote(key)}?X-Mock-Expires={int(self.now()) + seconds}"
        if attachment:
            url += "&response-content-disposition=" + quote(f'attachment; filename="{attachment}"', safe="")
        return url

    def _project(self, project_id: str, *, detail: str = "Video not found") -> Project:
        project = self.projects.get(project_id)
        if project is None:
            raise FrameOSHTTPError(404, detail)
        return project

    def _org_clip(self, clip_id: str) -> Clip:
        clip = self.clips.get(clip_id)
        if clip is None or clip.deleted:
            raise FrameOSHTTPError(404, "Clip not found")
        return clip

    @staticmethod
    def _caption_meta(clip: Clip) -> tuple:
        if isinstance(clip.caption, dict):
            return str(clip.caption.get("mode") or "burned"), clip.caption.get("style")
        return "burned", None

    @staticmethod
    def _caption_appearance(clip: Clip) -> Optional[dict]:
        if not isinstance(clip.caption, dict):
            return None
        try:
            return _normalize_appearance(clip.caption.get("appearance"))
        except ValueError:
            return None

    @staticmethod
    def _media_parts(clip: Clip) -> tuple:
        head, _, fname = clip.media.rpartition("/")
        match = re.match(r"clip_(\d+)", fname)
        if not head or not match:
            raise FrameOSHTTPError(409, "Unexpected clip path")
        return head, match.group(1)

    def _export_key(self, clip: Clip, style: str, appearance: Optional[dict]) -> str:
        head, index = self._media_parts(clip)
        slug = _appearance_slug(appearance)
        return f"{head}/clip_{index}__export_{style}{f'-a{slug}' if slug else ''}.mp4"

    def _clip_title(self, clip: Clip) -> str:
        hook = str(clip.caption.get("hook") or "") if isinstance(clip.caption, dict) else ""
        return (
            _clean_text(hook)
            or _clean_text(_derived_headline(clip.transcript))
            or os.path.splitext(clip.filename)[0].replace("_", " ").title()
        )

    def _dash_clip(self, clip: Clip) -> dict:
        mode, style = self._caption_meta(clip)
        title = self._clip_title(clip)
        head, _, fname = clip.media.rpartition("/")
        match = re.match(r"clip_(\d+)", fname)
        cues = self._signed(f"{head}/clip_{match.group(1)}.cues.json") if match else None
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("_") or "clip"
        return {
            "id": clip.id,
            "videoId": clip.video_id,
            "filename": clip.filename,
            "title": title,
            "name": title,
            "hook": title,
            "url": self._signed(clip.media),
            "downloadUrl": self._signed(clip.media, attachment=f"{safe}.mp4"),
            "previewUrl": self._signed(clip.media[:-4] + "_preview.mp4") if clip.media.endswith(".mp4") else None,
            "captionMode": mode,
            "captionStyle": style,
            "captionAppearance": self._caption_appearance(clip),
            "cuesUrl": cues,
            "transcript": clip.transcript,
            "startTime": clip.start_ms / 1000.0,
            "endTime": clip.end_ms / 1000.0,
            "startTimeMs": clip.start_ms,
            "endTimeMs": clip.end_ms,
            "score": clip.score,
            "rank": clip.rank,
            "aspectRatio": clip.aspect_ratio,
            "thumbnailUrl": self._signed(f"{head}/{os.path.splitext(fname)[0].split('_v')[0]}.jpg"),
            "size": clip.size_bytes,
            "sizeBytes": clip.size_bytes,
            "xmlExport": bool(clip.render_metadata.get("xml_export")),
            "createdAt": _iso(clip.created_at),
        }

    def _safe_clip(self, clip: Clip) -> dict:
        result = self._dash_clip(clip)
        needs_export = result.get("captionMode") == "overlay" and result.get("captionStyle") != "none"
        result["exportRequired"] = needs_export
        if needs_export:
            result["downloadUrl"] = None
        return result

    # ----- jobs -------------------------------------------------------------
    def _new_job(self, job_id: str, kind: str, stages: list, *, eta: Optional[int] = None,
                 duration: Optional[float] = None,
                 on_stage: Optional[Callable[[Job, Stage], None]] = None) -> Job:
        now = self.now()
        job = Job(id=job_id, kind=kind, stages=stages, created_at=now, started_at_ms=int(now * 1000),
                  eta_seconds=eta, source_duration_seconds=duration, on_stage=on_stage)
        self.jobs[job_id] = job
        if on_stage:
            on_stage(job, stages[0])
        return job

    def _fraction(self, job: Job) -> float:
        if self.config.speed == "fast":
            return min(1.0, job.polls / FAST_POLLS[job.kind])
        total = max(2.0, float(self.config.speed) * TIME_SCALE[job.kind])
        return min(1.0, (self.now() - job.created_at) / total)

    def _advance(self, job: Job, *, observe: bool) -> None:
        if job.current.state in ("completed", "failed", "cancelled"):
            return
        if observe:
            job.polls += 1
        fraction = self._fraction(job)
        target = max(i for i, stage in enumerate(job.stages) if stage.at <= fraction + 1e-9)
        while job.applied < target:
            job.applied += 1
            stage = job.stages[job.applied]
            if job.on_stage:
                job.on_stage(job, stage)
            if stage.state in ("completed", "failed"):
                break

    def tick(self) -> None:
        """Let wall-clock jobs finish on their own, as real jobs do (no-op in fast mode)."""
        if self.config.speed != "fast":
            for job in list(self.jobs.values()):
                self._advance(job, observe=False)

    def _observe_project(self, project: Project) -> None:
        job = self.jobs.get(project.job_id or "")
        if job is not None:
            self._advance(job, observe=True)

    def _job_view(self, job_id: str) -> dict:
        job = self.jobs.get(job_id)
        if job is None:  # owned id without any state reads as pending (queue.py)
            return {"id": job_id, "state": "pending", "progress": 0.0, "message": "", "eta_seconds": None,
                    "eta_remaining_seconds": None, "started_at_ms": None,
                    "source_duration_seconds": None, "result": None}
        stage = job.current
        remaining = None
        if job.eta_seconds is not None:
            if stage.state in ("completed", "failed", "cancelled"):
                remaining = 0
            else:
                elapsed = max(0, int(self.now() * 1000) - job.started_at_ms) // 1000
                remaining = max(0, job.eta_seconds - int(elapsed))
        return {
            "id": job_id,
            "state": stage.state,
            "progress": float(stage.progress),
            "message": stage.message,
            "eta_seconds": job.eta_seconds,
            "eta_remaining_seconds": remaining,
            "started_at_ms": job.started_at_ms,
            "source_duration_seconds": job.source_duration_seconds,
            "result": job.result,
        }

    # ----- seed data ----------------------------------------------------------
    def _seed_social_accounts(self) -> None:
        connected = self.now() - 20 * 86400
        for platform, name, ref in (
            ("youtube", "Mock Creator", "mock-youtube-channel"),
            ("instagram", "@mock.creator", "mock-instagram-business"),
            ("linkedin", "Mock Creator", "urn:li:person:mock"),
            ("facebook", "Mock Creator Page", "mock-facebook-page"),
        ):
            self.social_accounts.append({
                "id": str(uuid.uuid4()), "platform": platform, "accountRef": ref, "displayName": name,
                "avatarUrl": f"{MOCK_HOST}/avatars/{platform}.png", "status": "connected",
                "connectedAt": _iso(connected),
            })
            connected += 60

    def _seed_legacy_project(self) -> None:
        """An older, completed project: burned-in captions, no stored source
        transcript, and one clip left over (soft-deleted) from an earlier run that
        list_clips still returns, like the real route does."""
        created = self.now() - 40 * 86400
        project = Project(
            id=str(uuid.uuid4()), title=f"{SHOW_NAME}, Ep. 41", source=f"{MOCK_HOST}/sources/build-room-ep41.mp4",
            source_type="url", filename=None, created_at=created, sim_duration=1418.0, known_duration=1418.0,
            status="completed", progress=100, duration_sec=1418, credits_charged_minutes=24,
            max_clips=3, aspect_ratio="9:16", run=2,
        )
        self.projects[project.id] = project
        for rank, key, start, run, deleted in (
            (0, "hooks", 312.4, "legacy-run2", False),
            (1, "sponsors", 861.7, "legacy-run2", False),
            (2, "analytics", 1104.2, "legacy-run1", True),
        ):
            text = " ".join(BLOCK_BY_KEY[key]["lines"])
            length = 41.6 + rank * 3.1
            clip = Clip(
                id=str(uuid.uuid4()), video_id=project.id, filename=f"clip_{rank}.mp4",
                start_ms=int(start * 1000), end_ms=int((start + length) * 1000), score=round(0.88 - rank * 0.05, 2),
                rank=rank, transcript=text, media=f"outputs/{project.id}/{run}/clip_{rank}.mp4",
                caption="karaoke", size_bytes=int(length * 610_000), aspect_ratio="9:16",
                created_at=created + 1500 - (400 if deleted else 0), topic=key, deleted=deleted,
            )
            self.clips[clip.id] = clip

    # ----- synthetic media ------------------------------------------------------
    @staticmethod
    def _sim_duration(source: str) -> float:
        if "too-short" in source.lower():
            return 12.0
        seed = _seed_of(source)
        return float(6 * 60 + seed % (56 * 60))

    @staticmethod
    def _source_title(source: str) -> str:
        host = (urlparse(source).hostname or "").lower()
        if any(h in host for h in ("youtube.com", "youtu.be", "vimeo.com", "twitch.tv", "kick.com")):
            return f"{SHOW_NAME}, Ep. {10 + _seed_of(source) % 80}"
        tail = source.rstrip("/").rsplit("/", 1)[-1]
        return (tail or source)[:80]

    @staticmethod
    def _known_duration_at_submit(source: str, sim: float) -> Optional[float]:
        # The real API learns the duration at submit only from oEmbed metadata
        # (Vimeo has it, YouTube does not); otherwise the worker measures it.
        host = (urlparse(source).hostname or "").lower()
        if "too-short" in source.lower() or "vimeo.com" in host:
            return sim
        return None

    def _build_transcript(self, project: Project) -> tuple:
        """(segments, occurrences) for the source; occurrences maps block key ->
        list of (first_segment_index, last_segment_index)."""
        seed = _seed_of(project.source)
        order = sorted(range(len(BLOCKS)), key=lambda i: _seed_of(f"{seed}:{i}"))
        segments: list[dict] = []
        occurrences: dict[str, list] = {b["key"]: [] for b in BLOCKS}
        t = 0.0

        def add(text: str) -> bool:
            nonlocal t
            if t >= project.sim_duration:
                return False
            length = max(3.0, round(len(text.split()) / 2.6, 2))
            end = min(project.sim_duration, t + length)
            segments.append({"start": round(t, 2), "end": round(end, 2), "text": text, "language": "en"})
            t = end + 0.2
            return True

        for line in INTRO:
            if not add(line):
                break
        cycle = 0
        while t < project.sim_duration:
            for position, block_index in enumerate(order):
                block = BLOCKS[block_index]
                first = len(segments)
                ok = True
                for line in block["lines"]:
                    ok = add(line)
                    if not ok:
                        break
                if ok:
                    occurrences[block["key"]].append((first, len(segments) - 1))
                if not ok or not add(BRIDGES[(cycle + position) % len(BRIDGES)]):
                    break
            cycle += 1
        return segments, occurrences

    @staticmethod
    def _with_words(segment: dict) -> dict:
        words = segment["text"].split()
        span = max(0.01, segment["end"] - segment["start"])
        step = span / max(1, len(words))
        return {**segment, "words": [
            {"text": w, "start": round(segment["start"] + i * step, 2),
             "end": round(segment["start"] + (i + 1) * step, 2)}
            for i, w in enumerate(words)
        ]}

    @staticmethod
    def _focus_words(focus: Optional[str]) -> list:
        text = (focus or "")[:400].lower()  # the backend silently keeps 400 chars
        return [w for w in re.findall(r"[a-z0-9']+", text) if len(w) >= 4 and w not in _FOCUS_STOPWORDS]

    def _make_clips(self, project: Project, segments: list) -> list:
        _, occurrences = self._build_transcript(project)
        seed = _seed_of(project.source)
        focus = self._focus_words(project.focus_prompt)
        base_scores = [0.93, 0.9, 0.87, 0.84, 0.81, 0.78, 0.75, 0.72]
        candidates = []
        for i, block in enumerate(sorted(BLOCKS, key=lambda b: _seed_of(f"{seed}:score:{b['key']}"))):
            spans = occurrences[block["key"]]
            if not spans:
                continue
            text = " ".join(block["lines"]).lower()
            matched = bool(focus) and any(re.search(rf"\b{re.escape(w)}", text) for w in focus)
            score = base_scores[i] + (_seed_of(f"{seed}:j:{i}") % 9) / 1000.0
            if matched:  # a focus match outranks everything else, so rank still follows score
                score = 0.95 + (base_scores[i] - 0.72) / 10.0
            candidates.append((matched, round(score, 2), block, spans))
        candidates.sort(key=lambda c: (not c[0], -c[1]))
        count = min(project.max_clips, 3 + seed % 3, len(candidates))
        project.run += 1
        run_key = f"run{project.run}-{int(self.now())}"
        clips = []
        for rank, (_, score, block, spans) in enumerate(candidates[:count]):
            first, last = spans[(rank * 3 + seed) % len(spans)]
            start, end = segments[first]["start"], segments[last]["end"]
            clip = Clip(
                id=str(uuid.uuid4()), video_id=project.id, filename=f"clip_{rank}.mp4",
                start_ms=int(start * 1000), end_ms=int(end * 1000), score=round(score, 2), rank=rank,
                transcript=" ".join(s["text"] for s in segments[first:last + 1])[:24000],
                media=f"outputs/{project.id}/{run_key}/clip_{rank}.mp4",
                caption={"mode": "overlay", "style": "shorts_default", "hook": block["hook"]},
                size_bytes=int((end - start) * 640_000), aspect_ratio=project.aspect_ratio,
                created_at=self.now(), render_metadata={"xml_export": True}, topic=block["key"],
            )
            clips.append(clip)
        return clips

    # ----- render pipeline ----------------------------------------------------
    def _render_stages(self, project: Project, n_clips: int, n_segments: int, fail: bool) -> list:
        stages = [
            Stage(0.0, "pending", 0.0, "queued", 0),
            Stage(0.12, "processing", 0.05, "downloading source", 5),
            Stage(0.22, "processing", 0.1, "transcribing", 10),
            Stage(0.36, "processing", 0.3, f"scoring hooks across {n_segments} segments", 30),
        ]
        if fail:
            stages.append(Stage(0.5, "failed", 1.0, NO_CLIPS_MESSAGE, 100))
            return stages
        stages.append(Stage(0.5, "processing", 0.45, f"rendering {n_clips} clips", 45))
        for i in range(1, n_clips + 1):
            frac = 0.45 + 0.5 * (i / max(1, n_clips))
            stages.append(Stage(0.5 + 0.45 * i / n_clips, "processing", round(frac, 3),
                                f"rendered {i}/{n_clips} clips", int(frac * 100)))
        stages.append(Stage(1.0, "completed", 1.0, f"{n_clips} clips ready", 100))
        return stages

    def _start_render(self, project: Project) -> dict:
        duration = project.known_duration
        if duration is not None and duration < MIN_SOURCE_SECONDS:
            reason = (
                f"This video is only {int(round(duration))} seconds long, which is too short to pull a "
                f"highlight out of. FrameOS needs at least {MIN_SOURCE_SECONDS} seconds of video to work with."
            )
            project.status, project.progress = "failed", 0
            project.error_message = f"{reason} (source_too_short)"
            raise FrameOSHTTPError(422, reason)

        project.status, project.progress, project.error_message = "processing", 0, None
        fail = "no-clips" in project.source.lower()
        needed = self._credits_needed(project)
        short = (self.config.guardrails and duration is None and self._balance() < needed)
        segments, _ = self._build_transcript(project)
        planned = [] if (fail or short) else self._make_clips(project, segments)
        job_id = f"clip:render:{project.id}"
        eta = _eta_seconds(duration, project.max_clips)

        def on_stage(job: Job, stage: Stage) -> None:
            if stage.db_progress is not None:
                project.progress = max(project.progress, stage.db_progress) if stage.state == "processing" \
                    else stage.db_progress
            if stage.message == "downloading source" and job.eta_seconds is None:
                # the worker publishes a real ETA once it has measured the source
                job.eta_seconds = _eta_seconds(project.sim_duration, project.max_clips)
                job.source_duration_seconds = round(project.sim_duration, 2)
            if stage.message.startswith("scoring hooks"):
                project.transcript = segments  # persisted right after transcription
            if stage.state == "completed":
                self._finish_render(project, planned)
            elif stage.state == "failed":
                project.status, project.progress, project.error_message = "failed", 100, stage.message

        if short:
            stages = [
                Stage(0.0, "pending", 0.0, "queued", 0),
                Stage(0.12, "processing", 0.05, "downloading source", 5),
                Stage(0.3, "failed", 1.0, SHORTFALL_WORKER_MESSAGE.format(
                    minutes=needed, needed=needed, balance=self._balance()), 100),
            ]
        else:
            stages = self._render_stages(project, len(planned), len(segments), fail)
        self._new_job(job_id, "render", stages, eta=eta, duration=duration, on_stage=on_stage)
        project.job_id = job_id
        return {
            "message": "Processing queued",
            "video_id": project.id,
            "job_id": job_id,
            "max_clips": project.max_clips,
            "eta_seconds": eta,
            "source_duration_seconds": duration,
        }

    def _finish_render(self, project: Project, clips: list) -> None:
        for clip in self.clips.values():  # a re-process replaces the clip set
            if clip.video_id == project.id and not clip.deleted:
                clip.deleted = True
        for clip in clips:
            clip.created_at = self.now()
            self.clips[clip.id] = clip
        project.status, project.progress = "completed", 100
        project.duration_sec = int(round(project.sim_duration))
        # The paid-span ledger lives on the project row (video.settings), so only a
        # re-run of the SAME row is free; resubmitting a completed link makes a new
        # row and is charged again in full.
        if not project.credits_charged_minutes:
            charge = max(1, math.ceil(project.sim_duration / 60.0))
            self._spend(charge)
            project.credits_charged_minutes = charge
        if project.uploaded:  # uploaded sources are deleted after a successful render
            project.source_deleted = True

    @staticmethod
    def _credits_needed(project: Project) -> int:
        # Billable minutes for the whole source, minus a span this row already paid for.
        if project.credits_charged_minutes:
            return 0
        return max(1, math.ceil(project.sim_duration / 60.0))

    def _start_video(self, source: str, filename: str, max_clips: int, aspect_ratio: str,
                     focus_prompt: Optional[str], *, uploaded: bool = False) -> dict:
        if aspect_ratio not in {"9:16", "3:4", "4:5", "1:1", "16:9"}:
            raise FrameOSHTTPError(422, "Unsupported aspect ratio")
        prior = None
        for project in sorted(self.projects.values(), key=lambda p: p.created_at, reverse=True):
            if project.source == source:
                prior = project
                break
        if prior is not None and prior.status in ("pending", "processing"):
            live = self.jobs.get(f"clip:render:{prior.id}")
            if live is not None and live.current.state in ("pending", "processing"):
                return {"project": self._video_response(prior),
                        "job": {"job_id": f"clip:render:{prior.id}", "status": "already_running"}}
        if self.config.guardrails:
            # Only renders with a live job count: a row left pending by a failed start
            # (for example a 402) must not lock the workspace out.
            active = sum(1 for p in self.projects.values()
                         if p.status in ("pending", "processing") and (prior is None or p.id != prior.id)
                         and (job := self.jobs.get(f"clip:render:{p.id}")) is not None
                         and job.current.state in ("pending", "processing"))
            if active >= self.config.max_concurrent:
                raise FrameOSHTTPError(429, CONCURRENCY_MESSAGE.format(active=active, limit=self.config.max_concurrent))
        if prior is not None and prior.status in ("failed", "cancelled", "pending", "processing"):
            if prior.status in ("failed", "cancelled"):
                prior.status, prior.progress, prior.error_message = "pending", 0, None
            project = prior
            snapshot = self._video_response(project)
            live = self.jobs.get(f"clip:render:{project.id}")
            if project.status in ("processing", "pending") and live is not None \
                    and live.current.state in ("pending", "processing"):
                return {"project": snapshot,
                        "job": {"job_id": f"clip:render:{project.id}", "status": "already_running"}}
        else:
            sim = self._sim_duration(source)
            known = sim if uploaded else self._known_duration_at_submit(source, sim)
            project = Project(
                id=str(uuid.uuid4()),
                title=_clean_text(filename) or self._source_title(source),
                source=source, source_type="url" if source.startswith(("http://", "https://")) else "file",
                filename=filename or None, created_at=self.now(), sim_duration=sim, known_duration=known,
                duration_sec=int(known) if known else None,
                thumbnail_url=f"{MOCK_HOST}/source-thumbs/{_seed_of(source):x}.jpg" if not uploaded else None,
                uploaded=uploaded,
            )
            self.projects[project.id] = project
            snapshot = self._video_response(project)
        if self._balance() <= 0:
            raise FrameOSHTTPError(402, "Out of credits. Upgrade your plan or add credits to keep processing.")
        needed = self._credits_needed(project)
        if self.config.guardrails and project.known_duration is not None \
                and project.known_duration >= MIN_SOURCE_SECONDS and self._balance() < needed:
            raise FrameOSHTTPError(402, SHORTFALL_SUBMIT_MESSAGE.format(
                minutes=needed, needed=needed, balance=self._balance()))
        project.max_clips = max(1, min(20, int(max_clips)))
        project.aspect_ratio = aspect_ratio
        project.focus_prompt = (focus_prompt or "")[:400] or None
        job = self._start_render(project)
        return {"project": snapshot, "job": job}

    def _video_response(self, project: Project, *, count_deleted: bool = False) -> dict:
        # get_project counts soft-deleted clips too (a real-route bug); the submit
        # response (create_video) counts only live ones.
        clips = sum(1 for c in self.clips.values() if c.video_id == project.id and (count_deleted or not c.deleted))
        return {"id": project.id, "status": project.status, "url": project.source,
                "filename": project.filename or "", "clips_count": clips, "progress": project.progress / 100.0}

    def _reap_stray_rows(self) -> None:
        for project in self.projects.values():
            if project.status in ("pending", "processing") and f"clip:render:{project.id}" not in self.jobs:
                if self.now() - project.created_at > STRAY_ROW_REAP_SECONDS:
                    project.status = "failed"
                    project.error_message = project.error_message or STRAY_ROW_MESSAGE

    # ===== API surface (one method per MCP tool) ===============================
    def whoami(self) -> dict:
        return {
            "user_id": self.user_id,
            "organization_id": self.org_id,
            "organization_name": self.org_name,
            "account": {
                "plan": self.config.plan,
                "credits": self._balance(),
                "paid_credits": self.paid_credits,
                "trial_credits": self.trial_credits,
                "trial_credits_expires_at": None,
                "trial_credits_expired": False,
            },
        }

    def get_usage(self) -> dict:
        cutoff = self.now() - 30 * 86400
        items = []
        renders = [p for p in self.projects.values() if p.status == "completed" and p.created_at >= cutoff]
        for p in renders:
            credits = p.credits_charged_minutes if p.credits_charged_minutes else (
                max(1, (p.duration_sec + 59) // 60) if p.duration_sec else None)
            items.append({"id": p.id, "kind": "render", "title": p.title, "thumbnailUrl": p.thumbnail_url,
                          "durationSec": p.duration_sec, "credits": credits, "at": _iso(p.created_at)})
        groups: dict[str, list] = {}
        for row in self.thumbnails:
            if row["created_at"] >= cutoff:
                groups.setdefault(row["jobId"], []).append(row)
        thumb_total = 0
        for job_id, rows in groups.items():
            n = len(rows)
            thumb_total += n * THUMBNAIL_CREDITS_PER
            items.append({"id": job_id, "kind": "thumbnail",
                          "title": f"{rows[0]['title'] or 'Thumbnail'} — {n} thumbnail{'s' if n != 1 else ''}",
                          "thumbnailUrl": self._signed(rows[0]["key"]), "durationSec": None,
                          "credits": n * THUMBNAIL_CREDITS_PER,
                          "at": _iso(max(r["created_at"] for r in rows))})
        items.sort(key=lambda it: it["at"] or "", reverse=True)
        render_total = sum(i["credits"] or 0 for i in items if i["kind"] == "render")
        return {"items": items[:10], "total_count_30d": len(renders) + len(groups),
                "total_credits_30d": int(render_total + thumb_total), "balance": self._balance(),
                "has_more": len(items) > 10}

    def get_brand(self) -> dict:
        if not self.config.brand_logo:
            return {"brand": {}, "logoUrl": None}
        key = f"brand/{self.org_id}/logo-mock.png"
        return {"brand": {"logo": {"gsPath": f"gs://{BUCKET}/{key}", "position": "tr", "sizePct": 0.18,
                                   "opacity": 0.9}},
                "logoUrl": self._signed(key)}

    def submit_video(self, source_url: str, max_clips: int, aspect_ratio: str, focus_prompt: Optional[str]) -> dict:
        payload = _body(_SubmitVideo, {"source_url": source_url, "max_clips": max_clips,
                                       "aspect_ratio": aspect_ratio, "focus_prompt": focus_prompt})
        return self._start_video(payload.source_url, "", payload.max_clips, payload.aspect_ratio,
                                 payload.focus_prompt)

    def list_projects(self, limit: Any, offset: Any) -> list:
        limit = _query_int("limit", limit, ge=1, le=50)
        offset = _query_int("offset", offset, ge=0)
        for project in self.projects.values():
            if project.status in ("pending", "processing"):
                self._observe_project(project)
        self._reap_stray_rows()
        rows = sorted(self.projects.values(), key=lambda p: p.created_at, reverse=True)[offset:offset + limit]
        out = []
        for p in rows:
            job = self.jobs.get(p.job_id or "")
            live = self._job_view(job.id) if job is not None and p.status in ("pending", "processing") else None
            progress = p.progress
            if live is not None and p.status == "processing":
                progress = max(progress, int(round(live["progress"] * 100)))
            out.append({
                "id": p.id, "title": p.title, "status": p.status, "progress": progress,
                "etaRemainingSeconds": (live or {}).get("eta_remaining_seconds")
                if p.status in ("processing", "pending") else None,
                "processingMessage": (live or {}).get("message") or None,
                "source": p.source, "sourceType": p.source_type, "filename": p.filename,
                "thumbnailUrl": p.thumbnail_url, "durationSec": p.duration_sec, "errorMessage": p.error_message,
                "createdAt": _iso(p.created_at),
                "clipCount": sum(1 for c in self.clips.values() if c.video_id == p.id and not c.deleted),
                "clips": [],
            })
        return out

    def get_project(self, project_id: str) -> dict:
        project = self._project(_path_uuid("project_id", project_id))
        if project.status in ("pending", "processing"):
            self._observe_project(project)
        return self._video_response(project, count_deleted=True)

    def get_job(self, job_id: str) -> dict:
        if job_id.startswith("thumb:"):
            parts = job_id.split(":")
            if len(parts) != 3 or parts[1] != self.org_id:
                raise FrameOSHTTPError(404, "Job not found")
        else:
            clip_prefix = next((p for p in ("recap:", "export:", "social:post:") if job_id.startswith(p)), None)
            if clip_prefix is not None:
                try:
                    clip_id = str(uuid.UUID(job_id[len(clip_prefix):].split(":", 1)[0]))
                except ValueError:
                    clip_id = None
                if clip_id is None or clip_id not in self.clips:
                    raise FrameOSHTTPError(404, "Job not found")
            else:
                try:
                    video_id = str(uuid.UUID(job_id.rsplit(":", 1)[-1]))
                except ValueError:
                    raise FrameOSHTTPError(404, "Job not found") from None
                if video_id not in self.projects:
                    raise FrameOSHTTPError(404, "Job not found")
        job = self.jobs.get(job_id)
        if job is not None:
            self._advance(job, observe=True)
        return self._job_view(job_id)

    def get_transcript(self, project_id: str, start_ms: Any, end_ms: Any, offset: Any, limit: Any,
                       include_words: bool) -> dict:
        project_id = _path_uuid("project_id", project_id)
        start_ms = _query_int("start_ms", start_ms, ge=0)
        end_ms = None if end_ms is None else _query_int("end_ms", end_ms, ge=0)
        offset = _query_int("offset", offset, ge=0)
        limit = _query_int("limit", limit, ge=1, le=500)
        if end_ms is not None and end_ms <= start_ms:
            raise FrameOSHTTPError(422, "end_ms must be greater than start_ms")
        project = self._project(project_id, detail="Project not found")
        if not project.transcript:
            raise FrameOSHTTPError(404, "Source transcript unavailable for this project")
        matching = [s for s in project.transcript
                    if s["end"] * 1000 >= start_ms and (end_ms is None or s["start"] * 1000 < end_ms)]
        page = matching[offset:offset + limit]
        page = [self._with_words(s) if include_words else dict(s) for s in page]
        return {"project_id": project_id, "segments": page, "total": len(matching),
                "next_offset": offset + limit if offset + limit < len(matching) else None}

    def list_clips(self, project_id: str) -> list:
        project = self._project(_path_uuid("project_id", project_id))
        rows = [c for c in self.clips.values() if c.video_id == project.id]  # includes soft-deleted rows
        rows.sort(key=lambda c: (c.rank, c.created_at))
        return [self._safe_clip(c) for c in rows]

    def describe_clip(self, clip_id: str) -> dict:
        clip = self._org_clip(_path_uuid("clip_id", clip_id))
        result = self._safe_clip(clip)
        result["layout"] = {k: clip.render_metadata[k] for k in ("layout_dominant", "layout_timeline",
                                                                   "reframe_policy") if k in clip.render_metadata}
        return result

    def duplicate_clip(self, clip_id: str) -> dict:
        original = self._org_clip(_path_uuid("clip_id", clip_id))
        title = self._clip_title(original)
        meta = dict(original.caption) if isinstance(original.caption, dict) else {}
        meta["hook"] = f"{title} (Copy)"
        meta.setdefault("mode", "burned")
        meta.setdefault("style", "none")
        ranks = [c.rank for c in self.clips.values() if c.video_id == original.video_id and not c.deleted]
        copy = Clip(
            id=str(uuid.uuid4()), video_id=original.video_id,
            filename=f"{original.filename.rsplit('.', 1)[0]} (Copy).mp4",
            start_ms=original.start_ms, end_ms=original.end_ms, score=original.score,
            rank=(max(ranks) if ranks else 0) + 1, transcript=original.transcript, media=original.media,
            caption=meta, size_bytes=original.size_bytes, aspect_ratio=original.aspect_ratio,
            created_at=self.now(), render_metadata={**original.render_metadata, "duplicated_from": original.id},
            topic=original.topic,
        )
        self.clips[copy.id] = copy
        return self._safe_clip(copy)

    def set_caption_style(self, clip_id: str, style: str, appearance: Optional[dict]) -> dict:
        clip_id = _path_uuid("clip_id", clip_id)
        payload = _body(_CaptionStyle, {"style": style, "appearance": appearance})
        normalized = _normalize_caption_style(payload.style)
        look = _appearance_or_422(payload.appearance)
        clip = self._org_clip(clip_id)
        mode, _ = self._caption_meta(clip)
        if mode != "overlay":
            raise FrameOSHTTPError(409, "This clip has burned-in captions — use POST /clips/{id}/recaption.")
        meta = dict(clip.caption) if isinstance(clip.caption, dict) else {}
        meta.update({"mode": "overlay", "style": normalized})
        if look:
            meta["appearance"] = look
        else:
            meta.pop("appearance", None)
        clip.caption = meta
        return {"clip_id": clip_id, "mode": "overlay", "style": normalized, "appearance": look}

    def recaption_clip(self, clip_id: str, style: str, appearance: Optional[dict]) -> dict:
        clip_id = _path_uuid("clip_id", clip_id)
        payload = _body(_CaptionStyle, {"style": style, "appearance": appearance})
        clip = self._org_clip(clip_id)
        mode, _ = self._caption_meta(clip)
        if mode == "overlay":
            raise FrameOSHTTPError(
                409,
                "This clip uses overlay captions — set the style via PATCH "
                "/clips/{id}/captions (instant); burning happens on export.",
            )
        head, index = self._media_parts(clip)
        look = _appearance_or_422(payload.appearance)
        raw_style = payload.style or "karaoke"  # NOT validated, exactly like the real route
        job_id = f"recap:{clip_id}:{int(self.now())}"

        def on_stage(job: Job, stage: Stage) -> None:
            if stage.state == "completed":
                meta = dict(clip.caption) if isinstance(clip.caption, dict) else {}
                meta.update({"mode": "overlay", "style": raw_style})
                if look:
                    meta["appearance"] = look
                else:
                    meta.pop("appearance", None)
                clip.caption = meta
                clip.media = f"{head}/clip_{index}_v{int(self.now())}.mp4"

        stages = [
            Stage(0.0, "pending", 0.0, "queued"),
            Stage(0.3, "processing", 0.1, "loading master"),
            Stage(0.55, "processing", 0.4, f"burning {raw_style} captions"),
            Stage(0.8, "processing", 0.8, "uploading"),
            Stage(1.0, "completed", 1.0, f"re-captioned · {raw_style}"),
        ]
        self._new_job(job_id, "recap", stages, on_stage=on_stage)
        return {"job_id": job_id, "clip_id": clip_id, "style": payload.style}

    def export_clip(self, clip_id: str, style: Optional[str], filename: Optional[str]) -> dict:
        clip_id = _path_uuid("clip_id", clip_id)
        payload = _body(_Export, {"style": style, "filename": filename})
        clip = self._org_clip(clip_id)
        mode, persisted = self._caption_meta(clip)
        resolved = _normalize_caption_style(payload.style or persisted or "none")
        raw_name = payload.filename or clip.filename or "clip.mp4"
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", raw_name) or "clip.mp4"
        if not safe_name.lower().endswith(".mp4"):
            safe_name += ".mp4"
        if mode != "overlay" or resolved == "none":
            return {"status": "ready", "style": resolved, "url": self._signed(clip.media, attachment=safe_name)}
        key = self._export_key(clip, resolved, self._caption_appearance(clip))
        if key in self.exported:
            return {"status": "ready", "style": resolved, "url": self._signed(key, attachment=safe_name)}
        job_id = f"export:{clip_id}:{int(self.now())}"

        def on_stage(job: Job, stage: Stage) -> None:
            if stage.state == "completed":
                self.exported.add(key)

        stages = [
            Stage(0.0, "pending", 0.0, "queued"),
            Stage(0.3, "processing", 0.1, "loading master"),
            Stage(0.55, "processing", 0.4, f"burning {resolved} captions"),
            Stage(0.8, "processing", 0.85, "uploading export"),
            Stage(1.0, "completed", 1.0, f"export ready · {resolved}"),
        ]
        self._new_job(job_id, "export", stages, on_stage=on_stage)
        return {"status": "rendering", "job_id": job_id, "style": resolved}

    # ----- collections ----------------------------------------------------------
    def _collection(self, collection_id: str) -> dict:
        collection = self.collections.get(collection_id)
        if collection is None:
            raise FrameOSHTTPError(404, "Collection not found")
        return collection

    def list_collections(self) -> list:
        rows = sorted(self.collections.values(), key=lambda c: c["created_at"], reverse=True)
        return [{"id": c["id"], "name": c["name"], "created_at": _iso(c["created_at"]),
                 "clip_count": sum(1 for cid, _ in c["items"]
                                   if cid in self.clips and not self.clips[cid].deleted)} for c in rows]

    def create_collection(self, name: str) -> dict:
        payload = _body(_NewCollection, {"name": name})
        if any(c["name"] == payload.name for c in self.collections.values()):
            raise FrameOSHTTPError(409, "A collection with that name already exists")
        collection = {"id": str(uuid.uuid4()), "name": payload.name, "created_at": self.now(), "items": []}
        self.collections[collection["id"]] = collection
        return {"id": collection["id"], "name": payload.name, "created_at": _iso(collection["created_at"]),
                "clip_count": 0}

    def add_clip_to_collection(self, collection_id: str, clip_id: str) -> dict:
        collection_id = _path_uuid("collection_id", collection_id)
        payload = _body(_AddCollectionClip, {"clip_id": clip_id})
        collection = self._collection(collection_id)
        clip = self._org_clip(str(payload.clip_id))
        added = all(cid != clip.id for cid, _ in collection["items"])
        if added:
            collection["items"].append((clip.id, self.now()))
        return {"collection_id": collection_id, "clip_id": clip.id, "added": added}

    def list_clips_in_collection(self, collection_id: str) -> list:
        collection = self._collection(_path_uuid("collection_id", collection_id))
        rows = [self.clips[cid] for cid, _ in sorted(collection["items"], key=lambda item: item[1])
                if cid in self.clips and not self.clips[cid].deleted]
        return [self._safe_clip(c) for c in rows]

    def export_collection(self, collection_id: str) -> dict:
        collection_id = _path_uuid("collection_id", collection_id)
        items = self.list_clips_in_collection(collection_id)
        if len(items) > 50:
            raise FrameOSHTTPError(422, "Export up to 50 clips per collection")
        results = []
        for item in items:
            try:
                export = self.export_clip(item["id"], None, None)
            except FrameOSHTTPError as exc:
                export = {"status": "unavailable", "reason": exc.detail}
            results.append({"clip_id": item["id"], **export})
        return {"collection_id": collection_id, "clips": results}

    # ----- uploads ----------------------------------------------------------------
    def create_upload_link(self, filename: str, content_type: Optional[str]) -> dict:
        payload = _body(_SignedUpload, {"filename": filename, "content_type": content_type})
        name = payload.filename or "upload.mp4"
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else "mp4"
        key = f"inputs/{uuid.uuid4().hex}.{ext}"
        expires = self.now() + UPLOAD_CLAIM_SECONDS
        gs_path = f"gs://{BUCKET}/{key}"
        with self.lock:
            self.issued_uploads[key] = expires
        self.upload_claims[gs_path] = (payload.filename[:255], expires)
        upload_url = f"{self.upload_base}/{key}?X-Mock-Signature=mock&X-Mock-Expires={int(expires)}"
        return {"upload_url": upload_url, "gs_path": gs_path}

    def receive_upload(self, key: str, size: int) -> bool:
        """Called by the PUT handler: record that the signed object now exists."""
        with self.lock:
            expires = self.issued_uploads.get(key)
            if expires is None or expires < self.now():
                return False
            self.uploaded_objects[key] = int(size)
            return True

    def submit_uploaded_video(self, gs_path: str, max_clips: int, aspect_ratio: str,
                              focus_prompt: Optional[str]) -> dict:
        payload = _body(_SubmitUploadedVideo, {"gs_path": gs_path, "max_clips": max_clips,
                                               "aspect_ratio": aspect_ratio, "focus_prompt": focus_prompt})
        if not payload.gs_path.startswith(f"gs://{BUCKET}/inputs/"):
            raise FrameOSHTTPError(422, "Invalid uploaded video path")
        claim = self.upload_claims.get(payload.gs_path)
        if claim is None or claim[1] < self.now():
            raise FrameOSHTTPError(404, "Upload link was not issued to this workspace or expired")
        key = payload.gs_path[len(f"gs://{BUCKET}/"):]
        with self.lock:
            present = key in self.uploaded_objects
        if not present:
            raise FrameOSHTTPError(409, "Video upload has not completed")
        result = self._start_video(payload.gs_path, claim[0], payload.max_clips, payload.aspect_ratio,
                                   payload.focus_prompt, uploaded=True)
        self.upload_claims.pop(payload.gs_path, None)
        return result

    # ----- thumbnails -----------------------------------------------------------------
    def create_thumbnail_job(self, clip_id: Optional[str], video_id: Optional[str], url: str,
                             max_thumbnails: int, include_face: bool, aspect: str, style_ref: str) -> dict:
        payload = _body(_Thumbnails, {"clip_id": clip_id, "video_id": video_id, "url": url,
                                      "max_thumbnails": max_thumbnails, "include_face": include_face,
                                      "aspect": aspect, "style_ref": style_ref})
        source_url = (payload.url or "").strip()
        title_hint = ""
        topic = ""
        source_gone = False
        source_aspect = "16:9"
        if payload.clip_id is not None:
            if payload.video_id is not None or payload.url:
                raise FrameOSHTTPError(422, "Provide clip_id, video_id, or url, not more than one")
            clip = self._org_clip(str(payload.clip_id))
            source_url = f"gs://{BUCKET}/{clip.media}"
            title_hint, topic, source_aspect = self._clip_title(clip), clip.topic, clip.aspect_ratio
        elif payload.video_id is not None:
            project = self._project(str(payload.video_id))
            source_url = (project.source or source_url).strip()
            title_hint = project.title
            source_gone = project.uploaded and project.source_deleted
            topic = next((c.topic for c in sorted(self.clips.values(), key=lambda c: c.rank)
                          if c.video_id == project.id and not c.deleted), "")
        if not source_url:
            raise FrameOSHTTPError(400, "A video link is required.")
        requested = payload.max_thumbnails if payload.max_thumbnails else THUMBNAIL_MAX
        n = max(1, min(THUMBNAIL_MAX, int(requested)))
        affordable = self._balance() // THUMBNAIL_CREDITS_PER
        if affordable < 1:
            raise FrameOSHTTPError(402, f"Out of credits. Thumbnails cost {THUMBNAIL_CREDITS_PER} credits each; "
                                        "add credits to continue.")
        n = min(n, int(affordable))
        aspect_key = (payload.aspect or "auto").strip().lower()
        if aspect_key not in THUMBNAIL_ASPECTS:
            raise FrameOSHTTPError(400, f"Unsupported aspect {payload.aspect!r}. Use one of: "
                                        f"{sorted(THUMBNAIL_ASPECTS)}")
        ref = (payload.style_ref or "").strip()
        if ref and not ref.startswith(("gs://", "http://", "https://")):
            raise FrameOSHTTPError(400, "style_ref must be a gs:// or http(s) URL.")
        job_id = f"thumb:{self.org_id}:{int(self.now() * 1000)}"
        width, height = THUMB_CANVAS[source_aspect if aspect_key == "auto" else aspect_key]
        title = title_hint or "Your next favourite video"
        block = BLOCK_BY_KEY.get(topic, BLOCKS[0])

        def on_stage(job: Job, stage: Stage) -> None:
            if stage.state != "completed":
                return
            roles = ("Best Match", "Alternative", "Wildcard")
            templates = ("dynamic_best_match", "dynamic_story_sequence", "dynamic_wildcard_poster")
            thumbs = []
            for i in range(n):
                key = f"thumbnails/{job_id.replace(':', '_')}_{templates[i]}.jpg"
                thumbs.append({
                    "url": self._signed(key),
                    "downloadUrl": self._signed(key, attachment=f"frameos-{roles[i].replace(' ', '_')}.jpg"),
                    "template": templates[i], "role": roles[i],
                    "reason": "Mock layout built from frames of this video.",
                    "fit_score": round(1.0 - i * 0.15, 2), "width": width, "height": height,
                })
                self.thumbnails.append({"id": str(uuid.uuid4()), "key": key, "template": templates[i],
                                        "role": roles[i], "title": title, "width": width, "height": height,
                                        "jobId": job_id, "created_at": self.now()})
            words = block["hook"].upper().split()
            half = max(1, len(words) // 2)
            job.result = {
                "thumbnails": thumbs,
                "title": title,
                "hook": {"topic": block["key"], "kicker": SHOW_NAME.upper(), "line1": " ".join(words[:half]),
                         "line2": " ".join(words[half:]), "rationale": "Mock hook taken from the clip's own words.",
                         "source": "groq_transcript", "template_family": "framed_interview"},
            }
            self._spend(n * THUMBNAIL_CREDITS_PER)

        stages = [Stage(0.0, "pending", 0.0, "queued"),
                  Stage(0.1, "processing", 0.05, "starting"),
                  Stage(0.25, "processing", 0.15, "downloading source")]
        if source_gone:
            stages.append(Stage(0.5, "failed", 1.0, THUMBNAIL_FAILED_MESSAGE))
        else:
            stages += [Stage(0.45, "processing", 0.3, "transcribing clip"),
                       Stage(0.6, "processing", 0.45, "matching your style" if ref else "sampling frames"),
                       Stage(0.8, "processing", 0.8, "finalizing"),
                       Stage(1.0, "completed", 1.0, "done")]
        self._new_job(job_id, "thumb", stages, eta=120, on_stage=on_stage)
        return {"jobId": job_id, "status": "queued"}

    def list_thumbnails(self, limit: Any) -> list:
        limit = _query_int("limit", limit, ge=1, le=100)
        rows = sorted(self.thumbnails, key=lambda r: r["created_at"], reverse=True)[:limit]
        out = []
        for r in rows:
            label = r["title"] or r["role"] or r["template"] or "thumbnail"
            safe = re.sub(r"[^A-Za-z0-9._-]+", "_", label).strip("_") or "thumbnail"
            out.append({"id": r["id"], "url": self._signed(r["key"]),
                        "downloadUrl": self._signed(r["key"], attachment=f"frameos-{safe}.jpg"),
                        "template": r["template"], "role": r["role"], "title": r["title"], "width": r["width"],
                        "height": r["height"], "jobId": r["jobId"], "createdAt": _iso(r["created_at"])})
        return out

    # ----- social -------------------------------------------------------------------------
    def list_social_accounts(self) -> list:
        return [dict(a) for a in self.social_accounts]

    def generate_social_copy(self, clip_id: str, platform: str, tone: str) -> dict:
        clip_id = _path_uuid("clip_id", clip_id)
        payload = _body(_SocialCopy, {"platform": platform, "tone": tone})
        clip = self._org_clip(clip_id)
        transcript = (clip.transcript or "").strip()
        if not transcript:
            raise FrameOSHTTPError(409, "This clip has no transcript")
        now = self.now()
        self.social_copy_calls = [t for t in self.social_copy_calls if now - t < 3600] + [now]
        if len(self.social_copy_calls) > SOCIAL_COPY_LIMIT_PER_HOUR:
            raise FrameOSHTTPError(429, "Social copy limit reached; try again in an hour")
        title = self._clip_title(clip)
        sentences = re.split(r"(?<=[.!?])\s+", transcript)
        tags = list(BLOCK_BY_KEY.get(clip.topic, {}).get("tags", ["#podcast"])) + ["#podcast"]
        if payload.platform == "x":
            caption = f"{title}. {sentences[0]}"[:270]
        elif payload.platform == "linkedin":
            caption = "\n\n".join([f"{title}.", *sentences[:4]])
        elif payload.platform == "instagram":
            caption = f"{title}.\n\n" + " ".join(sentences[:3])
        else:
            caption = " ".join(sentences[:2 if payload.platform in ("youtube", "tiktok") else 3])
        return {"clip_id": clip_id, "platform": payload.platform, "title": title[:100],
                "caption": caption.strip()[:4500], "hashtags": [t[:50] for t in tags[:10]], "posted": False}

    def post_clip(self, clip_id: str, account_id: str, title: str, description: str, privacy: str) -> dict:
        payload = _body(_SocialPost, {"clip_id": clip_id, "account_id": account_id, "title": title,
                                      "description": description, "privacy": privacy})
        clip = self._org_clip(str(payload.clip_id))
        account = next((a for a in self.social_accounts
                        if a["id"] == str(payload.account_id) and a["status"] == "connected"), None)
        if account is None:
            raise FrameOSHTTPError(404, "Social account not found")
        mode, style = self._caption_meta(clip)
        if mode == "overlay":
            resolved = _normalize_caption_style(style or "none")
            if resolved != "none" and self._export_key(clip, resolved, self._caption_appearance(clip)) \
                    not in self.exported:
                raise FrameOSHTTPError(409, "Captions for this clip aren't rendered yet. Export the clip first, "
                                            "then post.")
        effective = payload.privacy if payload.privacy in ("public", "unlisted", "private") else "public"
        job_id = f"social:post:{clip.id}:{int(self.now())}"
        platform = account["platform"]
        post_id = hashlib.sha1(job_id.encode()).hexdigest()
        urls = {
            "youtube": f"{MOCK_HOST}/posts/youtube/shorts/{post_id[:11]}",
            "facebook": f"{MOCK_HOST}/posts/facebook/watch/?v={int(post_id[:12], 16)}",
            "instagram": f"{MOCK_HOST}/posts/instagram/reel/{post_id[:11]}/",
            "linkedin": f"{MOCK_HOST}/posts/linkedin/feed/update/urn:li:share:{int(post_id[:12], 16)}/",
        }
        steps = {
            "youtube": [(0.25, "loading account", 0.1), (0.45, "downloading clip", 0.25),
                        (0.65, "uploading to YouTube", 0.45)],
            "facebook": [(0.25, "loading account", 0.1), (0.45, "downloading clip", 0.25),
                         (0.65, "uploading to Facebook", 0.45)],
            "instagram": [(0.25, "loading account", 0.1), (0.45, "preparing Instagram Reel", 0.25),
                          (0.65, "publishing Instagram Reel", 0.85)],
            "linkedin": [(0.2, "loading account", 0.1), (0.4, "downloading clip", 0.25),
                         (0.55, "preparing LinkedIn video", 0.45), (0.65, "publishing LinkedIn post", 0.9)],
        }
        stages = [Stage(0.0, "pending", 0.0, "queued")]
        stages += [Stage(at, "processing", progress, message) for at, message, progress in steps.get(platform, [])]
        if platform in urls:
            stages.append(Stage(1.0, "completed", 1.0, urls[platform]))
        else:
            stages.append(Stage(0.5, "failed", 1.0, f"posting to {platform} is not supported yet"))
        record = {"clip_id": clip.id, "account_id": account["id"], "platform": platform,
                  "title": (payload.title or "").strip()[:95], "description": (payload.description or "").strip()[:4500],
                  "privacy": effective, "url": urls.get(platform), "job_id": job_id, "published": False}

        def on_stage(job: Job, stage: Stage) -> None:
            if stage.state == "completed":
                record["published"] = True
                self.posts.append(record)

        self._new_job(job_id, "post", stages, on_stage=on_stage)
        return {"job_id": job_id, "platform": platform, "account": account["displayName"]}


# ---------------------------------------------------------------------------
# MCP server: the real tool signatures, titles, annotations and docstrings, verbatim.
# ---------------------------------------------------------------------------
def _call(state: MockState, fn: Callable[..., Any], *args: Any) -> Any:
    state.tick()
    try:
        result = fn(*args)
    except FrameOSHTTPError as exc:
        text = f"FrameOS returned HTTP {exc.status}: {str(exc.detail)[:300]}"
        if state.config.errors == "opaque":
            # Legacy: what the real server showed before it switched to ToolError. It
            # raised RuntimeError, which the mcp 2.2.0 SDK reports to the client only as
            # "Error executing tool <name>".
            raise RuntimeError(text) from None
        raise ToolError(text) from None
    return json.loads(json.dumps(result))


def create_server(state: Optional[MockState] = None) -> MCPServer:
    """Build the mock MCPServer. `server.mock_state` is the backing MockState."""
    state = state or MockState()
    server = MCPServer(
        "frameos",
        title="FrameOS (mock)",
        version="0.1.0",
        instructions=INSTRUCTIONS,
        log_level="WARNING",
    )

    @server.tool(title="Submit Video", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True))
    async def submit_video(
        source_url: str,
        max_clips: int = 3,
        aspect_ratio: Literal["9:16", "3:4", "4:5", "1:1", "16:9"] = "9:16",
        focus_prompt: str | None = None,
    ) -> dict:
        """Submit a video URL for AI clipping. Starts a credit-consuming render job and returns its job ID."""
        return _call(state, state.submit_video, source_url, max_clips, aspect_ratio, focus_prompt)

    @server.tool(title="List Projects", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    async def list_projects(limit: int = 10, offset: int = 0) -> list[dict]:
        """List clipping projects owned by the connected FrameOS account."""
        return _call(state, state.list_projects, limit, offset)

    @server.tool(title="Get Project", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    async def get_project(project_id: str) -> dict:
        """Get the status and summary of one FrameOS clipping project."""
        return _call(state, state.get_project, project_id)

    @server.tool(title="Get Job", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    async def get_job(job_id: str) -> dict:
        """Check render progress using the job ID returned by submit_video."""
        return _call(state, state.get_job, job_id)

    @server.tool(title="List Clips", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    async def list_clips(project_id: str) -> list[dict]:
        """List project clips. If exportRequired is true, call export_clip for the captioned download."""
        return _call(state, state.list_clips, project_id)

    @server.tool(title="Whoami", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    async def whoami() -> dict:
        """Identify the connected FrameOS user, workspace, plan, and credit balance."""
        return _call(state, state.whoami)

    @server.tool(title="Get Usage", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    async def get_usage() -> dict:
        """Read the workspace's recent credit usage and current credit balance."""
        return _call(state, state.get_usage)

    @server.tool(title="Describe Clip", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    async def describe_clip(clip_id: str) -> dict:
        """Read one clip's title, score, transcript, aspect, preview, and export requirement."""
        return _call(state, state.describe_clip, clip_id)

    @server.tool(title="Get Transcript", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    async def get_transcript(
        project_id: str,
        start_ms: int = 0,
        end_ms: int | None = None,
        offset: int = 0,
        limit: int = 100,
        include_words: bool = False,
    ) -> dict:
        """Read a page or time range of the full source-video transcript. New renders store this artifact; older projects may lack it."""
        return _call(state, state.get_transcript, project_id, start_ms, end_ms, offset, limit, include_words)

    @server.tool(title="Get Brand", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    async def get_brand() -> dict:
        """Read the connected workspace's current brand settings; FrameOS has one brand kit, not a template library."""
        return _call(state, state.get_brand)

    @server.tool(title="Export Clip", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False))
    async def export_clip(clip_id: str, style: str | None = None, filename: str | None = None) -> dict:
        """Get a captioned MP4 download. May start an export job; poll get_job, then call again for its URL."""
        return _call(state, state.export_clip, clip_id, style, filename)

    @server.tool(title="Duplicate Clip", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False))
    async def duplicate_clip(clip_id: str) -> dict:
        """Create a separate clip record using the same rendered media, without charging or re-rendering."""
        return _call(state, state.duplicate_clip, clip_id)

    @server.tool(title="List Collections", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    async def list_collections() -> list[dict]:
        """List clip collections in the connected FrameOS workspace."""
        return _call(state, state.list_collections)

    @server.tool(title="Create Collection", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False))
    async def create_collection(name: str) -> dict:
        """Create a named workspace collection for organizing clips."""
        return _call(state, state.create_collection, name)

    @server.tool(title="Add Clip To Collection", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False))
    async def add_clip_to_collection(collection_id: str, clip_id: str) -> dict:
        """Add an owned clip to an owned collection; repeated calls do not create duplicates."""
        return _call(state, state.add_clip_to_collection, collection_id, clip_id)

    @server.tool(title="List Clips In Collection", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    async def list_clips_in_collection(collection_id: str) -> list[dict]:
        """List clips in a workspace collection with fresh preview URLs."""
        return _call(state, state.list_clips_in_collection, collection_id)

    @server.tool(title="Export Collection", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False))
    async def export_collection(collection_id: str) -> dict:
        """Get captioned export URLs or export job IDs for up to 50 clips in a collection."""
        return _call(state, state.export_collection, collection_id)

    @server.tool(title="Create Upload Link", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False))
    async def create_upload_link(filename: str, content_type: str = "video/mp4") -> dict:
        """Get a one-hour signed PUT URL for a video file; upload bytes, then call submit_uploaded_video."""
        return _call(state, state.create_upload_link, filename, content_type)

    @server.tool(title="Submit Uploaded Video", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False))
    async def submit_uploaded_video(
        gs_path: str,
        max_clips: int = 3,
        aspect_ratio: Literal["9:16", "3:4", "4:5", "1:1", "16:9"] = "9:16",
        focus_prompt: str | None = None,
    ) -> dict:
        """Start clipping an uploaded file using the gs_path from create_upload_link. Consumes credits."""
        return _call(state, state.submit_uploaded_video, gs_path, max_clips, aspect_ratio, focus_prompt)

    @server.tool(title="Set Caption Style", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False))
    async def set_caption_style(clip_id: str, style: str, appearance: dict | None = None) -> dict:
        """Change the saved overlay caption style and optional appearance; export uses the new look."""
        return _call(state, state.set_caption_style, clip_id, style, appearance)

    @server.tool(title="Recaption Clip", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False))
    async def recaption_clip(clip_id: str, style: str, appearance: dict | None = None) -> dict:
        """Re-render captions on an older burned-caption clip; returns a job to poll."""
        return _call(state, state.recaption_clip, clip_id, style, appearance)

    @server.tool(title="Create Thumbnail Job", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True))
    async def create_thumbnail_job(
        clip_id: str | None = None,
        video_id: str | None = None,
        url: str = "",
        max_thumbnails: int = 3,
        include_face: bool = False,
        aspect: Literal["auto", "16:9", "9:16", "1:1", "4:5", "3:4"] = "auto",
        style_ref: str = "",
    ) -> dict:
        """Generate up to three thumbnails for a clip, project, or URL. Costs FrameOS credits; returns a job ID."""
        return _call(state, state.create_thumbnail_job, clip_id, video_id, url, max_thumbnails, include_face,
                     aspect, style_ref)

    @server.tool(title="Get Thumbnail Job", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    async def get_thumbnail_job(job_id: str) -> dict:
        """Check a thumbnail job's progress and result images."""
        return _call(state, state.get_job, job_id)

    @server.tool(title="List Thumbnails", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    async def list_thumbnails(limit: int = 30) -> list[dict]:
        """List generated thumbnails in the connected workspace."""
        return _call(state, state.list_thumbnails, limit)

    @server.tool(title="List Social Accounts", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    async def list_social_accounts() -> list[dict]:
        """List social publishing accounts already connected to the FrameOS workspace."""
        return _call(state, state.list_social_accounts)

    @server.tool(title="Generate Social Copy", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False))
    async def generate_social_copy(
        clip_id: str,
        platform: Literal["youtube", "instagram", "facebook", "linkedin", "tiktok", "x"],
        tone: str = "clear and natural",
    ) -> dict:
        """Draft title, caption, and hashtags from a clip transcript using the configured model; does not post or charge credits."""
        return _call(state, state.generate_social_copy, clip_id, platform, tone)

    @server.tool(title="Post Clip", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=True))
    async def post_clip(
        clip_id: str,
        account_id: str,
        title: str = "",
        description: str = "",
        privacy: Literal["public", "unlisted", "private"] = "public",
    ) -> dict:
        """Publish a clip now to a connected social account. Call only when the user explicitly asks to publish."""
        return _call(state, state.post_clip, clip_id, account_id, title, description, privacy)

    server.mock_state = state  # type: ignore[attr-defined]
    return server


# ---------------------------------------------------------------------------
# Upload receiver (signed PUT target) and entry point
# ---------------------------------------------------------------------------
def _upload_key_from_path(path: str) -> Optional[str]:
    path = path.split("?", 1)[0]
    if not path.startswith("/upload/inputs/"):
        return None
    return path[len("/upload/"):]


def start_upload_receiver(state: MockState, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    """Serve PUT /upload/inputs/<name> on a background thread (used in stdio mode
    and by the tests) and point the state's upload links at it."""

    class Handler(BaseHTTPRequestHandler):
        def do_PUT(self) -> None:  # noqa: N802 - http.server naming
            key = _upload_key_from_path(self.path)
            remaining = int(self.headers.get("Content-Length") or 0)
            size = 0
            while remaining > 0:
                chunk = self.rfile.read(min(remaining, 1 << 20))
                if not chunk:
                    break
                size += len(chunk)
                remaining -= len(chunk)
            ok = key is not None and state.receive_upload(key, size)
            self.send_response(200 if ok else 403)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args: Any) -> None:  # keep stdout/stderr clean
            return

    httpd = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=httpd.serve_forever, name="frameos-mock-uploads", daemon=True).start()
    state.upload_base = f"http://{host}:{httpd.server_address[1]}/upload"
    return httpd


def build_http_app(server: MCPServer, host: str, port: int):
    """Streamable HTTP app (stateless + JSON responses, like the real server) with
    the upload PUT route mounted on the same port."""
    from starlette.requests import Request
    from starlette.responses import Response

    state: MockState = server.mock_state  # type: ignore[attr-defined]
    state.upload_base = f"http://{'127.0.0.1' if host in ('0.0.0.0', '::') else host}:{port}/upload"

    @server.custom_route("/upload/{key:path}", methods=["PUT"])
    async def upload(request: Request) -> Response:
        key = _upload_key_from_path(request.url.path)
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
        ok = key is not None and state.receive_upload(key, size)
        return Response(status_code=200 if ok else 403)

    return server.streamable_http_app(stateless_http=True, json_response=True, host=host)


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(description="Stateful mock FrameOS MCP server (no credentials, no credits).")
    parser.add_argument("--http", action="store_true", help="serve Streamable HTTP at /mcp instead of stdio")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_HTTP_PORT, help=f"HTTP port (default {DEFAULT_HTTP_PORT})")
    args = parser.parse_args(argv)

    quiet = str(os.environ.get("FRAMEOS_MOCK_QUIET", "")).strip().lower() in {"1", "true", "yes", "on"}
    server = create_server()
    state: MockState = server.mock_state  # type: ignore[attr-defined]
    if args.http:
        import uvicorn

        app = build_http_app(server, args.host, args.port)
        if not quiet:
            print(f"FrameOS mock MCP server: http://{args.host}:{args.port}/mcp (no auth). Ctrl+C to stop.",
                  file=sys.stderr)
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
        return
    try:
        port = int(os.environ.get("FRAMEOS_MOCK_UPLOAD_PORT", "0"))
    except ValueError:
        port = 0
    start_upload_receiver(state, port=port)
    if not quiet:
        print(f"FrameOS mock MCP server on stdio; upload links PUT to {state.upload_base}/", file=sys.stderr)
    server.run("stdio")


if __name__ == "__main__":
    main()
