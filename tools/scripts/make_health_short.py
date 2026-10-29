#!/usr/bin/env python3
"""
Animated health & nutrition awareness Short (1080x1920, 30 fps) with native
Urdu narration, 3D icons that never stop moving, and word-by-word captions
synced to the voice. Zero cost: Pillow + numpy + ffmpeg + offline TTS.

Usage:
    python make_health_short.py script.json out.mp4

script.json:
{
  "lang": "ur",                         # "ur" (native Piper voice) or "en" (Kokoro)
  "palette": 0,                          # 0-3
  "handle": "@Bright-Life-m4",
  "hook":   {"text": "...", "icons": ["candy", "shocked"]},
  "points": [
     {"text": "...", "icons": ["soda"], "mark": "bad",            # mark: good | bad | warn | null
      "count": {"icon": "teaspoon", "n": 10}}                     # optional: icon pops in n times
  ],
  "cta":    {"text": "...", "icons": ["water", "greenheart"]},
  "disclaimer": "..."                    # small line under the last scene
}
Icon names = file names in tools/assets/icons (without .png).
"""
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
ICONS = os.path.join(ASSETS, "icons")
UR_FONT = os.path.join(ASSETS, "fonts", "NotoNastaliqUrdu-VF.ttf")
EN_FONT = os.path.join(ASSETS, "fonts", "Montserrat-VF.ttf")
SR_V = 24000
LEAD, TAIL = 0.35, 0.55

PALETTES = [
    # fresh mint / coral
    dict(bg1=(226, 252, 241), bg2=(196, 236, 252), blobs=[(125, 226, 190), (255, 196, 170), (170, 210, 255)],
         text=(16, 40, 58), accent=(255, 88, 96), accent2=(0, 166, 140), card=(255, 255, 255)),
    # sunny lemon / teal
    dict(bg1=(255, 248, 220), bg2=(214, 246, 238), blobs=[(255, 220, 120), (140, 220, 210), (255, 180, 200)],
         text=(30, 38, 60), accent=(0, 150, 160), accent2=(255, 140, 50), card=(255, 255, 255)),
    # lavender / green
    dict(bg1=(240, 234, 255), bg2=(220, 250, 232), blobs=[(200, 180, 255), (150, 230, 170), (255, 210, 160)],
         text=(36, 30, 70), accent=(124, 77, 255), accent2=(40, 180, 100), card=(255, 255, 255)),
    # peach / sky
    dict(bg1=(255, 236, 226), bg2=(214, 236, 255), blobs=[(255, 180, 150), (150, 200, 255), (255, 230, 150)],
         text=(40, 30, 40), accent=(235, 80, 60), accent2=(40, 120, 220), card=(255, 255, 255)),
]
MARKS = {"good": "check", "bad": "cross", "warn": "warning"}


# ---------------------------------------------------------------- helpers
def ease_out_back(t, s=1.9):
    t = max(0.0, min(1.0, t)) - 1
    return t * t * ((s + 1) * t + s) + 1


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


_icon_cache = {}


