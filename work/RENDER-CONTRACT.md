# Render contract (final, from Claude, for W4)

The source of truth is `render/src/schema.ts`. A summary of the rules that matter for `coordinator/render_props.py`:

- **Strict:** unknown keys are rejected and every key is required. "No value" is `null`, never an omitted key. The CLI validates **before** rendering and exits 1 with `render-error: invalid <kind> props at <path>: <message>`.
- **Hash:** `manifest_hash` must match `^sha256:[0-9a-f]{7,64}$`. Pass the candidate's (or the release's) real manifest hash; the renderer only displays it.
- **Timestamps:** ISO with an offset (`2026-11-06T16:30:00+05:30`).
- **Limits** (`LIMITS` in `schema.ts`): shots 6, people 8, scenes 20, crew 30, locations 8, changes 6, manifest file 256 KiB. Strings: label 80, scene_title 80, location 40, names 40, roles 60, summary 400, change lines 160, hold_reason 200, confirm_hint 120.

## Preview props
```json
{"letter":"A","label":"Stairwell, reduced coverage","scene_number":3,"scene_title":"The confession",
 "location":"stairwell","start":"2026-11-06T16:30:00+05:30","end":"2026-11-06T17:15:00+05:30",
 "shots":["two-shot","close-up"],"people":[{"id":"maya","name":"Maya"},{"id":"dev","name":"Dev"}],
 "sunset":null,"crowd":null,"manifest_hash":"sha256:..."}
```
- `letter` is a single capital letter: A, B, C… in the order of the passing candidates on the card.
- `people` lists only on-screen cast; the renderer draws the first two. Leave out crew such as Leela (camera).

## Call sheet props
```json
{"production":{"title":"The Last Light","day":"Day 1","date":"Friday 6 November 2026","timezone":"Asia/Kolkata"},
 "release":{"number":2,"release_id":"r2","manifest_hash":"sha256:...","summary":"...","changes":["..."],"created_at":"..."},
 "general_call":"2026-11-06T14:45:00+05:30","sunset":null,
 "scenes":[
   {"status":"scheduled","number":1,"title":"The missed call","location":"stairwell","start":"...","end":"...","cast":["2"],"changed":false},
   {"status":"held","number":3,"title":"The confession","hold_reason":"Rooftop permission refused. Do not go to the rooftop.","changed":true}],
 "crew":[{"name":"Maya","role":"Actor (1)","call_time":"...","changed":true}],
 "locations":[{"name":"Stairwell","note":null}],
 "confirm_hint":"Reply “confirm r2” in #crew."}
```
- **Cast numbers:** the 1-based index among crew whose role is an actor, as strings.
- `changed`: whether this scene's or person's plan differs from the previous published release.
- `general_call`: the earliest call time in the release.
- `sunset`: only if the fixtures carry a verified value; otherwise `null`.

## CLI behaviour
- `node render/cli.mjs --kind preview|callsheet --manifest <abs json> --out <abs path>`
- Exit 0 prints `rendered <kind> <path>`. Exit 1 prints one `render-error: ...` line on stderr.
- Typical time on a loaded machine: preview 30–40 s, call sheet about 10 s, plus a one-time bundle of about 80 s after `render/src` changes. **Use a timeout of at least 150 s**, and run warm-up renders at coordinator start (`scripts/` can trigger one sample render) so the first demo render isn't the cold one.
- The CLI closes its own headless browser; Windows may take up to about 2 minutes to reap it. Don't run more than 2 renders at once.
