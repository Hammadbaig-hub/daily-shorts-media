#!/usr/bin/env python3
"""
Decide today's language and theme from history.json, and list past topics so
nothing repeats.

Usage:
    python plan_today.py <path/to/history.json>

Prints JSON: {"lang": "en"|"ur", "theme": int, "already_done": [...], "posted_today": bool}
"""
import datetime
import json
import os
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "history.json"
hist = []
if os.path.exists(path):
    with open(path, encoding="utf-8") as fh:
        hist = json.load(fh)

today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5))).date().isoformat()
posted_today = any(h.get("date") == today for h in hist)

last_lang = hist[-1]["lang"] if hist else "ur"   # so the very first video is English
lang = "ur" if last_lang == "en" else "en"
theme = (hist[-1].get("theme", -1) + 1) % 6 if hist else 0

print(json.dumps({
    "date": today,
    "lang": lang,
    "theme": theme,
    "posted_today": posted_today,
    "already_done": [h["topic"] for h in hist],
}, ensure_ascii=False, indent=2))
