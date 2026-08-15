import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api, type Profile } from "../lib/api";

const EMPTY_PROFILE: Profile = {
  id: "",
  full_name: "",
  email: "",
  phone: "",
  location: "",
  links: {},
  summary: "",
  work_history: [],
  education: [],
  skills: [],
  projects: [],
  achievements: [],
  raw_resume_text: null,
  created_at: "",
  updated_at: "",
};

export function ProfilePage() {
  const [profile, setProfile] = useState<Profile>(EMPTY_PROFILE);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [resumeText, setResumeText] = useState("");
  const [importing, setImporting] = useState(false);
  const [importNotes, setImportNotes] = useState<string[]>([]);

  useEffect(() => {
    api
      .getProfile()
      .then(setProfile)
      .catch(() =>
        setError("Couldn't reach the backend. Make sure the API is running locally."),
      )
      .finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const saved = await api.updateProfile(profile);
      setProfile(saved);
      setSavedAt(Date.now());
    } catch {
      setError("Couldn't save your profile just now. Mind trying again?");
    } finally {
      setSaving(false);
    }
  }

  async function handleImport() {
    if (!resumeText.trim()) return;
    setImporting(true);
    setError(null);
    try {
      const { profile: parsed, notes } = await api.importResume(resumeText.trim());
      setProfile((prev) => ({ ...prev, ...parsed }));
      setImportNotes(notes);
    } catch {
      setError("Couldn't parse that resume text. You can still fill things in by hand below.");
    } finally {
      setImporting(false);
    }
  }

  if (loading) {
    return <div className="mx-auto max-w-3xl px-6 py-16 text-ink-200">Loading your profile…</div>;
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="font-display text-2xl font-bold text-ink-50">Your profile</h1>
      <p className="mt-1 text-sm text-ink-200">
        This is the only truth Vrutti draws from. Everything tailored later — bullets, cover
        letters, story banks — comes from what you put here, nothing more.
      </p>

      <section className="mt-6 rounded-3xl border border-ink-800 bg-ink-900/60 p-6">
        <h2 className="font-display text-lg font-semibold text-ink-50">Import from a resume</h2>
        <p className="mt-1 text-sm text-ink-200">
          Paste your existing resume text and Vrutti will draft a structured profile for you to
          review — nothing is saved until you hit "Save profile" below.
        </p>
        <textarea
          value={resumeText}
          onChange={(e) => setResumeText(e.target.value)}
          rows={6}
          placeholder="Paste your resume text here…"
          className="mt-3 w-full resize-y rounded-2xl border border-ink-700 bg-ink-950 p-4 text-sm text-ink-50 placeholder:text-ink-400 focus:border-mint-500 focus:outline-none"
        />
        <button
          onClick={handleImport}
          disabled={importing || !resumeText.trim()}
          className="mt-3 rounded-full border border-ink-700 px-5 py-2 text-sm font-semibold text-ink-100 transition-colors hover:border-mint-500 hover:text-mint-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {importing ? "Reading it…" : "Parse into profile"}
        </button>
        {importNotes.length > 0 && (
          <div className="mt-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-300">
            <p className="font-semibold">Worth double-checking:</p>
            <ul className="mt-1 list-inside list-disc">
              {importNotes.map((note, i) => (
                <li key={i}>{note}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <section className="mt-6 rounded-3xl border border-ink-800 bg-ink-900/60 p-6">
        <h2 className="font-display text-lg font-semibold text-ink-50">Basics</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Full name" value={profile.full_name} onChange={(v) => setProfile({ ...profile, full_name: v })} />
          <Field label="Email" value={profile.email} onChange={(v) => setProfile({ ...profile, email: v })} />
          <Field label="Phone" value={profile.phone} onChange={(v) => setProfile({ ...profile, phone: v })} />
          <Field label="Location" value={profile.location} onChange={(v) => setProfile({ ...profile, location: v })} />
        </div>
        <div className="mt-4">
          <label className="text-xs font-semibold uppercase tracking-wide text-ink-400">
            Summary
          </label>
          <textarea
            value={profile.summary}
            onChange={(e) => setProfile({ ...profile, summary: e.target.value })}
            rows={3}
            className="mt-1 w-full resize-y rounded-xl border border-ink-700 bg-ink-950 p-3 text-sm text-ink-50 focus:border-mint-500 focus:outline-none"
          />
        </div>

        <p className="mt-6 text-xs text-ink-400">
          Work history, education, skills, projects, and achievements have real structure behind
          the scenes already (visible via the API) — a dedicated editor for adding and reordering
          entries is coming next. For now the fastest way to fill those in is the resume import
          above, then refine here.
        </p>

        {profile.work_history.length > 0 && (
          <div className="mt-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-400">
              Work history ({profile.work_history.length})
            </p>
            <ul className="mt-2 space-y-2">
              {profile.work_history.map((w, i) => (
                <li key={i} className="rounded-xl border border-ink-800 bg-ink-950 p-3 text-sm">
                  <p className="font-medium text-ink-50">
                    {w.title} · {w.company}
                  </p>
                  <ul className="mt-1 list-inside list-disc text-ink-200">
                    {w.bullets.map((b, bi) => (
                      <li key={bi}>{b}</li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {error && <p className="mt-4 text-sm text-coral-400">{error}</p>}

      <div className="mt-6 flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-full bg-coral-500 px-6 py-2.5 text-sm font-semibold text-ink-950 transition-transform hover:scale-105 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save profile"}
        </button>
        {savedAt && (
          <motion.span
            key={savedAt}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-sm text-mint-400"
          >
            Saved.
          </motion.span>
        )}
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label className="text-xs font-semibold uppercase tracking-wide text-ink-400">{label}</label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-xl border border-ink-700 bg-ink-950 p-3 text-sm text-ink-50 focus:border-mint-500 focus:outline-none"
      />
    </div>
  );
}
