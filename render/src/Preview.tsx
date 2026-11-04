import { AbsoluteFill, Easing, interpolate, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import type { PreviewProps } from "./schema";
import { Courtyard, Figure, GRAPHITE, H, Park, PencilFilter, Room, Rooftop, Stairwell, Sun, W, ZoomContext } from "./sketch";
import { PAPER_STYLE } from "./paper";

// Where each location seats its two characters (hip position) and how they sit.
type Blocking = { a: [number, number]; b: [number, number]; pose: "stand" | "sit"; sun?: [number, number] };
const BLOCKING: Record<string, Blocking> = {
  stairwell: { a: [430, 426], b: [565, 392], pose: "sit" },
  park: { a: [436, 454], b: [532, 454], pose: "sit", sun: [520, 326] },
  rooftop: { a: [420, 420], b: [540, 420], pose: "stand", sun: [560, 300] },
  courtyard: { a: [420, 430], b: [540, 430], pose: "stand" },
  room: { a: [420, 440], b: [540, 440], pose: "stand" },
};
const HEAD = 123; // head centre above the figure's anchor

const SUNSET_LOCATIONS = new Set(["park", "rooftop", "beach", "terrace"]);
const CROWD_LOCATIONS = new Set(["park", "market", "street"]);

// Art area inside the frame, above the caption band.
const ART = { x: 14, y: 14, w: W - 28, h: H - 14 - 70 };

function framing(shot: string, bl: Blocking): { scale: number; cx: number; cy: number } {
  const ha: [number, number] = [bl.a[0], bl.a[1] - HEAD];
  const hb: [number, number] = [bl.b[0], bl.b[1] - HEAD];
  const mid: [number, number] = [(ha[0] + hb[0]) / 2, (ha[1] + hb[1]) / 2];
  switch (shot) {
    case "two-shot": return { scale: 1.7, cx: mid[0], cy: mid[1] + 55 };
    case "medium": return { scale: 2.1, cx: ha[0] + 10, cy: ha[1] + 50 };
    case "close-up": return { scale: 4.2, cx: ha[0] + 6, cy: ha[1] + 20 };
    case "over-shoulder": return { scale: 2.4, cx: hb[0] - 30, cy: hb[1] + 30 };
    case "insert": return { scale: 3.2, cx: mid[0], cy: bl.a[1] - 50 };
    default: return { scale: 1, cx: W / 2, cy: ART.y + ART.h / 2 + 10 };
  }
}

function hhmm(iso: string) {
  const m = /T(\d\d:\d\d)/.exec(iso);
  return m ? m[1] : iso;
}

export const Preview: React.FC<PreviewProps> = (p) => {
  const { durationInFrames } = useVideoConfig();
  const shots = p.shots.length ? p.shots : ["wide"];
  const per = Math.floor(durationInFrames / shots.length);

  return (
    <AbsoluteFill style={PAPER_STYLE}>
      {shots.map((shot, i) => {
        const len = i === shots.length - 1 ? durationInFrames - i * per : per;
        return (
          <Sequence key={i} from={i * per} durationInFrames={len} layout="none">
            <Shot shot={shot} p={p} total={len} />
            <Caption p={p} shot={shot} index={i} count={shots.length} />
          </Sequence>
        );
      })}
      <Frame letter={p.letter} />
    </AbsoluteFill>
  );
};

function Shot({ shot, p, total }: { shot: string; p: PreviewProps; total: number }) {
  const frame = useCurrentFrame();
  const loc = p.location.toLowerCase();
  const bl = BLOCKING[loc] ?? BLOCKING.room;
  const sunset = p.sunset ?? SUNSET_LOCATIONS.has(loc);
  const crowd = p.crowd ?? CROWD_LOCATIONS.has(loc);
  const f = framing(shot, bl);
  const push = interpolate(frame, [0, total], [1, 1.07], { easing: Easing.bezier(0.33, 0, 0.2, 1), extrapolateRight: "clamp" });
  const s = f.scale * push;
  const cx = ART.x + ART.w / 2;
  const cy = ART.y + ART.h / 2;
  const seed = Math.floor(frame / 2) % 6; // line boil, every other frame
  const [a, b] = p.people;

  return (
    <AbsoluteFill>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%">
        <defs>
          <PencilFilter id="pencil" seed={seed} scale={2.2} />
          <clipPath id="art"><rect x={ART.x} y={ART.y} width={ART.w} height={ART.h} rx={8} /></clipPath>
          <linearGradient id="dusk" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#f0a15a" stopOpacity="0.42" />
            <stop offset="0.6" stopColor="#f6c79b" stopOpacity="0.14" />
            <stop offset="1" stopColor="#f6c79b" stopOpacity="0" />
          </linearGradient>
        </defs>
        <g clipPath="url(#art)">
          {sunset && <rect x={ART.x} y={ART.y} width={ART.w} height={ART.h} fill="url(#dusk)" />}
          {/* the filter sits outside the camera transform, so the wobble stays pencil-sized at any zoom */}
          <g filter="url(#pencil)">
            <g transform={`translate(${cx - f.cx * s} ${cy - f.cy * s}) scale(${s})`}>
              <ZoomContext.Provider value={s}>
                {sunset && bl.sun && <Sun x={bl.sun[0]} y={bl.sun[1]} />}
                {loc === "stairwell" ? <Stairwell /> : loc === "park" ? <Park crowd={crowd} frame={frame * 2} /> : loc === "rooftop" ? <Rooftop /> : loc === "courtyard" ? <Courtyard /> : <Room />}
                {a && <Figure x={bl.a[0]} y={bl.a[1]} pose={bl.pose} facing={1} label={shot === "close-up" ? undefined : a.name} hair="long" />}
                {b && <Figure x={bl.b[0]} y={bl.b[1]} pose={bl.pose} facing={-1} label={shot === "close-up" ? undefined : b.name} />}
              </ZoomContext.Provider>
            </g>
          </g>
        </g>
      </svg>
    </AbsoluteFill>
  );
}

function Caption({ p, shot, index, count }: { p: PreviewProps; shot: string; index: number; count: number }) {
  return (
    <div style={{ position: "absolute", left: 14, right: 14, bottom: 14, height: 70, borderTop: `2px solid ${GRAPHITE}`, display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0 22px", color: GRAPHITE }}>
      <div style={{ fontFamily: "Courier Prime" }}>
        <div style={{ fontSize: 17, fontWeight: 700, letterSpacing: 1.5 }}>
          SC {p.scene_number} · {p.location.toUpperCase()} · {shot.toUpperCase()}
        </div>
        <div style={{ fontSize: 14, opacity: 0.72, marginTop: 1 }}>
          {p.label} — {hhmm(p.start)}–{hhmm(p.end)}
        </div>
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        {Array.from({ length: count }, (_, i) => (
          <div key={i} style={{ width: 22, height: 4, borderRadius: 2, background: GRAPHITE, opacity: i === index ? 0.9 : 0.2 }} />
        ))}
      </div>
    </div>
  );
}

function Frame({ letter }: { letter: string }) {
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", inset: 14, border: `2.5px solid ${GRAPHITE}`, borderRadius: 10, opacity: 0.9 }} />
      <div style={{ position: "absolute", top: 28, left: 28, width: 42, height: 42, borderRadius: 8, background: GRAPHITE, color: "#f4f1e8", display: "grid", placeItems: "center", fontFamily: "Geist Mono", fontWeight: 700, fontSize: 22 }}>
        {letter}
      </div>
      <div style={{ position: "absolute", top: 30, right: 32, padding: "4px 9px", background: "rgba(244,241,232,0.85)", borderRadius: 4, fontFamily: "Geist Mono", fontSize: 11.5, letterSpacing: 2, color: GRAPHITE, opacity: 0.7 }}>
        TAKE TWO · PREVIEW
      </div>
    </AbsoluteFill>
  );
}
