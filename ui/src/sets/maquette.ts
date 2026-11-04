// Set maquettes: a small architectural model of each location on a base plate, built with the
// Anatomy kit (MIT, Ryan; see ./kit/LICENSE). Drawn from the option's own manifest: the location
// picks the set, the cast stand on their marks, the camera and one tape mark per extra set-up
// come from the shot list.
import * as k from "./kit/iso-kit.mjs";

type Pt = [number, number, number];
type Plan = { x: number; y: number; w: number; d: number; r: number };
type Item = { at: Pt; svg: string };

export interface MaquetteInput {
  location: string;
  people: string[]; // on-screen cast ids, in order
  shots: string[];
  names: Record<string, string>;
}

const W = 600;
const H = 280;
const PLATE: Plan = { x: -110, y: -60, w: 220, d: 120, r: 6 };
const PLATE_H = 7;

export function maquette(input: MaquetteInput): string {
  const set = SETS[input.location.toLowerCase()] ?? SETS.studio;
  const corners: Pt[] = [...k.boxCorners(PLATE, -PLATE_H, 0), [PLATE.x, PLATE.y, set.tall], [PLATE.x + PLATE.w, PLATE.y, set.tall]];
  const P = k.fitProjection(corners, W, H, { pad: 8, azimuth: 34, elevation: 26 });
  const ctx = new Ctx(P);

  ctx.plate(input.location);
  set.build(ctx);
  const marks = set.marks.slice(0, Math.max(1, Math.min(2, input.people.length)));
  marks.forEach((m, i) => ctx.pawn(m, input.names[input.people[i]]?.[0] ?? String(i + 1), i));
  ctx.camera(set.camera, set.aim, input.shots.length);

  return k.figureSvg({
    width: W,
    height: H,
    label: `Set model of the ${input.location}: ${input.people.map((p) => input.names[p] ?? p).join(" and ")} on their marks, camera with ${input.shots.length} set-ups (${input.shots.join(", ")}).`,
    body: [ctx.under.join(""), ctx.flush(), ctx.over.join("")],
  });
}

class Ctx {
  P: unknown;
  items: Item[] = [];
  under: string[] = [];
  over: string[] = [];
  constructor(P: unknown) {
    this.P = P;
  }
  at = (p: Pt) => k.iso(p, this.P);
  add(at: Pt, svg: string) {
    this.items.push({ at, svg });
  }
  flush() {
    return this.items
      .sort((a, b) => k.depthOf(a.at, this.P) - k.depthOf(b.at, this.P))
      .map((i) => i.svg)
      .join("");
  }
  S = (paths: unknown, style: Record<string, unknown>) => k.solidSvg(paths, style);
  L = (d: string, style: Record<string, unknown>) => k.lineSvg(d, style);
  D = (pts: unknown[], style: Record<string, unknown>) => k.dotsSvg(pts, style);

  slab(plan: Plan, z: number, h: number, tone = "mid", bevel = 0.5) {
    this.add([plan.x + plan.w / 2, plan.y + plan.d / 2, z], this.S(k.slabOf(plan, z, h, this.P, 4, bevel), { tone }));
  }
  cyl(x: number, y: number, r: number, z: number, h: number, tone = "mid", key?: Pt) {
    this.add(key ?? [x, y, z], this.S(k.cylinder(x, y, r, z, h, this.P, 28), { tone }));
  }

  plate(_name: string) {
    const P = this.P;
    const out = [`<path class="iso-halo" d="${k.haloOf(PLATE, -PLATE_H, PLATE_H, P)}"/>`];
    out.push(this.S(k.slabOf(PLATE, -PLATE_H, PLATE_H, P, 8, 1.4), { tone: "mid" }));
    out.push(this.L(k.planOutline(k.insetPlan(PLATE, 4), 0, P), { tone: "lo" }));
    const screws = k.corners(PLATE, 8);
    out.push(this.L(screws.map(([x, y]: number[]) => k.ring(x, y, 1.8, 0, P, 14)).join(""), { tone: "lo" }));
    out.push(this.D(screws.map(([x, y]: number[]) => this.at([x, y, 0])), { size: 0.45 }));
    // Scale rule along the front edge: one tick per metre, a major every five.
    const strip: Plan = { x: PLATE.x + 14, y: PLATE.y + PLATE.d - 9, w: 90, d: 5, r: 1 };
    out.push(this.S(k.slabOf(strip, 0, 0.5, P, 3), { tone: "lo", crease: "none" }));
    const t = k.topTicks(strip.x + 3, strip.x + strip.w - 3, 4, 5, strip.y + 0.6, 0.5, [1.6, 3], P);
    out.push(this.L(t.minor, { tone: "lo" }), this.L(t.major, { tone: "mid" }));
    this.under.push(out.join(""));
  }

