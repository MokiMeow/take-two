import { useEffect } from "react";
import { useProductionState } from "./data";
import { Stripboard } from "./components/Stripboard";
import { Pipeline } from "./components/Pipeline";
import { DecisionPanel, Headline } from "./components/Decision";
import { CrewConfirmations, ReleaseStack } from "./components/Releases";
import { ReportChange, Timeline, TopBar } from "./components/Chrome";
import "./App.css";

export default function App() {
  const { state, source, setFixture } = useProductionState();

  // In fixture replay, keys 1–6 step through the demo moments.
  useEffect(() => {
    if (source.kind !== "fixture") return;
    const onKey = (e: KeyboardEvent) => {
      const n = Number(e.key);
      if (n >= 1 && n <= 9 && !(e.target instanceof HTMLInputElement)) setFixture(n - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [source.kind, setFixture]);

  if (!state) {
    return (
      <div className="boot grain">
        <span className="mono faint">Connecting to the coordinator…</span>
      </div>
    );
  }

  const tz = state.production.timezone;
  return (
    <div className="app grain">
      <TopBar state={state} source={source} setFixture={setFixture} />
      <main className="board">
        <aside className="col col-left">
          <Stripboard scenes={state.scenes} crew={state.crew} day={state.production.day} tz={tz} />
          <Timeline items={state.timeline} tz={tz} />
        </aside>

        <section className="col col-center" aria-label="Change desk">
          <div className="desk-head">
            <Headline state={state} />
            <ReportChange disabled={source.kind !== "live"} />
          </div>
          <div className="desk-pipeline">
            <Pipeline state={state} />
          </div>
          {state.decision && (
            <DecisionPanel decision={state.decision} crew={state.crew} current={state.revisions.constraints} tz={tz} />
          )}
        </section>

        <aside className="col col-right">
          <ReleaseStack releases={state.releases} scenes={state.scenes} tz={tz} />
          <CrewConfirmations crew={state.crew} release={state.releases[0]} tz={tz} />
        </aside>
      </main>
    </div>
  );
}
