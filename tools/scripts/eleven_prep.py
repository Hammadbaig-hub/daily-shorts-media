#!/usr/bin/env python3
"""Write voice/<date>/segments.json from script.json for the ElevenLabs workflow.

    python eleven_prep.py script.json daily-shorts-media/voice/2026-11-12

The segment order matches make_myth_short.py (hook, claim/explain x3, cta), so
seg{k}.mp3 lines up with segment k at render time (VOICE_DIR=<that folder>).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_myth_short import build_segments  # noqa: E402


def main(script, job):
    with open(script, encoding="utf-8") as fh:
        spec = json.load(fh)
    os.makedirs(job, exist_ok=True)
    for f in os.listdir(job):
        if f.startswith("seg"):
            os.remove(os.path.join(job, f))
    segs = [{"kind": s["kind"], "text": s["text"]} for s in build_segments(spec)]
    with open(os.path.join(job, "segments.json"), "w", encoding="utf-8") as fh:
        json.dump({"segments": segs}, fh, ensure_ascii=False, indent=1)
    n = sum(len(s["text"]) for s in segs)
    print(f"{len(segs)} segments, {n} characters -> {job}/segments.json")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