  // A cast member as a model-maker's figure: base disc, body, head. Initial engraved on the base.
  pawn(m: { x: number; y: number; z: number; sit?: boolean }, initial: string, order = 0) {
    const { x, y, z } = m;
    const body = m.sit ? 12 : 21;
    const P = this.P;
    const parts = [
      m.sit ? "" : this.S(k.cylinder(x, y, 6, z, 1.6, P, 28, 0.3), { tone: "mid" }),
      this.S(k.cylinder(x, y, 4.4, z + (m.sit ? 0 : 1.6), body, P, 28, 0.8), { tone: "hi", lit: true }),
      this.S(k.cylinder(x, y, 3.6, z + body + (m.sit ? 0.8 : 2.4), 6.2, P, 28, 1.6), { tone: "hi", lit: true }),
      m.sit ? "" : k.faceTextSvg(k.topMatrix([x + 5, y + 0.9], z + 1.6, P, "x"), initial, { size: 3.4, tone: "lo", anchor: "middle" }),
    ];
    this.add([x + 4, y + 10, z + 0.1], `<g class="set-pawn" style="--i:${order}">${parts.join("")}</g>`);
  }

  // Tripod, camera body and lens pointing at `aim`; the view cone lies on the floor.
  camera(c: { x: number; y: number }, aim: { x: number; y: number }, setups: number) {
    const P = this.P;
    const head = 24;
    const ang = Math.atan2(aim.y - c.y, aim.x - c.x);
    const dir = [Math.cos(ang), Math.sin(ang)];
    const side = [-dir[1], dir[0]];
    // View cone: 40° wide, reaching just past the cast.
    const reach = Math.hypot(aim.x - c.x, aim.y - c.y) + 18;
    const half = Math.tan((20 * Math.PI) / 180) * reach;
    const tip = [c.x, c.y];
    const l = [c.x + dir[0] * reach + side[0] * half, c.y + dir[1] * reach + side[1] * half];
    const r = [c.x + dir[0] * reach - side[0] * half, c.y + dir[1] * reach - side[1] * half];
    const cone = [tip, l, r].map(([x, y]) => this.at([x, y, 0.15]));
    const d = `M${cone.map((p: number[]) => p.join(",")).join("L")}Z`;
    this.under.push(`<g class="set-cone"><path d="${d}" style="fill:var(--set-cone);stroke:none"/>${this.L(`M${cone[0].join(",")}L${cone[1].join(",")}M${cone[0].join(",")}L${cone[2].join(",")}`, { tone: "lit", dashed: true })}</g>`);

    // Extra set-ups as tape marks on the floor, stepped back along the camera's side.
    const tapes: string[] = [];
    for (let i = 1; i < setups; i++) {
      const tx = c.x - dir[0] * (8 + i * 9) + side[0] * (i % 2 ? 10 : -10);
      const ty = c.y - dir[1] * (8 + i * 9) + side[1] * (i % 2 ? 10 : -10);
      tapes.push(k.lineOnTop([tx - 3, ty], [tx + 3, ty], 0.2, P), k.lineOnTop([tx, ty - 3], [tx, ty + 3], 0.2, P));
    }
    if (tapes.length) this.under.push(`<g class="set-cone">${this.L(tapes.join(""), { tone: "hi" })}</g>`);

    const legs = [0, 1, 2].map((i) => {
      const a = ang + Math.PI + (i - 1) * 2.1;
      return [c.x + Math.cos(a) * 8, c.y + Math.sin(a) * 8];
    });
    const hub = this.at([c.x, c.y, head - 2]);
    const legSvg = this.L(legs.map(([x, y]) => `M${this.at([x, y, 0]).join(",")}L${hub.join(",")}`).join(""), { tone: "hi" });
    const feet = this.D(legs.map(([x, y]) => this.at([x, y, 0])), { size: 0.6, tone: "hi" });
    const bodyPlan: Plan = { x: c.x - 5, y: c.y - 4, w: 10, d: 8, r: 1.2 };
    const lens = { x: c.x + dir[0] * 7, y: c.y + dir[1] * 7 };
    const parts = [
      legSvg,
      feet,
      this.S(k.cylinder(c.x, c.y, 2.2, head - 3, 2, P, 20), { tone: "mid" }),
      this.S(k.slabOf(bodyPlan, head - 1, 7, P, 3, 0.6), { tone: "mid" }),
      this.S(k.cylinder(lens.x, lens.y, 2.6, head + 0.4, 4.2, P, 24, 0.4), { tone: "lo" }),
      this.S(k.cylinder(c.x - dir[0] * 1.5, c.y - dir[1] * 1.5, 1.6, head + 6, 2.2, P, 16), { tone: "mid" }),
      this.D([this.at([c.x - dir[0] * 1.5, c.y - dir[1] * 1.5, head + 8.2])], { size: 0.55, tone: "lit" }),
    ];
    this.add([c.x, c.y, 0], parts.join(""));
  }
}

