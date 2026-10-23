import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Job } from "../api.ts";
import { JobList } from "./JobList.tsx";

function job(overrides: Partial<Job>): Job {
  return {
    id: 1,
    text: "Ein Text",
    analysis: "word_count",
    status: "pending",
    result: null,
    error: null,
    created_at: "2026-01-01T12:00:00Z",
    updated_at: "2026-01-01T12:00:00Z",
    ...overrides,
  };
}

describe("JobList", () => {
  it("shows the empty state", () => {
    render(<JobList jobs={[]} />);
    expect(screen.getByText("Noch keine Jobs")).toBeInTheDocument();
  });

  it("renders every status label", () => {
    render(
      <JobList
        jobs={[
          job({ id: 1, status: "pending" }),
          job({ id: 2, status: "running" }),
          job({ id: 3, status: "done", result: { words: 2 } }),
          job({ id: 4, status: "failed", error: "Kaputt" }),
        ]}
      />,
    );
    const labels = screen.getAllByTestId("status-badge").map((b) => b.textContent);
    expect(labels).toEqual(["wartend", "in Arbeit", "fertig", "fehlgeschlagen"]);
    expect(screen.getByText("#1")).toBeInTheDocument();
    expect(screen.getByText("Kaputt")).toBeInTheDocument();
  });

  it("renders each result form", () => {
    render(
      <JobList
        jobs={[
          job({ id: 1, status: "done", result: { words: 42 } }),
          job({ id: 2, status: "done", analysis: "reading_time", result: { minutes: 1.2, words: 240 } }),
          job({
            id: 3,
            status: "done",
            analysis: "top_words",
            result: { top_words: [{ word: "hallo", count: 3 }, { word: "welt", count: 1 }] },
          }),
        ]}
      />,
    );
    const cards = screen.getAllByTestId("job-card");
    expect(cards[0]).toHaveTextContent("Wörter: 42");
    expect(cards[1]).toHaveTextContent("ca. 1,2 Min.");
    expect(cards[2]).toHaveTextContent("hallo");
    expect(cards[2]).toHaveTextContent("welt");
    expect(cards[2].querySelectorAll("li")).toHaveLength(2);
  });

  it("shortens long text", () => {
    render(<JobList jobs={[job({ text: "a".repeat(300) })]} />);
    expect(screen.getByText(`${"a".repeat(140)}…`)).toBeInTheDocument();
  });

  it("renders script text as plain text", () => {
    const evil = "<script>window.x=1</script><img src=x onerror=alert(1)>";
    const { container } = render(
      <JobList jobs={[job({ text: evil, status: "failed", error: "<b>bad</b>" })]} />,
    );
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("b")).toBeNull();
    expect(screen.getByText(evil)).toBeInTheDocument();
  });
});
