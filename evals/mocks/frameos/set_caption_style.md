---
type: agent
expect:
  clip_id: ["5b0e8f3a-7c1d-4e92-b6a4-3d8f1e2c9a07", "c2d7a1e9-3f5b-4a80-9d6c-8e1b4f7a2c36", "9e4f2c6b-1a8d-4f37-8c5e-6b2a9d0f3e18", "2f8a4c1e-6b3d-4e70-9a5c-1d7e3b8f0c64"]
  style: ["karaoke", "default", "shorts-default", "shorts_default", "float", "beasty", "bounce", "deep-diver", "type", "youshaei", "pod-p", "mozi", "popline", "glitch-infinite", "seamless-bounce", "baby-earthquake", "blur-switch", "highlighter-box", "simple", "think-media", "focus", "blur-in", "with-backdrop", "soft-landing", "baby-steps", "grow", "breathe", "instagram", "none"]
---
You play the FrameOS `set_caption_style` tool for the overlay-caption clips in this workspace. Every clip this mock accepts is an overlay clip, so the call always succeeds.

Reply with one JSON object and nothing else:
{"clip_id": "<the clip_id sent>", "mode": "overlay", "style": "<canonical style id>", "appearance": <saved appearance object>}

Canonical style id: lowercase the sent style and change "_" to "-". Then map the aliases "default", "shorts-default" and "float" to "karaoke", "bounce" to "beasty", and "type" to "deep-diver". Any other value is already canonical.

Saved appearance object: start from the "appearance" object that was sent ({} when none was sent or it was null). Keep only the keys font, scale, yPct and anim. Clamp scale to 0.5-2.0, round it to 2 decimals, and drop it when it equals exactly 1.0. Clamp yPct to 0.05-0.95 and round it to 3 decimals. Leave font and anim exactly as sent.

If the font is not one of Montserrat, Poppins, Roboto, Anton, Bebas Neue, Oswald, Archivo, Heebo, Kanit, Lilita One, Spline Sans, Poltawski Nowy, Lemon, Luckiest Guy, Marcellus, Roboto Mono (exact spelling), reply with the single line
ERROR: FrameOS returned HTTP 422: Unknown caption font: <font>
If the anim is not one of pop, scale, scale-in, hover, blur-in, blur-switch, deep-diver, individual-focus, seamless-bounce, baby-earthquake, glitch-infinite-zoom, simple-words-pop, slide-in-from-top, breathe-scale-wiggle, word-level_karaoke_fill-pop, word-level_karaoke_bg-highlight, word-level_simple_bg-highlight, none, reply with the single line
ERROR: FrameOS returned HTTP 422: Unknown caption animation: <anim>
