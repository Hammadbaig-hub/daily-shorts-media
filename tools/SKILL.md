---
name: youtube-daily-shorts
description: Makes and auto-publishes one free Urdu health & nutrition awareness YouTube Short per day for Bright Life — picks a fresh topic, verifies every claim against WHO/NHS-level sources, renders an animated 1080x1920 video with native Urdu narration and moving 3D icons (no AI credits), hosts it on GitHub and schedules it on YouTube through Metricool. Use whenever the user asks to make, post, upload or schedule today's Short, run the daily Shorts routine, manage the channel, or check how the Shorts are doing — even if they just say "aaj ki video bana do" or "YouTube wala kaam kar do".
---

# YouTube Daily Shorts — Health & Nutrition Awareness (Urdu)

One Short per day, fully automatic, zero cost. Since 2026-10-30 the channel posts
**health and nutrition awareness** videos in professional Urdu: everyday habits,
food, water, sleep, movement, hygiene — explained simply, with animated 3D icons
that never stop moving and captions that light up word by word as the voice
speaks. (Before that it posted general "amazing facts"; those are in history.json.)

## Fixed settings (change here if the user changes them)

| Setting | Value |
|---|---|
| GitHub media repo | `Hammadbaig-hub/daily-shorts-media` (public, branch `main`) — also holds the render tools in `tools/` |
| Metricool brand (blogId) | `7592220`, timezone `Asia/Karachi` |
| Channel | "Bright Life", handle `@Bright-Life-m4` |
| Publish time | 19:00 Pakistan time (or the next free slot if that has passed; at least 15 min from now) |
| Privacy | public (user chose full auto-upload) |
| Language | Urdu only |
| Renderer | `tools/scripts/make_health_short.py` |

## Why it is built this way

- **Free:** the user has no budget. Video = Pillow + numpy + ffmpeg; music is
  synthesized in the script (original, so no Content ID claims).
- **Native Urdu voice:** Piper "Fasih" (ur_PK, male, MIT licence), trained on real
  Urdu speech, so the accent is genuinely Pakistani Urdu. Downloads once (~67 MB)
  from the sherpa-onnx GitHub release into `~/tts`. The renderer speeds it up 6%,
  EQs it for clarity, compresses it and normalises the mix to −14 LUFS (YouTube's
  playback level) so it sounds clear and lively on phones. The user approved this
  voice on 2026-10-29.
- **Animation:** Microsoft Fluent 3D emoji (MIT) in `tools/assets/icons/` — they
  pop in, bob, sway and breathe the whole time; faint icons drift in the
  background; captions appear word by word with the spoken word highlighted.
  Constant motion keeps viewers from swiping away.
- **Accuracy and YouTube's medical policy:** YouTube removes health content that
  contradicts WHO or local health authorities, and can strike the channel. Every
  claim must come from an authoritative source, and the channel only does
  *awareness* — never diagnosis, treatment, dosing or cures.

## Daily workflow

### 1. Get the repo and plan the day

```bash
cd ~ && (git -C daily-shorts-media pull -q || git clone https://github.com/Hammadbaig-hub/daily-shorts-media.git)
pip install -q --break-system-packages piper-tts pillow numpy soundfile
python daily-shorts-media/tools/scripts/plan_today.py daily-shorts-media/history.json
```

If the repo is not in the session, attach it first with `add_repo`
(owner `Hammadbaig-hub`, repo `daily-shorts-media`, access `push`) and clone it.

`plan_today.py` returns `theme`, whether a video was already posted today, and
every topic used so far. If `posted_today` is true, stop and report that — never
post twice in one day. Use `theme % 4` as the video's `palette`.

### 2. Pick a topic

Rotate across these so the channel stays varied and useful for Pakistani families:

- **Nutrition:** sugar, salt, oil/ghee and trans fats, fruit vs juice, vegetables,
  daal and protein, whole grains, breakfast, fast food, packaged snacks, cold drinks
- **Water & hydration:** how much, signs of dehydration, heat-wave safety
- **Daily habits:** sleep, walking/physical activity, screen time, sitting too long
- **Hygiene:** handwashing, food safety at home, clean drinking water
- **Body awareness:** blood pressure basics, why checkups matter, dental care,
  eye care, sun and heat
- **Family:** healthy lunchbox ideas for children, breastfeeding facts (WHO),
  elderly nutrition — always general, never personal medical guidance

Pick something not in `already_done` and not a near-duplicate of it.

**Stay away from:** treatment or medicine advice (doses, which pill to take),
cures or "nuskhe", supplements and weight-loss products, claims that a food
treats or prevents a specific disease beyond what WHO/NHS says, vaccines and
reproductive health debates, mental-health crisis content, anything about a real
person, politics, and religious rulings.

### 3. Write the script and verify every claim

Use only these kinds of sources: WHO, NHS (UK), CDC, US NIH/MedlinePlus, Pakistan
Ministry of National Health Services / NIH Pakistan, UNICEF, FAO, or a major
university or hospital health page (e.g. Mayo Clinic, Harvard T.H. Chan). Run
WebSearch/WebFetch, read the actual page, and keep its URL. If a claim can't be
confirmed there, or sources disagree, drop it. Keep numbers exactly as the
source states them, and keep hedges ("تقریباً", "تک").

Structure (40–70 seconds total):
- **hook** — a question or surprising line that stops the scroll (under 14 words)
- **points** — 3–5 short points, one idea each, one or two sentences
- **cta** — one practical action for today + "صحت مند زندگی کے لیے برائٹ لائف کو فالو کریں"
- **disclaimer** — always: "یہ معلومات صرف آگاہی کے لیے ہیں۔ کسی بیماری میں ڈاکٹر سے مشورہ کریں۔"

