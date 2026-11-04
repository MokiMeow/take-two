import type { CSSProperties } from "react";

const GRAIN =
  "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='p'><feTurbulence type='fractalNoise' baseFrequency='1.2' numOctaves='2'/><feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.07 0'/></filter><rect width='100%' height='100%' filter='url(%23p)'/></svg>\")";

export function paperStyle(bg: string): CSSProperties {
  return {
    backgroundColor: bg,
    backgroundImage: `radial-gradient(120% 90% at 50% 40%, rgba(255,255,255,0.25), rgba(0,0,0,0.05)), ${GRAIN}`,
  };
}

export const PAPER_STYLE = paperStyle("#f4f1e8");

// Industry script-revision paper order; release n prints on colour n.
export const REVISION_PAPER = [
  ["White", "#F7F5EE"], ["Blue", "#CFE3F3"], ["Pink", "#F6CFD8"], ["Yellow", "#F5EAA8"], ["Green", "#D3E9C9"],
  ["Goldenrod", "#E8C46A"], ["Buff", "#EBDDB8"], ["Salmon", "#F3BBA4"], ["Cherry", "#E58A8F"],
] as const;

export function paperFor(n: number) {
  const [name, bg] = REVISION_PAPER[(Math.max(1, n) - 1) % REVISION_PAPER.length];
  return { name, bg };
}
