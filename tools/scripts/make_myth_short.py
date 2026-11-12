#!/usr/bin/env python3
"""
Fast, high-energy "Myth ya Fact?" health Short (1080x1920, 30 fps).

Style v2 (2026-11-02): vivid dark backgrounds, big kinetic word-by-word
captions (2-3 words at a time, active word in yellow), slam-in MYTH/FACT
stamps with screen shake + flash, zoom punches, whoosh/buzz/ding SFX,
a punchy synthesized beat that ducks under the voice, and a livelier,
faster native Urdu voice (Piper Fasih). Zero cost, all offline.

Usage:
    python make_myth_short.py script.json out.mp4
    PREVIEW=1 python make_myth_short.py script.json out.mp4   # PNG per segment

script.json:
{
  "lang": "ur", "palette": 0, "handle": "@Bright-Life-m4",
  "hook":  {"text": "...", "icons": ["shocked", "thinking"]},
  "items": [
    {"claim": "...", "claim_icons": ["honey"],
     "verdict": "myth" | "fact",
     "explain": "...", "explain_icons": ["candy"], "mark": "bad"}
  ],
  "cta":   {"text": "...", "icons": ["greenheart"]},
  "disclaimer": "..."
}
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_health_short import (ICONS, UR_FONT, EN_FONT, SR_V, icon, paste_icon,  # noqa: E402
                               ease_out, ease_out_back, speech_span, MARKS)

W, H, FPS = 1080, 1920, 30
SR = 44100
LEAD, TAIL = 0.18, 0.22
SUSPENSE = 1.0          # pause after each claim: "MYTH یا FACT؟" + ticks
VOICE_SPEED = 1.16
NOISE, NOISE_W = 0.78, 0.95
PITCH = 1.035           # slight pitch lift = brighter, more energetic

PALETTES = [
    dict(bg1=(38, 16, 92), bg2=(196, 30, 120), blob=[(255, 90, 160), (120, 70, 255), (255, 170, 60)],
         accent=(255, 214, 0), pill=(255, 70, 120)),
    dict(bg1=(6, 40, 90), bg2=(0, 160, 170), blob=[(0, 220, 200), (60, 120, 255), (255, 200, 80)],
         accent=(255, 230, 40), pill=(0, 200, 170)),
    dict(bg1=(70, 10, 40), bg2=(250, 110, 40), blob=[(255, 160, 40), (230, 40, 90), (255, 230, 120)],
         accent=(255, 240, 90), pill=(255, 90, 50)),
    dict(bg1=(10, 50, 30), bg2=(40, 170, 90), blob=[(120, 240, 120), (0, 160, 200), (255, 220, 70)],
         accent=(255, 225, 30), pill=(30, 190, 110)),
]
MYTH_COL, FACT_COL = (235, 40, 55), (20, 175, 85)


def ufont(size):
    f = ImageFont.truetype(UR_FONT, size)
    try:
        f.set_variation_by_axes([700])
    except Exception:
        pass
    return f


def efont(size, wght=900):
    f = ImageFont.truetype(EN_FONT, size)
    try:
        f.set_variation_by_axes([wght])
    except Exception:
        pass
    return f


RTL = {"direction": "rtl", "language": "ur"}


# ---------------------------------------------------------------- audio
def speak(text):
    import voice
    a = voice.speak_urdu_native(text, speed=VOICE_SPEED, noise_scale=NOISE, noise_w=NOISE_W)
    # pitch lift without changing speed: resample then stretch back
    n_out = int(len(a) / PITCH)
    a = np.interp(np.linspace(0, len(a) - 1, n_out), np.arange(len(a)), a).astype(np.float32)
    return a  # (slightly faster too, which is what we want)


def load_voice(vdir, k, text):
    """ElevenLabs clip k (24 kHz float) + word start times from its character alignment."""
    mp3 = os.path.join(vdir, f"seg{k}.mp3")
    meta_p = os.path.join(vdir, f"seg{k}.json")
    if not os.path.exists(mp3):
        sys.exit(f"missing {mp3} — did the ElevenLabs workflow run?")
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", mp3, "-f", "f32le", "-ac", "1",
                          "-ar", str(SR_V), "-"], check=True, capture_output=True).stdout
    clip = np.frombuffer(raw, dtype=np.float32).copy()
    starts = None
    try:
        with open(meta_p, encoding="utf-8") as fh:
            meta = json.load(fh)
        if meta.get("text") != text:
            sys.exit(f"seg{k}: voice text doesn't match script.json — rerun eleven_prep + workflow")
        al = meta.get("alignment") or {}
        chars, st = al.get("characters") or [], al.get("character_start_times_seconds") or []
        if "".join(chars) == text and len(st) == len(chars):
            starts = [st[i] for i, c in enumerate(text)
                      if not c.isspace() and (i == 0 or text[i - 1].isspace())]
    except (OSError, ValueError):
        pass
    return clip, starts


def tone(f, dur, decay, sr=SR):
    t = np.arange(int(dur * sr)) / sr
    return np.sin(2 * np.pi * f * t) * np.exp(-t * decay)


def sfx_whoosh():
    n = int(0.38 * SR)
    rnd = np.random.default_rng(1)
    x = rnd.standard_normal(n)
    t = np.arange(n) / n
    # moving low-pass via cumulative smoothing of varying length
    out = np.zeros(n)
    acc = 0.0
    for i in range(n):
        k = 0.02 + 0.5 * math.sin(math.pi * t[i])
        acc += k * (x[i] - acc)
        out[i] = acc
    env = np.sin(np.pi * t) ** 2
    return out * env / (np.abs(out).max() + 1e-9) * 0.7


def sfx_buzz():
    t = np.arange(int(0.42 * SR)) / SR
    s = np.sign(np.sin(2 * np.pi * 110 * t)) * 0.5 + np.sign(np.sin(2 * np.pi * 116 * t)) * 0.5
    return s * np.minimum(1, (0.42 - t) / 0.05) * 0.45 + tone(70, 0.42, 6) * 0.6


def sfx_ding():
    return (tone(1318.5, 0.9, 5) * 0.6 + tone(1975.5, 0.9, 7) * 0.35 + tone(2637, 0.9, 10) * 0.2)


def sfx_tick():
    return tone(1800, 0.05, 80) * 0.5 + tone(900, 0.05, 60) * 0.3


def sfx_boom():
    t = np.arange(int(0.5 * SR)) / SR
    f = 120 * np.exp(-t * 8) + 40
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)


def synth_beat(total, seed):
    """Punchy original 124 bpm loop: kick, clap, hats, bass, plucks."""
    rnd = random.Random(seed)
    n = int(total * SR) + SR
    out = np.zeros(n)
    beat = 60 / 124
    roots = [55.0, 43.65, 65.41, 49.0]            # A1 F1 C2 G1
    chords = [[440, 523.25, 659.25], [349.23, 440, 523.25], [523.25, 659.25, 783.99], [392, 493.88, 587.33]]
    kick = sfx_boom()[: int(0.3 * SR)] * 0.9
    rng = np.random.default_rng(seed)
    hat = rng.standard_normal(int(0.04 * SR)) * np.exp(-np.arange(int(0.04 * SR)) / SR * 120) * 0.18
    hat = np.diff(hat, prepend=0)
    clap = rng.standard_normal(int(0.12 * SR)) * np.exp(-np.arange(int(0.12 * SR)) / SR * 30) * 0.35
    k = 0
    while k * beat / 2 < total:
        s = int(k * beat / 2 * SR)
        bar = (k // 8) % 4
        if k % 2 == 0:
            out[s:s + len(kick)] += kick[: n - s]
        else:
            out[s:s + len(hat)] += hat[: n - s]
        if k % 4 == 2:
            out[s:s + len(clap)] += clap[: n - s]
        # bass on 8ths
        b = tone(roots[bar] * (2 if k % 2 else 1), beat / 2, 4)
        out[s:s + len(b)] += 0.35 * b[: n - s]
        if rnd.random() < 0.55:
            p = tone(chords[bar][rnd.randrange(3)], 0.3, 10)
            out[s:s + len(p)] += 0.22 * p[: n - s]
        k += 1
    t = np.arange(n) / SR
    out *= np.clip(np.minimum(t / 0.3, (total - t) / 1.2), 0, 1)
    return out[: int(total * SR)] / (np.abs(out).max() + 1e-9)


# ---------------------------------------------------------------- visuals
class Background:
    def __init__(self, pal, seed, floats):
        self.sw, self.sh = 180, 320
        y = np.linspace(0, 1, self.sh)[:, None, None]
        base = np.array(pal["bg1"]) * (1 - y) + np.array(pal["bg2"]) * y
        self.base = np.repeat(base, self.sw, axis=1).astype(np.float32)
        self.xs = np.linspace(0, 1, self.sw)[None, :]
        self.ys = np.linspace(0, 1.78, self.sh)[:, None]
        rnd = random.Random(seed)
        self.blobs = [(rnd.uniform(0, 6.28), rnd.uniform(0.4, 0.7), c) for c in pal["blob"]]
        self.floaters = [dict(name=rnd.choice(floats), x=rnd.uniform(60, W - 60), y=rnd.uniform(0, H),
                              size=rnd.uniform(80, 140), sp=rnd.uniform(60, 120), rot=rnd.uniform(-30, 30),
                              rs=rnd.uniform(-40, 40), ph=rnd.uniform(0, 6.28)) for _ in range(9)]
        self.sparks = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(3, 8), rnd.uniform(0, 6.28),
                        rnd.uniform(60, 160)) for _ in range(40)]
        # light rays (drawn once, rotated per frame)
        R = 1300
        rays = Image.new("RGBA", (R, R), (0, 0, 0, 0))
        d = ImageDraw.Draw(rays)
        for i in range(16):
            a0 = i * 22.5
            d.pieslice([0, 0, R, R], a0, a0 + 9, fill=(255, 255, 255, 34))
        mask = Image.new("L", (R, R), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, R, R], fill=255)
        g = Image.radial_gradient("L").resize((R, R))
        alpha = Image.eval(g, lambda v: 255 - v)
        rays.putalpha(Image.composite(Image.eval(rays.getchannel("A"), lambda v: v),
                                      Image.new("L", (R, R), 0), mask))
        a = np.array(rays.getchannel("A"), dtype=np.float32) * (np.array(alpha, dtype=np.float32) / 255)
        rays.putalpha(Image.fromarray(a.astype(np.uint8)))
        self.rays = rays.resize((R // 2, R // 2), Image.BILINEAR)

    def frame(self, t, ray_center=(W / 2, 700), ray_alpha=1.0):
        img = self.base.copy()
        for ph, spd, col in self.blobs:
            cx = 0.5 + 0.42 * math.sin(t * spd + ph)
            cy = 0.89 + 0.75 * math.cos(t * spd * 0.8 + ph * 1.3)
            g = np.exp(-(((self.xs - cx) ** 2) + ((self.ys - cy) ** 2)) / 0.12)[..., None]
            img = img * (1 - g * 0.5) + np.array(col, dtype=np.float32) * g * 0.5
        im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR).convert("RGBA")
        if ray_alpha > 0.02:
            r = self.rays.rotate(t * 25, resample=Image.BILINEAR).resize((1300, 1300), Image.BILINEAR)
            if ray_alpha < 0.99:
                r.putalpha(r.getchannel("A").point(lambda v: int(v * ray_alpha)))
            im.alpha_composite(r, (int(ray_center[0] - 650), int(ray_center[1] - 650)))
        d = ImageDraw.Draw(im, "RGBA")
        for (x, y, rr, ph, sp) in self.sparks:
            yy = (y - t * sp) % H
            xx = x + 25 * math.sin(t * 1.5 + ph)
            a = int(110 + 90 * math.sin(t * 4 + ph))
            d.ellipse([xx - rr, yy - rr, xx + rr, yy + rr], fill=(255, 255, 255, a))
        for f in self.floaters:
            yy = (f["y"] - t * f["sp"]) % (H + 200) - 100
            xx = f["x"] + 40 * math.sin(t + f["ph"])
            paste_icon(im, f["name"], xx, yy, f["size"], f["rot"] + t * f["rs"], alpha=0.16, shadow=False)
        return im


class Kinetic:
    """Big 2-3 word chunks, active word yellow, thick outline, pop-in."""

    def __init__(self, text, times, pal, size=118, max_w=960):
        self.words = text.split()
        self.times = times
        self.pal = pal
        scratch = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        self.chunks = []
        cur, cur_len = [], 0
        for i, w in enumerate(self.words):
            if cur and (len(cur) >= 3 or cur_len + len(w) > 15):
                self.chunks.append(cur)
                cur, cur_len = [], 0
            cur.append(i)
            cur_len += len(w)
            if w[-1] in "۔!؟?،":
                self.chunks.append(cur)
                cur, cur_len = [], 0
        if cur:
            self.chunks.append(cur)
        self.size, self.max_w = size, max_w
        self.cache = {}
        self.scratch = scratch

    def _render(self, ci, active):
        key = (ci, active)
        if key in self.cache:
            return self.cache[key]
        idx = self.chunks[ci]
        size = self.size
        while True:
            f = ufont(size)
            sp = self.scratch.textlength(" ", font=f) * 2.2
            ws = [self.scratch.textlength(self.words[i], font=f, **RTL) for i in idx]
            tw = sum(ws) + sp * (len(ws) - 1)
            if tw <= self.max_w or size <= 70:
                break
            size -= 6
        pad = 60
        hh = int(size * 3.0)
        im = Image.new("RGBA", (int(tw + pad * 2), hh), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        x = im.width - pad
        for i, w in zip(idx, ws):
            col = self.pal["accent"] if i == active else (255, 255, 255)
            d.text((x - w, int(size * 0.55)), self.words[i], font=f, fill=col + (255,),
                   stroke_width=max(6, size // 13), stroke_fill=(20, 10, 30, 255), **RTL)
            x -= w + sp
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.55)))
        out = Image.new("RGBA", im.size, (0, 0, 0, 0))
        out.alpha_composite(sh, (0, 0))
        out.alpha_composite(im, (0, 0))
        self.cache[key] = out
        return out

    def draw(self, canvas, t, cy):
        active = -1
        for i, wt in enumerate(self.times):
            if t >= wt - 0.03:
                active = i
        if active < 0:
            return
        ci = next(k for k, c in enumerate(self.chunks) if active in c)
        chunk_start = self.times[self.chunks[ci][0]]
        img = self._render(ci, active)
        k = ease_out_back((t - chunk_start + 0.03) / 0.2, 2.2)
        s = 0.6 + 0.4 * k
        wob = 1 + 0.015 * math.sin(t * 9)
        s *= wob
        if abs(s - 1) > 0.01:
            img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BILINEAR)
        canvas.alpha_composite(img, (int(W / 2 - img.width / 2), int(cy - img.height / 2)))


def pill(canvas, text, cx, cy, fnt, bg, fg=(255, 255, 255), rtl=False, alpha=1.0, pad=(44, 18)):
    d = ImageDraw.Draw(canvas, "RGBA")
    kw = RTL if rtl else {}
    bx = d.textbbox((0, 0), text, font=fnt, **kw)
    tw, th = bx[2] - bx[0], bx[3] - bx[1]
    box = [cx - tw / 2 - pad[0], cy - th / 2 - pad[1], cx + tw / 2 + pad[0], cy + th / 2 + pad[1]]
    d.rounded_rectangle(box, int((box[3] - box[1]) / 2), fill=bg + (int(255 * alpha),))
    d.text((cx - tw / 2 - bx[0], cy - th / 2 - bx[1]), text, font=fnt, fill=fg + (int(255 * alpha),), **kw)


def stamp_img(verdict):
    col = MYTH_COL if verdict == "myth" else FACT_COL
    en = "MYTH" if verdict == "myth" else "FACT"
    ur = "غلط" if verdict == "myth" else "سچ"
    fe, fu = efont(150), ufont(120)
    im = Image.new("RGBA", (820, 330), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 10, 810, 320], 50, fill=col + (255,), outline=(255, 255, 255, 255), width=14)
    d.text((70, 70), en, font=fe, fill=(255, 255, 255, 255))
    bx = d.textbbox((0, 0), ur, font=fu, **RTL)
    d.text((760 - (bx[2] - bx[0]) - bx[0], 165 - (bx[3] - bx[1]) / 2 - bx[1]), ur, font=fu,
           fill=(255, 255, 255, 255), **RTL)
    return im.rotate(-7, resample=Image.BICUBIC, expand=True)


# ---------------------------------------------------------------- build
def build_segments(spec):
    segs = [dict(kind="hook", text=spec["hook"]["text"], icons=spec["hook"].get("icons", []))]
    n = len(spec["items"])
    for i, it in enumerate(spec["items"]):
        segs.append(dict(kind="claim", text=it["claim"], icons=it.get("claim_icons", []), item=i, n=n))
        segs.append(dict(kind="explain", text=it["explain"], icons=it.get("explain_icons", it.get("claim_icons", [])),
                         verdict=it["verdict"], mark=it.get("mark"), item=i, n=n))
    segs.append(dict(kind="cta", text=spec["cta"]["text"], icons=spec["cta"].get("icons", [])))
    return segs


def render(spec, out_path):
    pal = PALETTES[int(spec.get("palette", 0)) % len(PALETTES)]
    seed = sum(map(ord, spec["hook"]["text"])) & 0xFFFF
    segs = build_segments(spec)

    t = 0.0
    vdir = os.environ.get("VOICE_DIR")   # ElevenLabs narration made by eleven_tts.py
    for k, sg in enumerate(segs):
        word_starts = None
        if vdir:
            clip, word_starts = load_voice(vdir, k, sg["text"])
        else:
            clip = speak(sg["text"])
        sg["clip"] = clip
        s0, s1 = speech_span(clip)
        lead = LEAD + (0.55 if sg["kind"] == "explain" else 0.0)   # room for the stamp slam
        sg["lead"] = lead
        sg["s0"], sg["s1"] = lead + s0, lead + s1
        sg["dur"] = lead + len(clip) / SR_V + TAIL
        if sg["kind"] == "claim":
            sg["dur"] += SUSPENSE
        if sg["kind"] == "cta":
            sg["dur"] += 1.6
        sg["start"] = t
        t += sg["dur"]
        words = sg["text"].split()
        wts = np.array([len(w) + 1.2 for w in words], dtype=float)
        cum = np.concatenate([[0], np.cumsum(wts)[:-1]]) / wts.sum()
        sg["wt"] = list(sg["s0"] + cum * (sg["s1"] - sg["s0"]))
        if word_starts and len(word_starts) == len(words):
            sg["wt"] = [lead + w for w in word_starts]   # exact ElevenLabs timing
        sg["kin"] = Kinetic(sg["text"], sg["wt"], pal)
    total = t
    if total > 175:
        sys.exit(f"Video would be {total:.0f}s — too long")

    # ---- audio
    n = int(total * SR)
    v = np.zeros(n + SR, dtype=np.float32)
    voice_mask = np.zeros(n + SR, dtype=np.float32)
    for sg in segs:
        x = np.interp(np.arange(0, len(sg["clip"]), SR_V / SR), np.arange(len(sg["clip"])), sg["clip"])
        a = int((sg["start"] + sg["lead"]) * SR)
        v[a:a + len(x)] += x[: len(v) - a].astype(np.float32)
        voice_mask[a:a + len(x)] = 1
    v = v[:n]
    sfx = np.zeros(n + 2 * SR)

    def add(arr, at, g=1.0):
        a = int(at * SR)
        if 0 <= a < n:
            sfx[a:a + len(arr)] += g * arr[: len(sfx) - a]

    wh, bz, dg, tk, bm = sfx_whoosh(), sfx_buzz(), sfx_ding(), sfx_tick(), sfx_boom()
    for sg in segs:
        if sg["kind"] in ("claim", "cta", "hook"):
            add(wh, max(0, sg["start"] - 0.12), 0.8)
        if sg["kind"] == "hook":
            add(bm, sg["start"] + 0.05, 0.9)
        if sg["kind"] == "claim":
            tend = sg["start"] + sg["dur"]
            for k in range(3):
                add(tk, tend - SUSPENSE + 0.1 + k * 0.3, 0.9)
        if sg["kind"] == "explain":
            add(bm, sg["start"] + 0.02, 0.8)
            add(bz if sg["verdict"] == "myth" else dg, sg["start"] + 0.05, 0.7)
    sfx = sfx[:n]
    music = synth_beat(total, seed)
    # duck music under the voice (smoothed)
    m = np.convolve(voice_mask[:n], np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")
    duck = 1 - 0.55 * np.clip(m, 0, 1)

    tmp = tempfile.mkdtemp()

    def write_wav(path, arr):
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.clip(arr, -0.98, 0.98) * 32767).astype(np.int16).tobytes())

    raw_v, clean_v = os.path.join(tmp, "v_raw.wav"), os.path.join(tmp, "v_clean.wav")
    write_wav(raw_v, v / (np.abs(v).max() + 1e-9) * 0.9)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw_v, "-af",
                    "highpass=f=80,equalizer=f=250:t=q:w=1:g=-3,equalizer=f=3000:t=q:w=1.2:g=5,"
                    "equalizer=f=8500:t=q:w=1:g=3,acompressor=threshold=-24dB:ratio=4:attack=3:release=80:makeup=4",
                    "-ar", str(SR), "-ac", "1", clean_v], check=True)
    with wave.open(clean_v) as w:
        vc = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32767
    vc = np.pad(vc, (0, max(0, n - len(vc))))[:n]
    vc = vc / (np.abs(vc).max() + 1e-9)
    sfx = sfx / (np.abs(sfx).max() + 1e-9)
    premix = os.path.join(tmp, "premix.wav")
    write_wav(premix, vc * 0.9 + music * 0.30 * duck + sfx * 0.32)
    wav = os.path.join(tmp, "mix.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", premix, "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=8", "-ar", str(SR), "-ac", "1", wav], check=True)

    # Remotion renderer: write the finished audio mix + a timeline, skip Pillow visuals
    tl_dir = os.environ.get("TIMELINE_OUT")
    if tl_dir:
        import shutil
        os.makedirs(tl_dir, exist_ok=True)
        shutil.copy(wav, os.path.join(tl_dir, "mix.wav"))
        keep = ("kind", "text", "icons", "item", "n", "verdict", "mark", "lead", "s0", "s1", "dur", "start", "wt")
        timeline = dict(
            total=total, fps=FPS, suspense=SUSPENSE, palette=int(spec.get("palette", 0)) % len(PALETTES),
            handle=spec.get("handle", ""), disclaimer=spec.get("disclaimer", ""), seed=seed,
            segments=[{k: (float(v) if isinstance(v, (np.floating,)) else
                           [float(x) for x in v] if k == "wt" else v)
                       for k, v in sg.items() if k in keep} for sg in segs])
        with open(os.path.join(tl_dir, "timeline.json"), "w", encoding="utf-8") as fh:
            json.dump(timeline, fh, ensure_ascii=False, indent=1)
        print(f"timeline + audio written to {tl_dir} ({total:.1f}s)")
        return

    # ---- visuals
    floats = sorted({i for sg in segs for i in sg["icons"]} | {"sparkles", "greenheart", "bulb"})
    bg = Background(pal, seed, floats)
    stamps = {"myth": stamp_img("myth"), "fact": stamp_img("fact")}
    f_label = ufont(64)
    f_count = efont(52)
    f_handle = efont(40, 800)
    f_disc = ufont(34)
    f_hookbadge = efont(64)

    def draw_icons(im, sg, tl, cy, base=360):
        icons = sg["icons"][:3]
        nI = len(icons)
        if nI == 0:
            return
        size = base if nI == 1 else (300 if nI == 2 else 250)
        gap = size * 1.05
        for k, name in enumerate(icons):
            x = W / 2 + (k - (nI - 1) / 2) * gap
            x = W - x  # RTL order
            ent = ease_out_back((tl - 0.02 - k * 0.09) / 0.38, 2.4)
            ph = k * 1.9
            bob = math.sin(tl * 3.4 + ph) * 22
            rot = math.sin(tl * 2.6 + ph) * 9
            breathe = 1 + 0.06 * math.sin(tl * 4.2 + ph)
            paste_icon(im, name, x + math.sin(tl * 1.8 + ph) * 12, cy + bob, size * max(0, ent) * breathe, rot)

    def draw_frame(tt):
        sg_i = next((i for i, s in enumerate(segs) if s["start"] <= tt < s["start"] + s["dur"]), len(segs) - 1)
        sg = segs[sg_i]
        tl = tt - sg["start"]
        im = bg.frame(tt, ray_center=(W / 2, 760), ray_alpha=1.0)
        shake = (0, 0)
        kind = sg["kind"]
        if kind == "hook":
            draw_icons(im, sg, tl, 760, 380)
            ent = ease_out_back((tl - 0.1) / 0.35, 2.5)
            if ent > 0:
                b = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
                pill(b, "MYTH  or  FACT ?", W / 2, 100, f_hookbadge, pal["pill"])
                b = b.resize((max(1, int(W * ent)), max(1, int(200 * ent))))
                im.alpha_composite(b, (int(W / 2 - b.width / 2), int(330 - b.height / 2)))
        elif kind == "claim":
            pill(im, f"{sg['item'] + 1}/{sg['n']}", W / 2, 200, f_count, pal["pill"])
            draw_icons(im, sg, tl, 760)
            q_ent = ease_out_back((tl - 0.15) / 0.35, 2.2)
            if q_ent > 0:
                lab = Image.new("RGBA", (W, 160), (0, 0, 0, 0))
                pill(lab, "سچ یا غلط؟", W / 2, 80, f_label, (255, 255, 255), fg=(30, 20, 40), rtl=True)
                lab = lab.resize((max(1, int(W * q_ent)), max(1, int(160 * q_ent))))
                im.alpha_composite(lab, (int(W / 2 - lab.width / 2), int(380 - lab.height / 2)))
            # suspense ring
            t_sus = tl - (sg["dur"] - SUSPENSE)
            if t_sus > 0:
                d = ImageDraw.Draw(im, "RGBA")
                frac = min(1, t_sus / (SUSPENSE - 0.05))
                r = 95 + 8 * math.sin(tt * 20)
                cx, cy = W / 2, 1560
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0, 120))
                d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * frac, fill=pal["accent"] + (255,), width=16)
                num = str(3 - min(2, int(t_sus / 0.3)))
                fn = efont(110)
                bx = d.textbbox((0, 0), num, font=fn)
                d.text((cx - (bx[2] - bx[0]) / 2 - bx[0], cy - (bx[3] - bx[1]) / 2 - bx[1]), num, font=fn,
                       fill=(255, 255, 255, 255))
        elif kind == "explain":
            pill(im, f"{sg['item'] + 1}/{sg['n']}", W / 2, 200, f_count, pal["pill"])
            draw_icons(im, sg, max(0, tl - 0.35), 860, 320)
            mk = MARKS.get(sg.get("mark") or "")
            if mk and tl > 0.6:
                e = ease_out_back((tl - 0.6) / 0.3, 3)
                paste_icon(im, mk, W / 2 + 230, 1000, 150 * e * (1 + 0.08 * math.sin(tl * 7)), math.sin(tl * 4) * 10)
            # stamp slam
            st = stamps[sg["verdict"]]
            k = min(1, tl / 0.16)
            s = 2.6 - 1.6 * ease_out(k)
            stay_y = 470
            img = st.resize((int(st.width * s), int(st.height * s)), Image.BILINEAR) if abs(s - 1) > 0.01 else st
            if tl < 0.16:
                img.putalpha(img.getchannel("A").point(lambda v: int(v * k)))
            pulse = 1 + 0.03 * math.sin(tl * 6) if tl > 0.3 else 1
            if pulse != 1:
                img = img.resize((int(img.width * pulse), int(img.height * pulse)), Image.BILINEAR)
            im.alpha_composite(img, (int(W / 2 - img.width / 2), int(stay_y - img.height / 2)))
            if 0.14 < tl < 0.5:
                amp = 22 * (1 - (tl - 0.14) / 0.36)
                shake = (int(amp * math.sin(tl * 90)), int(amp * math.cos(tl * 77)))
        elif kind == "cta":
            draw_icons(im, sg, tl, 760, 340)
        # captions
        cap_y = 1290 if kind != "explain" else 1330
        sg["kin"].draw(im, tl, cap_y)
        if kind == "cta" and spec.get("disclaimer"):
            a = ease_out((tl - 0.5) / 0.4)
            if a > 0:
                d = ImageDraw.Draw(im, "RGBA")
                txt = spec["disclaimer"]
                bx = d.textbbox((0, 0), txt, font=f_disc, **RTL)
                tw = bx[2] - bx[0]
                if tw > 980:
                    words = txt.split()
                    half = len(words) // 2
                    lines = [" ".join(words[:half]), " ".join(words[half:])]
                else:
                    lines = [txt]
                d.rounded_rectangle([60, 1600, W - 60, 1600 + 70 * len(lines) + 30], 30, fill=(0, 0, 0, int(110 * a)))
                for li, ln in enumerate(lines):
                    bx = d.textbbox((0, 0), ln, font=f_disc, **RTL)
                    d.text(((W - (bx[2] - bx[0])) / 2 - bx[0], 1615 + li * 70), ln, font=f_disc,
                           fill=(255, 255, 255, int(235 * a)), **RTL)
        # progress + handle
        d = ImageDraw.Draw(im, "RGBA")
        d.rounded_rectangle([40, 60, W - 40, 80], 10, fill=(255, 255, 255, 70))
        d.rounded_rectangle([40, 60, 40 + (W - 80) * tt / total, 80], 10, fill=pal["accent"] + (255,))
        hw = d.textlength(spec.get("handle", ""), font=f_handle)
        d.text(((W - hw) / 2, 1830), spec.get("handle", ""), font=f_handle, fill=(255, 255, 255, 190))
        # zoom punch at segment start
        z = 1 + 0.07 * (1 - ease_out(tl / 0.35)) if tl < 0.35 else 1
        if z > 1.001 or shake != (0, 0):
            big = im.resize((int(W * z), int(H * z)), Image.BILINEAR) if z > 1.001 else im
            ox = (big.width - W) // 2 + shake[0]
            oy = (big.height - H) // 2 + shake[1]
            im2 = Image.new("RGBA", (W, H), pal["bg1"] + (255,))
            im2.paste(big, (-ox, -oy))
            im = im2
        # white flash on stamp / new item
        flash = 0
        if kind == "explain" and 0.12 < tl < 0.3:
            flash = 0.55 * (1 - (tl - 0.12) / 0.18)
        if kind == "claim" and tl < 0.1:
            flash = 0.35 * (1 - tl / 0.1)
        if flash > 0:
            im = Image.blend(im, Image.new("RGBA", (W, H), (255, 255, 255, 255)), flash)
        return im

    if os.environ.get("PREVIEW"):
        for k, sg in enumerate(segs):
            tt = sg["start"] + min(sg["dur"] - 0.05, max(0.7, (sg["s0"] + sg["s1"]) / 2))
            draw_frame(tt).convert("RGB").save(f"{out_path}.seg{k}.png")
        print("preview frames written; total", round(total, 1), "s")
        return

    part = out_path + ".part.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", part]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frames = int(total * FPS)
    for fi in range(frames):
        proc.stdin.write(draw_frame(fi / FPS).convert("RGB").tobytes())
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
