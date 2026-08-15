import { motion } from "framer-motion";
import type { Profile, TailoredResumeContent } from "../lib/api";

function normalize(text: string): string {
  return text.trim().toLowerCase().replace(/\s+/g, " ");
}

function findBaseRole(base: Profile["work_history"], company: string, title: string) {
  return base.find(
    (r) => normalize(r.company) === normalize(company) && normalize(r.title) === normalize(title),
  );
}

/** Side-by-side comparison of your real resume vs the tailored draft.
 *
 * Not a full word-level diff — bullets are compared whole. A tailored
 * bullet that doesn't exactly match one of your real bullets is marked as
 * reworded/emphasized (mint highlight); this is a readability aid, not a
 * fabrication check — that's the Reviewer's job, shown separately.
 */
export function ResumeDiff({ base, tailored }: { base: Profile; tailored: TailoredResumeContent }) {
  return (
    <div className="flex flex-col gap-6">
      {tailored.work_history.map((role, i) => {
        const baseRole = findBaseRole(base.work_history, role.company, role.title);
        const baseBullets = baseRole?.bullets ?? [];
        const baseSet = new Set(baseBullets.map(normalize));

        return (
          <div key={i} className="rounded-2xl border border-ink-800 bg-ink-950 p-4">
            <p className="font-display text-sm font-semibold text-ink-50">
              {role.title} · {role.company}
            </p>
            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-400">
                  Your real resume
                </p>
                {baseBullets.length === 0 ? (
                  <p className="text-xs text-ink-400 italic">No matching role found in your profile.</p>
                ) : (
                  <ul className="flex flex-col gap-1.5 text-sm text-ink-200">
                    {baseBullets.map((b, bi) => (
                      <li key={bi} className="leading-snug">
                        {b}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-400">
                  Tailored for this job
                </p>
                <ul className="flex flex-col gap-1.5 text-sm">
                  {role.bullets.map((b, bi) => {
                    const changed = !baseSet.has(normalize(b));
                    return (
                      <motion.li
                        key={bi}
                        initial={{ opacity: 0, x: 6 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: bi * 0.05, duration: 0.25 }}
                        className={`leading-snug ${
                          changed
                            ? "rounded-md border-l-2 border-mint-500 bg-mint-500/10 py-1 pl-2 text-ink-50"
                            : "text-ink-200"
                        }`}
                      >
                        {b}
                      </motion.li>
                    );
                  })}
                </ul>
              </div>
            </div>
          </div>
        );
      })}
      <div className="flex items-center gap-2 text-xs text-ink-400">
        <span className="inline-block h-2 w-2 rounded-full bg-mint-500" />
        Reworded or re-emphasized from your real bullets — not new content.
      </div>
    </div>
  );
}
