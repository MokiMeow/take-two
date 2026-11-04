import { useEffect, useRef, useState } from "react";
import type { ChangeCommand, State } from "./types";

// Fixture snapshots, one per demo moment. Used only when the coordinator is not reachable,
// and always labelled "Fixture replay" in the UI so it can't be mistaken for live data.
// `?fixtures` replays the rooftop story; `?fixtures=day` replays the recorded multi-problem shoot day.
const storyModules = import.meta.glob<State>("../../fixtures/ui-state/*.json", { eager: true, import: "default" });
const dayModules = import.meta.glob<State>("../../fixtures/ui-state/day/*.json", { eager: true, import: "default" });

const toList = (mods: Record<string, State>) =>
  Object.entries(mods)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([path, state]) => ({
      name: path.split("/").pop()!.replace(/\.json$/, "").replace(/^\d+-/, "").replace(/-/g, " "),
      state,
    }));

const wantDay = new URLSearchParams(location.search).get("fixtures") === "day";
export const fixtures: { name: string; state: State }[] = toList(wantDay && Object.keys(dayModules).length ? dayModules : storyModules);

export type Source =
  | { kind: "connecting" }
  | { kind: "live" }
  | { kind: "reconnecting" }
  | { kind: "fixture"; index: number };

const API = import.meta.env.VITE_API_BASE ?? "";
const RETRY_MS = [1000, 2000, 4000, 8000];

export function useProductionState(): {
  state: State | null;
  source: Source;
  setFixture: (index: number) => void;
} {
  const [state, setState] = useState<State | null>(null);
  const [source, setSource] = useState<Source>({ kind: "connecting" });
  const fixtureMode = useRef(new URLSearchParams(location.search).has("fixtures"));

  useEffect(() => {
    if (fixtureMode.current) {
      setSource({ kind: "fixture", index: 0 });
      setState(fixtures[0]?.state ?? null);
      return;
    }
    let es: EventSource | null = null;
    let attempt = 0;
    let timer: number | undefined;
    let closed = false;

    const open = () => {
      es = new EventSource(`${API}/api/events`);
      es.addEventListener("state", (e) => {
        attempt = 0;
        try {
          setState(JSON.parse((e as MessageEvent).data) as State);
          setSource({ kind: "live" });
        } catch {
          // A malformed frame is skipped; the next commit sends a full snapshot again.
        }
      });
      es.onerror = () => {
        es?.close();
        if (closed) return;
        setSource((s) => (s.kind === "live" ? { kind: "reconnecting" } : s));
        const wait = RETRY_MS[Math.min(attempt++, RETRY_MS.length - 1)];
        // After the first failed attempts with no data at all, fall back to fixtures.
        if (attempt === 3) {
          setState((cur) => {
            if (cur) return cur;
            setSource({ kind: "fixture", index: 0 });
            return fixtures[0]?.state ?? null;
          });
        }
        timer = window.setTimeout(open, wait);
      };
    };

    // Seed with a snapshot so the first paint doesn't wait for a commit.
    fetch(`${API}/api/state`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((s: State) => {
        setState(s);
        setSource({ kind: "live" });
      })
      .catch(() => {})
      .finally(open);

    return () => {
      closed = true;
      es?.close();
      window.clearTimeout(timer);
    };
  }, []);

  const setFixture = (index: number) => {
    const f = fixtures[index];
    if (!f) return;
    setSource({ kind: "fixture", index });
    setState(f.state);
  };

  return { state, source, setFixture };
}

export async function postChange(cmd: ChangeCommand): Promise<{ status: string; reason?: string }> {
  const r = await fetch(`${API}/api/changes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cmd),
  });
  if (!r.ok) return { status: "rejected", reason: `Coordinator returned ${r.status}` };
  return r.json();
}

export function mediaUrl(path: string | undefined): string | undefined {
  if (!path) return undefined;
  return path.startsWith("http") ? path : `${API}${path}`;
}
