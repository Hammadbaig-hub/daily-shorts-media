#!/usr/bin/env python3
"""Bright Life "Myth ya Fact?" Short — Remotion renderer (default since 2026-11-12).

Same script.json as make_myth_short.py. Python makes the Urdu Piper voice, SFX,
beat and the -14 LUFS mix plus a word-timed timeline; Remotion (tools/remotion)
draws the video in Chrome (proper Nastaliq shaping, smoother motion).

    PREVIEW=1 python make_remotion_short.py script.json out.mp4   # PNG per segment + contact sheet
    python make_remotion_short.py script.json out.mp4             # full render (~3-5 min on 2 CPUs)

First run in a fresh sandbox: `npm ci` inside tools/remotion (done automatically).
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
RM = os.path.join(TOOLS, "remotion")
PUB = os.path.join(RM, "public")


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def main(script, out_path):
    out_path = os.path.abspath(out_path)
    if not os.path.isdir(os.path.join(RM, "node_modules")):
        run(["npm", "ci", "--no-audit", "--no-fund"], cwd=RM)

    # 1. audio + timeline from the Python pipeline
    job = os.path.join(PUB, "job")
    shutil.rmtree(job, ignore_errors=True)
    env = dict(os.environ, TIMELINE_OUT=job)
    env.pop("PREVIEW", None)
    run([sys.executable, os.path.join(HERE, "make_myth_short.py"), script, out_path], env=env)

    # 2. assets into public/
    for sub in ("icons", "fonts"):
        dst = os.path.join(PUB, sub)
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(os.path.join(TOOLS, "assets", sub), dst)
    with open(os.path.join(job, "timeline.json"), encoding="utf-8") as fh:
        tl = json.load(fh)
    missing = sorted({i for s in tl["segments"] for i in s["icons"]}
                     - {f[:-4] for f in os.listdir(os.path.join(PUB, "icons"))})
    if missing:
        sys.exit(f"missing icons: {missing}")
    props = os.path.join(job, "props.json")
    with open(props, "w", encoding="utf-8") as fh:
        json.dump({"timeline": tl, "audio": "job/mix.wav"}, fh, ensure_ascii=False)

    npx = ["npx", "remotion"]
    if os.environ.get("PREVIEW"):
        frames = []
        for s in tl["segments"]:
            t = s["start"] + min(s["dur"] - 0.05, max(0.7, (s["s0"] + s["s1"]) / 2))
            frames.append(int(t * tl["fps"]))
        pngs = []
        for k, f in enumerate(frames):
            png = f"{out_path}.seg{k}.png"
            run(npx + ["still", "MythShort", png, f"--frame={f}", f"--props={props}", "--log=error"], cwd=RM)
            pngs.append(png)
        from PIL import Image
        ims = [Image.open(p).convert("RGB").resize((324, 576)) for p in pngs]
        cols = 4
        sheet = Image.new("RGB", (324 * cols, 576 * ((len(ims) + cols - 1) // cols)))
        for i, im in enumerate(ims):
            sheet.paste(im, ((i % cols) * 324, (i // cols) * 576))
        sheet.save(f"{out_path}.sheet.png")
        print(f"preview frames written ({len(pngs)}) + {out_path}.sheet.png; total {tl['total']:.1f} s")
        return

    part = out_path + ".part.mp4"
    run(npx + ["render", "MythShort", part, f"--props={props}", "--codec=h264", "--crf=20", f"--concurrency={min(os.cpu_count() or 2, 4)}",
               "--audio-codec=aac", "--audio-bitrate=160k", "--log=error"], cwd=RM)
    os.replace(part, out_path)
    print(f"OK {out_path} ({tl['total']:.1f}s)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
