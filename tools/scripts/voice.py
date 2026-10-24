#!/usr/bin/env python3
"""
Free offline voiceover with Kokoro (82M neural TTS, runs on CPU, no API key).

Model files (~350 MB) are downloaded once from GitHub releases into ~/tts
(override with KOKORO_DIR). English uses a native English voice; Urdu is spoken
by Kokoro's Hindi voice from Urdu-script text — spoken Urdu and Hindi share
nearly all sounds, and a few espeak Urdu phonemes are remapped to the ones the
Hindi voice was trained on.
"""
import os
import subprocess

import numpy as np

KOKORO_DIR = os.environ.get("KOKORO_DIR", os.path.expanduser("~/tts"))
BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FILES = ["kokoro-v1.0.onnx", "voices-v1.0.bin"]
SR = 24000

VOICES = {"en": ("am_michael", "en-us", 1.0), "ur": ("hm_omega", "ur", 0.92)}

# espeak 'ur' phonemes -> phonemes the Hindi voice knows
UR_FIX = [("ʂ", "s"), ("hẽ", "hɛ̃"), ("nahˈiːn", "nˈʌhĩ"), ("r", "ɾ")]

_k = None


def ensure_model():
    os.makedirs(KOKORO_DIR, exist_ok=True)
    for f in FILES:
        p = os.path.join(KOKORO_DIR, f)
        if not os.path.exists(p) or os.path.getsize(p) < 1_000_000:
            subprocess.run(["curl", "-sSfL", "-o", p, BASE + f], check=True)


def engine():
    global _k
    if _k is None:
        try:
            from kokoro_onnx import Kokoro  # noqa
        except ImportError:
            subprocess.run(["pip", "install", "-q", "--break-system-packages",
                            "kokoro-onnx", "soundfile"], check=True)
        from kokoro_onnx import Kokoro
        ensure_model()
        _k = Kokoro(os.path.join(KOKORO_DIR, FILES[0]), os.path.join(KOKORO_DIR, FILES[1]))
    return _k


def speak(text, lang):
    """Return float32 mono audio at 24 kHz for one line of text."""
    k = engine()
    voice, espeak_lang, speed = VOICES[lang]
    if lang == "ur":
        ph = k.tokenizer.phonemize(text, lang="ur")
        for a, b in UR_FIX:
            ph = ph.replace(a, b)
        audio, _ = k.create(ph, voice=voice, speed=speed, is_phonemes=True)
    else:
        audio, _ = k.create(text, voice=voice, speed=speed, lang=espeak_lang)
    return np.asarray(audio, dtype=np.float32)
