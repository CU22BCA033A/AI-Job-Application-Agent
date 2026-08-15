import { motion, useReducedMotion } from "framer-motion";

const SIZE = 148;
const STROKE = 12;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function colorFor(score: number): string {
  if (score >= 70) return "var(--color-mint-500)";
  if (score >= 40) return "var(--color-amber-500)";
  return "var(--color-coral-500)";
}

export function FitScoreRing({ score }: { score: number }) {
  const reduceMotion = useReducedMotion();
  const offset = CIRCUMFERENCE * (1 - score / 100);
  const color = colorFor(score);

  return (
    <div className="relative" style={{ width: SIZE, height: SIZE }}>
      <svg width={SIZE} height={SIZE} className="-rotate-90">
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          stroke="var(--color-ink-700)"
          strokeWidth={STROKE}
          fill="none"
        />
        <motion.circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          stroke={color}
          strokeWidth={STROKE}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={CIRCUMFERENCE}
          initial={{ strokeDashoffset: CIRCUMFERENCE }}
          animate={{ strokeDashoffset: offset }}
          transition={
            reduceMotion
              ? { duration: 0 }
              : { duration: 1.1, ease: [0.16, 1, 0.3, 1], delay: 0.15 }
          }
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          className="font-display text-3xl font-bold text-ink-50"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: reduceMotion ? 0 : 0.5, duration: 0.4 }}
        >
          {score}
        </motion.span>
        <span className="text-xs text-ink-200">fit score</span>
      </div>
    </div>
  );
}
