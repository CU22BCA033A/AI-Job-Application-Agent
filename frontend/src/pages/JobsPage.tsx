import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { api, type Job, type JobStatus } from "../lib/api";
import { EvaluationProgress } from "../components/EvaluationProgress";
import { FitScoreRing } from "../components/FitScoreRing";
import { JobCard } from "../components/JobCard";

const COLUMNS: { status: JobStatus; label: string }[] = [
  { status: "new", label: "New" },
  { status: "evaluated", label: "Evaluated" },
  { status: "drafting", label: "Drafting" },
  { status: "ready", label: "Ready" },
  { status: "submitted", label: "Submitted" },
  { status: "interviewing", label: "Interviewing" },
  { status: "closed", label: "Closed" },
];

export function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pasteText, setPasteText] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [lastResult, setLastResult] = useState<Job | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [dragJobId, setDragJobId] = useState<string | null>(null);

  useEffect(() => {
    refreshJobs();
  }, []);

  async function refreshJobs() {
    try {
      setJobs(await api.listJobs());
      setLoadError(null);
    } catch (err) {
      setLoadError(
        "Couldn't reach the backend. Make sure the API is running at the address in VITE_API_BASE_URL.",
      );
    }
  }

  async function handleEvaluate() {
    if (!pasteText.trim()) return;
    setIsEvaluating(true);
    setSubmitError(null);
    setLastResult(null);
    try {
      const created = await api.createJob(pasteText.trim(), sourceUrl.trim() || undefined);
      const evaluated = await api.evaluateJob(created.id);
      setLastResult(evaluated);
      setPasteText("");
      setSourceUrl("");
      await refreshJobs();
    } catch (err) {
      setSubmitError(
        err instanceof Error
          ? err.message
          : "Something went wrong evaluating that posting. Mind trying again?",
      );
    } finally {
      setIsEvaluating(false);
    }
  }

  const jobsByStatus = useMemo(() => {
    const grouped: Record<JobStatus, Job[]> = {
      new: [],
      evaluated: [],
      drafting: [],
      ready: [],
      submitted: [],
      interviewing: [],
      closed: [],
    };
    for (const job of jobs) grouped[job.status].push(job);
    return grouped;
  }, [jobs]);

  async function handleDrop(status: JobStatus) {
    if (!dragJobId) return;
    const job = jobs.find((j) => j.id === dragJobId);
    setDragJobId(null);
    if (!job || job.status === status) return;

    setJobs((prev) => prev.map((j) => (j.id === job.id ? { ...j, status } : j)));
    try {
      await api.updateJobStatus(job.id, status);
    } catch {
      await refreshJobs();
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <section className="rounded-3xl border border-ink-800 bg-ink-900/60 p-6 sm:p-8">
        <h1 className="font-display text-2xl font-bold text-ink-50">Paste a job posting</h1>
        <p className="mt-1 text-sm text-ink-200">
          Drop in the full description. Vrutti will read it against your profile and give you an
          honest fit score — no auto-apply, just a clear read on whether it's worth your time.
        </p>

        <textarea
          value={pasteText}
          onChange={(e) => setPasteText(e.target.value)}
          placeholder="Paste the full job description here…"
          rows={7}
          className="mt-4 w-full resize-y rounded-2xl border border-ink-700 bg-ink-950 p-4 text-sm text-ink-50 placeholder:text-ink-400 focus:border-coral-500 focus:outline-none"
        />
        <input
          value={sourceUrl}
          onChange={(e) => setSourceUrl(e.target.value)}
          placeholder="Posting URL (optional)"
          className="mt-3 w-full rounded-xl border border-ink-700 bg-ink-950 p-3 text-sm text-ink-50 placeholder:text-ink-400 focus:border-coral-500 focus:outline-none"
        />

        <button
          onClick={handleEvaluate}
          disabled={isEvaluating || !pasteText.trim()}
          className="mt-4 rounded-full bg-coral-500 px-6 py-2.5 text-sm font-semibold text-ink-950 transition-transform hover:scale-105 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
        >
          {isEvaluating ? "Evaluating…" : "Evaluate fit"}
        </button>

        {submitError && <p className="mt-3 text-sm text-coral-400">{submitError}</p>}

        <AnimatePresence mode="wait">
          {isEvaluating && (
            <motion.div key="progress" exit={{ opacity: 0 }}>
              <EvaluationProgress />
            </motion.div>
          )}

          {!isEvaluating && lastResult && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="mt-6 flex flex-col items-start gap-6 rounded-2xl border border-ink-800 bg-ink-950 p-6 sm:flex-row"
            >
              <FitScoreRing score={lastResult.fit_score ?? 0} />
              <div className="flex-1">
                <p className="font-display text-lg font-semibold text-ink-50">
                  {lastResult.title} at {lastResult.company}
                </p>
                <p className="mt-2 text-sm text-ink-200">{lastResult.fit_reasoning}</p>
                {lastResult.fit_strengths.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-mint-400">
                      Strengths
                    </p>
                    <ul className="mt-1 list-inside list-disc text-sm text-ink-100">
                      {lastResult.fit_strengths.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {lastResult.fit_gaps.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-amber-400">
                      Real gaps
                    </p>
                    <ul className="mt-1 list-inside list-disc text-sm text-ink-100">
                      {lastResult.fit_gaps.map((g, i) => (
                        <li key={i}>{g}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      <section className="mt-10">
        <h2 className="font-display text-xl font-bold text-ink-50">Your pipeline</h2>
        {loadError && <p className="mt-2 text-sm text-coral-400">{loadError}</p>}
        {!loadError && jobs.length === 0 && (
          <p className="mt-2 text-sm text-ink-200">
            Nothing here yet — paste a job posting above to get started.
          </p>
        )}

        <div className="mt-4 grid grid-cols-1 gap-4 overflow-x-auto sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
          {COLUMNS.map((column) => (
            <div
              key={column.status}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => handleDrop(column.status)}
              className="min-h-[120px] rounded-2xl border border-ink-800/70 bg-ink-900/30 p-3"
            >
              <p className="mb-3 flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-ink-400">
                {column.label}
                <span className="rounded-full bg-ink-800 px-2 py-0.5 text-[10px] text-ink-200">
                  {jobsByStatus[column.status].length}
                </span>
              </p>
              <div className="flex flex-col gap-3">
                {jobsByStatus[column.status].map((job) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    draggable
                    onDragStart={() => setDragJobId(job.id)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
