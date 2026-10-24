---
name: youtube-daily-shorts
description: Makes and auto-publishes one free animated-text "facts / motivation" YouTube Short per day — picks a fresh topic, verifies every fact on the web, renders a 1080x1920 video with code (no AI credits), hosts it on GitHub and schedules it on YouTube through Metricool, alternating English and Urdu days. Use this whenever the user asks to make, post, upload or schedule today's YouTube Short, run the daily Shorts routine, manage the facts channel, or check how the Shorts are performing — even if they just say "aaj ki video bana do" or "YouTube wala kaam kar do".
---

# YouTube Daily Shorts

One Short per day, fully automatic, zero cost. The channel posts "Did you know?"
style facts and short motivational pieces, one day in English and the next in Urdu.

## Fixed settings (change here if the user changes them)

| Setting | Value |
|---|---|
| GitHub media repo | `Hammadbaig-hub/daily-shorts-media` (public, branch `main`) — also holds the render tools in `tools/` |
| Metricool brand (blogId) | `7592220`, timezone `Asia/Karachi` |
| Channel | "Bright Life", handle `@Bright-Life-m4` (put the handle in script.json; CTA mentions "Bright Life") |
| Publish time | 19:00 Pakistan time (or the next free slot if that has passed; at least 15 min from now) |
| Privacy | public (user chose full auto-upload) |

## Why it is built this way

- **Free:** the user has no budget, so the video is drawn with Pillow + ffmpeg
  (`tools/scripts/make_short.py` in the repo) and the music is synthesized in the same script, which
  also means no Content ID copyright claims.
- **Voiceover:** narration comes from Kokoro, a small free neural TTS model that
  runs offline on CPU (`tools/scripts/voice.py`). Its ~350 MB model files download once
  from GitHub releases into `~/tts`. English uses `am_michael`; Urdu is spoken by
  the Hindi voice `hm_omega` from Urdu-script text, with a few phonemes remapped.
  Each slide lasts as long as its narration, and the music is ducked underneath.
  Cloud TTS (Microsoft/Google) is blocked from the workspace, which is why it is offline.
- **GitHub hosting:** Metricool needs a public video URL. The cloud workspace can
  push to GitHub, and the raw file URL is public, so that is the bridge.
- **Fact-checking:** a facts channel lives or dies on accuracy. YouTube also
  suppresses mass-produced, low-value or misleading content, and a wrong "fact"
  invites dislikes and correction comments. Every fact gets verified before it is
  used — this is the part of the job that adds real value.

## Daily workflow

### 1. Get the repo and plan the day

```bash
cd ~ && (git -C daily-shorts-media pull -q || git clone https://github.com/Hammadbaig-hub/daily-shorts-media.git)
pip install -q --break-system-packages kokoro-onnx soundfile pillow numpy
python daily-shorts-media/tools/scripts/plan_today.py daily-shorts-media/history.json
```

If the repo is not in the session, attach it first with `add_repo`
(owner `Hammadbaig-hub`, repo `daily-shorts-media`, access `push`) and clone it.

`plan_today.py` returns today's `lang`, `theme`, whether a video was already
posted today, and every topic used so far. If `posted_today` is true, stop and
report that — never post twice in one day.

### 2. Pick a topic

Rotate across categories so the channel stays varied: space, animals, human body,
history, geography, science, technology, food, ocean, inventions, language,
and roughly one day in five a motivation piece (a lesson or habit backed by a real
study, or a well-documented true story). Pick something not in `already_done` and
not a near-duplicate of it.

Stay away from: medical or diet advice, politics, sectarian or religious debate,
anything about real private people, and "facts" that are commonly repeated myths
(e.g. goldfish 3-second memory, the Great Wall being visible from space).

### 3. Write the script and verify it

Write a hook (under 12 words, curiosity-driven), 3–5 facts (each one sentence,
under 25 words), and a CTA.

For every fact, run a WebSearch and confirm it from a reliable source (NASA,
National Geographic, Britannica, a university, a peer-reviewed study, a major
encyclopedia). If a fact can't be confirmed, or sources disagree, drop it and use
another. Keep the source URLs — they go in the description.

Urdu days: write natural, simple Urdu in Urdu script (not Roman Urdu), the way a
Pakistani viewer speaks — not a word-for-word translation. Write numbers as
Urdu words (بیس فیصد, ہزاروں) so the voice pronounces them correctly.

CTA examples — EN: "Follow Bright Life for a new fact every day". UR: "روزانہ نئے حقائق کے لیے برائٹ لائف کو فالو کریں".

Save as `script.json`:

```json
{"lang": "en", "hook": "...", "facts": ["...", "..."], "cta": "...",
 "handle": "@Bright-Life-m4", "theme": 2}
```

