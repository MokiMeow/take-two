// Turns coordinator state into plain sentences and timeline marks.
// Display only: every decision here is already made by the coordinator.
import type { Candidate, CrewMember, Scene, State } from "./types";
import { hhmm, title } from "./format";

export type Tone = "calm" | "hold" | "ask" | "stop" | "done";

export interface Story {
  tone: Tone;
  headline: string;
  detail: string;
}

export const nameOf = (crew: CrewMember[], id: string) => crew.find((c) => c.id === id)?.name ?? title(id);

// A person as the crew would say it. Accepts a crew id, "Director (Arun)", or a raw Switch/Matrix
// id such as "@switch-mattermost-<uuid>-w4-director:localhost" (-> "Director").
export function who(crew: CrewMember[], raw: string | undefined): string {
  if (!raw) return "Someone";
  const named = crew.find((c) => c.id === raw);
  if (named) return named.name;
  const paren = /\((.*?)\)/.exec(raw)?.[1];
  if (paren) return paren;
  if (raw.startsWith("@")) {
    if (/^@switch-agent-/.test(raw)) return "Take Two";
    const tail = raw.slice(1).split(":")[0].split("-").pop() ?? raw;
    return nameOf(crew, tail);
  }
  return nameOf(crew, raw);
}
const personOf = (authority: string) => who([], authority);

// Replace raw Switch ids inside coordinator text with names.
export function humanize(crew: CrewMember[], text: string): string {
  return text.replace(/@switch-[A-Za-z0-9-]+:[A-Za-z0-9.-]+/g, (m) => who(crew, m));
}

// A hard stop may arrive as "18:00" (production local time) or as a full timestamp.
export function asInstant(s: State, value: string): string | null {
  if (/^\d{4}-\d{2}-\d{2}T/.test(value)) return value;
  const hm = /^(\d{1,2}):(\d{2})$/.exec(value.trim());
  const ref = s.scenes.find((x) => x.plan)?.plan?.start ?? s.production.now;
  if (!hm || !ref) return null;
  const off = /([+-]\d\d:\d\d|Z)$/.exec(ref)?.[1] ?? "Z";
  return `${ref.slice(0, 10)}T${hm[1].padStart(2, "0")}:${hm[2]}:00${off}`;
}

export function roleLabel(role: string): string {
  const map: Record<string, string> = { actor: "Actor", camera_sound: "Camera / sound", camera: "Camera", sound: "Sound", director: "Director" };
  if (map[role]) return map[role];
  return role.includes("/") ? role : title(role);
}

export function listJoin(xs: string[]): string {
  if (xs.length <= 1) return xs.join("");
  return `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}`;
}

export function currentRelease(s: State) {
  return s.releases.find((r) => r.status === "published") ?? s.releases[0];
}

export function pendingCrew(s: State): CrewMember[] {
  const r = currentRelease(s);
  if (!r) return [];
  const done = new Set(r.acks.confirmed.map((c) => c.person));
  return s.crew.filter((c) => r.acks.expected.includes(c.id) && !done.has(c.id));
}

export function story(s: State): Story {
  const tz = s.production.timezone;
  const held = s.scenes.filter((x) => x.validity === "held");
  const d = s.decision;
  const r = currentRelease(s);

  if (d?.status === "open") {
    const pass = d.candidates.filter((c) => c.check.result === "pass").length;
    const out = d.candidates.length - pass;
    const nums = [...new Set(d.candidates.flatMap(rowsOf).map((m) => s.scenes.find((x) => x.id === m.scene_id)?.number))]
      .filter((n): n is number => n != null)
      .sort((a, b) => a - b);
    return {
      tone: "ask",
      headline: `${d.authority_name ?? personOf(d.authority)} needs to pick a new plan for Scene${nums.length > 1 ? "s" : ""} ${listJoin(nums.map(String))}.`,
      detail: `${whyNow(s)}${pass} option${pass === 1 ? "" : "s"} passed every check${out ? `, ${out} ruled out` : ""}. Answer by ${hhmm(d.expires_at, tz)}.`,
    };
  }
  if (d?.status === "closed_outdated") {
    const latest = s.changes.find((c) => c.status === "recorded");
    const fact = latest ? changeSentence(s, latest) : "The facts changed.";
    return {
      tone: "stop",
      headline: "Plans changed again. Options are being re-checked.",
      detail: `${fact} The earlier options were made before that, so nobody can pick them.`,
    };
  }
  if (held.length) {
    const nums = held.map((x) => String(x.number));
    return {
      tone: "hold",
      headline: `Scene${held.length > 1 ? "s" : ""} ${listJoin(nums)} ${held.length > 1 ? "are" : "is"} on hold.`,
      detail: held[0].hold_reason ?? "Waiting for a new plan.",
    };
  }
  if (r) {
    const waiting = pendingCrew(s);
    if (waiting.length) {
      return {
        tone: "calm",
        headline: `Release ${r.number} is out. Waiting for ${listJoin(waiting.map((c) => c.name))}.`,
        detail: r.summary,
      };
    }
    return { tone: "done", headline: `Everyone is on release ${r.number}.`, detail: r.summary };
  }
  return { tone: "calm", headline: "No plan released yet.", detail: "The first release goes out once the day is scheduled." };
}

