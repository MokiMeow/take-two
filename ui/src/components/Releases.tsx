import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Check, DiscordLogo, ChatsCircle } from "@phosphor-icons/react";
import type { CrewMember, Release, Scene } from "../types";
import { hhmm, initials, paperFor, shortHash, span, stripFor } from "../format";
import { Section, Stamp, StatusDot, type DotState } from "./bits";
import "./Releases.css";

const STEP = 24;
const PUB_DOT: Record<string, DotState> = { pending: "queued", sent: "done", uncertain: "hold", failed: "failed" };

export function ReleaseStack({ releases, scenes, tz }: { releases: Release[]; scenes: Scene[]; tz: string }) {
  const reduce = useReducedMotion();
  const [current, ...older] = releases;
  if (!current) {
    return (
      <Section label="Releases">
        <div className="release-empty">No release yet. The first approved plan appears here.</div>
      </Section>
    );
  }
  const paper = paperFor(current.number);

  return (
    <Section label="Releases" right={<span className="eyebrow">{paper.name} pages</span>}>
      <div className="stack" style={{ paddingTop: Math.min(older.length, 2) * STEP }}>
        {older.slice(0, 2).reverse().map((r, i, arr) => {
          const depth = arr.length - i;
          return (
            <motion.div
              key={r.release_id}
              className="stack-under paper"
              style={{ backgroundColor: paperFor(r.number).bg, top: i * STEP, insetInline: depth * 7 }}
              initial={false}
              animate={{ opacity: 1 }}
            >
              <span className="mono stack-under-label">RELEASE {r.number}</span>
              <Stamp tone="muted" size="sm" rotate={-2}>Superseded</Stamp>
            </motion.div>
          );
        })}
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.article
            key={current.release_id}
            className="page paper"
            style={{ backgroundColor: paper.bg }}
            initial={reduce ? false : { y: -34, rotate: -2.2, opacity: 0 }}
            animate={{ y: 0, rotate: 0, opacity: 1 }}
            exit={{ y: 10, opacity: 0 }}
            transition={{ duration: 0.56, ease: [0.22, 1, 0.36, 1] }}
          >
            <header className="page-head">
              <div>
                <div className="mono page-kicker">RELEASE {current.number} · {paper.name.toUpperCase()}</div>
                <div className="mono page-sub">{current.release_id} · {hhmm(current.created_at, tz)} · {shortHash(current.manifest_hash)}</div>
              </div>
              {current.status === "approved" && <Stamp tone="muted" size="sm">Approved · not sent</Stamp>}
            </header>
            <p className="page-summary script">{current.summary}</p>
            <table className="page-table">
              <thead>
                <tr><th>SC</th><th>SET</th><th>TIME</th></tr>
              </thead>
              <tbody>
                {scenes.map((s) => (
                  <tr key={s.id} className={s.validity !== "valid" ? "is-held" : ""}>
                    <td className="mono">{s.number}</td>
                    <td className="mono">{stripFor(s.plan?.location, s.plan?.start).heading}</td>
                    <td className="mono">{s.plan ? span(s.plan.start, s.plan.end, tz) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <ul className="page-pubs">
              {current.publications.map((p) => (
                <li key={p.platform + p.room}>
                  {p.platform === "discord" ? <DiscordLogo size={13} /> : <ChatsCircle size={13} />}
                  <span className="mono">{p.room}</span>
                  <StatusDot state={PUB_DOT[p.status] ?? "idle"} size={7} />
                  <span className="page-pub-status">{p.status}</span>
                </li>
              ))}
            </ul>
          </motion.article>
        </AnimatePresence>
      </div>
    </Section>
  );
}

export function CrewConfirmations({ crew, release, tz }: { crew: CrewMember[]; release?: Release; tz: string }) {
  const reduce = useReducedMotion();
  if (!release) return null;
  const confirmed = new Map(release.acks.confirmed.map((c) => [c.person, c.at]));
  const expected = new Set(release.acks.expected);
  const n = release.acks.confirmed.filter((c) => expected.has(c.person)).length;

  return (
    <Section
      label="Crew"
      right={
        <span className="crew-count mono">
          <AnimatePresence mode="popLayout" initial={false}>
            <motion.span key={n} initial={reduce ? false : { y: 8, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: -8, opacity: 0 }} transition={{ duration: 0.22 }}>
              {n}
            </motion.span>
          </AnimatePresence>
          /{expected.size} on r{release.number}
        </span>
      }
    >
      <ul className="crew">
        {crew.map((c) => {
          const at = confirmed.get(c.id);
          const onCurrent = at !== undefined || c.acked_release === release.number;
          const stale = !onCurrent && expected.has(c.id);
          return (
            <li key={c.id} className={`crew-row ${stale ? "is-stale" : ""}`}>
              <span className="avatar mono">{initials(c.name)}</span>
              <span className="crew-who">
                <span className="crew-name">{c.name}</span>
                <span className="crew-role">{c.role}</span>
              </span>
              <span className="crew-call mono" title="Call time">{hhmm(c.call_time, tz)}</span>
              <span className="crew-ack">
                {onCurrent ? (
                  <span className="ack-ok">
                    <motion.svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
                      <motion.path d="M2.5 7.5 L5.6 10.4 L11.5 3.8" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"
                        initial={reduce ? false : { pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.24, ease: "easeOut" }} />
                    </motion.svg>
                    <span className="mono">r{release.number}{at ? ` · ${hhmm(at, tz)}` : ""}</span>
                  </span>
                ) : stale ? (
                  <span className="ack-stale mono">still on r{c.acked_release ?? "—"}</span>
                ) : (
                  <span className="ack-carry mono"><Check size={12} /> unchanged</span>
                )}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="crew-policy">
        {release.acks.policy === "affected_only"
          ? "Only people whose call changed re-confirm. Others carry forward."
          : "Everyone confirms this release."}
      </p>
    </Section>
  );
}
