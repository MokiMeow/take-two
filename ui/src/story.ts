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
// "Director (Arun)" -> "Arun"
const personOf = (authority: string) => /\((.*?)\)/.exec(authority)?.[1] ?? authority;

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
    const scene = s.scenes.find((x) => x.id === d.candidates[0]?.manifest.scene_id);
    return {
      tone: "ask",
      headline: `${personOf(d.authority)} needs to pick a new plan for Scene ${scene?.number ?? ""}.`.replace(" .", "."),
      detail: `${pass} option${pass === 1 ? "" : "s"} passed every check${out ? `, ${out} ruled out` : ""}. Answer by ${hhmm(d.expires_at, tz)}.`,
    };
  }
  if (d?.status === "closed_outdated") {
    const latest = s.changes[0];
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

export function changeSentence(s: State, c: State["changes"][number]): string {
  const tz = s.production.timezone;
  if (c.entity === "person" && /stop|leave/.test(c.field)) return `${nameOf(s.crew, c.target)} must leave at ${hhmm(c.value, tz)}.`;
  if (c.entity === "location" && c.field === "permission") return `${title(c.target)} permission ${c.value}.`;
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
    if (c.entity === "person" && /stop|leave/.test(c.field) && c.status !== "rejected") {
      out.push({ at: c.value, label: `${nameOf(s.crew, c.target)} leaves`, who: c.target, tone: "stop" });
    }
  }
  return out;
}

// A block that runs past a person's hard stop while that person is in it.
export function clash(m: Mark[], people: string[], end: string): Mark | undefined {
  return m.find((k) => k.who && people.includes(k.who) && new Date(end) > new Date(k.at));
}

export function sceneOf(s: State, c: Candidate): Scene | undefined {
  return s.scenes.find((x) => x.id === c.manifest.scene_id);
}

// Hours shown on the plan: one hour before the first block to one after the last.
export function dayWindow(s: State): { from: number; to: number } {
  const times: number[] = [];
  for (const sc of s.scenes) if (sc.plan) times.push(+new Date(sc.plan.start), +new Date(sc.plan.end));
  for (const c of s.decision?.candidates ?? []) times.push(+new Date(c.manifest.start), +new Date(c.manifest.end));
  for (const m of marks(s)) times.push(+new Date(m.at));
  times.push(+new Date(s.production.now));
  // Round to whole hours in the production's own timezone (offset taken from "now").
  const H = 3600_000;
  const tzm = /([+-])(\d\d):(\d\d)$/.exec(s.production.now);
  const off = tzm ? (tzm[1] === "-" ? -1 : 1) * (+tzm[2] * 60 + +tzm[3]) * 60_000 : 0;
  const lo = Math.min(...times) + off;
  const hi = Math.max(...times) + off;
  return { from: Math.floor(lo / H) * H - off, to: Math.ceil(hi / H) * H - off };
}
