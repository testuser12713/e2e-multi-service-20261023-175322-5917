import type { Job } from "../api.ts";

export interface JobListProps {
  /** Jobs to show, newest first, as delivered by GET /api/jobs. */
  jobs: Job[];
}

/**
 * List of job cards with status badge and result or error.
 *
 * Skeleton: the cards, the empty state and the result rendering are built by
 * the job list ticket; until then this slot shows a placeholder.
 */
export function JobList(props: JobListProps) {
  return (
    <div className="slot-placeholder" data-job-count={props.jobs.length}>
      Die Jobliste erscheint hier.
    </div>
  );
}