interface SetDef {
  tall: number;
  marks: { x: number; y: number; z: number; sit?: boolean }[];
  camera: { x: number; y: number };
  aim: { x: number; y: number };
  build: (c: Ctx) => void;
}

const wallBack = (c: Ctx, h: number, windows = true) => {
  // Two walls along the far edges, with a skirting line and window slots.
  c.slab({ x: PLATE.x + 4, y: PLATE.y + 4, w: PLATE.w - 8, d: 4, r: 0.5 }, 0, h, "lo");
  c.slab({ x: PLATE.x + 4, y: PLATE.y + 8, w: 4, d: PLATE.d - 12, r: 0.5 }, 0, h, "lo");
  const P = c.P;
  const lines = [k.lineOnTop([PLATE.x + 8, PLATE.y + 8], [PLATE.x + PLATE.w - 4, PLATE.y + 8], 6, P)];
  if (windows) {
    for (const x of [-60, -20, 20, 60]) {
      const a = c.at([x - 7, PLATE.y + 8, h - 18]);
      const b = c.at([x + 7, PLATE.y + 8, h - 18]);
      const e = c.at([x + 7, PLATE.y + 8, h - 6]);
      const f = c.at([x - 7, PLATE.y + 8, h - 6]);
      lines.push(`M${a}L${b}L${e}L${f}Z`);
      const mid = (p: number[], q: number[]) => [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2];
      lines.push(`M${mid(a, f)}L${mid(b, e)}M${mid(a, b)}L${mid(f, e)}`);
    }
  }
  // A door in the side wall: frame, panel line and a handle.
  const dx = PLATE.x + 8;
  const door = [[dx, 14, 0], [dx, 14, 30], [dx, 32, 30], [dx, 32, 0]].map((p) => c.at(p as Pt));
  lines.push(`M${door.map((p: number[]) => p.join(",")).join("L")}`);
  lines.push(`M${c.at([dx, 17, 3])}L${c.at([dx, 17, 27])}L${c.at([dx, 29, 27])}L${c.at([dx, 29, 3])}Z`);
  c.add([PLATE.x + PLATE.w / 2, PLATE.y + 8.1, 0], c.L(lines.join(""), { tone: "lo" }));
  c.add([dx, 30, 1], c.D([c.at([dx, 27, 14])], { size: 0.55, tone: "hi" }));
};