def icon(name, size):
    size = max(8, int(size // 4 * 4))
    key = (name, size)
    if key not in _icon_cache:
        im = Image.open(os.path.join(ICONS, name + ".png")).convert("RGBA")
        _icon_cache[key] = im.resize((size, size), Image.LANCZOS)
    return _icon_cache[key]


def paste_icon(canvas, name, cx, cy, size, angle=0.0, alpha=1.0, shadow=True):
    if size < 6 or alpha <= 0.01:
        return
    im = icon(name, size)
    if abs(angle) > 0.3:
        im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
    if alpha < 0.99:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im = im.copy()
        im.putalpha(a)
    x, y = int(cx - im.width / 2), int(cy - im.height / 2)
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(im.getchannel("A").point(lambda v: int(v * 0.22)))
        canvas.alpha_composite(sh, (x + int(size * 0.04), y + int(size * 0.07)))
    canvas.alpha_composite(im, (x, y))


def font(lang, size):
    f = ImageFont.truetype(UR_FONT if lang == "ur" else EN_FONT, size)
    try:
        f.set_variation_by_axes([700 if lang == "ur" else 800])
    except Exception:
        pass
    return f


def tkw(lang):
    return {"direction": "rtl", "language": "ur"} if lang == "ur" else {}


# ---------------------------------------------------------------- audio
def voice_clip(text, lang):
    sys.path.insert(0, HERE)
    import voice
    if lang == "ur":
        return voice.speak_urdu_native(text, speed=1.06)
    return voice.speak(text, lang)


def speech_span(clip):
    """(start, end) seconds of actual speech inside a clip."""
    env = np.abs(clip)
    thr = max(1e-3, env.max() * 0.04)
    idx = np.where(env > thr)[0]
    if len(idx) == 0:
        return 0.0, len(clip) / SR_V
    return idx[0] / SR_V, idx[-1] / SR_V


def synth_music(total, seed):
    """Light, upbeat original loop (no copyright claims): soft plucks + pad."""
    sr = 44100
    rnd = random.Random(seed)
    n = int(sr * total)
    t = np.arange(n) / sr
    out = np.zeros(n)
    prog = [[261.63, 329.63, 392.0], [220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 246.94, 293.66]]
    beat = 60 / 104
    # pad
    for i in range(int(total / (beat * 4)) + 1):
        ch = prog[i % 4]
        s, e = int(i * beat * 4 * sr), min(n, int((i + 1) * beat * 4 * sr))
        if s >= n:
            break
        tt = t[s:e] - i * beat * 4
        for f in ch:
            out[s:e] += 0.25 * np.sin(2 * np.pi * f * tt) * np.minimum(1, tt / 0.3)
    # plucks on 8th notes
    k = 0
    while k * beat / 2 < total:
        bar = int(k / 8) % 4
        f = prog[bar][rnd.choice([0, 1, 2])] * 2
        s = int(k * beat / 2 * sr)
        e = min(n, s + int(0.35 * sr))
        tt = np.arange(e - s) / sr
        out[s:e] += 0.5 * np.sin(2 * np.pi * f * tt) * np.exp(-tt * 9)
        k += 1
    fade = np.clip(np.minimum(t / 1.0, (total - t) / 1.5), 0, 1)
    out *= fade
    return out / (np.abs(out).max() + 1e-9)


# ---------------------------------------------------------------- background
class Background:
    def __init__(self, pal, seed, float_icons):
        self.pal = pal
        self.sw, self.sh = 270, 480
        y = np.linspace(0, 1, self.sh)[:, None, None]
        self.base = (np.array(pal["bg1"]) * (1 - y) + np.array(pal["bg2"]) * y).astype(np.float32)
        self.base = np.repeat(self.base, self.sw, axis=1)
        self.xs = np.linspace(0, 1, self.sw)[None, :]
        self.ys = np.linspace(0, 1.78, self.sh)[:, None]
        rnd = random.Random(seed)
        self.blobs = [(rnd.uniform(0, 6.28), rnd.uniform(0.15, 0.3), c) for c in pal["blobs"]]
        self.floaters = [
            dict(name=rnd.choice(float_icons), x=rnd.uniform(60, W - 60), y=rnd.uniform(0, H),
                 size=rnd.uniform(70, 130), sp=rnd.uniform(25, 60), rot=rnd.uniform(-30, 30),
                 rs=rnd.uniform(-20, 20), ph=rnd.uniform(0, 6.28))
            for _ in range(11)
        ]
        self.dots = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(4, 10), rnd.uniform(0, 6.28)) for _ in range(28)]

    def frame(self, t):
        img = self.base.copy()
        for ph, spd, col in self.blobs:
            cx = 0.5 + 0.38 * math.sin(t * spd + ph)
            cy = 0.89 + 0.7 * math.cos(t * spd * 0.8 + ph * 1.3)
            g = np.exp(-(((self.xs - cx) ** 2) + ((self.ys - cy) ** 2)) / 0.09)[..., None]
            img = img * (1 - g * 0.55) + np.array(col, dtype=np.float32) * g * 0.55
        im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR).convert("RGBA")
        d = ImageDraw.Draw(im, "RGBA")
        for (x, y, r, ph) in self.dots:
            yy = (y - t * 30) % H
            xx = x + 20 * math.sin(t + ph)
            a = int(90 + 60 * math.sin(t * 2 + ph))
            d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(255, 255, 255, a))
        for f in self.floaters:
            yy = (f["y"] - t * f["sp"]) % (H + 200) - 100
            xx = f["x"] + 30 * math.sin(t * 0.8 + f["ph"])
            paste_icon(im, f["name"], xx, yy, f["size"], f["rot"] + t * f["rs"], alpha=0.22, shadow=False)
        return im


