import { useRef } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import type { Job } from "../lib/api";

const RECOMMENDATION_STYLE: Record<string, string> = {
  tailor_and_apply: "bg-mint-500/15 text-mint-400 border-mint-500/30",
  stretch_tailor_carefully: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  skip: "bg-coral-500/15 text-coral-400 border-coral-500/30",
};

const RECOMMENDATION_LABEL: Record<string, string> = {
  tailor_and_apply: "Tailor & apply",
  stretch_tailor_carefully: "Stretch — tailor carefully",
  skip: "Skip",
};

export function JobCard({
  job,
  draggable,
  onDragStart,
}: {
  job: Job;
  draggable?: boolean;
  onDragStart?: (e: React.DragEvent) => void;
}) {
  const navigate = useNavigate();
  const dragged = useRef(false);

  return (
    <div
      draggable={draggable}
      onDragStart={(e) => {
        dragged.current = true;
        onDragStart?.(e);
      }}
      className="cursor-grab active:cursor-grabbing"
    >
      <motion.div
        layout
        whileHover={{ scale: 1.02, y: -2 }}
        transition={{ type: "spring", stiffness: 300, damping: 22 }}
        onClick={() => {
          if (dragged.current) {
            dragged.current = false;
            return;
          }
          navigate(`/jobs/${job.id}`);
        }}
        className="cursor-pointer rounded-2xl border border-ink-800 bg-ink-900 p-4 shadow-sm"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate font-display text-sm font-semibold text-ink-50">
              {job.title || "Untitled role"}
            </p>
            <p className="truncate text-xs text-ink-200">{job.company || "Unknown company"}</p>
          </div>
          {job.fit_score !== null && (
            <span className="shrink-0 rounded-full bg-ink-800 px-2 py-1 text-xs font-semibold text-ink-50">
              {job.fit_score}
            </span>
          )}
        </div>
        {job.location && <p className="mt-2 text-xs text-ink-400">{job.location}</p>}
        {job.fit_recommendation && (
          <span
            className={`mt-3 inline-block rounded-full border px-2 py-0.5 text-[11px] font-medium ${RECOMMENDATION_STYLE[job.fit_recommendation]}`}
          >
            {RECOMMENDATION_LABEL[job.fit_recommendation]}
          </span>
        )}
      </motion.div>
    </div>
  );
}
