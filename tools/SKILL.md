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
| Language | Urdu voice and captions; YouTube **title in English** (since 2026-11-12) |
| Voice | ElevenLabs `eleven_v3` via GitHub Actions (since 2026-11-12); Piper "Fasih" only as fallback |
| Renderer | `tools/scripts/make_remotion_short.py` (Remotion, since 2026-11-12; "Myth ya Fact?" style since 2026-11-02). Fallback: `make_myth_short.py` |

## Why it is built this way

- **Free:** the user has no budget. Audio (voice, SFX, beat, mix) = Python +
  ffmpeg; music is synthesized in the script (original, so no Content ID claims).
- **Remotion visuals (user asked for Remotion on 2026-11-12):** the video is drawn
  by the Remotion project in `tools/remotion/` (React, rendered in headless
  Chrome) — proper Nastaliq shaping, smooth spring animations. Python
  (`make_myth_short.py` with `TIMELINE_OUT`) still makes the audio mix and a
  word-timed `timeline.json`; `make_remotion_short.py` runs both. Remotion can't
  download its own Chrome in the cloud sandbox, so `remotion.config.ts` points it
  at the preinstalled Playwright headless shell (`REMOTION_CHROME` overrides).
  Remotion is free for individuals/teams up to 3 people.
- **Urdu voice = ElevenLabs (since 2026-11-12):** the user found the free Piper
  "Fasih" voice bad with wrong pronunciation, rejected all free alternatives
  (Kokoro/Piper Hindi voices), and chose ElevenLabs with **his own ElevenLabs
  account**. Model `eleven_v3` (speaks Urdu), about 520 characters per video.
  The cloud sandbox can't reach api.elevenlabs.io, so the GitHub Actions workflow
  `.github/workflows/eleven-tts.yml` makes the audio (repo secret
  `ELEVENLABS_API_KEY`; optional repo variables `ELEVENLABS_VOICE_ID`,
  `ELEVENLABS_MODEL`) and commits `voice/<date>/seg*.mp3` + character
  timestamps, which give exact word-by-word caption timing. The user picked a
  deep male voice ("Marcus" in a Higgsfield test); until he sets
  `ELEVENLABS_VOICE_ID`, the premade male voice "Brian" is used.
  The mix is EQ'd, compressed and normalised to −14 LUFS (YouTube's level).
  **Fallback:** Piper "Fasih" (old voice) only if the workflow fails — and say so.
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

Pick a theme not in `already_done` and not a near-duplicate of it. A theme can
revisit an earlier area (sugar, fruit) only with new beliefs/facts.

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

**Format (since 2026-11-02): "Myth ya Fact?"** — the user found the old
tip-list Shorts slow and boring, and approved this faster style. Each video is a
quiz: a hook, then 3 popular beliefs about one theme, each answered with a
MYTH (غلط) or FACT (سچ) stamp, then a comment CTA. Mix verdicts (e.g. 2 myths +
1 fact) so viewers can't guess. 30–45 seconds total.

- **hook** — under 12 words, a challenge: "یہ تین باتیں سب مانتے ہیں! لیکن کیا یہ سچ ہیں؟"
- **items** — exactly 3. `claim` = the belief as people say it (short, ends with
  "!"), `verdict` = `myth` or `fact`, `explain` = starts with "غلط!" or "بالکل سچ!",
  then one or two short sentences with the sourced fact.
  A *myth* is only a myth if the source clearly says the opposite; a *fact* must
  be stated by the source. Pick beliefs Pakistani families really hold.
- **cta** — "آپ کتنے صحیح نکلے؟ کمنٹ میں بتائیں! صحت مند زندگی کے لیے برائٹ لائف کو فالو کریں"
- **disclaimer** — always: "یہ معلومات صرف آگاہی کے لیے ہیں۔ کسی بیماری میں ڈاکٹر سے مشورہ کریں۔"

