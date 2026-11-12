# Bright Life — Remotion renderer

Draws the "Myth ya Fact?" Shorts. Don't run this directly for the daily video;
use `tools/scripts/make_remotion_short.py script.json out.mp4`, which makes the
Urdu voice/audio mix + `timeline.json` with Python and then renders this
`MythShort` composition with those props.

- `src/MythShort.tsx` — the video (background, icons, kinetic captions, stamps, timer)
- `src/types.ts` — timeline types + the 4 palettes
- `src/sample-timeline.json` — sample props for Remotion Studio (`npx remotion studio`)
