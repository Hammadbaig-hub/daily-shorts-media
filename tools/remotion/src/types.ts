export type Segment = {
  kind: "hook" | "claim" | "explain" | "cta";
  text: string;
  icons: string[];
  item?: number;
  n?: number;
  verdict?: "myth" | "fact";
  mark?: string | null;
  lead: number;
  s0: number;
  s1: number;
  dur: number;
  start: number;
  wt: number[];
};

export type Timeline = {
  total: number;
  fps: number;
  suspense: number;
  palette: number;
  handle: string;
  disclaimer: string;
  seed: number;
  segments: Segment[];
};

export type Palette = { bg1: string; bg2: string; blob: string[]; accent: string; pill: string };

// same 4 palettes as make_myth_short.py (theme % 4)
export const PALETTES: Palette[] = [
  { bg1: "#26105c", bg2: "#c41e78", blob: ["#ff5aa0", "#7846ff", "#ffaa3c"], accent: "#ffd600", pill: "#ff4678" },
  { bg1: "#06285a", bg2: "#00a0aa", blob: ["#00dcc8", "#3c78ff", "#ffc850"], accent: "#ffe628", pill: "#00c8aa" },
  { bg1: "#460a28", bg2: "#fa6e28", blob: ["#ffa028", "#e6285a", "#ffe678"], accent: "#fff05a", pill: "#ff5a32" },
  { bg1: "#0a321e", bg2: "#28aa5a", blob: ["#78f078", "#00a0c8", "#ffdc46"], accent: "#ffe11e", pill: "#1ebe6e" },
];