Never make a "myth" out of something a health authority recommends, and never
frame a treatment, medicine or remedy as a fact.

Write natural, simple, professional Urdu in Urdu script — the way a Pakistani
health presenter talks, not a translation. Write numbers as Urdu words (تیس گرام,
دس گلاس) so the voice reads them properly, avoid English abbreviations, and keep
sentences short; use "!" and "؟" — the voice reads them with more energy. If a
word keeps coming out wrong, add aerab (zabar/zer/pesh) to that word only.

Pick 1–3 icons per claim and per explanation, and an optional `mark` (`good` ✅,
`bad` ❌, `warn` ⚠️) on the explanation. Icon names are the file names in
`tools/assets/icons/` (more Fluent 3D emoji, MIT, can be added from
github.com/microsoft/fluentui-emoji `assets/<Name>/3D/*_3d.png`, resized to 256×256):

water glass milk apple orange banana grapes lemon watermelon avocado carrot
broccoli leafy cucumber salad soup egg fish bread peanuts burger fries soda candy
chocolate donut cake salt teaspoon honey potato ice droplet heart greenheart
anatomicalheart lungs brain tooth bicep runner walking yoga sleep bed zzz check
cross warning noentry bulb sparkles fire sun stopwatch target chartup chartdown
stethoscope pill microbe shield baby child oldman doctor strong happy sick dizzy
thinking shocked yum scale sweat

Save as `script.json`:

```json
{
 "lang": "ur", "palette": 0, "handle": "@Bright-Life-m4",
 "hook": {"text": "یہ تین باتیں سب مانتے ہیں! لیکن کیا یہ سچ ہیں؟", "icons": ["shocked", "thinking"]},
 "items": [
  {"claim": "شہد قدرتی ہے، اس لیے جتنا مرضی کھائیں!", "claim_icons": ["honey", "teaspoon"],
   "verdict": "myth",
   "explain": "غلط! شہد کی مٹھاس بھی چینی میں گنی جاتی ہے۔ ...", "explain_icons": ["honey", "candy"], "mark": "warn"},
  {"claim": "...", "claim_icons": ["potato", "thinking"], "verdict": "fact",
   "explain": "بالکل سچ! ...", "explain_icons": ["potato", "bread"]}
 ],
 "cta": {"text": "آپ کتنے صحیح نکلے؟ کمنٹ میں بتائیں! صحت مند زندگی کے لیے برائٹ لائف کو فالو کریں", "icons": ["greenheart", "happy"]},
 "disclaimer": "یہ معلومات صرف آگاہی کے لیے ہیں۔ کسی بیماری میں ڈاکٹر سے مشورہ کریں۔"
}
```

### 3b. Make the ElevenLabs voice (GitHub Actions)

```bash
python daily-shorts-media/tools/scripts/eleven_prep.py script.json daily-shorts-media/voice/<date>
cd daily-shorts-media && git add voice && git commit -qm "Voice job <date>" && git push -q
```

Then start the workflow with the GitHub MCP tool `actions_run_trigger`
(method `run_workflow`, owner `Hammadbaig-hub`, repo `daily-shorts-media`,
workflow_id `eleven-tts.yml`, ref `main`, inputs `{"job": "voice/<date>"}`).
Find the run with `actions_list` (`list_workflow_runs`, resource_id
`eleven-tts.yml`) and check it with `actions_get` (`get_workflow_run`) every
~30 s (Bash `sleep 30` between checks) — it takes about 1 minute. When it
succeeds, `git pull` and check `voice/<date>/seg0.mp3` … exist. If it fails,
read the log with `get_job_logs` (failed_only) and report the exact error
(e.g. missing secret, quota used up, invalid voice ID); then render with the
Piper fallback (leave out `VOICE_DIR`) so the day still gets a video.

If you change script.json after this step, rerun this step — the renderer
refuses voice files whose text doesn't match.

### 4. Check frames, then render

