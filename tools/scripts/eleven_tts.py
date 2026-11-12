#!/usr/bin/env python3
"""ElevenLabs Urdu narration for one Short — runs in GitHub Actions.

    python eleven_tts.py voice/2026-11-12

Reads <job>/segments.json  ({"segments": [{"text": "..."}, ...]}) and writes, per
segment k, <job>/seg{k}.mp3 and <job>/seg{k}.json (character timestamps, used
for the word-by-word captions).

Why GitHub Actions: the Claude cloud sandbox that renders the video can't reach
api.elevenlabs.io, but Actions runners can. Needs the repo secret
ELEVENLABS_API_KEY. Optional repo variables: ELEVENLABS_VOICE_ID,
ELEVENLABS_MODEL (default eleven_v3 — the ElevenLabs model that speaks Urdu).
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128"
DEFAULT_VOICE = "nPczCjzI2devNBz1zQrb"   # "Brian" (premade, deep male) — override with ELEVENLABS_VOICE_ID
DEFAULT_MODEL = "eleven_v3"


def tts(text, key, voice, model, lang=True):
    body = {"text": text, "model_id": model,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    if lang:
        body["language_code"] = "ur"
    req = urllib.request.Request(API.format(voice=voice), data=json.dumps(body).encode(),
                                 headers={"xi-api-key": key, "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:500]
            if e.code == 400 and lang and "language" in msg.lower():
                return tts(text, key, voice, model, lang=False)
            if e.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(5 * (attempt + 1))
                continue
            sys.exit(f"ElevenLabs HTTP {e.code}: {msg}")
    sys.exit("ElevenLabs: too many retries")


def main(job):
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        sys.exit("ELEVENLABS_API_KEY secret is not set (repo Settings → Secrets and variables → Actions)")
    voice = os.environ.get("ELEVENLABS_VOICE_ID", "").strip() or DEFAULT_VOICE
    model = os.environ.get("ELEVENLABS_MODEL", "").strip() or DEFAULT_MODEL
    with open(os.path.join(job, "segments.json"), encoding="utf-8") as fh:
        segs = json.load(fh)["segments"]
    chars = 0
    for k, s in enumerate(segs):
        out = tts(s["text"], key, voice, model)
        with open(os.path.join(job, f"seg{k}.mp3"), "wb") as fh:
            fh.write(base64.b64decode(out["audio_base64"]))
        with open(os.path.join(job, f"seg{k}.json"), "w", encoding="utf-8") as fh:
            json.dump({"text": s["text"], "voice": voice, "model": model,
                       "alignment": out.get("alignment")}, fh, ensure_ascii=False)
        chars += len(s["text"])
        print(f"seg{k}: {len(s['text'])} chars ok", flush=True)
    print(f"done: {len(segs)} segments, {chars} characters, voice {voice}, model {model}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
