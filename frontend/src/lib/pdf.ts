import { jsPDF } from "jspdf";
import type { CoverLetterContent, Profile, TailoredResumeContent } from "./api";

/** Client-side PDF generation — deliberately NOT server-side.
 *
 * WeasyPrint (the original plan for HTML->PDF) needs native Cairo/Pango
 * libraries that don't reliably exist in a serverless function. Generating
 * the PDF in the browser instead sidesteps that entirely, and — just as
 * important for a resume — produces real selectable text via jsPDF's text
 * API, not a rasterized screenshot, so it stays ATS-parseable.
 */

const PAGE_WIDTH = 612; // 8.5in letter, in points
const MARGIN = 54; // 0.75in
const CONTENT_WIDTH = PAGE_WIDTH - MARGIN * 2;

function newDoc(): jsPDF {
  return new jsPDF({ unit: "pt", format: "letter" });
}

function ensureRoom(doc: jsPDF, y: number, needed: number): number {
  const pageHeight = doc.internal.pageSize.getHeight();
  if (y + needed > pageHeight - MARGIN) {
    doc.addPage();
    return MARGIN;
  }
  return y;
}

function writeParagraph(doc: jsPDF, text: string, y: number, size = 10.5, lineHeight = 14): number {
  doc.setFontSize(size);
  const lines = doc.splitTextToSize(text, CONTENT_WIDTH) as string[];
  for (const line of lines) {
    y = ensureRoom(doc, y, lineHeight);
    doc.text(line, MARGIN, y);
    y += lineHeight;
  }
  return y;
}

function writeBullet(doc: jsPDF, text: string, y: number): number {
  const size = 10;
  const lineHeight = 13;
  doc.setFontSize(size);
  const lines = doc.splitTextToSize(text, CONTENT_WIDTH - 14) as string[];
  lines.forEach((line, i) => {
    y = ensureRoom(doc, y, lineHeight);
    doc.text(i === 0 ? `•  ${line}` : `    ${line}`, MARGIN, y);
    y += lineHeight;
  });
  return y;
}

export function downloadResumePdf(resume: TailoredResumeContent, profile: Profile, jobLabel: string) {
  const doc = newDoc();
  let y = MARGIN;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text(profile.full_name || "Resume", MARGIN, y);
  y += 22;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9.5);
  const contactLine = [profile.email, profile.phone, profile.location].filter(Boolean).join("  ·  ");
  if (contactLine) {
    doc.text(contactLine, MARGIN, y);
    y += 18;
  } else {
    y += 6;
  }

  if (resume.summary) {
    doc.setFont("helvetica", "italic");
    y = writeParagraph(doc, resume.summary, y, 10.5, 14);
    doc.setFont("helvetica", "normal");
    y += 6;
  }

  if (resume.skills_highlighted?.length) {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    y = ensureRoom(doc, y, 16);
    doc.text("Skills", MARGIN, y);
    y += 14;
    doc.setFont("helvetica", "normal");
    y = writeParagraph(doc, resume.skills_highlighted.join("  ·  "), y, 10, 13);
    y += 8;
  }

  if (resume.work_history?.length) {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    y = ensureRoom(doc, y, 16);
    doc.text("Experience", MARGIN, y);
    y += 16;

    for (const role of resume.work_history) {
      y = ensureRoom(doc, y, 28);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(10.5);
      doc.text(`${role.title} — ${role.company}`, MARGIN, y);

      const dateRange = [role.start_date, role.current ? "Present" : role.end_date]
        .filter(Boolean)
        .join(" – ");
      if (dateRange) {
        doc.setFont("helvetica", "normal");
        doc.setFontSize(9.5);
        const dateWidth = doc.getTextWidth(dateRange);
        doc.text(dateRange, MARGIN + CONTENT_WIDTH - dateWidth, y);
      }
      y += 15;

      doc.setFont("helvetica", "normal");
      for (const bullet of role.bullets ?? []) {
        y = writeBullet(doc, bullet, y);
      }
      y += 8;
    }
  }

  doc.save(fileName(profile.full_name, jobLabel, "Resume"));
}

export function downloadCoverLetterPdf(letter: CoverLetterContent, profile: Profile, jobLabel: string) {
  const doc = newDoc();
  let y = MARGIN;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(10.5);
  const today = new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
  doc.text(today, MARGIN, y);
  y += 28;

  y = writeParagraph(doc, letter.greeting, y, 10.5, 16);
  y += 10;

  for (const paragraph of letter.paragraphs) {
    y = writeParagraph(doc, paragraph, y, 10.5, 15);
    y += 12;
  }

  y += 8;
  y = writeParagraph(doc, letter.closing, y, 10.5, 15);

  doc.save(fileName(profile.full_name, jobLabel, "Cover Letter"));
}

function fileName(name: string, jobLabel: string, kind: string): string {
  const safe = (s: string) => s.replace(/[^a-z0-9]+/gi, "_").replace(/^_+|_+$/g, "");
  return `${safe(name || "Candidate")}_${safe(jobLabel)}_${safe(kind)}.pdf`;
}