### 4. Render

```bash
python daily-shorts-media/tools/scripts/make_short.py script.json daily-shorts-media/videos/<date>-<slug>.mp4 > render.log 2>&1
```

Rendering takes about 5 minutes on CPU, so run it with Bash `run_in_background`
and wait for the completion notice. Don't wait with a `pgrep -f make_short` loop —
it matches its own command line and never ends. Length follows the narration — usually 25–45 s for 3–5 facts. Keep it under
55 s so it stays a Short: if the facts are long, use 3 instead of 5.

Because the text is spoken, write it to be *heard*: spell out awkward symbols
("percent", not "%" in English; "فیصد" in Urdu), avoid brackets and
abbreviations, and keep sentences short so the voice doesn't rush. Then grab one frame and look at it with Read to
catch text overflow or broken Urdu:

```bash
ffmpeg -loglevel error -y -ss 5.5 -i <video> -frames:v 1 check.png
```

If text runs off the edge or looks wrong, shorten that line and re-render.

### 5. Push to GitHub

Append today's entry to `history.json`:
`{"date": "...", "lang": "...", "theme": n, "topic": "...", "title": "...", "file": "videos/...mp4"}`

Keep only the 20 newest `.mp4` files in `videos/` (delete older ones — they are
already on YouTube) so the repo stays small. Then:

```bash
cd daily-shorts-media && git add -A && git commit -qm "Short <date>: <topic>" && git push -q
```

Public URL: `https://raw.githubusercontent.com/Hammadbaig-hub/daily-shorts-media/main/videos/<file>.mp4`

Check it returns 200 before scheduling (`curl -sI <url> | head -1`); if the
workspace can't reach that host, trust the successful push and continue.

### 6. Schedule on YouTube through Metricool

Call `createScheduledPost` with `blogId` `7592220`, a top-level `date`
(`YYYY-MM-DDT19:00:00+05:00` — the call fails without it), and this `info` JSON
(Metricool copies the video into its own storage, so the GitHub file can be
pruned later):

```json
{
  "providers": [{"network": "youtube"}],
  "text": "<description>",
  "media": ["<raw GitHub URL>"],
  "publicationDate": {"dateTime": "YYYY-MM-DDT19:00:00", "timezone": "Asia/Karachi"},
  "autoPublish": true,
  "draft": false,
  "descendants": [], "firstCommentText": "", "hasNotReadNotes": false,
  "mediaAltText": [], "shortener": false, "smartLinkData": {"ids": []},
  "youtubeData": {
    "title": "<title>",
    "type": "short",
    "privacy": "public",
    "tags": ["facts", "did you know", "..."],
    "category": "EDUCATION",
    "madeForKids": false,
    "isAiGeneratedContent": false
  }
}
```

`isAiGeneratedContent` is false because the video is plain animated text, not
realistic synthetic footage; YouTube's disclosure is meant for realistic altered
media. If a later version adds AI-generated realistic visuals or voices, set it
to true.

**Title:** under 70 characters, curiosity hook + `#shorts`. Write it in the
day's language. Example: `Your Brain Can't Feel Pain?! 🧠 #shorts`

**Description:** 2–3 lines expanding the hook, then `Sources:` with the URLs
you verified, then 3–5 hashtags (`#facts #didyouknow #shorts` plus topic tags;
Urdu days add `#urdu #urdufacts`).

### 7. Report

Tell the user in Roman Urdu, in a few lines: topic, language, title, scheduled
time, and the Metricool `plannerUrl`. If running as a scheduled task with nobody
watching, send that summary with SendUserMessage.

## Weekly check (Sundays, or when asked "channel kaisa chal raha hai")

Use `getAnalyticsDataByMetrics` for the YouTube network over the last 7 days
(views, watch time, subscribers gained, top videos). Summarize what worked —
which categories and which language got more views — and use that to lean
next week's topic choices toward what performs. Keep the alternating language
unless the user says otherwise.

## When something fails

- **Metricool rejects the post:** report the exact error; don't retry the same
  input. Common causes: missing top-level `date`, video URL not reachable yet (wait a minute, retry once),
  or the YouTube connection in Metricool expired (user must reconnect it in Metricool).
- **Git push fails:** the repo isn't attached with push access — call `add_repo`
  with `access: push`. If it still says Claude has no GitHub access, the Claude
  GitHub App must have `daily-shorts-media` in its selected repositories
  (github.com/settings/installations → Claude → Configure); the user confirms
  that step themselves because GitHub asks for 2FA.
- **Fonts missing:** they live in `tools/assets/fonts/` in the repo; the script reads them from there.
- **Voice model download fails:** render with `"voice": false` in script.json so
  the day's video still goes out (music only), and mention it in the report.