Renderer: `tools/scripts/make_remotion_short.py` (Remotion) — vivid gradient
backgrounds with rotating light rays and drifting icons, big 2–3-word kinetic
captions (spoken word in yellow with a pop), 3-2-1 suspense ring with ticks after
each claim, MYTH/FACT stamp slam with shake, flash and buzzer/ding, zoom punches
and whooshes, a 124 bpm original beat that ducks under the voice, and the
livelier Fasih voice. Same `script.json` as before. The first run in a fresh
sandbox does `npm ci` in `tools/remotion` automatically (~1 min).

First draw one frame per segment (~1 min) and look at the contact sheet:

```bash
VOICE_DIR=daily-shorts-media/voice/<date> PREVIEW=1 python daily-shorts-media/tools/scripts/make_remotion_short.py script.json out.mp4
```

It writes `out.mp4.seg0.png`, `seg1.png`, … and `out.mp4.sheet.png`. Look at the
sheet with Read: captions fully visible and not clipped, stamp readable, icons
not covering the caption. Delete the PNGs, then render:

```bash
VOICE_DIR=daily-shorts-media/voice/<date> python daily-shorts-media/tools/scripts/make_remotion_short.py script.json daily-shorts-media/videos/<date>-<slug>.mp4 > render.log 2>&1
```

Rendering takes about 4–5 minutes on 2 CPUs; run it with Bash `run_in_background`
(or a 600000 ms timeout) and wait for the completion notice. Don't wait with a
`pgrep -f make_` loop — it matches its own command line and never ends. Aim for
30–45 s. Never leave `tools/remotion/public/{job,icons,fonts}` or
`tools/remotion/out` in a commit (they are git-ignored).

If the Remotion render fails (npm install or Chrome problem), use the Pillow
renderer for the same script so the day still gets a video, and say so in the
report:

```bash
python daily-shorts-media/tools/scripts/make_myth_short.py script.json daily-shorts-media/videos/<date>-<slug>.mp4 > render.log 2>&1
```

The old calm tip-list renderer, `make_health_short.py` (script format with
`points`), stays as a last fallback.

### 5. Push to GitHub

Append today's entry to `history.json`:
`{"date": "...", "lang": "ur", "theme": n, "niche": "health", "style": "myth-fact", "topic": "...", "title": "...", "file": "videos/...mp4"}`

Keep only the 20 newest `.mp4` files in `videos/` (Metricool keeps its own copy) and the 20 newest folders in `voice/`.
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

**Title (ENGLISH, since 2026-11-12):** the user saw very low views with Urdu-script
titles and asked for titles in English. Write the title in simple English (no Urdu
script), under 70 characters: a curiosity/quiz hook + emoji + `#shorts`, and add
"Urdu" or "Pakistan" when it fits naturally so the audience knows the language,
e.g. `Is Banaspati Ghee Safe? Myth or Fact! 🧈 #shorts` or
`Eat Unlimited Honey? Myth or Fact | Urdu Health Tips 🍯 #shorts`.
The video itself (voice and captions) stays in Urdu.

**Description:** first line in English (the hook/takeaway, with the main search
keywords), then 2–3 Urdu lines on the takeaway, the disclaimer line, then
`Sources:` with every URL used, then hashtags: `#HealthTipsUrdu #Nutrition
#MythOrFact #shorts #صحت` plus 1–2 English topic tags. Tags: mostly English
search terms (e.g. "health tips urdu", "myth or fact", the topic in English).

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
- **ElevenLabs workflow fails:** render with Piper "Fasih" (no `VOICE_DIR`), and
  tell the user the exact error (missing `ELEVENLABS_API_KEY` secret, quota
  used up → upgrade/wait for monthly reset, bad voice ID).
- **Urdu voice download fails:** fall back to the older renderer
  `tools/scripts/make_short.py` (Kokoro voice) so the day still gets a video,
  and say so in the report.
- **Icons/fonts missing:** they live in `tools/assets/`; the scripts read them from there.