Write natural, simple, professional Urdu in Urdu script — the way a Pakistani
health presenter talks, not a translation. Write numbers as Urdu words (چھ چمچ,
دس گلاس) so the voice reads them properly, avoid English abbreviations, and keep
sentences short. If a word keeps coming out wrong, add aerab (zabar/zer/pesh) to
that word only.

For each scene pick 1–3 icons that show the idea, add `mark` (`good` ✅, `bad` ❌,
`warn` ⚠️) when the point is a do or a don't, and use `count` when a number of
things is the point (e.g. 10 spoons of sugar). Icon names are the file names in
`tools/assets/icons/`:

water glass milk apple orange banana grapes lemon watermelon avocado carrot
broccoli leafy cucumber salad soup egg fish bread peanuts burger fries soda candy
chocolate donut cake salt teaspoon heart greenheart anatomicalheart lungs brain
tooth bicep runner walking yoga sleep bed zzz check cross warning noentry bulb
sparkles fire sun stopwatch target chartup chartdown stethoscope pill microbe
shield baby child oldman doctor strong happy sick dizzy thinking shocked yum
scale sweat

Save as `script.json`:

```json
{
 "lang": "ur", "palette": 1, "handle": "@Bright-Life-m4",
 "hook": {"text": "...", "icons": ["candy", "shocked"]},
 "points": [
  {"text": "...", "icons": ["soda", "shocked"], "mark": "bad", "count": {"icon": "teaspoon", "n": 10}},
  {"text": "...", "icons": ["apple", "orange", "milk"], "mark": "good"}
 ],
 "cta": {"text": "...", "icons": ["water", "greenheart"]},
 "disclaimer": "یہ معلومات صرف آگاہی کے لیے ہیں۔ کسی بیماری میں ڈاکٹر سے مشورہ کریں۔"
}
```

### 4. Check frames, then render

First draw one frame per scene (takes ~30 s) and look at the contact sheet:

```bash
PREVIEW=1 python daily-shorts-media/tools/scripts/make_health_short.py script.json out.mp4
```

It writes `out.mp4.scene0.png`, `scene1.png`, … Look at them with Read: text
inside the white card, highlight on the right word, icons not overlapping the
card. If a caption is too long, shorten that line. Delete the PNGs, then render:

```bash
python daily-shorts-media/tools/scripts/make_health_short.py script.json daily-shorts-media/videos/<date>-<slug>.mp4 > render.log 2>&1
```

Rendering takes about 6–8 minutes on CPU, so run it with Bash `run_in_background`
and wait for the completion notice. Don't wait with a `pgrep -f make_` loop — it
matches its own command line and never ends. The script refuses anything over 3
minutes; aim for 40–70 s.

### 5. Push to GitHub

Append today's entry to `history.json`:
`{"date": "...", "lang": "ur", "theme": n, "niche": "health", "topic": "...", "title": "...", "file": "videos/...mp4"}`

Keep only the 20 newest `.mp4` files in `videos/` (Metricool keeps its own copy).
Then:

```bash
cd daily-shorts-media && git add -A && git commit -qm "Short <date>: <topic>" && git push -q
```

Public URL: `https://raw.githubusercontent.com/Hammadbaig-hub/daily-shorts-media/main/videos/<file>.mp4`
— check it returns 200 (`curl -sI <url> | head -1`) before scheduling.

### 6. Schedule on YouTube through Metricool

Call `createScheduledPost` with `blogId` `7592220`, a top-level `date`
(`YYYY-MM-DDT19:00:00+05:00` — the call fails without it), and this `info` JSON:

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
    "tags": ["صحت", "health tips urdu", "nutrition", "..."],
    "category": "EDUCATION",
    "madeForKids": false,
    "isAiGeneratedContent": false
  }
}
```

`isAiGeneratedContent` stays false: the video is animated icons and text, not
realistic synthetic footage of people or events, which is what YouTube's
disclosure covers.

**Title (Urdu):** under 70 characters, a curiosity or benefit hook + emoji +
`#shorts`, e.g. `ایک کین سوڈا میں دس چمچ چینی؟! 🥤 #shorts`.

**Description:** 2–3 Urdu lines on the takeaway, the disclaimer line, then
`Sources:` with every URL used, then hashtags: `#صحت #HealthTipsUrdu #Nutrition
#shorts` plus 1–2 topic tags.

### 7. Report

Tell the user in Roman Urdu, in a few lines: topic, title, scheduled time, and the
Metricool `plannerUrl`. If running as a scheduled task with nobody watching,
send that summary with SendUserMessage.

## Weekly check (Sundays, or when asked "channel kaisa chal raha hai")

Use `getAnalyticsDataByMetrics` for YouTube over the last 7 days (views, watch
time, subscribers gained, top videos). Say which topics did best and lean next
week's choices toward those categories.

## When something fails

- **Metricool rejects the post:** report the exact error; don't retry the same
  input. Common causes: missing top-level `date`, video URL not reachable yet
  (wait a minute, retry once), or the YouTube connection in Metricool expired
  (user must reconnect it in Metricool).
- **Git push fails:** call `add_repo` with `access: push`. If it still says Claude
  has no GitHub access, the Claude GitHub App must include `daily-shorts-media`
  (github.com/settings/installations → Claude → Configure); the user confirms that
  step because GitHub asks for 2FA.
- **Urdu voice download fails:** fall back to the older renderer
  `tools/scripts/make_short.py` (Kokoro voice) so the day still gets a video,
  and say so in the report.
- **Icons/fonts missing:** they live in `tools/assets/`; the scripts read them from there.
