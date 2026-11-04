import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import type { CrewMember, Scene } from "../types";
import { span, stripFor } from "../format";
import { Section, Stamp } from "./bits";
import "./Stripboard.css";

export function Stripboard({ scenes, crew, day, tz }: { scenes: Scene[]; crew: CrewMember[]; day: string; tz: string }) {
  const cast = crew.filter((c) => /actor|cast/i.test(c.role));
  const castNo = (id: string) => cast.findIndex((c) => c.id === id) + 1;
  const held = scenes.filter((s) => s.validity !== "valid").length;

  return (
    <Section label="Stripboard" right={<span className="eyebrow">{scenes.length} scenes{held ? ` · ${held} held` : ""}</span>}>
      <ol className="strips" aria-label="Shooting order">
        {scenes.map((s) => (
          <Strip key={s.id} scene={s} castNo={castNo} tz={tz} />
        ))}
        <li className="daybreak">
          <span className="mono">END OF {day.split(" - ")[0].toUpperCase()}</span>
          <span className="mono faint">{scenes.length} SC</span>
        </li>
      </ol>
    </Section>
  );
}

function Strip({ scene, castNo, tz }: { scene: Scene; castNo: (id: string) => number; tz: string }) {
  const reduce = useReducedMotion();
  const plan = scene.plan;
  const strip = stripFor(plan?.location, plan?.start);
  const held = scene.validity !== "valid";
  const ids = (plan?.people ?? []).map(castNo).filter((n) => n > 0).sort((a, b) => a - b);

  return (
    <motion.li
      layout={!reduce}
      className={`strip ${held ? "is-held" : ""}`}
      style={{ ["--strip" as string]: strip.bg }}
      aria-label={`Scene ${scene.number}, ${scene.title}${held ? ", on hold" : ""}`}
    >
      <div className="strip-num mono">{scene.number}</div>
      <div className="strip-main paper">
        <div className="strip-row">
          <span className={`strip-heading mono ${held ? "struck" : ""}`}>{strip.heading}</span>
          {plan && <span className="strip-time mono">{span(plan.start, plan.end, tz)}</span>}
        </div>
        <div className="strip-row">
          <span className="strip-title script">{scene.title}</span>
          <span className="strip-cast mono" title="Cast IDs">
            {ids.map((n) => (
              <span key={n} className="cast-id">{n}</span>
            ))}
          </span>
        </div>
        <AnimatePresence>
          {held && (
            <motion.div
              className="strip-hold"
              initial={reduce ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <Stamp tone="hold" rotate={-4} size="md">{scene.validity === "held" ? "Hold" : "Invalid"}</Stamp>
              {scene.hold_reason && <p className="strip-reason">{scene.hold_reason}</p>}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.li>
  );
}
