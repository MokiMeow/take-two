import { useEffect, useRef, useState } from "react";
import { MotionConfig } from "motion/react";
import { fixtures, useProductionState } from "./data";
import type { ScenePlan, State } from "./types";
import { Schedule } from "./components/Schedule";
import { CrewCard, DecisionCard, PendingCard, ReleaseCard } from "./components/Side";
import { History, Lead, ReportDialog, SheetDialog, TopBar } from "./components/Shell";
import "./App.css";

// Where each scene was in the previous state, for the dashed "was here" outline.
function useGhosts(state: State | null): Record<string, ScenePlan> {
  const prev = useRef<State | null>(null);
  const [ghosts, setGhosts] = useState<Record<string, ScenePlan>>({});
  useEffect(() => {
    if (!state) return;
    const before = prev.current;
    const next: Record<string, ScenePlan> = {};
    for (const s of state.scenes) {
      const old = before?.scenes.find((x) => x.id === s.id)?.plan;
      if (old && s.plan && (old.location !== s.plan.location || old.start !== s.plan.start)) next[s.id] = old;
    }
    if (before) setGhosts(next);
    prev.current = state;
  }, [state]);
  return ghosts;
}

export default function App() {
  const { state, source, setFixture } = useProductionState();
  const ghosts = useGhosts(state);
  const [focus, setFocus] = useState<string | null>(null);
  const [history, setHistory] = useState(false);
  const [report, setReport] = useState(false);
  const [sheet, setSheet] = useState<string | null>(null);

  // In demo replay, keys 1–6 step through the story.
  useEffect(() => {
    if (source.kind !== "fixture") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;
      const n = Number(e.key);
      if (n >= 1 && n <= 9 && fixtures.length <= 9) setFixture(n - 1);
      if (e.key === "ArrowRight") setFixture(Math.min(fixtures.length - 1, (source.kind === "fixture" ? source.index : 0) + 1));
      if (e.key === "ArrowLeft") setFixture(Math.max(0, (source.kind === "fixture" ? source.index : 0) - 1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [source, setFixture]);

  if (!state) {
    return <div className="boot"><span className="boot-dot" /> Connecting to the coordinator</div>;
  }

  return (
    <MotionConfig reducedMotion="user">
      <div className="app">
        <TopBar state={state} source={source} setFixture={setFixture} onHistory={() => setHistory(true)} onReport={() => setReport(true)} />
        <Lead state={state} />
        <main className="layout">
          <div className="main-col">
            <Schedule state={state} ghosts={ghosts} focus={focus} onFocus={setFocus} />
            <CrewCard state={state} />
          </div>
          <aside className="side">
            <PendingCard state={state} />
            <DecisionCard state={state} focus={focus} onFocus={setFocus} />
            {!(state.decision && ["open", "closed_outdated"].includes(state.decision.status)) && <ReleaseCard state={state} onSheet={setSheet} />}
          </aside>
        </main>
      </div>
      <History state={state} open={history} onClose={() => setHistory(false)} />
      <ReportDialog open={report} onClose={() => setReport(false)} />
      <SheetDialog url={sheet} onClose={() => setSheet(null)} />
    </MotionConfig>
  );
}
