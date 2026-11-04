import { AbsoluteFill } from "remotion";
import type { CallSheetProps } from "./schema";
import { paperFor, paperStyle } from "./paper";

const INK = "#1a1916";
const MUTED = "#5f5a4f";
const RULE = "rgba(26,25,22,0.22)";

function hhmm(iso: string | null | undefined) {
  if (!iso) return "—";
  const m = /T(\d\d:\d\d)/.exec(iso);
  return m ? m[1] : iso;
}

const INTERIORS = new Set(["stairwell", "studio", "apartment", "office", "cafe", "hall", "corridor"]);
const heading = (loc: string) => `${INTERIORS.has(loc.toLowerCase()) ? "INT" : "EXT"}. ${loc.toUpperCase()}`;

export const CallSheet: React.FC<CallSheetProps> = (p) => {
  const paper = paperFor(p.release.number);
  const mono = { fontFamily: "Geist Mono" } as const;

  return (
    <AbsoluteFill style={{ ...paperStyle(paper.bg), color: INK, fontFamily: "Geist", padding: "64px 72px" }}>
      {/* revision header, like a revised script page */}
      <div style={{ display: "flex", justifyContent: "space-between", ...mono, fontSize: 15, letterSpacing: 2, color: MUTED }}>
        <span>CALL SHEET · RELEASE {p.release.number} · {paper.name.toUpperCase()}</span>
        <span>{p.release.release_id} · {hhmm(p.release.created_at)} · {p.release.manifest_hash.replace("sha256:", "").slice(0, 7)}</span>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginTop: 28, paddingBottom: 22, borderBottom: `2px solid ${INK}` }}>
        <div>
          <div style={{ fontFamily: "Instrument Serif", fontSize: 76, lineHeight: 1 }}>{p.production.title}</div>
          <div style={{ fontSize: 22, marginTop: 10, color: MUTED }}>{p.production.day} · {p.production.date}</div>
        </div>
        <div style={{ display: "flex", gap: 14 }}>
          <Box label="CREW CALL" value={hhmm(p.general_call)} />
          {p.sunset && <Box label="SUNSET" value={hhmm(p.sunset)} />}
        </div>
      </div>

      {/* what changed */}
      <div style={{ marginTop: 28, padding: "20px 24px", border: `2px solid ${INK}`, borderRadius: 8, background: "rgba(255,255,255,0.28)" }}>
        <div style={{ ...mono, fontSize: 14, letterSpacing: 2, fontWeight: 700 }}>WHAT CHANGED</div>
        <div style={{ fontFamily: "Courier Prime", fontSize: 24, lineHeight: 1.4, marginTop: 8 }}>{p.release.summary}</div>
        <ul style={{ margin: "10px 0 0", paddingLeft: 22, fontSize: 18, color: MUTED, lineHeight: 1.55 }}>
          {p.release.changes.map((c) => <li key={c}>{c}</li>)}
        </ul>
      </div>

      <Heading>SCHEDULE</Heading>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 19 }}>
        <thead>
          <tr style={{ ...mono, fontSize: 13, letterSpacing: 2, color: MUTED, textAlign: "left" }}>
            <th style={th}>SC</th><th style={th}>SET</th><th style={th}>SCENE</th><th style={th}>CAST</th><th style={{ ...th, textAlign: "right" }}>TIME</th>
          </tr>
        </thead>
        <tbody>
          {p.scenes.map((s) =>
            s.status === "held" ? (
              <tr key={s.number} style={{ borderBottom: `1px solid ${RULE}`, background: "repeating-linear-gradient(-45deg, rgba(26,25,22,0.06) 0 8px, transparent 8px 16px)" }}>
                <td style={{ ...td, ...mono, fontWeight: 700 }}>{s.number}{s.changed ? "*" : ""}</td>
                <td style={{ ...td, ...mono, fontSize: 16, fontWeight: 700, letterSpacing: 2 }}>ON HOLD</td>
                <td style={{ ...td, fontFamily: "Courier Prime" }}>{s.title}</td>
                <td colSpan={2} style={{ ...td, color: MUTED, fontSize: 16 }}>{s.hold_reason}</td>
              </tr>
            ) : (
              <tr key={s.number} style={{ borderBottom: `1px solid ${RULE}` }}>
                <td style={{ ...td, ...mono, fontWeight: 700 }}>{s.number}{s.changed ? "*" : ""}</td>
                <td style={{ ...td, ...mono, fontSize: 16 }}>{heading(s.location)}</td>
                <td style={{ ...td, fontFamily: "Courier Prime" }}>{s.title}</td>
                <td style={{ ...td, ...mono, fontSize: 16 }}>{s.cast.join(", ")}</td>
                <td style={{ ...td, ...mono, textAlign: "right" }}>{hhmm(s.start)}–{hhmm(s.end)}</td>
              </tr>
            ),
          )}
        </tbody>
      </table>

      <Heading>CAST &amp; CREW</Heading>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 19 }}>
        <tbody>
          {p.crew.map((c) => (
            <tr key={c.name} style={{ borderBottom: `1px solid ${RULE}` }}>
              <td style={{ ...td, fontWeight: 600, width: "34%" }}>{c.name}</td>
              <td style={{ ...td, color: MUTED }}>{c.role}</td>
              <td style={{ ...td, ...mono, textAlign: "right", fontWeight: c.changed ? 700 : 400 }}>
                {c.changed ? "* " : ""}{hhmm(c.call_time)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <Heading>LOCATIONS</Heading>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 18 }}>
        {p.locations.map((l) => (
          <div key={l.name}><b>{l.name}.</b> {l.note && <span style={{ color: MUTED }}>{l.note}</span>}</div>
        ))}
      </div>

      <div style={{ position: "absolute", left: 72, right: 72, bottom: 56, display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 18, borderTop: `2px solid ${INK}` }}>
        <span style={{ fontFamily: "Courier Prime", fontSize: 22, fontWeight: 700 }}>{p.confirm_hint}</span>
        <span style={{ ...mono, fontSize: 13, color: MUTED, letterSpacing: 1.5 }}>* = changed in this release · TAKE TWO</span>
      </div>
    </AbsoluteFill>
  );
};

const th: React.CSSProperties = { padding: "0 10px 8px 0", borderBottom: `2px solid ${INK}`, fontWeight: 600 };
const td: React.CSSProperties = { padding: "12px 10px 12px 0", verticalAlign: "top" };

function Heading({ children }: { children: React.ReactNode }) {
  return <div style={{ fontFamily: "Geist Mono", fontSize: 14, letterSpacing: 2.5, fontWeight: 700, margin: "34px 0 10px" }}>{children}</div>;
}

function Box({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ border: `2px solid ${INK}`, borderRadius: 8, padding: "10px 18px", textAlign: "center", minWidth: 150 }}>
      <div style={{ fontFamily: "Geist Mono", fontSize: 12, letterSpacing: 2, color: MUTED }}>{label}</div>
      <div style={{ fontFamily: "Geist Mono", fontSize: 40, fontWeight: 600, lineHeight: 1.1 }}>{value}</div>
    </div>
  );
}
