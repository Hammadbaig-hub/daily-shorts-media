#!/usr/bin/env python3
"""
Render a vertical (1080x1920) animated-text YouTube Short from a JSON script.

Zero cost: uses only Pillow, numpy and ffmpeg. No AI credits, no network.
Background music is synthesized here, so there is no copyright claim risk.

Usage:
    python make_short.py script.json out.mp4

script.json:
{
  "lang": "en" | "ur",
  "hook": "Short attention-grabbing opening line",
  "facts": ["fact 1", "fact 2", "fact 3"],      # 3-5 items work best
  "cta": "Follow for a new fact every day",
  "handle": "@yourchannel",                       # optional watermark
  "theme": 0,                                     # optional 0-5, colour palette
  "voice": true                                   # optional, false = music only
}
With voice on, each slide lasts as long as its narration (see voice.py).
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
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "..", "assets", "fonts")
EN_FONT = os.path.join(FONT_DIR, "Montserrat-VF.ttf")
UR_FONT = os.path.join(FONT_DIR, "NotoNastaliqUrdu-VF.ttf")

# (top colour, bottom colour, accent) — dark, high-contrast so white text pops
THEMES = [
    ((20, 12, 48), (88, 28, 135), (250, 204, 21)),    # violet night / gold
    ((8, 30, 46), (14, 116, 144), (253, 186, 116)),   # ocean / peach
    ((40, 10, 10), (153, 27, 27), (254, 240, 138)),   # ember / cream
    ((6, 40, 24), (21, 128, 61), (190, 242, 100)),    # forest / lime
    ((17, 24, 39), (55, 65, 81), (56, 189, 248)),     # slate / sky
    ((49, 10, 49), (190, 24, 93), (165, 243, 252)),   # magenta / ice
]

HOOK_SEC, FACT_SEC, CTA_SEC = 3.0, 5.5, 3.0


def font(lang, size, weight=800):
    f = ImageFont.truetype(UR_FONT if lang == "ur" else EN_FONT, size)
    try:
        f.set_variation_by_axes([weight if lang == "en" else 700])
    except Exception:
        pass
    return f


def text_kwargs(lang):
    if lang == "ur":
        return {"direction": "rtl", "language": "ur"}
    return {}


def wrap(draw, text, fnt, max_w, lang):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt, **text_kwargs(lang)) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_text(draw, text, lang, max_w, max_h, start, min_size=40):
    """Largest font size where wrapped text fits the box."""
    size = start
    while size >= min_size:
        f = font(lang, size)
        lines = wrap(draw, text, f, max_w, lang)
        lh = int(size * (2.0 if lang == "ur" else 1.25))
        if len(lines) * lh <= max_h:
            return f, lines, lh
        size -= 4
    f = font(lang, min_size)
    return f, wrap(draw, text, f, max_w, lang), int(min_size * (2.0 if lang == "ur" else 1.25))


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


class Background:
    def __init__(self, theme, seed):
        top, bot, self.accent = theme
        y = np.linspace(0, 1, H)[:, None]
        self.top = np.array(top, dtype=np.float32)
        self.bot = np.array(bot, dtype=np.float32)
        self.y = np.repeat(y, W, axis=1)[..., None].astype(np.float32)
        xs = np.linspace(-1, 1, W)[None, :]
        ys = np.linspace(-1.78, 1.78, H)[:, None]
        self.xs, self.ys = xs.astype(np.float32), ys.astype(np.float32)
        rnd = random.Random(seed)
        self.particles = [
            (rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(2, 6), rnd.uniform(15, 50), rnd.uniform(0, 6.28))
            for _ in range(45)
        ]

    def frame(self, t):
        # slowly drifting gradient plus a soft moving glow
        shift = 0.12 * math.sin(t * 0.35)
        yy = np.clip(self.y + shift, 0, 1)
        img = self.top * (1 - yy) + self.bot * yy
        cx, cy = 0.5 * math.sin(t * 0.25), 0.9 * math.cos(t * 0.2)
        glow = np.exp(-(((self.xs - cx) ** 2) + ((self.ys - cy) ** 2)) * 1.6)[..., None]
        img = img + glow * 45
        im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(im, "RGBA")
        for (px, py, r, speed, ph) in self.particles:
            yv = (py - t * speed) % H
            xv = px + 18 * math.sin(t * 0.6 + ph)
            a = int(70 + 60 * math.sin(t * 1.3 + ph))
            d.ellipse([xv - r, yv - r, xv + r, yv + r], fill=(255, 255, 255, max(0, a)))
        return im


def draw_block(im, lines, fnt, lh, lang, cy, alpha, dy, color=(255, 255, 255)):
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    total = len(lines) * lh
    y = cy - total / 2 + dy
    for ln in lines:
        w = d.textlength(ln, font=fnt, **text_kwargs(lang))
        x = (W - w) / 2
        # shadow for readability on any frame
        d.text((x + 4, y + 5), ln, font=fnt, fill=(0, 0, 0, int(150 * alpha)), **text_kwargs(lang))
        d.text((x, y), ln, font=fnt, fill=color + (int(255 * alpha),), **text_kwargs(lang))
        y += lh
    im.alpha_composite(layer)


def build_timeline(spec, voice_clips=None):
    """Segment lengths follow the voiceover when there is one."""
    segs = [("hook", spec["hook"], HOOK_SEC)]
    for i, f in enumerate(spec["facts"]):
        segs.append(("fact", f, FACT_SEC, i + 1))
    segs.append(("cta", spec["cta"], CTA_SEC))
    out, t = [], 0.0
    for idx, s in enumerate(segs):
        dur = s[2]
        if voice_clips is not None:
            # 0.35s lead-in before speech, 0.6s breathing room after
            dur = max(2.2, VOICE_LEAD + len(voice_clips[idx]) / VOICE_SR + 0.6)
        out.append((t, t + dur, s))
        t += dur
    return out, t


VOICE_LEAD, VOICE_SR = 0.35, 24000


def synth_music(path, dur, seed, voice_track=None):
    """Soft ambient pad: original audio, so no Content ID claims.
    If voice_track (float32 @44.1k) is given, music is ducked under it."""
    sr = 44100
    rnd = random.Random(seed)
    roots = [[220.0, 261.63, 329.63], [196.0, 246.94, 293.66], [174.61, 220.0, 261.63], [196.0, 233.08, 293.66]]
    rnd.shuffle(roots)
    n = int(sr * dur)
    t = np.arange(n) / sr
    sig = np.zeros(n, dtype=np.float64)
    bar = 4.0
    for i in range(int(dur / bar) + 1):
        chord = roots[i % len(roots)]
        s, e = int(i * bar * sr), min(n, int((i + 1) * bar * sr + sr))
        if s >= n:
            break
        tt = t[s:e] - i * bar
        env = np.minimum(1, tt / 0.8) * np.exp(-np.maximum(0, tt - bar) * 2)
        for f in chord:
            sig[s:e] += env * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2 * tt))
    sig += 0.15 * np.sin(2 * np.pi * 55 * t)  # low drone
    fade = np.minimum(1, np.minimum(t / 1.0, (dur - t) / 1.5))
    sig = sig * np.clip(fade, 0, 1)
    sig = sig / (np.max(np.abs(sig)) + 1e-9) * 0.28
    if voice_track is not None:
        sig = sig * 0.35  # music sits quietly under the voice
        v = np.zeros(n)
        v[:min(n, len(voice_track))] = voice_track[:n]
        sig = sig + v / (np.max(np.abs(v)) + 1e-9) * 0.85
        sig = np.clip(sig, -0.98, 0.98)
    pcm = (sig * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def render(spec, out_path):
    lang = spec.get("lang", "en")
    theme = THEMES[int(spec.get("theme", 0)) % len(THEMES)]
    seed = hash(spec["hook"]) & 0xFFFF
    bg = Background(theme, seed)
    accent = theme[2]

    clips = None
    if spec.get("voice", True):
        sys.path.insert(0, HERE)
        from voice import speak
        say = spec.get("say") or {}  # optional spoken versions (Urdu days: Devanagari)
        texts = ([say.get("hook") or spec["hook"]]
                 + [(say.get("facts") or [None] * len(spec["facts"]))[i] or f
                    for i, f in enumerate(spec["facts"])]
                 + [say.get("cta") or spec["cta"]])
        clips = [speak(t, lang) for t in texts]
    timeline, total = build_timeline(spec, clips)

    voice_track = None
    if clips is not None:
        sr = 44100
        voice_track = np.zeros(int(total * sr) + sr, dtype=np.float32)
        for (s, e, seg), clip in zip(timeline, clips):
            # resample 24k -> 44.1k by linear interpolation
            x = np.interp(np.arange(0, len(clip), VOICE_SR / sr), np.arange(len(clip)), clip)
            a = int((s + VOICE_LEAD) * sr)
            voice_track[a:a + len(x)] += x[:len(voice_track) - a]
    n_facts = len(spec["facts"])

    scratch = Image.new("RGB", (W, H))
    sd = ImageDraw.Draw(scratch)
    layouts = []
    for (s, e, seg) in timeline:
        kind, text = seg[0], seg[1]
        start = 104 if kind == "hook" else (84 if kind == "fact" else 76)
        if lang == "ur":
            start = int(start * 0.85)
        layouts.append(fit_text(sd, text, lang, W - 160, 820, start))

    num_font = font("en", 150)
    small = font("en", 38, 600)
    label_txt = "DID YOU KNOW?" if lang == "en" else "کیا آپ جانتے ہیں؟"
    label_font = font(lang, 54 if lang == "en" else 50)

    tmpdir = tempfile.mkdtemp()
    audio = os.path.join(tmpdir, "music.wav")
    synth_music(audio, total, seed, voice_track)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", audio,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart",
        out_path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    frames = int(total * FPS)
    for fi in range(frames):
        t = fi / FPS
        im = bg.frame(t).convert("RGBA")
        d = ImageDraw.Draw(im)
        for idx, (s, e, seg) in enumerate(timeline):
            if not (s <= t < e):
                continue
            local, dur = t - s, e - s
            a_in = ease(local / 0.45)
            a_out = 1 - ease((local - (dur - 0.35)) / 0.35)
            alpha = max(0.0, min(a_in, a_out))
            dy = (1 - a_in) * 60
            fnt, lines, lh = layouts[idx]
            kind = seg[0]
            if kind == "hook":
                lw = d.textlength(label_txt, font=label_font, **text_kwargs(lang))
                d.text(((W - lw) / 2, 470), label_txt, font=label_font,
                       fill=accent + (int(255 * alpha),), **text_kwargs(lang))
                draw_block(im, lines, fnt, lh, lang, 960, alpha, dy)
            elif kind == "fact":
                num = str(seg[3])
                nw = d.textlength(num, font=num_font)
                d.text(((W - nw) / 2, 380 + dy * 0.5), num, font=num_font,
                       fill=accent + (int(255 * alpha),))
                draw_block(im, lines, fnt, lh, lang, 1000, alpha, dy)
                # dots showing which fact we're on
                for k in range(n_facts):
                    cx = W / 2 + (k - (n_facts - 1) / 2) * 40
                    on = k == seg[3] - 1
                    r = 10 if on else 7
                    col = accent if on else (255, 255, 255)
                    d.ellipse([cx - r, 1560 - r, cx + r, 1560 + r], fill=col + (int((255 if on else 120) * alpha),))
            else:
                draw_block(im, lines, fnt, lh, lang, 960, alpha, dy, color=accent)
        # top progress bar
        d.rectangle([0, 0, int(W * t / total), 10], fill=accent + (255,))
        if spec.get("handle"):
            hw = d.textlength(spec["handle"], font=small)
            d.text(((W - hw) / 2, 1760), spec["handle"], font=small, fill=(255, 255, 255, 170))
        proc.stdin.write(im.convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")
    print(f"OK {out_path} ({total:.1f}s, {frames} frames)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as fh:
        spec = json.load(fh)
    if not spec.get("facts"):
        sys.exit("script.json needs a non-empty 'facts' list")
    render(spec, sys.argv[2])
