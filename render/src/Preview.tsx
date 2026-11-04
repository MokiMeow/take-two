import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { useMemo } from "react";
import type { PreviewProps } from "./schema";
// The same set model the Control Room shows, so the crew and the director see one picture.
import { maquette } from "../../ui/src/sets/maquette";
import "../../ui/src/sets/sets.css";

const INK = "#eff0e9";
const MUTED = "#a9b0b3";
const FAINT = "#7d888d";
const EASE = Easing.bezier(0.23, 1, 0.32, 1);

function hhmm(iso: string) {
  const m = /T(\d\d:\d\d)/.exec(iso);
  return m ? m[1] : iso;
}

const title = (s: string) => s.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const Preview: React.FC<PreviewProps> = (p) => {
  const frame = useCurrentFrame();
  const { durationInFrames, fps } = useVideoConfig();

  const base = useMemo(
    () =>
      maquette({
        location: p.location,
        people: p.people.map((x) => x.id),
        shots: p.shots,
        names: Object.fromEntries(p.people.map((x) => [x.id, x.name])),
      }),
    [p.location, p.people, p.shots],
  );

  // Entrance, driven by frame: each cast member drops onto their mark, then the camera view appears.
  const svg = useMemo(() => {
    let out = base.replace(/class="set-pawn" style="--i:(\d+)"/g, (_m: string, n: string) => {
      const start = 0.25 * fps + Number(n) * 0.12 * fps;
      const t = interpolate(frame, [start, start + 0.5 * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE });
      return `class="set-pawn" style="opacity:${t};transform:translateY(${(1 - t) * -14}px);animation:none"`;
    });
    const cone = interpolate(frame, [0.75 * fps, 1.2 * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    out = out.replace(/class="set-cone"/g, `class="set-cone" style="opacity:${cone};animation:none"`);
    return out;
  }, [base, frame, fps]);

  // A slow push-in across the clip, like a dolly on the model.
  const push = interpolate(frame, [0, durationInFrames], [1, 1.07], { easing: Easing.inOut(Easing.quad) });
  const panel = interpolate(frame, [0.1 * fps, 0.6 * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: EASE });
  const shotIndex = Math.min(p.shots.length - 1, Math.floor((frame / durationInFrames) * p.shots.length));

  return (
    <AbsoluteFill style={{ background: "radial-gradient(120% 100% at 35% 40%, #232a2f, #16191c)", color: INK, fontFamily: "Geist" }}>
      <div style={{ position: "absolute", left: -40, top: 0, width: 720, height: 540, display: "grid", placeItems: "center" }}>
        <div
          className="set iso"
          style={{ width: 700, background: "none", transform: `scale(${push})`, transformOrigin: "50% 55%" }}
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      </div>

      <div style={{ position: "absolute", left: 640, top: 40, right: 40, bottom: 40, display: "flex", flexDirection: "column", gap: 18, opacity: panel, transform: `translateX(${(1 - panel) * 12}px)` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 54, height: 54, borderRadius: 12, background: INK, color: "#1d2226", display: "grid", placeItems: "center", fontSize: 30, fontWeight: 600 }}>{p.letter}</div>
          <div style={{ fontFamily: "Geist Mono", fontSize: 13, letterSpacing: 1.5, color: FAINT }}>OPTION {p.letter}</div>
        </div>
        <div style={{ fontSize: 30, fontWeight: 600, letterSpacing: -0.8, lineHeight: 1.12 }}>{p.label}</div>
        <div style={{ fontSize: 16, color: MUTED }}>Scene {p.scene_number} · {p.scene_title}</div>
        <div style={{ display: "flex", gap: 10, fontFamily: "Geist Mono", fontSize: 16 }}>
          <span style={{ padding: "6px 10px", borderRadius: 8, background: "#252b30" }}>{hhmm(p.start)}–{hhmm(p.end)}</span>
          <span style={{ padding: "6px 10px", borderRadius: 8, background: "#252b30" }}>{title(p.location)}</span>
        </div>
        <div>
          <div style={{ fontFamily: "Geist Mono", fontSize: 11.5, letterSpacing: 1.4, color: FAINT, marginBottom: 8 }}>SET-UPS</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {p.shots.map((s, i) => (
              <span key={s} style={{ padding: "5px 10px", borderRadius: 999, fontSize: 14, background: i === shotIndex ? INK : "#252b30", color: i === shotIndex ? "#1d2226" : INK }}>{s}</span>
            ))}
          </div>
        </div>
        <div style={{ fontSize: 15, color: MUTED }}>On set: {p.people.map((x) => x.name).join(", ")}</div>
        <div style={{ marginTop: "auto", fontFamily: "Geist Mono", fontSize: 11, color: FAINT }}>set model · plan {p.manifest_hash.replace("sha256:", "").slice(0, 8)}</div>
      </div>
    </AbsoluteFill>
  );
};
