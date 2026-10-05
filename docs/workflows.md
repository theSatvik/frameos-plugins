# Prompt library

Copy these into your agent and swap in your own links and details. They work in any app where FrameOS is installed (see the [install guides](install/)). You don't need to name tools or IDs: say what you want, the way you'd brief an editor.

Each prompt says what to expect, including anything that uses credits. Renders cost 1 credit per started minute of source video and are only charged when clips are delivered; thumbnails cost 10 credits each; everything else on this page is free.

**Jump to:** [Get started](#get-started) - [Clip](#clip-a-video) - [Captions](#captions) - [Find moments](#find-moments) - [Thumbnails](#thumbnails) - [Copy and posting](#copy-and-posting) - [Library](#library) - [Content packs](#content-packs) - [Things your agent will send to the web app](#things-your-agent-will-send-to-the-web-app)

## Get started

### 1. Check the connection

```text
Is FrameOS connected? What's my credit balance, and what can you do with it?
```

Your agent confirms your workspace and balance, then suggests a few things to try. If you're not signed in, it walks you through signing in.

### 2. Fix a sign-in problem

```text
FrameOS keeps saying I need to sign in. Can you fix it?
```

You get the exact sign-in step for the app you're using.

## Clip a video

### 3. Shorts, Reels or TikTok

```text
Turn this into 3 vertical shorts: https://www.youtube.com/watch?v=...
```

Up to 3 clips in 9:16. Your agent tells you roughly how long the render will take (usually 10 to 30 minutes) and checks back on its own.

### 4. A different format

```text
Clip this podcast episode into 8 clips for my Instagram feed: https://vimeo.com/...
```

Instagram feed maps to 4:5. Other formats: 3:4, 1:1 (square) and 16:9 (landscape). You can ask for up to 20 clips; it's a maximum, so you may get fewer.

### 5. Steer it toward a topic

```text
Make 5 clips about pricing and hiring from https://www.youtube.com/watch?v=... - we say "pricing", "price" and "hiring" a lot.
```

The focus is a preference, not a filter, and it's matched on words. Include the words the speaker actually says.

### 6. A file on your computer

```text
Clip this file into 3 shorts: ~/Videos/episode-42.mp4
```

Needs an agent that can run commands (Claude Code, Codex, Gemini CLI, Cursor and similar). In chat apps, use a public link or upload in the web app.

### 7. Come back to a render

```text
Check my FrameOS render.
```

Your agent finds your newest project and tells you whether it's still processing, finished, or failed and why.

### 8. Several videos at once

```text
Clip each of these into 3 shorts: https://... https://... https://...
```

Your agent confirms the batch and the credit use with you before starting.

### 9. Get the files

```text
Give me the MP4s for clips 1 and 3.
```

Your agent exports them with captions burned in. An export usually takes 15 to 60 seconds. Download links last about an hour; ask again for fresh ones.

## Captions

### 10. Bigger, higher

```text
Make the captions on clip 2 bigger and move them up a little, then export it.
```

Size and position change instantly and for free; the export renders the new look.

### 11. A punchy style

```text
Give my best clip MrBeast-style captions and export it.
```

Your agent picks a bold style from FrameOS's catalogue, such as Beasty, and tells you what it chose.

### 12. A clean podcast look

```text
Use the Simple caption style with the Montserrat font and no animation on all clips from my last project.
```

There are 22 caption styles, 16 fonts and 17 animations. Ask "what caption styles can I use?" for the list.

### 13. No captions

```text
Export clip 4 without captions.
```

## Find moments

These work on videos FrameOS has processed. Full transcripts are stored for videos processed after the connector launched; older projects only have each clip's own transcript.

### 14. Find a topic

```text
Where in last week's episode do we talk about fundraising? Give me quotes with timestamps.
```

### 15. Summarise an episode

```text
Summarise my latest episode in 5 bullet points, with the timestamp for each.
```

Speech in other languages is translated to English by default.

### 16. Pick moments to clip

```text
Find 5 moments in that episode that would make great shorts, and tell me why each one works.
```

### 17. Re-clip with a focus

```text
Re-clip that episode, focusing on the part where we talk about the launch.
```

FrameOS can't cut an exact time range here. Instead your agent re-runs the video with a focus built from the words used in that part. A re-run of a finished video is a new render and is charged again for the whole video, so your agent shows the estimate and asks before it starts.

## Thumbnails

### 18. YouTube thumbnails

```text
Make 3 YouTube thumbnails for clip 1.
```

Landscape 16:9, made from real frames of your video with text layout. 10 credits each, ready in about 2 minutes.

### 19. Match a style

```text
Make one vertical thumbnail for my Shorts version, in the style of this one: https://example.com/reference-thumbnail.jpg
```

The reference must be a public image link.

### 20. Find earlier thumbnails

```text
Show me the thumbnails I made this week.
```

## Copy and posting

Drafting never posts. Posting happens only when you ask for it, and your agent shows you the platform, account, text and privacy and waits for your yes on every single post.

### 21. Draft a post

```text
Write a LinkedIn post for clip 2 in a friendly, practical tone.
```

Drafts are based on what's said in the clip. Edit them before you use them.

### 22. Copy for several platforms

```text
Draft a title, caption and hashtags for YouTube, Instagram and TikTok for my top clip.
```

TikTok and X get copy only; FrameOS can't post there.

### 23. Post to YouTube

```text
Post clip 2 to my YouTube channel as unlisted.
```

If the clip's captions haven't been rendered in its current style yet, your agent exports it first. You get the link to the live post when it's done, usually within 1 to 3 minutes.

### 24. Check your connected accounts

```text
Which social accounts can FrameOS post to?
```

YouTube, a Facebook Page, an Instagram Business account and a LinkedIn personal profile. Accounts are connected in the web app. Instagram and LinkedIn posts are always public, and "unlisted" on Facebook still posts publicly.

## Library

### 25. Recent projects

```text
Show my last 5 projects and how many clips each one has.
```

### 26. Make a collection

```text
Put my 3 best clips from this week in a collection called "October launch".
```

Collection names are unique; if one already exists, your agent adds to it.

### 27. Export a collection

```text
Export everything in the "October launch" collection.
```

FrameOS renders up to 10 clips of a collection at a time, so for a big collection your agent asks for the rest once the first ones finish.

### 28. Where did my credits go?

```text
What did I spend FrameOS credits on in the last 30 days?
```

## Content packs

### 29. A week of content

```text
Turn this webinar into a week of content: 5 vertical clips with Beasty captions, a thumbnail for each, and copy for YouTube Shorts and LinkedIn. https://www.youtube.com/watch?v=...
```

Your agent shows you one plan first, including credit use (the render, plus 10 credits per thumbnail), and starts only when you approve. You get a summary table at the end; posting, if you want it, is confirmed post by post.

### 30. Pick it back up

```text
Let's finish the content pack for episode 42.
```

Progress lives in FrameOS (the project and its collection), so your agent can resume in a new conversation.

## Things your agent will send to the web app

These aren't available through your agent. It will say so and, where the web app offers them, point you to https://frameos.studio/dashboard:

- Scheduling posts, share links, censoring or bleeping, dubbing, free-form timeline edits.
- Choosing the exact clip length, or rendering a whole video without clipping.
- Cancelling a render that has started.
- Posting to TikTok or X.
- Connecting social accounts or uploading a brand logo.
- Renaming or deleting collections, or removing a clip from one (not available yet; your agent can make a new collection with just the clips you want).
