// API client for the job service. Types follow the sprint's shared contract.

export type JobStatus = "pending" | "running" | "done" | "failed";

export type Analysis = "word_count" | "top_words" | "reading_time";

export interface Job {
  id: number;
  text: string;
  analysis: Analysis;
  status: JobStatus;
  result: unknown | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

/** Thrown for every answer outside 2xx; carries the API's short error message. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string | null;

  constructor(status: number, code: string | null, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

/**
 * Base URL of the API, without a trailing slash. VITE_API_BASE_URL is set by
 * the start contract; without it requests go to the page's own origin.
 */
export function apiBaseUrl(): string {
  const raw: unknown = import.meta.env.VITE_API_BASE_URL;
  if (typeof raw !== "string") {
    return "";
  }
  return raw.trim().replace(/\/+$/, "");
}

interface ErrorBody {
  error?: { code?: unknown; message?: unknown };
}

async function toApiError(response: Response): Promise<ApiError> {
  const fallback = `Anfrage fehlgeschlagen (HTTP ${response.status})`;
  try {
    const body = (await response.json()) as ErrorBody;
    const code = typeof body.error?.code === "string" ? body.error.code : null;
    const message =
      typeof body.error?.message === "string" && body.error.message.trim() !== ""
        ? body.error.message
        : fallback;
    return new ApiError(response.status, code, message);
  } catch {
    // Not JSON (a proxy page, an empty body): keep the status only.
    return new ApiError(response.status, null, fallback);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  const response = await fetch(`${apiBaseUrl()}${path}`, { ...init, headers });
  if (!response.ok) {
    throw await toApiError(response);
  }
  return (await response.json()) as T;
}

/** GET /api/jobs: all jobs, newest first. */
export function listJobs(): Promise<Job[]> {
  return request<Job[]>("/api/jobs");
}

/** POST /api/jobs: creates a job and returns it (status 'pending'). */
export function createJob(text: string, analysis: Analysis): Promise<Job> {
  return request<Job>("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, analysis }),
  });
}
