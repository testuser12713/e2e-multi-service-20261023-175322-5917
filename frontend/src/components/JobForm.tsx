import type { Analysis } from "../api.ts";

export interface JobFormProps {
  /** Creates the job; rejects when the API refuses it, so the form keeps its input. */
  onSubmit: (text: string, analysis: Analysis) => Promise<void>;
  /** True while a submission is in flight: the submit button is disabled. */
  submitting: boolean;
}

/**
 * Form for a new analysis job (Text + Analyse + submit button).
 *
 * Skeleton: the fields and their validation are built by the job form ticket;
 * until then this slot shows a placeholder and offers no control.
 */
export function JobForm(props: JobFormProps) {
  return (
    <div className="slot-placeholder" aria-busy={props.submitting}>
      Das Formular zum Anlegen eines Jobs erscheint hier.
    </div>
  );
}