const SETS: Record<string, SetDef> = {
  stairwell: {
    tall: 46,
    marks: [{ x: -26, y: 20, z: 0 }, { x: 12, y: 1, z: 20, sit: true }],
    camera: { x: -44, y: 44 },
    aim: { x: -6, y: 12 },
    build(c) {
      wallBack(c, 46);
      // A flight of eight steps climbing toward the back wall, then a landing against it.
      const rise = 5;
      const run = 8;
      const front = 30;
      for (let i = 0; i < 8; i++) {
        c.slab({ x: -6, y: front - (i + 1) * run, w: 52, d: run, r: 0.4 }, 0, rise * (i + 1), "mid", 0.4);
      }
      c.slab({ x: -6, y: PLATE.y + 8, w: 52, d: front - 8 * run - PLATE.y - 8, r: 0.6 }, 0, rise * 8, "mid", 0.5);
      // Handrail on posts along the open (front-left) side of the flight.
      const posts = [0, 3, 6, 8].map((i) => ({ y: front - i * run - 2, z: rise * i }));
      posts.forEach(({ y, z }) => c.cyl(-3, y, 1, z, 22, "mid", [-3, y - 4, z]));
      const bal: string[] = [];
      for (let i = 0; i < 8; i++) {
        const y = front - i * run - run / 2;
        bal.push(`M${c.at([-3, y, rise * (i + 1)])}L${c.at([-3, y, rise * (i + 0.5) + 22])}`);
      }
      c.add([-3, front - 40, 2], c.L(bal.join(""), { tone: "mid" }));
      const rail = posts.map(({ y, z }) => c.at([-3, y, z + 22]));
      c.add([-3, front - 70, 30], c.L(`M${rail.map((p: number[]) => p.join(",")).join("L")}`, { tone: "hi" }));
    },
  },
  park: {
    tall: 44,
    marks: [{ x: -14, y: 3, z: 9.8, sit: true }, { x: 6, y: 3, z: 9.8, sit: true }],
    camera: { x: 56, y: 44 },
    aim: { x: -5, y: 6 },
    build(c) {
      const P = c.P;
      // Lawn inlay with a gravel path across it.
      c.under.push(c.S(k.slabOf(k.insetPlan(PLATE, 6), 0, 0.6, P, 6), { tone: "lo", crease: "none" }));
      c.under.push(c.S(k.slabOf({ x: PLATE.x + 6, y: 18, w: PLATE.w - 12, d: 16, r: 1 }, 0.6, 0.4, P, 3), { tone: "mid", crease: "none" }));
      // Bench: two legs, three seat slats, two back slats.
      for (const x of [-24, 14]) c.slab({ x, y: -2, w: 3, d: 12, r: 0.4 }, 0.6, 8, "mid");
      for (let i = 0; i < 3; i++) c.slab({ x: -26, y: -2 + i * 4, w: 43, d: 3.2, r: 0.4 }, 8.6, 1.2, "hi");
      for (const z of [12, 17]) c.slab({ x: -26, y: -4, w: 43, d: 2, r: 0.4 }, z, 2.4, "hi");
      for (const x of [-27, 15]) c.slab({ x, y: -3, w: 3, d: 13, r: 0.6 }, 9.8, 5, "mid");
      // Grass: a sparse, even stipple on the lawn (deterministic jitter).
      const tufts: number[][] = [];
      for (let gx = PLATE.x + 14; gx < PLATE.x + PLATE.w - 10; gx += 11)
        for (let gy = PLATE.y + 12; gy < PLATE.y + PLATE.d - 12; gy += 9) {
          const j = Math.sin(gx * 12.9898 + gy * 78.233) * 43758.5453;
          const fx = gx + ((j - Math.floor(j)) - 0.5) * 6;
          const fy = gy + ((j * 7 - Math.floor(j * 7)) - 0.5) * 5;
          if (fy > 16 && fy < 36) continue;
          if (Math.abs(fx + 5) < 32 && Math.abs(fy - 3) < 14) continue;
          tufts.push(c.at([fx, fy, 0.6]));
        }
      c.under.push(c.D(tufts, { size: 0.5, tone: "lo" }));
      // Trees: trunk and a stack of canopy discs.
      for (const [x, y, s] of [[-78, -44, 0.75], [70, -50, 0.65], [-86, 40, 0.55]] as const) {
        c.cyl(x, y, 2.2 * s, 0.6, 26 * s, "lo", [x, y, 1]);
        [16, 13, 9].forEach((r, i) => c.cyl(x, y, r * s, (24 + i * 7) * s, 7 * s, i === 1 ? "mid" : "lo", [x, y, 2 + i]));
      }
      // Lamp post.
      c.cyl(46, -18, 1.1, 0.6, 30, "mid", [46, -18, 1]);
      c.slab({ x: 43, y: -21, w: 6, d: 6, r: 1 }, 30.6, 4, "hi");
      const lamp = c.at([46, -18, 32]);
      c.over.push(`<circle cx="${lamp[0]}" cy="${lamp[1]}" r="9" style="fill:var(--set-glow)"/>`);
      // Passers-by on the path: the people who make the scene less private.
      for (const [x, y] of [[-60, 26], [-44, 28], [72, 24]]) {
        c.cyl(x, y, 2.2, 1, 10, "mid", [x, y, 1]);
        c.cyl(x, y, 1.8, 11.6, 3, "mid", [x, y, 1.1]);
      }
      // Low sun behind the far trees.
      const s = c.at([20, PLATE.y - 4, 34]);
      c.under.unshift(`<circle cx="${s[0]}" cy="${s[1]}" r="13" style="fill:var(--set-sun)"/><circle cx="${s[0]}" cy="${s[1]}" r="8.5" style="fill:var(--set-sun-core)"/>`);
    },
  },
  courtyard: {
    tall: 42,
    marks: [{ x: -10, y: 0, z: 0 }, { x: 10, y: 4, z: 0 }],
    camera: { x: 58, y: 42 },
    aim: { x: 0, y: 2 },
    build(c) {
      const P = c.P;
      wallBack(c, 40, false);
      // Paving grid.
      const g: string[] = [];
      for (let x = PLATE.x + 20; x < PLATE.x + PLATE.w - 4; x += 16) g.push(k.lineOnTop([x, PLATE.y + 10], [x, PLATE.y + PLATE.d - 12], 0.05, P));
      for (let y = PLATE.y + 22; y < PLATE.y + PLATE.d - 12; y += 16) g.push(k.lineOnTop([PLATE.x + 10, y], [PLATE.x + PLATE.w - 6, y], 0.05, P));
      c.under.push(c.L(g.join(""), { tone: "faint" }));
      // Planters with shrubs, and an arched gate frame.
      for (const [x, y] of [[-70, -40], [40, -44], [-74, 36]]) {
        c.slab({ x: x - 9, y: y - 9, w: 18, d: 18, r: 1 }, 0, 8, "mid");
        c.cyl(x, y, 7.5, 8, 9, "lo", [x, y, 1]);
      }
      c.slab({ x: 84, y: -30, w: 4, d: 4, r: 0.5 }, 0, 34, "mid");
      c.slab({ x: 84, y: 10, w: 4, d: 4, r: 0.5 }, 0, 34, "mid");
      c.slab({ x: 84, y: -30, w: 4, d: 44, r: 0.5 }, 34, 4, "mid");
    },
  },
  rooftop: {
    tall: 50,
    marks: [{ x: -8, y: 0, z: 0 }, { x: 10, y: 2, z: 0 }],
    camera: { x: 60, y: 48 },
    aim: { x: 0, y: 1 },
    build(c) {
      for (const p of [
        { x: PLATE.x + 4, y: PLATE.y + 4, w: PLATE.w - 8, d: 4, r: 0.5 },
        { x: PLATE.x + 4, y: PLATE.y + 8, w: 4, d: PLATE.d - 12, r: 0.5 },
      ]) c.slab(p, 0, 10, "lo");
      c.slab({ x: -90, y: -60, w: 34, d: 28, r: 1 }, 0, 30, "mid");
      for (const [x, y] of [[60, -46], [74, -46], [60, -34], [74, -34]]) c.cyl(x, y, 1, 0, 16, "mid", [x, y, 0]);
      c.cyl(67, -40, 12, 16, 18, "mid", [67, -40, 2]);
    },
  },
  studio: {
    tall: 40,
    marks: [{ x: -8, y: 0, z: 0 }, { x: 10, y: 2, z: 0 }],
    camera: { x: 60, y: 48 },
    aim: { x: 0, y: 1 },
    build(c) {
      wallBack(c, 40, false);
    },
  },
};
