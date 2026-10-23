import type { CSSProperties } from "react";
import type { Analysis, Job, JobStatus } from "../api.ts";
import "./jobs.css";

export interface JobListProps {
  /** Jobs to show, newest first, as delivered by GET /api/jobs. */
  jobs: Job[];
}

export const STATUS_LABELS: Record<JobStatus, string> = {
  pending: "wartend",
  running: "in Arbeit",
  done: "fertig",
  failed: "fehlgeschlagen",
};

export const ANALYSIS_LABELS: Record<Analysis, string> = {
  word_count: "Wörter zählen",
  top_words: "Häufigste Wörter",
  reading_time: "Lesezeit schätzen",
};

const PREVIEW_LENGTH = 140;

const decimal = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const integer = new Intl.NumberFormat("de-DE");
const dateTime = new Intl.DateTimeFormat("de-DE", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

export function previewText(text: string): string {
  const chars = Array.from(text);
  return chars.length > PREVIEW_LENGTH ? `${chars.slice(0, PREVIEW_LENGTH).join("")}…` : text;
}

export function formatMinutes(minutes: number): string {
  return `ca. ${decimal.format(minutes)} Min.`;
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "" : dateTime.format(date);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <span className={`badge badge--${status}`} data-testid="status-badge">
      <span className="badge__dot" aria-hidden="true" />
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

function ResultBlock({ job }: { job: Job }) {
  const result = job.result;
  if (job.status === "pending" || job.status === "running") {
    return (
      <div className="result result__muted">
        {job.status === "running" && <span className="spinner" aria-hidden="true" />} Ergebnis folgt…
      </div>
    );
  }
  if (isRecord(result)) {
    if (job.analysis === "word_count" && typeof result.words === "number") {
      return (
        <div className="result">
          Wörter: <span className="result__figure">{integer.format(result.words)}</span>
        </div>
      );
    }
    if (job.analysis === "reading_time" && typeof result.minutes === "number") {
      return (
        <div className="result">
          {formatMinutes(result.minutes)}
          {typeof result.words === "number" && (
            <span className="result__muted"> ({integer.format(result.words)} Wörter)</span>
          )}
        </div>
      );
    }
    if (job.analysis === "top_words" && Array.isArray(result.top_words)) {
      const rows = result.top_words
        .filter(
          (row): row is { word: string; count: number } =>
            isRecord(row) && typeof row.word === "string" && typeof row.count === "number",
        )
        .slice(0, 5);
      if (rows.length === 0) {
        return <div className="result result__muted">Keine Wörter gefunden.</div>;
      }
      const max = Math.max(...rows.map((r) => r.count), 1);
      return (
        <div className="result">
          <ol className="result__words" aria-label="Häufigste Wörter">
            {rows.map((row, index) => (
              <li key={`${index}-${row.word}`} className="result__word">
                <span className="result__word-name">{row.word}</span>
                <span
                  className="result__word-count"
                  style={{ "--bar": `${Math.round((row.count / max) * 100)}%` } as CSSProperties}
                >
                  {integer.format(row.count)}
                </span>
              </li>
            ))}
          </ol>
        </div>
      );
    }
  }
  return <div className="result result__muted">Kein Ergebnis verfügbar.</div>;
}

function JobCard({ job }: { job: Job }) {
  return (
    <li className="job-card" data-testid="job-card">
      <div className="job-card__head">
        <span className="job-card__id">#{job.id}</span>
        <span className="job-card__analysis">{ANALYSIS_LABELS[job.analysis] ?? job.analysis}</span>
        <StatusBadge status={job.status} />
        <time className="job-card__time" dateTime={job.created_at}>
          {formatTimestamp(job.created_at)}
        </time>
      </div>
      <p className="job-card__text">{previewText(job.text)}</p>
      <div className="job-card__foot">
        {job.status === "failed" ? (
          <div className="error-block" role="note">
            <strong>Fehler:</strong> {job.error ?? "Unbekannter Fehler"}
          </div>
        ) : (
          <ResultBlock job={job} />
        )}
      </div>
    </li>
  );
}

/** List of job cards with status badge and result or error. */
export function JobList({ jobs }: JobListProps) {
  if (jobs.length === 0) {
    return (
      <div className="empty-state">
        <svg className="empty-state__icon" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
          <path d="M4 4h16v16H4z" />
          <path d="M8 9h8M8 13h8M8 17h5" />
        </svg>
        <p className="empty-state__title">Noch keine Jobs</p>
        <p className="empty-state__hint empty-state__hint--desktop">
          Lege links einen Text an, um die erste Analyse zu starten.
        </p>
        <p className="empty-state__hint empty-state__hint--mobile">
          Lege oben einen Text an, um die erste Analyse zu starten.
        </p>
      </div>
    );
  }
  return (
    <ul className="job-list">
      {jobs.map((job) => (
        <JobCard key={job.id} job={job} />
      ))}
    </ul>
  );
}
