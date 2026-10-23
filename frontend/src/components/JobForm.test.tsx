import "@testing-library/jest-dom/vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { JobForm } from "./JobForm.tsx";

describe("JobForm", () => {
  it("shows no validation error initially and offers the three analyses", () => {
    render(<JobForm onSubmit={vi.fn()} submitting={false} />);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    const options = screen.getAllByRole("option").map((o) => o.textContent);
    expect(options).toEqual(["Wörter zählen", "Häufigste Wörter", "Lesezeit schätzen"]);
  });

  it("shows a message on empty submit and calls nothing", async () => {
    const onSubmit = vi.fn();
    render(<JobForm onSubmit={onSubmit} submitting={false} />);
    await userEvent.type(screen.getByLabelText("Text"), "   ");
    await userEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("alert")).toHaveTextContent("Bitte gib einen Text ein.");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits text and analysis, then clears the form", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<JobForm onSubmit={onSubmit} submitting={false} />);
    await userEvent.type(screen.getByLabelText("Text"), "Hallo Welt");
    await userEvent.selectOptions(screen.getByLabelText("Analyse"), "top_words");
    await userEvent.click(screen.getByRole("button"));
    expect(onSubmit).toHaveBeenCalledWith("Hallo Welt", "top_words");
    await waitFor(() => expect(screen.getByLabelText("Text")).toHaveValue(""));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("keeps the text when submitting fails", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("nope"));
    render(<JobForm onSubmit={onSubmit} submitting={false} />);
    await userEvent.type(screen.getByLabelText("Text"), "Bleibt");
    await userEvent.click(screen.getByRole("button"));
    await waitFor(() => expect(screen.getByRole("button")).toBeEnabled());
    expect(screen.getByLabelText("Text")).toHaveValue("Bleibt");
  });

  it("disables the button while submitting", async () => {
    let resolve: () => void = () => {};
    const onSubmit = vi.fn(() => new Promise<void>((r) => (resolve = r)));
    const { rerender } = render(<JobForm onSubmit={onSubmit} submitting={true} />);
    expect(screen.getByRole("button")).toBeDisabled();
    rerender(<JobForm onSubmit={onSubmit} submitting={false} />);
    await userEvent.type(screen.getByLabelText("Text"), "x");
    await userEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("button")).toBeDisabled();
    expect(screen.getByRole("button")).toHaveTextContent("Wird gesendet…");
    resolve();
    await waitFor(() => expect(screen.getByRole("button")).toBeEnabled());
  });
});
