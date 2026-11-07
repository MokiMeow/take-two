import { useEffect, useMemo, useRef, useState } from "react";
import { MotionConfig } from "motion/react";
import { DEMO, fixtures, useProductionState, type Source } from "./data";
import { DemoBar, DemoIntro, useAutoplay } from "./components/Demo";
import type { ScenePlan, State } from "./types";
import { Schedule } from "./components/Schedule";
import { SwitchFeed, SwitchGraph, useSwitchTraffic } from "./components/SwitchMap";
import { dayWindow } from "./story";
import { CrewCard, DecisionCard, PendingCard, ReleaseCard } from "./components/Side";
import { History, Lead, ReportDialog, SheetDialog, TopBar } from "./components/Shell";
import "./App.css";

// One hour window for the whole day. A replay knows every moment up front; live, it only grows.
function useDayWindow(state: State | null, replay: boolean) {
  const all = useMemo(() => {
    if (!replay || !fixtures.length) return null;
    const ws = fixtures.map((f) => dayWindow(f.state));
    return { from: Math.min(...ws.map((w) => w.from)), to: Math.max(...ws.map((w) => w.to)) };
  }, [replay]);
  const grown = useRef<{ from: number; to: number } | null>(null);
  if (all) return all;
  if (state) {
    const w = dayWindow(state);
    const g = grown.current;
    grown.current = g ? { from: Math.min(g.from, w.from), to: Math.max(g.to, w.to) } : w;
  }
  return grown.current ?? undefined;
}

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
  const win = useDayWindow(state, source.kind === "fixture");
  const film = new URLSearchParams(location.search).has("film");
  const [focus, setFocus] = useState<string | null>(null);
  const [history, setHistory] = useState(false);
  const [report, setReport] = useState(false);
  const [sheet, setSheet] = useState<string | null>(null);
  const [intro, setIntro] = useState(DEMO);
  const [playing, setPlaying] = useState(false);
  const index = source.kind === "fixture" ? source.index : 0;
  useAutoplay(index, DEMO && playing, setPlaying, setFixture);

  // In demo replay, keys 1–6 step through the story.
  useEffect(() => {
    if (source.kind !== "fixture") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") setPlaying(false);
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
  const demo = DEMO ? {
    bar: <DemoBar index={index} playing={playing} onToggle={() => {
      if (!playing && index >= fixtures.length - 1) setFixture(0);
      setPlaying(!playing);
    }} />,
    intro: <DemoIntro open={intro} onRun={() => { setIntro(false); setFixture(0); setPlaying(true); }} onClose={() => setIntro(false)} />,
  } : null;
  return <Room demo={demo} state={state} source={source} setFixture={setFixture} ghosts={ghosts} win={win} film={film}
    focus={focus} setFocus={setFocus} history={history} setHistory={setHistory} report={report} setReport={setReport} sheet={sheet} setSheet={setSheet} />;
}

function Room({ demo, state, source, setFixture, ghosts, win, film, focus, setFocus, history, setHistory, report, setReport, sheet, setSheet }: {
  demo: { bar: React.ReactNode; intro: React.ReactNode } | null;
  state: State; source: Source; setFixture: (i: number) => void; ghosts: Record<string, ScenePlan>;
  win: { from: number; to: number } | undefined; film: boolean; focus: string | null; setFocus: (f: string | null) => void;
  history: boolean; setHistory: (b: boolean) => void; report: boolean; setReport: (b: boolean) => void;
  sheet: string | null; setSheet: (s: string | null) => void;
}) {
  const traffic = useSwitchTraffic(state);
  return (
    <MotionConfig reducedMotion="user">
      {demo?.bar}
      <div className="app" data-film={film || undefined}>
        <TopBar state={state} source={source} setFixture={setFixture} onHistory={() => setHistory(true)} onReport={() => setReport(true)} />
        <Lead state={state} />
        <main className="layout">
          <div className="main-col">
            <Schedule state={state} ghosts={ghosts} focus={focus} onFocus={setFocus} window={win ?? undefined} />
            <CrewCard state={state} />
            <SwitchGraph traffic={traffic} />
          </div>
          <aside className="side">
            <PendingCard state={state} />
            <DecisionCard state={state} focus={focus} onFocus={setFocus} />
            {!(state.decision && ["open", "closed_outdated"].includes(state.decision.status)) && <ReleaseCard state={state} onSheet={setSheet} />}
            <SwitchFeed traffic={traffic} />
          </aside>
        </main>
      </div>
      <History state={state} open={history} onClose={() => setHistory(false)} />
      <ReportDialog open={report} onClose={() => setReport(false)} />
      <SheetDialog url={sheet} onClose={() => setSheet(null)} />
      {demo?.intro}
    </MotionConfig>
  );
}