// The newest recorded change, as a sentence with a trailing space, or nothing.
function whyNow(s: State): string {
  const c = s.changes.find((x) => x.status === "recorded");
  return c ? `${changeSentence(s, c)} ` : "";
}

export function changeSentence(s: State, c: State["changes"][number]): string {
  const tz = s.production.timezone;
  if (c.entity === "person" && /stop|leave/.test(c.field)) return `${nameOf(s.crew, c.target)} must leave at ${hhmm(asInstant(s, c.value) ?? c.value, tz)}.`;
  const t = (v: string) => hhmm(asInstant(s, v) ?? v, tz);
  const who = nameOf(s.crew, c.target);
  if (c.entity === "person" && c.field === "late_by") return `${who} is ${c.value} minutes late.`;
  if (c.entity === "person" && c.field === "available") return `${who} is available from ${t(c.value.split(/[-/]/)[0])}.`;
  if (c.entity === "location" && c.field === "permission") return `${title(c.target)} permission ${c.value}.`;
  if (c.entity === "location" && c.field === "light_until") return `Usable light at the ${c.target} ends at ${t(c.value)}.`;
  if (c.entity === "location" && c.field === "window") return `The ${c.target} is only available ${c.value}.`;
  if (c.entity === "capability") return `${title(c.target).replace(/^Sound Recorder$/, "The sound recorder")} is ${c.value}.`;
  if (c.entity === "scene" && c.field === "overrun") {
    const n = s.scenes.find((x) => x.id === c.target)?.number ?? c.target;
    return `Scene ${n} ran ${c.value} minutes over.`;
  }
  return `${title(c.target)} ${c.field.replace(/_/g, " ")}: ${c.value}.`;
}

// The six beats of one change, for the progress line.
export const BEATS = ["Change reported", "Scene held", "Agents find options", "Director picks", "Release sent", "Crew confirms"] as const;

export function beat(s: State): { at: number; redo: boolean } | null {
  if (!s.changes.length) return null;
  const d = s.decision;
  // `at` is the beat in progress (1-based); 7 means every beat is done.
  if (d?.status === "answered") return { at: pendingCrew(s).length ? 6 : 7, redo: false };
  if (d?.status === "open") return { at: 4, redo: false };
  if (d?.status === "closed_outdated") return { at: 3, redo: true };
  return { at: 3, redo: false };
}

// Times that limit the day, drawn as vertical lines on the plan.
export interface Mark {
  at: string;
  label: string;
  who?: string;
  tone: "stop" | "info";
}

export function marks(s: State): Mark[] {
  const out: Mark[] = [];
  for (const c of s.changes) {
    if (c.entity === "person" && /stop|leave/.test(c.field) && c.status === "recorded") {
      const at = asInstant(s, c.value);
      if (at) out.push({ at, label: `${nameOf(s.crew, c.target)} leaves`, who: c.target, tone: "stop" });
    }
  }
  return out;
}

// A block that runs past a person's hard stop while that person is in it.
export function clash(m: Mark[], people: string[], end: string): Mark | undefined {
  return m.find((k) => k.who && people.includes(k.who) && new Date(end) > new Date(k.at));
}

// Every scene an option re-plans: its schedule when it has one, otherwise its single manifest.
export function rowsOf(c: Candidate) {
  return c.schedule && c.schedule.length ? c.schedule : [c.manifest];
}

export function sceneOf(s: State, c: Candidate): Scene | undefined {
  return s.scenes.find((x) => x.id === c.manifest.scene_id);
}

// Hours shown on the plan: one hour before the first block to one after the last.
export function dayWindow(s: State, extra: { start: string; end: string }[] = []): { from: number; to: number } {
  const times: number[] = [];
  for (const x of extra) times.push(+new Date(x.start), +new Date(x.end));
  for (const sc of s.scenes) if (sc.plan) times.push(+new Date(sc.plan.start), +new Date(sc.plan.end));
  for (const c of s.decision?.candidates ?? []) for (const m of rowsOf(c)) times.push(+new Date(m.start), +new Date(m.end));
  for (const m of marks(s)) times.push(+new Date(m.at));
  // "Now" widens the board only on the shoot day itself.
  const now = +new Date(s.production.now);
  if (times.length && now > Math.min(...times) - 3 * 3600_000 && now < Math.max(...times) + 3600_000) times.push(now);
  if (!times.length) times.push(now);
  // Round to whole hours in the production's own timezone (offset taken from "now").
  const H = 3600_000;
  const tzm = /([+-])(\d\d):(\d\d)$/.exec(s.production.now);
  const off = tzm ? (tzm[1] === "-" ? -1 : 1) * (+tzm[2] * 60 + +tzm[3]) * 60_000 : 0;
  // Leave a little room before the first scene, but never a whole empty hour for "now".
  const firstPlan = Math.min(...times.filter((t) => t !== now));
  const lo = Math.min(Math.min(...times), firstPlan - 20 * 60_000) + off;
  const hi = Math.max(...times) + off;
  return { from: Math.floor(lo / H) * H - off, to: Math.ceil(hi / H) * H - off };
}