# ---------------------------------------------------------------- captions
def layout_words(draw, words, fnt, lang, max_w):
    space = draw.textlength(" ", font=fnt) * (2.6 if lang == "ur" else 1.0)
    widths = [draw.textlength(w, font=fnt, **tkw(lang)) for w in words]
    lines, cur, cw = [], [], 0
    for i, w in enumerate(widths):
        add = w + (space if cur else 0)
        if cur and cw + add > max_w:
            lines.append(cur)
            cur, cw = [], 0
            add = w
        cur.append(i)
        cw += add
    if cur:
        lines.append(cur)
    return lines, widths, space


class Caption:
    def __init__(self, text, lang, pal, word_times):
        self.lang, self.pal = lang, pal
        self.words = text.split()
        self.times = word_times
        scratch = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        size = 70 if lang == "ur" else 66
        while True:
            self.fnt = font(lang, size)
            self.lh = int(size * (1.95 if lang == "ur" else 1.3))
            self.lines, self.widths, self.space = layout_words(scratch, self.words, self.fnt, lang, 880)
            if len(self.lines) * self.lh <= 560 or size <= 48:
                break
            size -= 4
        self.h = len(self.lines) * self.lh + 90

    def draw(self, im, t, cy, slide):
        pal, lang = self.pal, self.lang
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        top = cy - self.h / 2 + (1 - slide) * 260
        box = [70, top, W - 70, top + self.h]
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([box[0], box[1] + 14, box[2], box[3] + 14], 46, fill=(0, 0, 0, int(40 * slide)))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
        d.rounded_rectangle(box, 46, fill=pal["card"] + (int(245 * slide),))
        active = -1
        for i, wt in enumerate(self.times):
            if t >= wt:
                active = i
        y = top + 45
        pills, texts = [], []
        for line in self.lines:
            lw = sum(self.widths[i] for i in line) + self.space * (len(line) - 1)
            if lang == "ur":
                x = W / 2 + lw / 2
            else:
                x = W / 2 - lw / 2
            for i in line:
                w = self.widths[i]
                wx = x - w if lang == "ur" else x
                appear = ease_out((t - self.times[i] + 0.12) / 0.22)
                if appear > 0:
                    dy = (1 - appear) * 26
                    a = int(255 * appear * slide)
                    oy = -self.lh * 0.06 if lang == "ur" else self.lh * 0.12
                    pos = (wx, y + oy + dy)
                    if i == active:
                        bx = d.textbbox(pos, self.words[i], font=self.fnt, **tkw(lang))
                        top = max(bx[1] - 8, y + dy + self.lh * 0.06)
                        bot = min(bx[3] + 10, y + dy + self.lh * 1.0)
                        pills.append(([bx[0] - 12, top, bx[2] + 12, bot], pal["accent"] + (a,)))
                        col = (255, 255, 255, a)
                    else:
                        col = pal["text"] + (a,)
                    texts.append((pos, self.words[i], col))
                x = x - w - self.space if lang == "ur" else x + w + self.space
            y += self.lh
        for box, colr in pills:
            d.rounded_rectangle(box, 24, fill=colr)
        for pos, word, col in texts:
            d.text(pos, word, font=self.fnt, fill=col, **tkw(lang))
        im.alpha_composite(layer)


# ---------------------------------------------------------------- scenes
def hero_slots(n, has_count):
    base_y = 560 if has_count else 720
    if n == 1:
        return [(W / 2, base_y, 470 if not has_count else 340)]
    if n == 2:
        s = 380 if not has_count else 290
        return [(W / 2 - 235, base_y, s), (W / 2 + 235, base_y + 30, s)]
    s = 290 if not has_count else 230
    return [(W / 2 - 300, base_y + 30, s), (W / 2, base_y - 40, s), (W / 2 + 300, base_y + 30, s)]


