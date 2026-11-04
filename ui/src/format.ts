// Display helpers. Times are shown in the production's timezone, never the viewer's.

const timeFmt = new Map<string, Intl.DateTimeFormat>();

export function hhmm(iso: string | undefined, tz = "Asia/Kolkata"): string {
  if (!iso) return "--:--";
  let f = timeFmt.get(tz);
  if (!f) {
    f = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: tz });
    timeFmt.set(tz, f);
  }
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "--:--" : f.format(d);
}

export function span(start: string, end: string, tz?: string): string {
  return `${hhmm(start, tz)}–${hhmm(end, tz)}`;
}

export function minutesBetween(a: string, b: string): number {
  return Math.round((new Date(b).getTime() - new Date(a).getTime()) / 60000);
}

export function title(s: string): string {
  return s.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function shortHash(h: string): string {
  return h.replace(/^sha256:/, "").slice(0, 7);
}

// Industry script-revision paper order. Release n is printed on colour n.
export const REVISION_PAPER = [
  { name: "White", bg: "#F7F5EE" },
  { name: "Blue", bg: "#CFE3F3" },
  { name: "Pink", bg: "#F6CFD8" },
  { name: "Yellow", bg: "#F5EAA8" },
  { name: "Green", bg: "#D3E9C9" },
  { name: "Goldenrod", bg: "#E8C46A" },
  { name: "Buff", bg: "#EBDDB8" },
  { name: "Salmon", bg: "#F3BBA4" },
  { name: "Cherry", bg: "#E58A8F" },
] as const;

export function paperFor(releaseNumber: number) {
  return REVISION_PAPER[(Math.max(1, releaseNumber) - 1) % REVISION_PAPER.length];
}

// Stripboard colours. INT/EXT is inferred from the location until the contract carries a scene heading.
const INTERIORS = new Set(["stairwell", "studio", "apartment", "office", "cafe", "hall", "corridor"]);

export function stripFor(location: string | undefined, start: string | undefined, sunset = "18:00") {
  if (!location) return { heading: "SET TO BE SCHEDULED", bg: "#E6E2D6", planned: false };
  const ext = location ? !INTERIORS.has(location.toLowerCase()) : false;
  const night = start ? hhmm(start) >= sunset : false;
  const heading = `${ext ? "EXT" : "INT"}. ${(location ?? "TBD").toUpperCase()} – ${night ? "NIGHT" : "DAY"}`;
  const bg = ext ? (night ? "#A8D5A2" : "#F2E27A") : night ? "#9DC3E6" : "#F4F1E8";
  return { heading, bg, planned: true };
}

// "2026-11-06" or "Day 1 - 6 November" → a short human label.
export function dayLabel(day: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(day);
  if (!m) return day.replace(" - ", " · ");
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "long", timeZone: "UTC" });
}

export function initials(name: string): string {
  return name.split(/\s+/).map((p) => p[0]).join("").slice(0, 2).toUpperCase();
}
