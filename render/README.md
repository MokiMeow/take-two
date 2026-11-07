# Renderer

Remotion 4.0.539. Two outputs, both built from data (never generated code):

| Kind | Size | Output | Input schema |
|---|---|---|---|
| `preview` | 960×540, 15 fps, 5 s (the option's isometric set model, shared with the Control Room) | MP4 (h264) | `previewSchema` in `src/schema.ts` (strict) |
| `callsheet` | 1200×1360 PNG, printed on the release's script-revision colour | PNG | `callSheetSchema` in `src/schema.ts` |

```
node render/cli.mjs --kind preview   --manifest <abs path>.json --out <abs path>.mp4
node render/cli.mjs --kind callsheet --manifest <abs path>.json --out <abs path>.png
```
- Exit 0: prints `rendered <kind> <path>`. Exit 1: prints one line `render-error: <reason>` to stderr.
- Props are validated by the zod schema; bad input fails the render with the schema error.
- The first run bundles `src/` into `.bundle/` (about 1 minute; reused until `src/` changes). Typical render: preview 10–25 s, call sheet about 5 s.
- Locations with their own set model: `stairwell`, `park`, `rooftop`, `courtyard` (from `ui/src/sets/maquette.ts`). The `sunset` and `crowd` fields are still accepted by the schema but the set model does not draw them.
- Shot types: `wide`, `two-shot`, `medium`, `close-up`, `over-shoulder`, `insert`.
- Examples: `samples/*.json`. Studio for design work: `npm run studio`.
