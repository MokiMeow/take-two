import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

export type DotState = "idle" | "queued" | "running" | "done" | "failed" | "hold" | "verify" | "cancelled";

const DOT_COLOR: Record<DotState, string> = {
  idle: "var(--faint)",
  queued: "var(--muted)",
  running: "var(--run)",
  done: "var(--pass)",
  failed: "var(--fail)",
  hold: "var(--hold)",
  verify: "var(--verify)",
  cancelled: "var(--faint)",
};

// Geist rule: only in-flight states animate; every dot sits next to a text label.
export function StatusDot({ state, size = 8 }: { state: DotState; size?: number }) {
  const reduce = useReducedMotion();
  const color = DOT_COLOR[state];
  const live = !reduce && (state === "running" || state === "queued" || state === "hold");
  return (
    <span className="dot" style={{ width: size, height: size }} aria-hidden>
      {live && (
        <motion.span
          className="dot-halo"
          style={{ background: color }}
          initial={{ scale: 1, opacity: 0.5 }}
          animate={{ scale: state === "queued" ? 1.8 : 2.6, opacity: 0 }}
          transition={{ duration: state === "queued" ? 2.2 : 1.4, repeat: Infinity, ease: "easeOut" }}
        />
      )}
      <span className="dot-core" style={{ background: state === "idle" ? "transparent" : color, borderColor: color }} />
    </span>
  );
}

// A rubber stamp that lands with a little overshoot, like ink hitting paper.
export function Stamp({
  children,
  tone = "hold",
  rotate = -6,
  size = "md",
  delay = 0,
}: {
  children: ReactNode;
  tone?: "hold" | "fail" | "pass" | "muted";
  rotate?: number;
  size?: "sm" | "md" | "lg";
  delay?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.span
      className={`stamp stamp-${tone} stamp-${size}`}
      initial={reduce ? false : { scale: 1.6, opacity: 0, rotate: rotate - 4 }}
      animate={{ scale: 1, opacity: 1, rotate }}
      transition={{ type: "spring", stiffness: 520, damping: 26, mass: 0.7, delay }}
    >
      {children}
    </motion.span>
  );
}

// Logo: a clapper slate. The take number is the current release.
export function Slate({ take }: { take: number }) {
  return (
    <div className="slate" aria-label={`Take Two, release ${take}`}>
      <svg className="slate-stick" viewBox="0 0 64 12" aria-hidden>
        <defs>
          <pattern id="slate-stripes" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="skewX(-35)">
            <rect width="6" height="12" fill="#ECEAE3" />
            <rect x="6" width="6" height="12" fill="#0E0E10" />
          </pattern>
        </defs>
        <rect x="0.5" y="0.5" width="63" height="11" rx="1.5" fill="url(#slate-stripes)" stroke="#ECEAE3" />
      </svg>
      <div className="slate-body">
        <span className="slate-word">TAKE</span>
        <span className="slate-num mono">{String(take).padStart(2, "0")}</span>
      </div>
    </div>
  );
}

export function Pill({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "pass" | "fail" | "hold" | "verify" | "run" }) {
  return <span className={`pill pill-${tone}`}>{children}</span>;
}

export function Section({ label, right, children, className = "" }: { label: string; right?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`section ${className}`}>
      <header className="section-head">
        <span className="eyebrow">{label}</span>
        {right}
      </header>
      {children}
    </section>
  );
}
