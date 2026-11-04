import { z } from "zod";

// Input for one 5-second option preview. The coordinator writes this as JSON from an
// approved-or-candidate manifest; nothing here is generated code.
export const previewSchema = z.object({
  letter: z.string().max(2),
  label: z.string().max(80),
  scene_number: z.number().int().min(0),
  scene_title: z.string().max(80),
  location: z.string().max(40),
  start: z.string(),
  end: z.string(),
  shots: z.array(z.string().max(30)).min(1).max(6),
  people: z.array(z.object({ id: z.string(), name: z.string().max(30) })).max(4),
  sunset: z.boolean().optional(),
  crowd: z.boolean().optional(),
  manifest_hash: z.string().max(80),
});
export type PreviewProps = z.infer<typeof previewSchema>;

export const callSheetSchema = z.object({
  production: z.object({ title: z.string(), day: z.string(), date: z.string(), timezone: z.string() }),
  release: z.object({
    number: z.number().int().min(1),
    release_id: z.string(),
    manifest_hash: z.string(),
    summary: z.string(),
    changes: z.array(z.string()).max(6),
    created_at: z.string(),
  }),
  general_call: z.string(),
  sunset: z.string().optional(),
  scenes: z.array(
    z.object({
      number: z.number(),
      title: z.string(),
      location: z.string(),
      start: z.string(),
      end: z.string(),
      cast: z.array(z.string()),
      changed: z.boolean().optional(),
    }),
  ).max(12),
  crew: z.array(
    z.object({ name: z.string(), role: z.string(), call_time: z.string(), changed: z.boolean().optional() }),
  ).max(20),
  locations: z.array(z.object({ name: z.string(), note: z.string().optional() })).max(6),
  confirm_hint: z.string(),
});
export type CallSheetProps = z.infer<typeof callSheetSchema>;

export const previewDefaults: PreviewProps = {
  letter: "A",
  label: "Stairwell, reduced coverage",
  scene_number: 3,
  scene_title: "The confession",
  location: "stairwell",
  start: "2026-11-06T16:30:00+05:30",
  end: "2026-11-06T17:15:00+05:30",
  shots: ["wide", "two-shot", "close-up"],
  people: [{ id: "maya", name: "Maya" }, { id: "dev", name: "Dev" }],
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
    { number: 1, title: "The missed call", location: "stairwell", start: "2026-11-06T15:00:00+05:30", end: "2026-11-06T15:15:00+05:30", cast: ["2"] },
    { number: 2, title: "A promise", location: "courtyard", start: "2026-11-06T15:25:00+05:30", end: "2026-11-06T15:35:00+05:30", cast: ["1", "2"] },
    { number: 3, title: "The confession", location: "stairwell", start: "2026-11-06T16:30:00+05:30", end: "2026-11-06T17:15:00+05:30", cast: ["1", "2"], changed: true },
  ],
  crew: [
    { name: "Maya", role: "Actor (1)", call_time: "2026-11-06T16:15:00+05:30", changed: true },
    { name: "Dev", role: "Actor (2)", call_time: "2026-11-06T16:15:00+05:30", changed: true },
    { name: "Leela", role: "Camera / sound", call_time: "2026-11-06T16:15:00+05:30", changed: true },
  ],
  locations: [{ name: "Stairwell", note: "Block B, east stairs. Quiet after 16:00." }, { name: "Courtyard", note: "Permission window until 17:00." }],
  confirm_hint: "Reply “confirm r2” in #crew.",
};
