# Control Room

The Take Two dashboard: React 19, TypeScript and Vite. It only displays what the coordinator owns; every decision, check and release happens in the coordinator and arrives here as `/api/state` (shape in [`docs/UI-CONTRACT.md`](../docs/UI-CONTRACT.md)).

```bash
npm ci
npm run dev        # http://localhost:5173/?fixtures=day replays the recorded day
npm run lint
npm run build      # served by scripts/serve_demo.py from ui/dist
```

Without `?fixtures=day` the page reads the live coordinator API through the Vite proxy (`vite.config.ts`).

## Where things are

| Path | What it draws |
|---|---|
| `src/App.tsx` | The page: headline, the six beats of a change, counters, replay control |
| `src/components/Schedule.tsx` | The day schedule: scenes on a time axis, held strips, hard stops and the candidate plan |
| `src/components/Side.tsx` | The decision panel, set-model stage, release card and crew tiles |
| `src/components/SwitchMap.tsx` | The Switch hub map and the "Through Switch" feed, replayed from the coordinator's timeline |
| `src/sets/maquette.ts` | Isometric set models (stairwell, courtyard, park, rooftop) on the Anatomy kit; also used by the renderer |
| `src/story.ts` | Plain-language sentences for changes, holds and beats |

Design rules and tokens: [`DESIGN.md`](DESIGN.md).
