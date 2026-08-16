import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  api,
  type Application,
  type CoverLetterContent,
  type GeneratedDocument,
  type InterviewPrep,
  type Job,
  type JobStatus,
  type Profile,
  type TailoredResumeContent,
} from "../lib/api";
import { FitScoreRing } from "../components/FitScoreRing";
import { EvaluationProgress, DRAFTING_STEPS, INTERVIEW_PREP_STEPS } from "../components/EvaluationProgress";
import { ResumeDiff } from "../components/ResumeDiff";
import { ReviewNoteList } from "../components/ReviewNoteList";
import { downloadCoverLetterPdf, downloadResumePdf } from "../lib/pdf";

const STATUS_LABEL: Record<JobStatus, string> = {
  new: "New",
  evaluated: "Evaluated",
  drafting: "Drafting",
  ready: "Ready",
  submitted: "Submitted",
  interviewing: "Interviewing",
  closed: "Closed",
};

const STATUS_ORDER: JobStatus[] = [
  "new",
  "evaluated",
  "drafting",
  "ready",
  "submitted",
  "interviewing",
  "closed",
];

function latestByType(docs: GeneratedDocument[]) {
  const map: Partial<Record<GeneratedDocument["doc_type"], GeneratedDocument>> = {};
  for (const doc of docs) {
    const current = map[doc.doc_type];
    if (!current || doc.version > current.version) map[doc.doc_type] = doc;
  }
  return map;
}

