import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

const DEFAULT_STEPS = [
  "Reading the job description…",
  "Matching it against your real experience…",
  "Weighing the honest gaps…",
  "Double-checking the reasoning…",
];

/** The "wow" moment: a friendly, alive progress sequence instead of a blank
 * spinner. Reused for fit evaluation, drafting, and interview prep — each
 * passes its own step copy so the "alive" feeling matches what's actually
 * happening.
 */
export function EvaluationProgress({ steps = DEFAULT_STEPS }: { steps?: string[] }) {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    setStepIndex(0);
    const interval = setInterval(() => {
      setStepIndex((i) => Math.min(i + 1, steps.length - 1));
    }, 900);
    return () => clearInterval(interval);
  }, [steps]);

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
          {steps[stepIndex]}
        </motion.p>
      </AnimatePresence>
    </div>
  );
}

export const DRAFTING_STEPS = [
  "Reading the job description…",
  "Selecting your most relevant experience…",
  "Writing tailored bullets — reworded, nothing invented…",
  "Drafting the cover letter in your voice…",
  "Double-checking every claim against your real profile…",
];

export const INTERVIEW_PREP_STEPS = [
  "Reading the job description…",
  "Thinking through what they're likely to ask…",
  "Matching questions to your real achievements…",
  "Writing STAR stories grounded in what actually happened…",
];
