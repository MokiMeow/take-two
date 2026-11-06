// Every message in Take Two travels through Switch. This panel draws the rooms, the agents and the
// coordinator around the Switch hub and replays, for each new state, the messages that produced it.
// Display only: hops are derived from the coordinator's own timeline, never invented.
import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { State, TimelineItem } from "../types";
import { hhmm } from "../format";
import { changeSentence, listJoin } from "../story";
import switchMark from "../assets/brands/switch.svg";
import mattermostMark from "../assets/brands/mattermost.svg";
import discordMark from "../assets/brands/discord.svg";
import claudeMark from "../assets/brands/claude.svg";
import openaiMark from "../assets/brands/openai.svg";
import "./SwitchMap.css";

type NodeId = "mm" | "discord" | "switch" | "claude" | "codex" | "coord";
export interface Hop {
  key: string;
  from: NodeId;
  to: NodeId;
  label: string;
  at: string;
  tone: "info" | "hold" | "ask" | "go";
  delay: number;
}

// Node centres, in percent of the map.
const POS: Record<NodeId, [number, number]> = {
  claude: [31, 16],
  codex: [69, 16],
  mm: [12, 52],
  switch: [50, 52],
  discord: [88, 52],
  coord: [50, 87],
};

const STEP = 0.5; // seconds between hops
const TRAVEL = 1.15; // seconds for one hop, through the hub

const short = (s: string, n = 58) => (s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s);

function key(t: TimelineItem) {
  return `${t.at}|${t.kind}|${t.text}`;
}

