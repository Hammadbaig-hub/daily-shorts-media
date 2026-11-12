import React, { useMemo } from "react";
import { Audio } from "@remotion/media";
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  random,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Palette, PALETTES, Segment, Timeline } from "./types";

export const W = 1080;
export const H = 1920;
const UR = "NotoNastaliq, serif";
const EN = "Montserrat, sans-serif";
const MYTH = "#eb2837";
const FACT = "#14af55";
const MARKS: Record<string, string> = { good: "check", bad: "cross", warn: "warning" };
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const outBack = Easing.out(Easing.back(2.2));
const outCubic = Easing.out(Easing.cubic);

const icon = (name: string) => staticFile(`icons/${name}.png`);

// ------------------------------------------------------------------ background
const Background: React.FC<{ pal: Palette; t: number; floats: string[]; seed: number }> = ({ pal, t, floats, seed }) => {
  const floaters = useMemo(
    () =>
      new Array(9).fill(0).map((_, i) => ({
        name: floats[Math.floor(random(`f${seed}${i}`) * floats.length)],
        x: 60 + random(`x${seed}${i}`) * (W - 120),
        y0: random(`y${seed}${i}`) * H,
        size: 80 + random(`s${seed}${i}`) * 60,
        sp: 60 + random(`v${seed}${i}`) * 60,
        rot: -30 + random(`r${seed}${i}`) * 60,
        rs: -40 + random(`q${seed}${i}`) * 80,
      })),
    [floats, seed],
  );
  const sparks = useMemo(
    () =>
      new Array(40).fill(0).map((_, i) => ({
        x: random(`sx${seed}${i}`) * W,
        y: random(`sy${seed}${i}`) * H,
        r: 3 + random(`sr${seed}${i}`) * 5,
        ph: random(`sp${seed}${i}`) * 6.28,
        sp: 60 + random(`ss${seed}${i}`) * 100,
      })),
    [seed],
  );
  return (
    <AbsoluteFill style={{ background: `linear-gradient(180deg, ${pal.bg1} 0%, ${pal.bg2} 100%)`, overflow: "hidden" }}>
      {pal.blob.map((c, i) => {
        const a = t * (0.25 + i * 0.07) + i * 2.1;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              width: 900,
              height: 900,
              borderRadius: "50%",
              left: W / 2 - 450 + Math.cos(a) * 380,
              top: H / 2 - 450 + Math.sin(a * 1.3) * 650,
              background: `radial-gradient(circle, ${c}aa 0%, ${c}00 65%)`,
            }}
          />
        );
      })}
      {/* rotating light rays */}
      <div
        style={{
          position: "absolute",
          width: 2800,
          height: 2800,
          left: W / 2 - 1400,
          top: 760 - 1400,
          rotate: `${t * 12}deg`,
          background:
            "repeating-conic-gradient(from 0deg, rgba(255,255,255,0.10) 0deg 7deg, rgba(255,255,255,0) 7deg 22.5deg)",
          maskImage: "radial-gradient(circle, black 0%, black 25%, transparent 60%)",
          WebkitMaskImage: "radial-gradient(circle, black 0%, black 25%, transparent 60%)",
        }}
      />
      {floaters.map((f, i) => {
        const y = (((f.y0 - t * f.sp) % (H + 300)) + H + 300) % (H + 300) - 150;
        return (
          <Img
            key={i}
            src={icon(f.name)}
            style={{
              position: "absolute",
              left: f.x - f.size / 2 + Math.sin(t * 0.8 + i) * 30,
              top: y,
              width: f.size,
              height: f.size,
              opacity: 0.16,
              rotate: `${f.rot + t * f.rs}deg`,
            }}
          />
        );
      })}
      {sparks.map((s, i) => {
        const y = (((s.y - t * s.sp) % H) + H) % H;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: s.x,
              top: y,
              width: s.r * 2,
              height: s.r * 2,
              borderRadius: "50%",
              background: "white",
              opacity: 0.25 + 0.6 * Math.max(0, Math.sin(t * 3 + s.ph)),
              boxShadow: "0 0 12px rgba(255,255,255,0.9)",
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ pieces
const Pill: React.FC<{
  text: string;
  y: number;
  bg: string;
  fg?: string;
  font?: string;
  size: number;
  scale?: number;
  rtl?: boolean;
}> = ({ text, y, bg, fg = "white", font = EN, size, scale = 1, rtl }) => (
  <div style={{ position: "absolute", left: 0, right: 0, top: y, display: "flex", justifyContent: "center" }}>
    <div
      dir={rtl ? "rtl" : "ltr"}
      style={{
        translate: "0 -50%",
        scale: String(Math.max(0, scale)),
        background: bg,
        color: fg,
        fontFamily: font,
        fontWeight: 900,
        fontSize: size,
        lineHeight: font === UR ? 1.7 : 1.15,
        padding: font === UR ? "0px 48px 10px" : "16px 46px",
        borderRadius: 999,
        letterSpacing: font === EN ? 2 : 0,
        boxShadow: "0 10px 30px rgba(0,0,0,0.35)",
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </div>
  </div>
);

const Icons: React.FC<{ names: string[]; tl: number; cy: number; base: number }> = ({ names, tl, cy, base }) => {
  const icons = names.slice(0, 3);
  const n = icons.length;
  if (!n) return null;
  const size = n === 1 ? base : n === 2 ? Math.min(base, 300) : Math.min(base, 250);
  const gap = size * 1.08;
  return (
    <>
      {icons.map((name, k) => {
        let x = W / 2 + (k - (n - 1) / 2) * gap;
        x = W - x; // RTL order
        const ent = interpolate(tl - 0.02 - k * 0.09, [0, 0.4], [0, 1], { ...clamp, easing: outBack });
        const ph = k * 1.9;
        const bob = Math.sin(tl * 3.4 + ph) * 22;
        const rot = Math.sin(tl * 2.6 + ph) * 9;
        const breathe = 1 + 0.06 * Math.sin(tl * 4.2 + ph);
        return (
          <Img
            key={k}
            src={icon(name)}
            style={{
              position: "absolute",
              width: size,
              height: size,
              left: x - size / 2 + Math.sin(tl * 1.8 + ph) * 12,
              top: cy - size / 2 + bob,
              scale: String(Math.max(0, ent * breathe)),
              rotate: `${rot}deg`,
              filter: "drop-shadow(0 22px 26px rgba(0,0,0,0.45))",
            }}
          />
        );
      })}
    </>
  );
};

const chunkWords = (words: string[]) => {
  const chunks: number[][] = [];
  let cur: number[] = [];
  let len = 0;
  words.forEach((w, i) => {
    if (cur.length && (cur.length >= 3 || len + w.length > 15)) {
      chunks.push(cur);
      cur = [];
      len = 0;
    }
    cur.push(i);
    len += w.length;
    if ("۔!؟?،".includes(w[w.length - 1])) {
      chunks.push(cur);
      cur = [];
      len = 0;
    }
  });
  if (cur.length) chunks.push(cur);
  return chunks;
};

const Kinetic: React.FC<{ seg: Segment; tl: number; cy: number; accent: string }> = ({ seg, tl, cy, accent }) => {
  const words = useMemo(() => seg.text.split(/\s+/), [seg.text]);
  const chunks = useMemo(() => chunkWords(words), [words]);
  let active = -1;
  seg.wt.forEach((w, i) => {
    if (tl >= w - 0.03) active = i;
  });
  if (active < 0) return null;
  const ci = chunks.findIndex((c) => c.includes(active));
  const chunk = chunks[ci];
  const start = seg.wt[chunk[0]];
  const pop = interpolate(tl - start + 0.03, [0, 0.22], [0.55, 1], { ...clamp, easing: outBack });
  const chars = chunk.reduce((a, i) => a + words[i].length, 0) + chunk.length;
  const size = Math.max(78, Math.min(122, Math.floor(1500 / Math.max(chars, 9))));
  return (
    <div
      style={{
        position: "absolute",
        left: 40,
        right: 40,
        top: cy,
        display: "flex",
        justifyContent: "center",
        translate: "0 -50%",
        scale: String(pop * (1 + 0.015 * Math.sin(tl * 9))),
      }}
    >
      <div
        dir="rtl"
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "0 34px",
          fontFamily: UR,
          fontWeight: 700,
          fontSize: size,
          lineHeight: 2.0,
          filter: "drop-shadow(0 10px 18px rgba(0,0,0,0.5))",
        }}
      >
        {chunk.map((i) => {
          const on = i === active;
          const bump = on ? interpolate(tl - seg.wt[i], [0, 0.08, 0.2], [1, 1.14, 1.06], clamp) : 1;
          return (
            <span
              key={i}
              style={{
                display: "inline-block",
                color: on ? accent : "white",
                WebkitTextStroke: `${Math.max(12, size / 7)}px #140a1e`,
                paintOrder: "stroke fill",
                scale: String(bump),
                opacity: i <= active ? 1 : 0.92,
              }}
            >
              {words[i]}
            </span>
          );
        })}
      </div>
    </div>
  );
};

const Stamp: React.FC<{ verdict: "myth" | "fact"; tl: number }> = ({ verdict, tl }) => {
  const col = verdict === "myth" ? MYTH : FACT;
  const s = interpolate(tl, [0, 0.16], [2.6, 1], { ...clamp, easing: outCubic });
  const op = interpolate(tl, [0, 0.12], [0, 1], clamp);
  const pulse = tl > 0.3 ? 1 + 0.03 * Math.sin(tl * 6) : 1;
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: 470, display: "flex", justifyContent: "center" }}>
      <div
        style={{
          translate: "0 -50%",
          rotate: "-7deg",
          scale: String(s * pulse),
          opacity: op,
          width: 800,
          height: 300,
          borderRadius: 50,
          background: col,
          border: "14px solid white",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 56px",
          boxSizing: "border-box",
          boxShadow: `0 0 60px ${col}aa, 0 20px 40px rgba(0,0,0,0.4)`,
          color: "white",
        }}
      >
        <span style={{ fontFamily: EN, fontWeight: 900, fontSize: 150, letterSpacing: 2 }}>
          {verdict === "myth" ? "MYTH" : "FACT"}
        </span>
        <span dir="rtl" style={{ fontFamily: UR, fontWeight: 700, fontSize: 112, lineHeight: 1.6 }}>
          {verdict === "myth" ? "غلط" : "سچ"}
        </span>
      </div>
    </div>
  );
};