def draw_scene(im, sc, t_local, dur, pal, lang, idx, n_points):
    exit_k = 1 - ease_out((t_local - (dur - 0.28)) / 0.28)
    has_count = bool(sc.get("count"))
    slots = hero_slots(len(sc["icons"]), has_count)
    for k, (name, (cx, cy, size)) in enumerate(zip(sc["icons"], slots)):
        ent = ease_out_back((t_local - 0.05 - k * 0.14) / 0.55)
        ph = k * 1.7 + idx
        bob = math.sin(t_local * 2.4 + ph) * 18
        sway = math.sin(t_local * 1.7 + ph) * 6
        breathe = 1 + 0.04 * math.sin(t_local * 3.1 + ph)
        s = size * max(0, ent) * breathe * exit_k
        paste_icon(im, name, cx + math.sin(t_local * 1.1 + ph) * 10, cy + bob, s, sway)
    mark = MARKS.get(sc.get("mark") or "")
    if mark:
        cx, cy, size = slots[0]
        if len(slots) > 1:
            cx, cy = W / 2, cy - size * 0.1
            ox, oy = 0, size * 0.55
        else:
            ox, oy = size * 0.38, size * 0.32
        ent = ease_out_back((t_local - 0.55) / 0.4, 3.0)
        pulse = 1 + 0.07 * math.sin(t_local * 6)
        paste_icon(im, mark, cx + ox, cy + oy, 150 * max(0, ent) * pulse * exit_k, math.sin(t_local * 3) * 8)
    cnt = sc.get("count")
    if cnt:
        n = int(cnt["n"])
        per_row = 5 if n > 6 else n
        rows = math.ceil(n / per_row)
        sz = 118 if n <= 10 else 92
        gap = sz * 1.08
        speak_span = max(0.6, sc["speech_end"] - sc["speech_start"])
        for i in range(n):
            r, c = divmod(i, per_row)
            in_row = min(per_row, n - r * per_row)
            x = W / 2 + (c - (in_row - 1) / 2) * gap
            if lang == "ur":
                x = W - x
            y = 860 + r * gap * 0.95 - (rows - 1) * gap * 0.3
            t_pop = sc["speech_start"] + 0.2 + speak_span * 0.75 * i / max(1, n - 1)
            ent = ease_out_back((t_local - t_pop) / 0.35, 2.6)
            if ent <= 0:
                continue
            wob = math.sin(t_local * 4 + i) * 6
            paste_icon(im, cnt["icon"], x, y + math.sin(t_local * 3 + i * 0.6) * 6, sz * ent * exit_k, wob)
    # step pill
    if sc["kind"] == "point":
        d = ImageDraw.Draw(im, "RGBA")
        txt = f"{idx}/{n_points}"
        f = font("en", 46)
        tw = d.textlength(txt, font=f)
        ent = ease_out_back(t_local / 0.45)
        x0 = W / 2 - (tw + 60) / 2
        y0 = 170 - (1 - ent) * 120
        d.rounded_rectangle([x0, y0, x0 + tw + 60, y0 + 84], 42, fill=pal["accent2"] + (int(255 * exit_k),))
        d.text((x0 + 30, y0 + 14), txt, font=f, fill=(255, 255, 255, int(255 * exit_k)))