export function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [documents, setDocuments] = useState<GeneratedDocument[]>([]);
  const [application, setApplication] = useState<Application | null>(null);
  const [interviewPrep, setInterviewPrep] = useState<InterviewPrep | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [generating, setGenerating] = useState(false);
  const [preppingInterview, setPreppingInterview] = useState(false);
  const [editingResume, setEditingResume] = useState(false);
  const [resumeDraft, setResumeDraft] = useState<TailoredResumeContent | null>(null);
  const [coverLetterDraft, setCoverLetterDraft] = useState<CoverLetterContent | null>(null);
  const [appNotesDraft, setAppNotesDraft] = useState("");

  async function loadAll() {
    if (!id) return;
    try {
      const [jobData, profileData, docsData, appData, prepData] = await Promise.all([
        api.getJob(id),
        api.getProfile(),
        api.listDocuments(id),
        api.getApplication(id),
        api.getInterviewPrep(id),
      ]);
      setJob(jobData);
      setProfile(profileData);
      setDocuments(docsData);
      setApplication(appData);
      setAppNotesDraft(appData?.notes ?? "");
      setInterviewPrep(prepData);
      setError(null);
    } catch {
      setError("Couldn't load this job. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setLoading(true);
    setEditingResume(false);
    setResumeDraft(null);
    setCoverLetterDraft(null);
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (loading) {
    return <div className="mx-auto max-w-4xl px-6 py-16 text-ink-200">Loading…</div>;
  }
  if (error || !job) {
    return <div className="mx-auto max-w-4xl px-6 py-16 text-coral-400">{error ?? "Job not found."}</div>;
  }

  const docsByType = latestByType(documents);
  const resumeDoc = docsByType.resume;
  const coverLetterDoc = docsByType.cover_letter;
  const resumeContent = resumeDoc?.content as TailoredResumeContent | undefined;
  const coverLetterContent = coverLetterDoc?.content as CoverLetterContent | undefined;

  async function handleGenerate() {
    if (!id) return;
    setGenerating(true);
    setError(null);
    try {
      const docs = await api.generateDocuments(id);
      setDocuments((prev) => [...prev, ...docs]);
      setJob((prev) => (prev ? { ...prev, status: "drafting" } : prev));
      setEditingResume(false);
      setResumeDraft(null);
      setCoverLetterDraft(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't generate drafts. Mind trying again?");
    } finally {
      setGenerating(false);
    }
  }

  async function handleApprove(doc: GeneratedDocument) {
    const updated = await api.updateDocument(doc.id, { status: "approved" });
    setDocuments((prev) => [...prev.filter((d) => d.id !== updated.id), updated]);
    const refreshedJob = await api.getJob(id!);
    setJob(refreshedJob);
  }

  function startEditingResume() {
    if (resumeContent) setResumeDraft(structuredClone(resumeContent));
    setEditingResume(true);
  }

  async function saveResumeEdits() {
    if (!resumeDoc || !resumeDraft) return;
    const updated = await api.updateDocument(resumeDoc.id, { content: resumeDraft });
    setDocuments((prev) => [...prev.filter((d) => d.id !== updated.id), updated]);
    setEditingResume(false);
  }

  async function saveCoverLetterEdits() {
    if (!coverLetterDoc || !coverLetterDraft) return;
    const updated = await api.updateDocument(coverLetterDoc.id, { content: coverLetterDraft });
    setDocuments((prev) => [...prev.filter((d) => d.id !== updated.id), updated]);
  }

  async function handleStatusChange(status: JobStatus) {
    const updated = await api.updateJobStatus(id!, status);
    setJob(updated);
    if (status === "submitted") {
      const app = await api.getApplication(id!);
      setApplication(app);
    }
  }

  async function handleGenerateInterviewPrep() {
    if (!id) return;
    setPreppingInterview(true);
    setError(null);
    try {
      const prep = await api.generateInterviewPrep(id);
      setInterviewPrep(prep);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't generate interview prep.");
    } finally {
      setPreppingInterview(false);
    }
  }

  async function saveAppNotes() {
    if (!id) return;
    const updated = await api.updateApplicationNotes(id, appNotesDraft);
    setApplication(updated);
  }

  async function handleMarkFollowedUp() {
    if (!id) return;
    const updated = await api.markFollowedUp(id);
    setApplication(updated);
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <Link to="/jobs" className="text-sm text-ink-400 hover:text-ink-100">
        ← Back to pipeline
      </Link>

      {/* ---------- Overview ---------- */}
      <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-ink-50">{job.title || "Untitled role"}</h1>
          <p className="text-ink-200">
            {job.company || "Unknown company"}
            {job.location ? ` · ${job.location}` : ""}
          </p>
        </div>
        <select
          value={job.status}
          onChange={(e) => handleStatusChange(e.target.value as JobStatus)}
          className="rounded-full border border-ink-700 bg-ink-900 px-4 py-2 text-sm text-ink-50 focus:border-mint-500 focus:outline-none"
        >
          {STATUS_ORDER.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABEL[s]}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="mt-4 text-sm text-coral-400">{error}</p>}

      {/* ---------- Fit ---------- */}
      {job.fit_score !== null && (
        <section className="mt-6 flex flex-col items-start gap-6 rounded-3xl border border-ink-800 bg-ink-900/60 p-6 sm:flex-row">
          <FitScoreRing score={job.fit_score} />
          <div className="flex-1">
            <p className="text-sm text-ink-200">{job.fit_reasoning}</p>
            {job.fit_strengths.length > 0 && (
              <p className="mt-2 text-xs text-mint-400">
                <span className="font-semibold uppercase tracking-wide">Strengths </span>
                {job.fit_strengths.join(" · ")}
              </p>
            )}
            {job.fit_gaps.length > 0 && (
              <p className="mt-1 text-xs text-amber-400">
                <span className="font-semibold uppercase tracking-wide">Gaps </span>
                {job.fit_gaps.join(" · ")}
              </p>
            )}
          </div>
        </section>
      )}

      {/* ---------- Drafting ---------- */}
      <section className="mt-6 rounded-3xl border border-ink-800 bg-ink-900/60 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-display text-lg font-semibold text-ink-50">Tailored documents</h2>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="rounded-full bg-coral-500 px-5 py-2 text-sm font-semibold text-ink-950 transition-transform hover:scale-105 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {generating ? "Drafting…" : resumeDoc ? "Regenerate drafts" : "Generate drafts"}
          </button>
        </div>

        <AnimatePresence mode="wait">
          {generating && (
            <motion.div key="progress" exit={{ opacity: 0 }}>
              <EvaluationProgress steps={DRAFTING_STEPS} />
            </motion.div>
          )}
        </AnimatePresence>

        {!generating && !resumeDoc && (
          <p className="mt-3 text-sm text-ink-200">
            Nothing drafted yet — hit "Generate drafts" and Vrutti will tailor your resume and write a
            cover letter for this job, using only what's in your profile.
          </p>
        )}

        {!generating && resumeContent && profile && (
          <div className="mt-5 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-ink-100">
                Resume
                {resumeDoc!.status === "approved" && (
                  <span className="ml-2 rounded-full bg-mint-500/15 px-2 py-0.5 text-[11px] font-medium text-mint-400">
                    Approved
                  </span>
                )}
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={() => (editingResume ? saveResumeEdits() : startEditingResume())}
                  className="rounded-full border border-ink-700 px-3 py-1.5 text-xs font-medium text-ink-100 hover:border-mint-500 hover:text-mint-400"
                >
                  {editingResume ? "Save edits" : "Edit"}
                </button>
                <button
                  onClick={() => downloadResumePdf(resumeContent, profile, job.title || job.company)}
                  className="rounded-full border border-ink-700 px-3 py-1.5 text-xs font-medium text-ink-100 hover:border-mint-500 hover:text-mint-400"
                >
                  Download PDF
                </button>
                <button
                  onClick={() => handleApprove(resumeDoc!)}
                  disabled={resumeDoc!.status === "approved"}
                  className="rounded-full bg-mint-500 px-3 py-1.5 text-xs font-semibold text-ink-950 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Approve
                </button>
              </div>
            </div>

            {editingResume && resumeDraft ? (
              <div className="flex flex-col gap-3 rounded-2xl border border-ink-800 bg-ink-950 p-4">
                <label className="text-xs font-semibold uppercase tracking-wide text-ink-400">Summary</label>
                <textarea
                  value={resumeDraft.summary}
                  onChange={(e) => setResumeDraft({ ...resumeDraft, summary: e.target.value })}
                  rows={3}
                  className="rounded-xl border border-ink-700 bg-ink-900 p-3 text-sm text-ink-50 focus:border-mint-500 focus:outline-none"
                />
                <label className="text-xs font-semibold uppercase tracking-wide text-ink-400">
                  Skills (comma-separated)
                </label>
                <input
                  value={resumeDraft.skills_highlighted.join(", ")}
                  onChange={(e) =>
                    setResumeDraft({
                      ...resumeDraft,
                      skills_highlighted: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  className="rounded-xl border border-ink-700 bg-ink-900 p-3 text-sm text-ink-50 focus:border-mint-500 focus:outline-none"
                />
                {resumeDraft.work_history.map((role, i) => (
                  <div key={i}>
                    <label className="text-xs font-semibold uppercase tracking-wide text-ink-400">
                      {role.title} · {role.company} — bullets (one per line)
                    </label>
                    <textarea
                      value={role.bullets.join("\n")}
                      onChange={(e) => {
                        const bullets = e.target.value.split("\n");
                        const next = { ...resumeDraft };
                        next.work_history = next.work_history.map((r, ri) =>
                          ri === i ? { ...r, bullets } : r,
                        );
                        setResumeDraft(next);
                      }}
                      rows={Math.max(3, role.bullets.length)}
                      className="mt-1 w-full rounded-xl border border-ink-700 bg-ink-900 p-3 text-sm text-ink-50 focus:border-mint-500 focus:outline-none"
                    />
                  </div>
                ))}
              </div>
            ) : (
              <ResumeDiff base={profile} tailored={resumeContent} />
            )}

            <ReviewNoteList notes={resumeDoc!.review_notes} />
          </div>
        )}

        {!generating && coverLetterContent && profile && (
          <div className="mt-6 flex flex-col gap-4 border-t border-ink-800 pt-6">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-ink-100">
                Cover letter
                {coverLetterDoc!.status === "approved" && (
                  <span className="ml-2 rounded-full bg-mint-500/15 px-2 py-0.5 text-[11px] font-medium text-mint-400">
                    Approved
                  </span>
                )}
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={() => downloadCoverLetterPdf(coverLetterContent, profile, job.title || job.company)}
                  className="rounded-full border border-ink-700 px-3 py-1.5 text-xs font-medium text-ink-100 hover:border-mint-500 hover:text-mint-400"
                >
                  Download PDF
                </button>
                <button
                  onClick={() => handleApprove(coverLetterDoc!)}
                  disabled={coverLetterDoc!.status === "approved"}
                  className="rounded-full bg-mint-500 px-3 py-1.5 text-xs font-semibold text-ink-950 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Approve
                </button>
              </div>
            </div>
            <div className="rounded-2xl border border-ink-800 bg-ink-950 p-4">
              <input
                value={(coverLetterDraft ?? coverLetterContent).greeting}
                onChange={(e) =>
                  setCoverLetterDraft({ ...(coverLetterDraft ?? coverLetterContent), greeting: e.target.value })
                }
                onBlur={saveCoverLetterEdits}
                className="w-full bg-transparent text-sm font-medium text-ink-50 focus:outline-none"
              />
              <textarea
                value={(coverLetterDraft ?? coverLetterContent).paragraphs.join("\n\n")}
                onChange={(e) =>
                  setCoverLetterDraft({
                    ...(coverLetterDraft ?? coverLetterContent),
                    paragraphs: e.target.value.split(/\n\n+/),
                  })
                }
                onBlur={saveCoverLetterEdits}
                rows={10}
                className="mt-3 w-full resize-y rounded-xl border border-ink-700 bg-ink-900 p-3 text-sm leading-relaxed text-ink-100 focus:border-mint-500 focus:outline-none"
              />
              <input
                value={(coverLetterDraft ?? coverLetterContent).closing}
                onChange={(e) =>
                  setCoverLetterDraft({ ...(coverLetterDraft ?? coverLetterContent), closing: e.target.value })
                }
                onBlur={saveCoverLetterEdits}
                className="mt-3 w-full bg-transparent text-sm font-medium text-ink-50 focus:outline-none"
              />
            </div>
            <ReviewNoteList notes={coverLetterDoc!.review_notes} />
          </div>
        )}
      </section>

      {/* ---------- Interview prep ---------- */}
      <section className="mt-6 rounded-3xl border border-ink-800 bg-ink-900/60 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-display text-lg font-semibold text-ink-50">Interview prep</h2>
          <button
            onClick={handleGenerateInterviewPrep}
            disabled={preppingInterview}
            className="rounded-full border border-ink-700 px-5 py-2 text-sm font-semibold text-ink-100 transition-colors hover:border-mint-500 hover:text-mint-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {preppingInterview ? "Preparing…" : interviewPrep ? "Regenerate" : "Generate prep"}
          </button>
        </div>

        <AnimatePresence mode="wait">
          {preppingInterview && (
            <motion.div key="prep-progress" exit={{ opacity: 0 }}>
              <EvaluationProgress steps={INTERVIEW_PREP_STEPS} />
            </motion.div>
          )}
        </AnimatePresence>

        {!preppingInterview && !interviewPrep && (
          <p className="mt-3 text-sm text-ink-200">
            Generate a likely question bank and STAR-format stories built from your real achievements.
          </p>
        )}

        {!preppingInterview && interviewPrep && (
          <div className="mt-5 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-400">
                Likely questions
              </h3>
              <ul className="mt-2 flex flex-col gap-3">
                {interviewPrep.questions.map((q, i) => (
                  <li key={i} className="rounded-xl border border-ink-800 bg-ink-950 p-3 text-sm">
                    <p className="text-ink-50">{q.question}</p>
                    <p className="mt-1 text-xs text-ink-400">
                      {q.category} — {q.why_likely}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-400">Story bank</h3>
              <ul className="mt-2 flex flex-col gap-3">
                {interviewPrep.story_bank.map((s, i) => (
                  <li key={i} className="rounded-xl border border-ink-800 bg-ink-950 p-3 text-sm">
                    <p className="font-medium text-ink-50">{s.title}</p>
                    <p className="mt-1 text-xs text-ink-400">
                      grounded in: {s.grounded_in}
                    </p>
                    <dl className="mt-2 space-y-1 text-xs text-ink-200">
                      <div><dt className="inline font-semibold text-ink-100">S: </dt><dd className="inline">{s.situation}</dd></div>
                      <div><dt className="inline font-semibold text-ink-100">T: </dt><dd className="inline">{s.task}</dd></div>
                      <div><dt className="inline font-semibold text-ink-100">A: </dt><dd className="inline">{s.action}</dd></div>
                      <div><dt className="inline font-semibold text-ink-100">R: </dt><dd className="inline">{s.result}</dd></div>
                    </dl>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </section>

      {/* ---------- Application tracking ---------- */}
      {job.status === "submitted" || job.status === "interviewing" || job.status === "closed" || application ? (
        <section className="mt-6 rounded-3xl border border-ink-800 bg-ink-900/60 p-6">
          <h2 className="font-display text-lg font-semibold text-ink-50">Application</h2>
          {application?.submitted_at && (
            <p className="mt-1 text-sm text-ink-200">
              Submitted {new Date(application.submitted_at).toLocaleDateString()}
              {application.needs_followup && (
                <span className="ml-2 rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] font-medium text-amber-400">
                  Worth a follow-up — no update in 10+ days
                </span>
              )}
            </p>
          )}
          <textarea
            value={appNotesDraft}
            onChange={(e) => setAppNotesDraft(e.target.value)}
            onBlur={saveAppNotes}
            placeholder="Recruiter contact, interview notes, anything worth remembering…"
            rows={3}
            className="mt-3 w-full resize-y rounded-xl border border-ink-700 bg-ink-950 p-3 text-sm text-ink-50 placeholder:text-ink-400 focus:border-mint-500 focus:outline-none"
          />
          {application?.submitted_at && (
            <button
              onClick={handleMarkFollowedUp}
              className="mt-3 rounded-full border border-ink-700 px-4 py-2 text-xs font-semibold text-ink-100 hover:border-mint-500 hover:text-mint-400"
            >
              Mark as followed up today
            </button>
          )}
        </section>
      ) : null}
    </div>
  );
}
