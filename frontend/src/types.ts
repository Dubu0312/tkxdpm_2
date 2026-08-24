export interface Schedule {
  id: number;
  title: string;
  description: string | null;
  location: string | null;
  /** ISO-8601 with an explicit offset, in the schedule's own timezone. */
  start_time: string;
  end_time: string;
  /** IANA timezone the schedule was entered in, e.g. "Asia/Tokyo". */
  timezone: string;
  /** ISO-8601 in UTC. */
  created_at: string;
  updated_at: string;
}

export interface ScheduleInput {
  title: string;
  description: string | null;
  location: string | null;
  /** Naive wall-clock time ("2026-09-01T09:00"), read by the API in `timezone`. */
  start_time: string;
  end_time: string;
  timezone: string;
}
