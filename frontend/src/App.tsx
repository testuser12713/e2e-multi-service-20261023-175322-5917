import { useCallback, useState } from "react";
import { createJob, type Analysis, type Job } from "./api.ts";
import { JobForm } from "./components/JobForm.tsx";
import { JobList } from "./components/JobList.tsx";

function errorMessage(err: unknown): string {
  return err instanceof Error && err.message !== "" ? err.message : "Unbekannter Fehler";
}

export default function App() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = useCallback(async (text: string, analysis: Analysis): Promise<void> => {
    setSubmitting(true);
    try {
      const job = await createJob(text, analysis);
      setJobs((previous) => [job, ...previous.filter((existing) => existing.id !== job.id)]);
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
      // Rethrown so the form keeps what the user typed.
      throw err;
    } finally {
      setSubmitting(false);
    }
  }, []);

  const offline = error !== null;

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
