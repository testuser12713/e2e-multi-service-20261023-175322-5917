import { type FormEvent, useId, useState } from "react";
import type { Analysis } from "../api.ts";
import "./jobs.css";

export interface JobFormProps {
  /** Creates the job; rejects when the API refuses it, so the form keeps its input. */
  onSubmit: (text: string, analysis: Analysis) => Promise<void>;
  /** True while a submission is in flight: the submit button is disabled. */
  submitting: boolean;
}

export const MAX_TEXT_LENGTH = 20000;

export const ANALYSIS_OPTIONS: ReadonlyArray<{ value: Analysis; label: string }> = [
  { value: "word_count", label: "Wörter zählen" },
  { value: "top_words", label: "Häufigste Wörter" },
  { value: "reading_time", label: "Lesezeit schätzen" },
];

const numberFormat = new Intl.NumberFormat("de-DE");

/** Form for a new analysis job (Text + Analyse + submit button). */
export function JobForm({ onSubmit, submitting }: JobFormProps) {
  const [text, setText] = useState("");
  const [analysis, setAnalysis] = useState<Analysis>("word_count");
  const [attempted, setAttempted] = useState(false);
  const [pending, setPending] = useState(false);
  const ids = useId();

  const busy = submitting || pending;
  const empty = text.trim() === "";
  const tooLong = text.length > MAX_TEXT_LENGTH;
  const errorText = !attempted
    ? null
    : empty
      ? "Bitte gib einen Text ein."
      : tooLong
        ? `Der Text darf höchstens ${numberFormat.format(MAX_TEXT_LENGTH)} Zeichen lang sein.`
        : null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (busy) return;
    setAttempted(true);
    if (empty || tooLong) return;
    setPending(true);
    try {
      await onSubmit(text, analysis);
      setText("");
      setAnalysis("word_count");
      setAttempted(false);
    } catch {
      // The caller shows the error; the form keeps what the user typed.
    } finally {
      setPending(false);
    }
  }

  const textId = `${ids}-text`;
  const errorId = `${ids}-error`;

  return (
    <form className="job-form" noValidate onSubmit={(e) => void handleSubmit(e)}>
      <div className="field">
        <label className="field__label" htmlFor={textId}>
          Text
        </label>
        <textarea
          id={textId}
          className={
            errorText ? "field__control field__textarea field__control--error" : "field__control field__textarea"
          }
          placeholder="Text hier einfügen…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-invalid={errorText ? true : undefined}
          aria-describedby={errorText ? errorId : undefined}
        />
        <span className={tooLong ? "field__counter field__counter--over" : "field__counter"}>
          {numberFormat.format(text.length)} / {numberFormat.format(MAX_TEXT_LENGTH)}
        </span>
        {errorText && (
          <p id={errorId} className="field-error" role="alert">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8v5M12 16h.01" />
            </svg>
            {errorText}
          </p>
        )}
      </div>
      <div className="field">
        <label className="field__label" htmlFor={`${ids}-analysis`}>
          Analyse
        </label>
        <select
          id={`${ids}-analysis`}
          className="field__control field__select"
          value={analysis}
          onChange={(e) => setAnalysis(e.target.value as Analysis)}
        >
          {ANALYSIS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <button type="submit" className="btn" disabled={busy}>
        {busy && <span className="spinner" aria-hidden="true" />}
        {busy ? "Wird gesendet…" : "Analyse starten"}
      </button>
    </form>
  );
}
