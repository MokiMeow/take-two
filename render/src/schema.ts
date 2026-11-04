import { z } from "zod";

// Render inputs. cli.mjs validates every input with these schemas in strict mode BEFORE rendering,
// because Remotion merges defaultProps into input props and would otherwise hide missing fields.
// Every field is required; "no value" is an explicit null, never an omitted key.

const id = z.string().min(1).max(64);
const text = (max: number) => z.string().min(1).max(max);
const iso = z.string().regex(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?([+-]\d{2}:\d{2}|Z)$/, "ISO timestamp with offset");
const hash = z.string().regex(/^sha256:[0-9a-f]{7,64}$/);

export const LIMITS = { shots: 6, people: 8, scenes: 20, crew: 30, locations: 8, changes: 6, manifestBytes: 262144 } as const;

export const previewSchema = z
  .object({
    letter: z.string().regex(/^[A-Z]$/),
    label: text(80),
    scene_number: z.number().int().min(0).max(999),
    scene_title: text(80),
    location: text(40),
    start: iso,
    end: iso,
    shots: z.array(text(30)).min(1).max(LIMITS.shots),
    people: z.array(z.object({ id, name: text(40) }).strict()).max(LIMITS.people),
    sunset: z.boolean().nullable(), // null = decide from the location
    crowd: z.boolean().nullable(), // null = decide from the location
    manifest_hash: hash,
  })
  .strict();
export type PreviewProps = z.infer<typeof previewSchema>;

const sceneRow = z.discriminatedUnion("status", [
  z
    .object({
      status: z.literal("scheduled"),
      number: z.number().int().min(0).max(999),
      title: text(80),
      location: text(40),
      start: iso,
      end: iso,
      cast: z.array(text(8)).max(LIMITS.people),
      changed: z.boolean(),
    })
    .strict(),
  z
    .object({
      status: z.literal("held"),
      number: z.number().int().min(0).max(999),
      title: text(80),
      hold_reason: text(200),
      changed: z.boolean(),
    })
    .strict(),
]);
export type SceneRow = z.infer<typeof sceneRow>;

export const callSheetSchema = z
  .object({
    production: z.object({ title: text(80), day: text(40), date: text(60), timezone: text(40) }).strict(),
    release: z
      .object({
        number: z.number().int().min(1).max(999),
        release_id: id,
        manifest_hash: hash,
        summary: text(400),
        changes: z.array(text(160)).max(LIMITS.changes),
        created_at: iso,
      })
      .strict(),
    general_call: iso,
    sunset: iso.nullable(),
    scenes: z.array(sceneRow).min(1).max(LIMITS.scenes),
    crew: z.array(z.object({ name: text(40), role: text(60), call_time: iso.nullable(), changed: z.boolean() }).strict()).max(LIMITS.crew),
    locations: z.array(z.object({ name: text(40), note: z.string().max(160).nullable() }).strict()).max(LIMITS.locations),
    confirm_hint: text(120),
  })
  .strict();
export type CallSheetProps = z.infer<typeof callSheetSchema>;

// Studio-only sample data. The CLI never relies on these.
export const previewDefaults: PreviewProps = {
  letter: "A",
  label: "Stairwell, reduced coverage",
  scene_number: 3,
  scene_title: "The confession",
  location: "stairwell",
  start: "2026-11-06T16:30:00+05:30",
  end: "2026-11-06T17:15:00+05:30",
  shots: ["two-shot", "close-up"],
  people: [{ id: "maya", name: "Maya" }, { id: "dev", name: "Dev" }],
  sunset: null,
  crowd: null,
  manifest_hash: "sha256:eaaed26f",
};

export const callSheetDefaults: CallSheetProps = {
  production: { title: "The Last Light", day: "Day 1", date: "Friday 6 November 2026", timezone: "Asia/Kolkata" },
  release: {
    number: 2,
    release_id: "r2",
    manifest_hash: "sha256:eaaed26f1c",
    summary: "Scene 3 moves to the stairwell, 16:30–17:15, with reduced coverage. Scenes 1 and 2 unchanged.",
    changes: ["Rooftop permission refused (Producer, 14:05)", "Maya must leave at 18:00 (14:15)", "Director chose: stairwell, reduced coverage"],
    created_at: "2026-11-06T14:24:00+05:30",
  },
  general_call: "2026-11-06T14:45:00+05:30",
  sunset: "2026-11-06T17:52:00+05:30",
  scenes: [
    { status: "scheduled", number: 1, title: "The missed call", location: "stairwell", start: "2026-11-06T15:00:00+05:30", end: "2026-11-06T15:15:00+05:30", cast: ["2"], changed: false },
    { status: "scheduled", number: 2, title: "A promise", location: "courtyard", start: "2026-11-06T15:25:00+05:30", end: "2026-11-06T15:35:00+05:30", cast: ["1", "2"], changed: false },
    { status: "scheduled", number: 3, title: "The confession", location: "stairwell", start: "2026-11-06T16:30:00+05:30", end: "2026-11-06T17:15:00+05:30", cast: ["1", "2"], changed: true },
  ],
  crew: [
    { name: "Maya", role: "Actor (1)", call_time: "2026-11-06T16:15:00+05:30", changed: true },
    { name: "Dev", role: "Actor (2)", call_time: "2026-11-06T16:15:00+05:30", changed: true },
    { name: "Leela", role: "Camera / sound", call_time: "2026-11-06T16:15:00+05:30", changed: true },
  ],
  locations: [{ name: "Stairwell", note: "Block B, east stairs. Quiet after 16:00." }, { name: "Courtyard", note: "Permission window until 17:00." }],
  confirm_hint: "Reply “confirm r2” in #crew.",
};