// Turn the new timeline items between two states into hops through Switch.
export function hopsBetween(prev: State | null, cur: State): Hop[] {
  const seen = new Set((prev?.timeline ?? []).map(key));
  const fresh = [...cur.timeline].reverse().filter((t) => !seen.has(key(t)));
  // The first state of a replay shows only its own last few messages.
  const items = prev ? fresh : fresh.slice(-6);
  const out: Omit<Hop, "delay">[] = [];
  const push = (from: NodeId, to: NodeId, label: string, t: TimelineItem, tone: Hop["tone"] = "info", n = 0) =>
    out.push({ key: `${key(t)}#${n}`, from, to, label, at: t.at, tone });
  const d = cur.decision;
  const answeredNow = d?.answer && (!prev?.decision?.answer || prev.decision.request_id !== d.request_id);
  let answerPlaced = false;
  const placeAnswer = (t: TimelineItem) => {
    if (!answeredNow || answerPlaced || !d?.answer) return;
    answerPlaced = true;
    const chosen = d.candidates.find((c) => c.candidate_id === d.answer!.candidate_id);
    push("mm", "coord", `${d.answer.answered_by_name ?? "Director"} chose “${short(chosen?.label ?? "an option", 40)}”`, { ...t, text: "answer" }, "go");
  };

  for (const t of items) {
    const text = t.text;
    switch (t.kind) {
      case "change": {
        const c = cur.changes.find((x) => x.reporter_name && text.startsWith(x.reporter_name));
        const src: NodeId = c?.source === "discord" ? "discord" : "mm";
        if (c && c.status === "pending_confirmation") push(src, "coord", `${c.reporter_name}: “${short(c.value, 34)}”`, t, "ask");
        else if (c) push(src, "coord", `${c.reporter_name}: ${short(changeSentence(cur, c), 46)}`, t, "hold");
        else push("mm", "coord", short(text), t, "hold");
        break;
      }
      case "hold": {
        const m = /Scene (\d+)/.exec(text);
        const label = `Hold · Scene ${m?.[1] ?? ""}`.trim();
        push("coord", "mm", label, t, "hold", 0);
        push("coord", "discord", label, t, "hold", 1);
        break;
      }
      case "job": {
        if (/script-supervisor/.test(text)) {
          push("coord", "claude", "Job: what must the scene keep?", t, "info", 0);
          if (d?.must_keep?.length) push("claude", "coord", `Keep: ${short(d.must_keep[0], 44)}`, t, "info", 1);
        } else if (/first-ad/.test(text)) {
          push("coord", "codex", "Job: draft plans that fit", t, "info", 0);
          const n = d?.candidates.length;
          if (n) push("codex", "coord", `${n} plan${n === 1 ? "" : "s"} drafted`, t, "info", 1);
        }
        break;
      }
      case "decision": {
        if (/ready for the named authority/.test(text)) push("coord", "mm", `Question card → ${d?.authority_name ?? "director"}`, t, "ask");
        else if (/outdated/.test(text)) push("coord", "mm", "Card closed: the facts changed", t, "hold");
        else if (/awaits the responsible authority/.test(text)) push("coord", "mm", "Record card → 1st AD", t, "ask");
        break;
      }
      case "release": {
        const m = /^r(\d+) published/.exec(text);
        if (m) {
          placeAnswer(t);
          const r = cur.releases.find((x) => x.number === +m[1]);
          const rooms = r?.publications ?? [];
          const label = (room?: string) => `Release ${m[1]} → ${room ?? "#production"}`;
          const mmRoom = rooms.find((p) => p.platform === "mattermost");
          const dRoom = rooms.find((p) => p.platform === "discord");
          if (!rooms.length || mmRoom) push("coord", "mm", label(mmRoom?.room_name), t, "go", 0);
          if (dRoom) push("coord", "discord", label(dRoom.room_name ?? "#day-1"), t, "go", 1);
        }
        break;
      }
      case "ack": {
        const m = /^(.+?) confirmed (r\d+)/.exec(text);
        const person = cur.crew.find((c) => c.name === m?.[1]);
        const rel = cur.releases.find((r) => `r${r.number}` === m?.[2]);
        const src = rel?.acks.confirmed.find((a) => a.person === person?.id)?.source;
        push(src === "discord" ? "discord" : "mm", "coord", `${m?.[1] ?? "Crew"}: confirm ${m?.[2] ?? ""}`, t, "go");
        break;
      }
      case "stale_reply": {
        push("discord", "coord", "A reply about an old release", t, "hold", 0);
        push("coord", "discord", "Corrected: here is the current release", t, "info", 1);
        break;
      }
      default:
        break;
    }
  }
  if (answeredNow && !answerPlaced && items.length) placeAnswer(items[items.length - 1]);

  // Pairs that leave the coordinator together (hold, release) start together.
  let slot = -1;
  let lastBase = "";
  return out.map((h) => {
    const base = h.key.replace(/#\d+$/, "");
    const together = base === lastBase && h.from === "coord" && (h.label.startsWith("Hold") || h.label.startsWith("Release"));
    if (!together) slot++;
    lastBase = base;
    return { ...h, delay: slot * STEP };
  });
}

function usePrevious<T>(value: T): T | null {
  const ref = useRef<{ cur: T | null; prev: T | null }>({ cur: null, prev: null });
  if (ref.current.cur !== value) {
    ref.current.prev = ref.current.cur;
    ref.current.cur = value;
  }
  return ref.current.prev;
}

export interface Traffic {
  state: State;
  hops: Hop[];
  feed: Hop[];
  lit: Partial<Record<NodeId, number>>;
  first: boolean;
}

export function useSwitchTraffic(state: State): Traffic {
  const prev = usePrevious(state);
  const hops = useMemo(() => hopsBetween(prev, state), [state]); // eslint-disable-line react-hooks/exhaustive-deps
  const [feed, setFeed] = useState<Hop[]>([]);
  const [lit, setLit] = useState<Partial<Record<NodeId, number>>>({});

  // Light each node as packets arrive, and grow the feed in step with the packets.
  useEffect(() => {
    const timers: number[] = [];
    for (const h of hops) {
      timers.push(window.setTimeout(() => setFeed((f) => [h, ...f.filter((x) => x.key !== h.key)].slice(0, 8)), h.delay * 1000));
      timers.push(window.setTimeout(() => setLit((l) => ({ ...l, switch: Date.now() })), (h.delay + TRAVEL / 2) * 1000));
      timers.push(window.setTimeout(() => setLit((l) => ({ ...l, [h.to]: Date.now() })), (h.delay + TRAVEL) * 1000));
    }
    return () => timers.forEach(clearTimeout);
  }, [hops]);
  return { state, hops, feed, lit, first: !prev };
}

export function SwitchGraph({ traffic }: { traffic: Traffic }) {
  const { state, hops, lit, first } = traffic;
  const running = new Set(state.jobs.filter((j) => j.status === "running" || j.status === "queued").map((j) => j.role));
  const crewNames = listJoin(state.crew.map((c) => c.name));
  const release = state.releases.find((r) => r.status === "published");
  const toDiscord = release?.publications.some((p) => p.platform === "discord");
  return (
    <section className="sm-graph" aria-label="Messages through Switch">
      <header className="sm-graph-head">
        <span>Every message goes through Switch</span>
        <small>rooms · agents · coordinator</small>
      </header>
      <svg className="sm-wires" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden>
        {(Object.keys(POS) as NodeId[]).filter((n) => n !== "switch").map((n) => (
          <line key={n} x1={POS[n][0]} y1={POS[n][1]} x2={POS.switch[0]} y2={POS.switch[1]} vectorEffect="non-scaling-stroke"
            data-live={hops.some((h) => h.from === n || h.to === n)} />
        ))}
      </svg>

      <Node id="claude" lit={lit.claude} icon={claudeMark} brand="#d97757" title="Claude Code" sub="role · script-supervisor" busy={running.has("script-supervisor")} />
      <Node id="codex" lit={lit.codex} icon={openaiMark} brand="#ffffff" title="Codex" sub="role · first-ad" busy={running.has("first-ad")} />
      <Node id="mm" lit={lit.mm} icon={mattermostMark} brand="#4a7bd9" title="#production" sub="Mattermost · producer, AD, director" />
      <Node id="discord" lit={lit.discord} icon={discordMark} brand="#7b86f5" title="#day-1" sub={`Discord · ${toDiscord ? crewNames : "crew room"}`} />
      <Node id="coord" lit={lit.coord} title="Take Two coordinator" sub="custom Switch agent · checks in code" glyph />
      <div className="sm-hub" data-lit={!!lit.switch} key={lit.switch ?? 0} style={{ left: `${POS.switch[0]}%`, top: `${POS.switch[1]}%` }}>
        <span className="sm-hub-mark" style={{ maskImage: `url("${switchMark}")`, WebkitMaskImage: `url("${switchMark}")` }} />
        <span className="sm-hub-name">Switch</span>
      </div>

      <AnimatePresence>
        {hops.map((h) => <Packet key={h.key + (first ? ":first" : "")} hop={h} />)}
      </AnimatePresence>
    </section>
  );
}

export function SwitchFeed({ traffic }: { traffic: Traffic }) {
  const { feed, state } = traffic;
  const tz = state.production.timezone;
  return (
    <section className="sm-feed" aria-label="Recent messages through Switch">
      <header>
        <span className="sm-feed-title">Through Switch</span>
        <span className="sm-feed-meta">latest first</span>
      </header>
      <ol>
        <AnimatePresence initial={false}>
          {feed.map((h) => (
            <motion.li key={h.key} layout initial={{ opacity: 0, y: -8, filter: "blur(4px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }} exit={{ opacity: 0 }} transition={{ duration: 0.32, ease: [0.23, 1, 0.32, 1] }} data-tone={h.tone}>
              <span className="sm-route"><Mini id={h.from} /><i>→</i><Mini id={h.to} /></span>
              <span className="sm-label">{h.label}</span>
              <time>{hhmm(h.at, tz)}</time>
            </motion.li>
          ))}
        </AnimatePresence>
      </ol>
    </section>
  );
}

const MINI: Record<NodeId, { icon?: string; color: string; name: string }> = {
  mm: { icon: mattermostMark, color: "#4a7bd9", name: "Mattermost" },
  discord: { icon: discordMark, color: "#7b86f5", name: "Discord" },
  claude: { icon: claudeMark, color: "#d97757", name: "Claude Code" },
  codex: { icon: openaiMark, color: "#e8e8e8", name: "Codex" },
  coord: { color: "#ff7049", name: "Take Two" },
  switch: { icon: switchMark, color: "#eff0e9", name: "Switch" },
};

function Mini({ id }: { id: NodeId }) {
  const m = MINI[id];
  return m.icon ? (
    <span className="sm-mini" title={m.name} style={{ background: m.color, maskImage: `url("${m.icon}")`, WebkitMaskImage: `url("${m.icon}")` }} />
  ) : (
    <span className="sm-mini sm-mini-t2" title={m.name}><i /><i /></span>
  );
}

function Node({ id, icon, brand, title, sub, lit, busy, glyph }: {
  id: NodeId; icon?: string; brand?: string; title: string; sub: string; lit?: number; busy?: boolean; glyph?: boolean;
}) {
  return (
    <div className="sm-node" data-node={id} data-lit={!!lit} style={{ left: `${POS[id][0]}%`, top: `${POS[id][1]}%` }}>
      <motion.span key={lit ?? 0} className="sm-ring" initial={{ opacity: lit ? 0.9 : 0, scale: 0.92 }} animate={{ opacity: 0, scale: 1.12 }} transition={{ duration: 0.9, ease: "easeOut" }} />
      {glyph ? (
        <span className="sm-icon sm-t2"><i /><i /></span>
      ) : (
        <span className="sm-icon" style={{ background: brand, maskImage: `url("${icon}")`, WebkitMaskImage: `url("${icon}")` }} />
      )}
      <span className="sm-text">
        <b>{title}{busy && <span className="sm-busy" />}</b>
        <small>{sub}</small>
      </span>
    </div>
  );
}

function Packet({ hop }: { hop: Hop }) {
  const [a, b, c] = [POS[hop.from], POS.switch, POS[hop.to]];
  return (
    <motion.div
      className="sm-packet"
      data-tone={hop.tone}
      initial={{ left: `${a[0]}%`, top: `${a[1]}%`, opacity: 0 }}
      animate={{ left: [`${a[0]}%`, `${b[0]}%`, `${c[0]}%`], top: [`${a[1]}%`, `${b[1]}%`, `${c[1]}%`], opacity: [0, 1, 1, 0] }}
      transition={{ delay: hop.delay, duration: TRAVEL, ease: "easeInOut", times: [0, 0.5, 1], opacity: { delay: hop.delay, duration: TRAVEL, times: [0, 0.12, 0.85, 1] } }}
      exit={{ opacity: 0 }}
    >
      <span className="sm-dot" />
      <span className="sm-tag">{hop.label}</span>
    </motion.div>
  );
}