const Suspense: React.FC<{ tSus: number; t: number; dur: number; accent: string }> = ({ tSus, t, dur, accent }) => {
  const frac = Math.min(1, tSus / (dur - 0.05));
  const r = 95 + 8 * Math.sin(t * 20);
  const num = 3 - Math.min(2, Math.floor(tSus / 0.3));
  const numPop = interpolate((tSus % 0.3) / 0.3, [0, 0.4], [1.5, 1], { ...clamp, easing: outCubic });
  return (
    <div
      style={{
        position: "absolute",
        left: W / 2 - r,
        top: 1560 - r,
        width: 2 * r,
        height: 2 * r,
        borderRadius: "50%",
        background: `conic-gradient(${accent} ${frac * 360}deg, rgba(0,0,0,0.45) 0deg)`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: `0 0 40px ${accent}88`,
      }}
    >
      <div
        style={{
          width: 2 * r - 32,
          height: 2 * r - 32,
          borderRadius: "50%",
          background: "rgba(20,10,30,0.85)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "white",
          fontFamily: EN,
          fontWeight: 900,
          fontSize: 110,
          scale: String(numPop),
        }}
      >
        {num}
      </div>
    </div>
  );
};

// ------------------------------------------------------------------ main
export const MythShort: React.FC<{ timeline: Timeline; audio: string }> = ({ timeline, audio }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const pal = PALETTES[timeline.palette % PALETTES.length];
  const segs = timeline.segments;
  let si = segs.findIndex((s) => s.start <= t && t < s.start + s.dur);
  if (si < 0) si = segs.length - 1;
  const seg = segs[si];
  const tl = t - seg.start;
  const kind = seg.kind;
  const floats = useMemo(
    () => Array.from(new Set([...segs.flatMap((s) => s.icons), "sparkles", "greenheart", "bulb"])).sort(),
    [segs],
  );

  // camera: zoom punch at each segment start + shake on stamp
  const zoom = 1 + interpolate(tl, [0, 0.35], [0.07, 0], { ...clamp, easing: outCubic });
  let sx = 0;
  let sy = 0;
  if (kind === "explain" && tl > 0.14 && tl < 0.5) {
    const amp = 22 * (1 - (tl - 0.14) / 0.36);
    sx = amp * Math.sin(tl * 90);
    sy = amp * Math.cos(tl * 77);
  }
  let flash = 0;
  if (kind === "explain" && tl > 0.12 && tl < 0.3) flash = 0.55 * (1 - (tl - 0.12) / 0.18);
  if (kind === "claim" && tl < 0.1) flash = 0.35 * (1 - tl / 0.1);

  const hookBadge = spring({ frame: (tl - 0.1) * fps, fps, config: { damping: 9, stiffness: 160 } });
  const qPop = spring({ frame: (tl - 0.15) * fps, fps, config: { damping: 9, stiffness: 160 } });
  const tSus = tl - (seg.dur - timeline.suspense);
  const discIn = interpolate(tl, [0.5, 0.9], [0, 1], clamp);

  return (
    <AbsoluteFill style={{ backgroundColor: pal.bg1 }}>
      {audio ? <Audio src={staticFile(audio)} /> : null}
      <AbsoluteFill style={{ scale: String(zoom), translate: `${sx}px ${sy}px` }}>
        <Background pal={pal} t={t} floats={floats} seed={timeline.seed} />

        {kind === "hook" && (
          <>
            <Icons names={seg.icons} tl={tl} cy={760} base={380} />
            <Pill text="MYTH  or  FACT ?" y={330} bg={pal.pill} size={66} scale={hookBadge} />
          </>
        )}
        {(kind === "claim" || kind === "explain") && (
          <Pill text={`${(seg.item ?? 0) + 1}/${seg.n}`} y={200} bg={pal.pill} size={52} />
        )}
        {kind === "claim" && (
          <>
            <Icons names={seg.icons} tl={tl} cy={760} base={360} />
            <Pill text="سچ یا غلط؟" y={385} bg="white" fg="#1e1428" font={UR} size={62} scale={qPop} rtl />
            {tSus > 0 && <Suspense tSus={tSus} t={t} dur={timeline.suspense} accent={pal.accent} />}
          </>
        )}
        {kind === "explain" && (
          <>
            <Icons names={seg.icons} tl={Math.max(0, tl - 0.35)} cy={870} base={320} />
            {seg.mark && MARKS[seg.mark] && tl > 0.6 && (
              <Img
                src={icon(MARKS[seg.mark])}
                style={{
                  position: "absolute",
                  width: 150,
                  height: 150,
                  left: W / 2 + 230 - 75,
                  top: 1000 - 75,
                  scale: String(
                    interpolate(tl - 0.6, [0, 0.3], [0, 1], { ...clamp, easing: Easing.out(Easing.back(3)) }) *
                      (1 + 0.08 * Math.sin(tl * 7)),
                  ),
                  rotate: `${Math.sin(tl * 4) * 10}deg`,
                  filter: "drop-shadow(0 12px 16px rgba(0,0,0,0.4))",
                }}
              />
            )}
            <Stamp verdict={seg.verdict ?? "myth"} tl={tl} />
          </>
        )}
        {kind === "cta" && <Icons names={seg.icons} tl={tl} cy={760} base={340} />}

        <Kinetic seg={seg} tl={tl} cy={kind === "explain" ? 1340 : 1300} accent={pal.accent} />

        {kind === "cta" && timeline.disclaimer && (
          <div
            dir="rtl"
            style={{
              position: "absolute",
              left: 60,
              right: 60,
              top: 1600,
              padding: "6px 30px 14px",
              borderRadius: 30,
              background: `rgba(0,0,0,${0.45 * discIn})`,
              color: `rgba(255,255,255,${0.95 * discIn})`,
              fontFamily: UR,
              fontSize: 34,
              lineHeight: 1.9,
              textAlign: "center",
              textWrap: "balance",
            }}
          >
            {timeline.disclaimer}
          </div>
        )}

        {/* progress bar + handle */}
        <div
          style={{
            position: "absolute",
            left: 40,
            right: 40,
            top: 60,
            height: 20,
            borderRadius: 10,
            background: "rgba(255,255,255,0.28)",
            overflow: "hidden",
          }}
        >
          <div style={{ width: `${(t / timeline.total) * 100}%`, height: "100%", background: pal.accent, borderRadius: 10 }} />
        </div>
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            top: 1815,
            textAlign: "center",
            fontFamily: EN,
            fontWeight: 800,
            fontSize: 40,
            color: "rgba(255,255,255,0.78)",
          }}
        >
          {timeline.handle}
        </div>
      </AbsoluteFill>
      {flash > 0 && <AbsoluteFill style={{ background: "white", opacity: flash }} />}
    </AbsoluteFill>
  );
};
