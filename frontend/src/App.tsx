import { useCallback, useEffect, useRef, useState } from "react";
import { createJob, listJobs, type Analysis, type Job } from "./api.ts";
import { JobForm } from "./components/JobForm.tsx";
import { JobList } from "./components/JobList.tsx";

/** Polling interval of the job list (SPEC AC-11). */
export const POLL_INTERVAL_MS = 3000;

/** Duration of the banner's fade-out (DESIGN.md ### ErrorBanner). */
const BANNER_FADE_MS = 200;

const BANNER_TEXT = "Verbindung zur API fehlgeschlagen. Neuer Versuch in wenigen Sekunden …";

export default function App() {
  const [jobs, setJobs] = useState<Job[]>([]);
  // True while the last poll failed; the next successful poll clears it.
  const [loadFailed, setLoadFailed] = useState(false);
  const [bannerLeaving, setBannerLeaving] = useState(false);
  const [bannerShown, setBannerShown] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const mounted = useRef(true);

  const refresh = useCallback(async (): Promise<void> => {
    try {
      const next = await listJobs();
      if (!mounted.current) return;
      // Only the jobs state changes: the form keeps its own local state.
      setJobs(next);
      setLoadFailed(false);
    } catch {
      if (!mounted.current) return;
      // Keep the last known jobs visible.
      setLoadFailed(true);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    void refresh();
    const timer = setInterval(() => {
      void refresh();
    }, POLL_INTERVAL_MS);
    return () => {
      mounted.current = false;
      clearInterval(timer);
    };
  }, [refresh]);

  // Banner visibility with a short fade-out once the API answers again.
  useEffect(() => {
    if (loadFailed) {
      setBannerShown(true);
      setBannerLeaving(false);
      return undefined;
    }
    setBannerLeaving(true);
    const timer = setTimeout(() => {
      setBannerShown(false);
      setBannerLeaving(false);
    }, BANNER_FADE_MS);
    return () => clearTimeout(timer);
  }, [loadFailed]);

  const handleSubmit = useCallback(
    async (text: string, analysis: Analysis): Promise<void> => {
      setSubmitting(true);
      try {
        const job = await createJob(text, analysis);
        if (mounted.current) {
          setJobs((previous) => [job, ...previous.filter((existing) => existing.id !== job.id)]);
        }
      } finally {
        if (mounted.current) setSubmitting(false);
      }
      // Rejections above propagate so the form keeps what the user typed.
      await refresh();
    },
    [refresh],
  );

  const offline = loadFailed;

  return (
    <div className="app">
      <header className="app-header">
        <div className="container app-header__inner">
          <div className="brand">
            <span className="brand__mark" aria-hidden="true" />
            <h1 className="brand__name">Job-Verarbeitung</h1>
          </div>
          <span className={offline ? "live-pill live-pill--offline" : "live-pill"}>
            <span className="live-pill__dot" aria-hidden="true" />
            {offline ? "Offline" : "Aktualisiert alle 3 Sekunden"}
          </span>
        </div>
      </header>

      <main className="container page">
        {bannerShown ? (
          <div
            className={bannerLeaving ? "error-banner error-banner--leaving" : "error-banner"}
            role="status"
            aria-live="polite"
          >
            <svg
              className="error-banner__icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <p className="error-banner__text">{BANNER_TEXT}</p>
          </div>
        ) : null}
        <div className="page__layout">
          <section className="card form-panel" aria-labelledby="form-title">
            <div className="card__head">
              <h2 id="form-title" className="card__title">
                Neuer Job
              </h2>
              <p className="card__subtitle">Text eingeben und Analyse wählen.</p>
            </div>
            <JobForm onSubmit={handleSubmit} submitting={submitting} />
          </section>

          <section className="list-panel" aria-labelledby="list-title">
            <div className="section-head">
              <h2 id="list-title" className="section-head__title">
                Jobs
              </h2>
              <p className="section-head__subtitle">Neueste zuerst</p>
            </div>
            <JobList jobs={jobs} />
          </section>
        </div>
      </main>
    </div>
  );
}
