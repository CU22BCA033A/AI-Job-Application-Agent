import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Analytics, type Application, type Job } from "../lib/api";

const STAT_LABEL: { key: keyof Analytics; label: string; suffix?: string }[] = [
  { key: "total_jobs", label: "Jobs tracked" },
  { key: "applications_sent", label: "Applications sent" },
  { key: "interviewing", label: "In interviews" },
  { key: "closed", label: "Closed out" },
  { key: "response_rate", label: "Response rate", suffix: "%" },
  { key: "interview_rate", label: "Interview rate", suffix: "%" },
];

export function ApplicationsPage() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [analyticsData, applicationsData, jobsData] = await Promise.all([
          api.getAnalytics(),
          api.listApplications(),
          api.listJobs(),
        ]);
        setAnalytics(analyticsData);
        setApplications(applicationsData);
        setJobs(jobsData);
        setError(null);
      } catch {
        setError("Couldn't load your applications. Make sure the backend is running.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const jobById = new Map(jobs.map((j) => [j.id, j]));
  const sorted = [...applications].sort((a, b) => {
    const aTime = a.submitted_at ? new Date(a.submitted_at).getTime() : 0;
    const bTime = b.submitted_at ? new Date(b.submitted_at).getTime() : 0;
    return bTime - aTime;
  });

  if (loading) {
    return <div className="mx-auto max-w-5xl px-6 py-16 text-ink-200">Loading…</div>;
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="font-display text-2xl font-bold text-ink-50">Applications</h1>
      <p className="mt-1 text-sm text-ink-200">
        Every job you've actually submitted, with follow-up reminders and honest response rates —
        no vanity metrics.
      </p>

      {error && <p className="mt-4 text-sm text-coral-400">{error}</p>}

      {analytics && (
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {STAT_LABEL.map(({ key, label, suffix }) => {
            const raw = analytics[key];
            const value = suffix === "%" ? Math.round(raw * 1000) / 10 : raw;
            return (
              <div key={key} className="rounded-2xl border border-ink-800 bg-ink-900/60 p-4">
                <p className="font-display text-2xl font-bold text-ink-50">
                  {value}
                  {suffix ?? ""}
                </p>
                <p className="mt-1 text-xs text-ink-400">{label}</p>
              </div>
            );
          })}
        </div>
      )}

      {analytics && analytics.needs_followup > 0 && (
        <p className="mt-4 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-300">
          {analytics.needs_followup} application{analytics.needs_followup === 1 ? "" : "s"} worth a
          follow-up — no update in 10+ days.
        </p>
      )}

      <section className="mt-8">
        <h2 className="font-display text-lg font-semibold text-ink-50">Submitted applications</h2>
        {sorted.length === 0 ? (
          <p className="mt-2 text-sm text-ink-200">
            Nothing submitted yet — move a job to "Submitted" from its detail page once you've
            actually applied.
          </p>
        ) : (
          <div className="mt-4 flex flex-col gap-3">
            {sorted.map((app) => {
              const job = jobById.get(app.job_id);
              return (
                <Link
                  key={app.id}
                  to={`/jobs/${app.job_id}`}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-ink-800 bg-ink-900/60 p-4 transition-colors hover:border-mint-500/40"
                >
                  <div>
                    <p className="font-display text-sm font-semibold text-ink-50">
                      {job?.title || "Untitled role"}
                    </p>
                    <p className="text-xs text-ink-400">{job?.company || "Unknown company"}</p>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-ink-300">
                    {app.submitted_at && (
                      <span>Submitted {new Date(app.submitted_at).toLocaleDateString()}</span>
                    )}
                    {job && (
                      <span className="rounded-full bg-ink-800 px-2 py-0.5 text-[11px] font-medium text-ink-100">
                        {job.status}
                      </span>
                    )}
                    {app.needs_followup && (
                      <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] font-medium text-amber-400">
                        Follow up
                      </span>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
