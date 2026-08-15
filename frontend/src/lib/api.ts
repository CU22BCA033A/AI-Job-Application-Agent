const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${options?.method ?? "GET"} ${path} failed (${res.status}): ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---------- Types (mirrors backend/app/schemas.py) ----------

export interface WorkHistoryItem {
  company: string;
  title: string;
  location: string;
  start_date: string;
  end_date: string;
  current: boolean;
  bullets: string[];
  skills_used: string[];
}

export interface EducationItem {
  institution: string;
  degree: string;
  field: string;
  start_date: string;
  end_date: string;
  gpa: string;
  notes: string;
}

export interface SkillItem {
  name: string;
  category: string;
  proficiency: string;
}

export interface ProjectItem {
  name: string;
  description: string;
  bullets: string[];
  technologies: string[];
  url: string;
}

export interface AchievementItem {
  title: string;
  description: string;
  metric: string;
  date: string;
}

export interface Profile {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  location: string;
  links: Record<string, string>;
  summary: string;
  work_history: WorkHistoryItem[];
  education: EducationItem[];
  skills: SkillItem[];
  projects: ProjectItem[];
  achievements: AchievementItem[];
  raw_resume_text: string | null;
  created_at: string;
  updated_at: string;
}

export type JobStatus =
  | "new"
  | "evaluated"
  | "drafting"
  | "ready"
  | "submitted"
  | "interviewing"
  | "closed";

export type FitRecommendation = "tailor_and_apply" | "stretch_tailor_carefully" | "skip";

export interface Job {
  id: string;
  source_url: string | null;
  raw_text: string;
  title: string;
  company: string;
  location: string;
  salary_range: string | null;
  requirements: string[];
  keywords: string[];
  status: JobStatus;
  fit_score: number | null;
  fit_reasoning: string | null;
  fit_strengths: string[];
  fit_gaps: string[];
  fit_recommendation: FitRecommendation | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

// ---------- API calls ----------

export const api = {
  getProfile: () => request<Profile>("/api/profile"),
  updateProfile: (payload: Partial<Profile>) =>
    request<Profile>("/api/profile", { method: "PUT", body: JSON.stringify(payload) }),
  importResume: (resume_text: string) =>
    request<{ profile: Partial<Profile>; notes: string[] }>("/api/profile/import", {
      method: "POST",
      body: JSON.stringify({ resume_text }),
    }),
  importResumePdf: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/api/profile/import/pdf`, { method: "POST", body: formData });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `Upload failed (${res.status}).`);
    }
    return res.json() as Promise<{ profile: Partial<Profile>; notes: string[] }>;
  },

  listJobs: () => request<Job[]>("/api/jobs"),
  getJob: (id: string) => request<Job>(`/api/jobs/${id}`),
  createJob: (raw_text: string, source_url?: string) =>
    request<Job>("/api/jobs", { method: "POST", body: JSON.stringify({ raw_text, source_url }) }),
  evaluateJob: (id: string) => request<Job>(`/api/jobs/${id}/evaluate`, { method: "POST" }),
  updateJobStatus: (id: string, status: JobStatus) =>
    request<Job>(`/api/jobs/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
  updateJobNotes: (id: string, notes: string) =>
    request<Job>(`/api/jobs/${id}/notes`, { method: "PATCH", body: JSON.stringify({ notes }) }),
  deleteJob: (id: string) => request<void>(`/api/jobs/${id}`, { method: "DELETE" }),
};
