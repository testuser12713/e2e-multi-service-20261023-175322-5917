import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App.tsx";

describe("App", () => {
  it("renders the product heading", () => {
    render(<App />);

    expect(screen.getByRole("heading", { level: 1, name: "Job-Verarbeitung" })).toBeInTheDocument();
  });

  it("renders the form slot and the list slot of the layout", () => {
    render(<App />);

    expect(screen.getByRole("region", { name: "Neuer Job" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Jobs" })).toBeInTheDocument();
  });
});
