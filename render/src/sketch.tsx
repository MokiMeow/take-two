import { createContext, useContext, type ReactNode } from "react";

// Camera zoom, so strokes keep a constant pencil weight on screen at any framing.
export const ZoomContext = createContext(1);

// Pencil storyboard primitives. All art lives in a 960x540 coordinate space.
export const W = 960;
export const H = 540;
export const GRAPHITE = "#2a2925";

// Line boil: the displacement seed changes every few frames, like a hand-drawn animatic.
export function PencilFilter({ id, seed, scale = 2.4 }: { id: string; seed: number; scale?: number }) {
  return (
    <filter id={id} x="-5%" y="-5%" width="110%" height="110%">
      <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed={seed} result="n" />
      <feDisplacementMap in="SourceGraphic" in2="n" scale={scale} xChannelSelector="R" yChannelSelector="G" />
    </filter>
  );
}

// Every stroke is drawn twice, slightly offset and lighter, for a sketchy double line.
export function Ink({ children, width = 2.2, opacity = 0.9 }: { children: ReactNode; width?: number; opacity?: number }) {
  const zoom = useContext(ZoomContext);
  width = width / Math.sqrt(zoom);
  return (
    <g fill="none" stroke={GRAPHITE} strokeLinecap="round" strokeLinejoin="round">
      <g strokeWidth={width} opacity={opacity}>{children}</g>
      <g strokeWidth={width * 0.55} opacity={opacity * 0.35} transform={`translate(${1.4 / zoom} ${0.8 / zoom})`}>{children}</g>
    </g>
  );
}

export function Hatch({ x, y, w, h, gap = 9, angle = 1 }: { x: number; y: number; w: number; h: number; gap?: number; angle?: number }) {
  const lines: ReactNode[] = [];
  for (let i = -h; i < w; i += gap) {
    lines.push(<line key={i} x1={x + i} y1={y + h} x2={x + i + h * angle} y2={y} />);
  }
  return (
    <g>
      <clipPath id={`hc-${x}-${y}`}><rect x={x} y={y} width={w} height={h} /></clipPath>
      <g clipPath={`url(#hc-${x}-${y})`} strokeWidth={1.1} opacity={0.4}>{lines}</g>
    </g>
  );
}

// A storyboard figure: head with hair, shoulders, tapered torso, limbs. pose: stand | sit. facing: 1 right, -1 left.
export function Figure({ x, y, pose = "stand", facing = 1, scale = 1, label, hair = "short" }: { x: number; y: number; pose?: "stand" | "sit"; facing?: 1 | -1; scale?: number; label?: string; hair?: "short" | "long" }) {
  const f = facing;
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      <Ink width={2.4}>
        {/* head + jaw turned toward facing side */}
        <path d={`M ${-11 * f} -126 Q ${-12 * f} -140 ${0} -141 Q ${13 * f} -140 ${13 * f} -124 Q ${13 * f} -110 ${2 * f} -105 Q ${-9 * f} -106 ${-11 * f} -118 Z`} />
        {hair === "long" ? (
          <path d={`M ${-12 * f} -124 Q ${-16 * f} -144 ${2 * f} -144 Q ${16 * f} -142 ${14 * f} -128 M ${-12 * f} -124 Q ${-18 * f} -104 ${-12 * f} -88 M ${-7 * f} -136 Q ${-12 * f} -112 ${-6 * f} -96`} />
        ) : (
          <path d={`M ${-12 * f} -126 Q ${-10 * f} -146 ${4 * f} -143 Q ${15 * f} -140 ${14 * f} -129 M ${-6 * f} -142 l ${3 * f} 4 M ${2 * f} -144 l ${2 * f} 4`} />
        )}
        <path d={`M ${8 * f} -121 l ${2 * f} 0`} />
        {/* neck, shoulders, torso */}
        <path d={`M ${1 * f} -105 L ${2 * f} -98 M ${-16 * f} -94 Q ${0} -100 ${18 * f} -93`} />
        <path d={`M ${-15 * f} -94 Q ${-13 * f} -74 ${-9 * f} -58 L ${12 * f} -58 Q ${16 * f} -76 ${17 * f} -93`} />
        {/* arms: near arm reaches forward, far arm rests */}
        <path d={`M ${17 * f} -92 Q ${26 * f} -76 ${22 * f} -62 Q ${20 * f} -56 ${28 * f} -54`} />
        <path d={`M ${-15 * f} -92 Q ${-20 * f} -76 ${-14 * f} -62`} />
        {pose === "stand" ? (
          <path d={`M ${-6 * f} -58 Q ${-6 * f} -30 ${-7 * f} 0 l ${-6 * f} 0 M ${9 * f} -58 Q ${12 * f} -28 ${10 * f} 0 l ${8 * f} 0`} />
        ) : (
          <path d={`M ${-8 * f} -58 L ${24 * f} -60 Q ${30 * f} -60 ${30 * f} -52 L ${28 * f} -22 l ${8 * f} 0 M ${10 * f} -58 L ${32 * f} -55 Q ${38 * f} -54 ${36 * f} -46 L ${34 * f} -22 l ${8 * f} 0`} />
        )}
      </Ink>
      <Ink width={1} opacity={0.45}>
        <path d={`M ${-12 * f} -88 l ${22 * f} -2 M ${-11 * f} -80 l ${24 * f} -2 M ${-10 * f} -72 l ${24 * f} -2 M ${-10 * f} -64 l ${22 * f} -2`} />
      </Ink>
      {label && (
        <text x={4 * f} y={pose === "stand" ? 22 : 4} textAnchor="middle" fontFamily="Courier Prime" fontWeight={700} fontSize={13} fill={GRAPHITE} opacity={0.65} letterSpacing={1.5}>
          {label.toUpperCase()}
        </text>
      )}
    </g>
  );
}

