import "@testing-library/jest-dom/vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Analysis, Job, JobStatus } from "./api.ts";

vi.mock("./api.ts", () => ({
  listJobs: vi.fn(),
  createJob: vi.fn(),
}));

// The real form and list belong to another ticket; these doubles expose only
// what App hands them (jobs, onSubmit, submitting).
vi.mock("./components/JobList.tsx", () => ({
  JobList: ({ jobs }: { jobs: Job[] }) => (
    <ul aria-label="jobs">
      {jobs.map((job) => (
        <li key={job.id}>{`#${job.id} ${job.status}`}</li>
      ))}
    </ul>
  ),
}));
vi.mock("./components/JobForm.tsx", () => ({
  JobForm: ({
    onSubmit,
    submitting,
  }: {
    onSubmit: (text: string, analysis: Analysis) => Promise<void>;
    submitting: boolean;
  }) => (
    <button
      type="button"
      disabled={submitting}
      onClick={() => {
        onSubmit("hello world", "word_count").catch(() => undefined);
      }}
    >
      Senden
    </button>
  ),
}));

const api = await import("./api.ts");
const { default: App } = await import("./App.tsx");
const listJobs = vi.mocked(api.listJobs);
const createJob = vi.mocked(api.createJob);

function job(id: number, status: JobStatus): Job {
  return {
    id,
    text: "hello world",
    analysis: "word_count",
    status,
    result: status === "done" ? { words: 2 } : null,
    error: null,
    created_at: "2026-01-01T12:00:00Z",
    updated_at: "2026-01-01T12:00:00Z",
  };
}

async function flush(): Promise<void> {
  await act(async () => {
    await Promise.resolve();
  });
}

async function tick(ms: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

beforeEach(() => {
  vi.useFakeTimers();
  listJobs.mockReset();
  createJob.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("App", () => {
  it("renders the shell", async () => {
    listJobs.mockResolvedValue([]);
    render(<App />);
    await flush();
    expect(screen.getByRole("heading", { level: 1, name: "Job-Verarbeitung" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Neuer Job" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Jobs" })).toBeInTheDocument();
  });

  it("loads on mount and polls every 3 seconds, stopping on unmount", async () => {
    listJobs.mockResolvedValue([]);
    const { unmount } = render(<App />);
    await flush();
    expect(listJobs).toHaveBeenCalledTimes(1);
    await tick(2999);
    expect(listJobs).toHaveBeenCalledTimes(1);
    await tick(1);
    expect(listJobs).toHaveBeenCalledTimes(2);
    await tick(3000);
    expect(listJobs).toHaveBeenCalledTimes(3);
    unmount();
    await tick(9000);
    expect(listJobs).toHaveBeenCalledTimes(3);
  });

  it("shows status progression pending -> running -> done across polls", async () => {
    listJobs
      .mockResolvedValueOnce([job(1, "pending")])
      .mockResolvedValueOnce([job(1, "running")])
      .mockResolvedValue([job(1, "done")]);
    render(<App />);
    await flush();
    expect(screen.getByText("#1 pending")).toBeInTheDocument();
    await tick(3000);
    expect(screen.getByText("#1 running")).toBeInTheDocument();
    await tick(3000);
    expect(screen.getByText("#1 done")).toBeInTheDocument();
  });

  it("shows a notice on failure, keeps the last jobs and recovers", async () => {
    listJobs
      .mockResolvedValueOnce([job(1, "pending")])
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValue([job(1, "done")]);
    render(<App />);
    await flush();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    await tick(3000);
    expect(screen.getByRole("status")).toHaveTextContent("Verbindung zur API fehlgeschlagen");
    expect(screen.getByText("Offline")).toBeInTheDocument();
    expect(screen.getByText("#1 pending")).toBeInTheDocument();

    await tick(3000);
    expect(screen.getByText("#1 done")).toBeInTheDocument();
    await tick(300);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.getByText("Aktualisiert alle 3 Sekunden")).toBeInTheDocument();
  });

  it("creates a job, disables the form while in flight and refreshes immediately", async () => {
    listJobs.mockResolvedValueOnce([]).mockResolvedValue([job(7, "pending")]);
    let resolveCreate: (value: Job) => void = () => undefined;
    createJob.mockImplementation(
      () =>
        new Promise<Job>((resolve) => {
          resolveCreate = resolve;
        }),
    );
    render(<App />);
    await flush();
    expect(listJobs).toHaveBeenCalledTimes(1);

    const button = screen.getByRole("button", { name: "Senden" });
    fireEvent.click(button);
    await flush();
    expect(createJob).toHaveBeenCalledWith("hello world", "word_count");
    expect(button).toBeDisabled();

    await act(async () => {
      resolveCreate(job(7, "pending"));
      await Promise.resolve();
    });
    await flush();
    expect(listJobs).toHaveBeenCalledTimes(2);
    expect(button).toBeEnabled();
    expect(screen.getByText("#7 pending")).toBeInTheDocument();
  });
});
