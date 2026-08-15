import type { ReviewNote } from "../lib/api";

const SEVERITY_STYLE: Record<ReviewNote["severity"], string> = {
  error: "border-coral-500/40 bg-coral-500/10 text-coral-300",
  warning: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  info: "border-ink-700 bg-ink-900 text-ink-200",
};

const SEVERITY_LABEL: Record<ReviewNote["severity"], string> = {
  error: "Possible fabrication",
  warning: "Worth a look",
  info: "Note",
};

export function ReviewNoteList({ notes }: { notes: ReviewNote[] }) {
  if (notes.length === 0) return null;
  return (
    <ul className="mt-3 flex flex-col gap-2">
      {notes.map((note, i) => (
        <li
          key={i}
          className={`rounded-xl border px-3 py-2 text-xs ${SEVERITY_STYLE[note.severity]}`}
        >
          <span className="font-semibold uppercase tracking-wide">{SEVERITY_LABEL[note.severity]}</span>
          <span className="ml-1.5">{note.message}</span>
        </li>
      ))}
    </ul>
  );
}