export function Sun({ x, y, r = 34, rays = true }: { x: number; y: number; r?: number; rays?: boolean }) {
  return (
    <Ink width={1.8} opacity={0.75}>
      <path d={`M ${x - r} ${y} A ${r} ${r} 0 0 1 ${x + r} ${y}`} />
      {rays && [-70, -45, -20, 20, 45, 70].map((a) => {
        const rad = ((a - 90) * Math.PI) / 180;
        return <line key={a} x1={x + Math.cos(rad) * (r + 10)} y1={y + Math.sin(rad) * (r + 10)} x2={x + Math.cos(rad) * (r + 26)} y2={y + Math.sin(rad) * (r + 26)} />;
      })}
    </Ink>
  );
}

// ——— Locations ———

export function Stairwell() {
  const steps: ReactNode[] = [];
  for (let i = 0; i < 9; i++) {
    const y = 470 - i * 34;
    const x = 160 + i * 52;
    steps.push(<path key={i} d={`M ${x} ${y} L ${x + 380} ${y} M ${x} ${y} L ${x} ${y - 34} L ${x + 52} ${y - 34}`} />);
  }
  return (
    <g>
      <Ink>
        <path d="M 60 520 L 60 40 M 900 520 L 900 40 M 60 470 L 900 470" />
        {steps}
        <path d="M 140 420 L 640 120 M 140 420 L 140 470 M 260 348 L 260 398 M 380 276 L 380 326 M 500 204 L 500 254 M 620 132 L 620 182" />
        <rect x={720} y={70} width={70} height={150} />
      </Ink>
      <Ink width={1.2} opacity={0.6}>
        <Hatch x={60} y={40} w={100} h={430} gap={11} />
        <path d="M 720 220 L 560 470 M 790 220 L 700 470" strokeDasharray="6 8" />
      </Ink>
    </g>
  );
}

export function Park({ crowd, frame }: { crowd: boolean; frame: number }) {
  const walkers = crowd
    ? [
        { x0: -60, speed: 1.6, y: 330, s: 0.42 },
        { x0: 980, speed: -1.2, y: 336, s: 0.38 },
        { x0: 300, speed: 0.9, y: 328, s: 0.34 },
      ]
    : [];
  return (
    <g>
      <Ink>
        <path d="M 0 330 Q 240 318 480 326 T 960 322" />
        <path d="M 120 330 L 128 210 M 112 220 Q 60 170 110 120 Q 160 70 210 130 Q 250 190 150 215" />
        <path d="M 820 326 L 812 190 M 800 205 Q 740 150 800 100 Q 870 60 905 130 Q 930 190 830 200" />
        <path d="M 320 398 L 640 398 M 332 398 L 330 440 M 628 398 L 630 440 M 336 398 L 336 346 L 624 346 L 624 398 M 336 368 L 624 368 M 320 398 L 326 406 L 634 406 L 640 398" />
      </Ink>
      <Ink width={1.1} opacity={0.5}>
        <path d="M 0 470 Q 300 460 960 480 M 0 505 Q 400 495 960 515" />
      </Ink>
      {walkers.map((w, i) => (
        <g key={i} opacity={0.75}>
          <Figure x={(w.x0 + w.speed * frame + 1100) % 1100 - 70} y={w.y} scale={w.s} facing={w.speed > 0 ? 1 : -1} />
        </g>
      ))}
    </g>
  );
}

export function Rooftop() {
  return (
    <g>
      <Ink>
        <path d="M 0 300 L 70 300 L 70 210 L 150 210 L 150 260 L 230 260 L 230 150 L 290 150 L 290 300 L 640 300 L 640 190 L 720 190 L 720 240 L 800 240 L 800 130 L 860 130 L 860 300 L 960 300" />
        <path d="M 0 420 L 960 420 M 0 445 L 960 445" />
        <rect x={420} y={230} width={70} height={70} />
        <path d="M 420 230 L 455 205 L 490 230" />
      </Ink>
      <Ink width={1.1} opacity={0.55}>
        {[0, 1, 2, 3].map((r) => [0, 1].map((c) => <rect key={`${r}${c}`} x={240 + c * 22} y={165 + r * 30} width={10} height={14} />))}
        <Hatch x={0} y={420} w={960} h={25} gap={14} />
      </Ink>
    </g>
  );
}

export function Courtyard() {
  return (
    <g>
      <Ink>
        <path d="M 40 360 L 920 360" />
        {[0, 1, 2, 3, 4].map((i) => {
          const x = 90 + i * 170;
          return <path key={i} d={`M ${x} 360 L ${x} 190 Q ${x + 60} 110 ${x + 120} 190 L ${x + 120} 360`} />;
        })}
        <path d="M 0 520 L 300 360 M 960 520 L 660 360 M 480 520 L 480 360" />
      </Ink>
      <Ink width={1.1} opacity={0.5}>
        <path d="M 120 470 L 840 470 M 200 420 L 760 420" />
      </Ink>
    </g>
  );
}

export function Room() {
  return (
    <Ink>
      <path d="M 120 80 L 840 80 L 840 460 L 120 460 Z M 120 460 L 40 530 M 840 460 L 920 530 M 120 80 L 40 20 M 840 80 L 920 20" />
      <rect x={600} y={150} width={140} height={120} />
    </Ink>
  );
}