def render(spec, out_path):
    lang = spec.get("lang", "ur")
    pal = PALETTES[int(spec.get("palette", 0)) % len(PALETTES)]
    seed = sum(map(ord, spec["hook"]["text"])) & 0xFFFF
    scenes = [dict(spec["hook"], kind="hook")]
    scenes += [dict(p, kind="point") for p in spec["points"]]
    scenes.append(dict(spec["cta"], kind="cta"))

    # voice + timing
    t = 0.0
    for sc in scenes:
        clip = voice_clip(sc["text"], lang)
        sc["clip"] = clip
        s0, s1 = speech_span(clip)
        sc["speech_start"], sc["speech_end"] = LEAD + s0, LEAD + s1
        sc["dur"] = LEAD + len(clip) / SR_V + TAIL
        if sc["kind"] == "cta":
            sc["dur"] += 1.2
        sc["start"] = t
        t += sc["dur"]
        words = sc["text"].split()
        wts = np.array([len(w) + 1.5 for w in words], dtype=float)
        cum = np.concatenate([[0], np.cumsum(wts)[:-1]]) / wts.sum()
        sc["word_times"] = list(sc["speech_start"] + cum * (sc["speech_end"] - sc["speech_start"]))
        sc["caption"] = Caption(sc["text"], lang, pal, sc["word_times"])
    total = t
    if total > 175:
        sys.exit(f"Video would be {total:.0f}s — keep Shorts under 3 minutes (aim for 45-75s)")

    # audio mix
    sr = 44100
    vtrack = np.zeros(int(total * sr) + sr, dtype=np.float32)
    for sc in scenes:
        x = np.interp(np.arange(0, len(sc["clip"]), SR_V / sr), np.arange(len(sc["clip"])), sc["clip"])
        a = int((sc["start"] + LEAD) * sr)
        vtrack[a:a + len(x)] += x[: len(vtrack) - a].astype(np.float32)
    music = synth_music(total, seed)
    n = len(music)
    tmp = tempfile.mkdtemp()

    def write_wav(path, arr):
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes((np.clip(arr, -0.98, 0.98) * 32767).astype(np.int16).tobytes())

    # Voice polish: cut rumble, a little less boom, more presence/clarity,
    # gentle compression so every word is equally loud.
    raw_v, clean_v = os.path.join(tmp, "v_raw.wav"), os.path.join(tmp, "v_clean.wav")
    write_wav(raw_v, vtrack[:n] / (np.abs(vtrack).max() + 1e-9) * 0.9)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw_v, "-af",
                    "highpass=f=75,equalizer=f=220:t=q:w=1:g=-2.5,equalizer=f=3200:t=q:w=1.2:g=4,"
                    "equalizer=f=9000:t=q:w=1:g=2,acompressor=threshold=-22dB:ratio=3.5:attack=4:release=90:makeup=3",
                    "-ar", str(sr), "-ac", "1", clean_v], check=True)
    with wave.open(clean_v) as w:
        v = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32767
    v = np.pad(v, (0, max(0, n - len(v))))[:n]
    v = v / (np.abs(v).max() + 1e-9)
    premix = os.path.join(tmp, "premix.wav")
    write_wav(premix, v * 0.92 + music * 0.11)
    wav = os.path.join(tmp, "mix.wav")
    # YouTube plays at about -14 LUFS: normalise so the voice is loud and clear on phones.
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", premix, "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=9", "-ar", str(sr), "-ac", "1", wav], check=True)

    floats = sorted({i for sc in scenes for i in sc["icons"]} | {"sparkles", "greenheart", "water", "apple", "leafy"})
    bg = Background(pal, seed, floats)
    handle_f = font("en", 38)
    disc_f = font(lang, 32)
    n_points = len(spec["points"])

    def draw_frame(tt):
        im = bg.frame(tt)
        for idx, sc in enumerate(scenes):
            if not (sc["start"] <= tt < sc["start"] + sc["dur"]):
                continue
            tl = tt - sc["start"]
            draw_scene(im, sc, tl, sc["dur"], pal, lang, idx, n_points)
            slide = ease_out(tl / 0.4) * (1 - ease_out((tl - (sc["dur"] - 0.25)) / 0.25))
            sc["caption"].draw(im, tl, 1390, slide)
            if sc["kind"] == "cta" and spec.get("disclaimer"):
                d = ImageDraw.Draw(im, "RGBA")
                lines, widths, sp = layout_words(d, spec["disclaimer"].split(), disc_f, lang, 900)
                a = int(230 * ease_out((tl - 0.6) / 0.5))
                for li, line in enumerate(lines):
                    txt = " ".join(spec["disclaimer"].split()[i] for i in line)
                    tw = d.textlength(txt, font=disc_f, **tkw(lang))
                    d.text(((W - tw) / 2, 1660 + li * 62), txt, font=disc_f, fill=pal["text"] + (a,), **tkw(lang))
        d = ImageDraw.Draw(im, "RGBA")
        d.rounded_rectangle([40, 60, 40 + (W - 80) * tt / total, 76], 8, fill=pal["accent"] + (255,))
        hw = d.textlength(spec.get("handle", ""), font=handle_f)
        d.text(((W - hw) / 2, 1810), spec.get("handle", ""), font=handle_f, fill=pal["text"] + (150,))
        return im

    if os.environ.get("PREVIEW"):
        # PREVIEW=1 -> save a frame from the busiest moment of every scene, no video
        for k, sc in enumerate(scenes):
            tt = sc["start"] + min(sc["dur"] - 0.4, sc["speech_end"] - 0.3)
            draw_frame(tt).convert("RGB").save(f"{out_path}.scene{k}.png")
        print("preview frames written; total", round(total, 1), "s")
        return

    part = out_path + ".part.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", part]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frames = int(total * FPS)
    for fi in range(frames):
        im = draw_frame(fi / FPS)
        proc.stdin.write(im.convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")
    os.replace(part, out_path)
    print(f"OK {out_path} ({total:.1f}s, {frames} frames)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as fh:
        render(json.load(fh), sys.argv[2])
