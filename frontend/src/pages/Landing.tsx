import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Hero3D } from "../components/Hero3D";

export function Landing() {
  return (
    <div className="relative overflow-hidden">
      <Hero3D />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-transparent via-ink-950/10 to-ink-950" />

      <div className="relative mx-auto flex min-h-[calc(100vh-73px)] max-w-3xl flex-col items-center justify-center px-6 text-center">
        <motion.span
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-5 rounded-full border border-ink-700 bg-ink-900/60 px-4 py-1.5 text-xs font-medium text-ink-200"
        >
          A friend who's really organized about your job search
        </motion.span>

        <motion.h1
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.05 }}
          className="font-display text-4xl font-bold leading-tight text-ink-50 sm:text-5xl"
        >
          Tailor every application.
          <br />
          <span className="text-coral-500">Never fake a word of it.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="mt-5 max-w-xl text-balance text-ink-200"
        >
          Vrutti reads a job posting, scores your real fit, and drafts a tailored resume and
          cover letter from what's actually in your profile — nothing invented. You review
          everything. Nothing sends itself.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.25 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-3"
        >
          <Link
            to="/jobs"
            className="rounded-full bg-coral-500 px-6 py-3 text-sm font-semibold text-ink-950 shadow-[var(--shadow-glow-coral)] transition-transform hover:scale-105"
          >
            Paste a job posting
          </Link>
          <Link
            to="/profile"
            className="rounded-full border border-ink-700 px-6 py-3 text-sm font-semibold text-ink-100 transition-colors hover:border-ink-600 hover:bg-ink-900"
          >
            Set up your profile
          </Link>
        </motion.div>
      </div>
    </div>
  );
}
