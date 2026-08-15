import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

const STEPS = [
  "Reading the job description…",
  "Matching it against your real experience…",
  "Weighing the honest gaps…",
  "Double-checking the reasoning…",
];

/** The "wow" moment: a friendly, alive progress sequence instead of a blank spinner. */
export function EvaluationProgress() {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setStepIndex((i) => Math.min(i + 1, STEPS.length - 1));
    }, 900);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center gap-4 py-10">
      <div className="relative h-10 w-10">
        <motion.div
          className="absolute inset-0 rounded-full border-2 border-coral-500/30"
          animate={{ scale: [1, 1.15, 1], opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute inset-2 rounded-full bg-coral-500"
          animate={{ scale: [1, 0.85, 1] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
      <AnimatePresence mode="wait">
        <motion.p
          key={stepIndex}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.3 }}
          className="text-sm text-ink-200"
        >
          {STEPS[stepIndex]}
        </motion.p>
      </AnimatePresence>
    </div>
  );
}
