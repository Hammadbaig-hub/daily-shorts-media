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
    if lang == "ur" and any("\u0900" <= c <= "\u097f" for c in text):
        # Best quality: Urdu written phonetically in Devanagari ("say" lines in
        # script.json). This is exactly what the Hindi voice was trained on, so
        # vowels, nasals and pauses come out right.
        ph = k.tokenizer.phonemize(text, lang="hi")
        audio, _ = k.create(ph, voice=voice, speed=speed, is_phonemes=True)
    elif lang == "ur":
        ph = k.tokenizer.phonemize(text, lang="ur")
        for a, b in UR_FIX:
            ph = ph.replace(a, b)
        audio, _ = k.create(ph, voice=voice, speed=speed, is_phonemes=True)
    else:
        audio, _ = k.create(text, voice=voice, speed=speed, lang=espeak_lang)
    return np.asarray(audio, dtype=np.float32)


# ---------------------------------------------------------------------------
# Native Urdu voice: Piper "Fasih" (ur_PK, male, MIT), trained on real Urdu
# speech, so the accent is genuinely Urdu. Hosted on sherpa-onnx GitHub releases.
PIPER_UR_URL = ("https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/"
                "vits-piper-ur_PK-fasih-medium.tar.bz2")
_piper = None


def _piper_voice():
    global _piper
    if _piper is None:
        try:
            from piper import PiperVoice  # noqa
        except ImportError:
            subprocess.run(["pip", "install", "-q", "--break-system-packages", "piper-tts"], check=True)
        from piper import PiperVoice
        d = os.path.join(KOKORO_DIR, "vits-piper-ur_PK-fasih-medium")
        onnx = os.path.join(d, "ur_PK-fasih-medium.onnx")
        if not os.path.exists(onnx):
            os.makedirs(KOKORO_DIR, exist_ok=True)
            tarp = os.path.join(KOKORO_DIR, "fasih.tar.bz2")
            subprocess.run(["curl", "-sSfL", "-o", tarp, PIPER_UR_URL], check=True)
            subprocess.run(["tar", "xjf", tarp, "-C", KOKORO_DIR], check=True)
        _piper = PiperVoice.load(onnx, config_path=onnx + ".json")
    return _piper


def speak_urdu_native(text, speed=1.0):
    """Float32 mono at 24 kHz (resampled from Piper's 22.05 kHz)."""
    from piper import SynthesisConfig
    v = _piper_voice()
    cfg = SynthesisConfig(length_scale=1.0 / speed)
    chunks = [c.audio_float_array for c in v.synthesize(text, syn_config=cfg)]
    a = np.concatenate(chunks).astype(np.float32)
    sr_in = v.config.sample_rate
    x = np.arange(0, len(a), sr_in / SR)
    return np.interp(x, np.arange(len(a)), a).astype(np.float32)
