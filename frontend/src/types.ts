export interface Schedule {
  id: number;
  title: string;
  description: string | null;
  location: string | null;
  /** Naive local wall-clock time, e.g. "2026-09-01T09:00:00". */
  start_time: string;
  end_time: string;
  created_at: string;
  updated_at: string;
}

export interface ScheduleInput {
  title: string;
  description: string | null;
  location: string | null;
  start_time: string;
  end_time: string;
}
