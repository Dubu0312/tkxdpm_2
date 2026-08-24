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
  /** ISO 3166-1 alpha-2 country whose public holidays apply; null = no check. */
  country: string | null;
  /** Minutes before the start to remind; null = no reminder. */
  reminder_minutes: number | null;
  /** Instant the reminder fires, in the schedule's own timezone; null if none. */
  notify_at: string | null;
  /** When the reminder was delivered (UTC); null while still pending. */
  notified_at: string | null;
  /** Linked Google Calendar event; null when the schedule has never been synced. */
  google_event_id: string | null;
  google_calendar_id: string | null;
  google_synced_at: string | null;
  /** True when the schedule changed after its last successful push to Google. */
  google_out_of_date: boolean;
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
  country: string | null;
  reminder_minutes: number | null;
}

/** A country the backend can check public holidays for. */
export interface Country {
  code: string;
  name: string;
}

/** One official holiday a rejected schedule would have fallen on. */
export interface HolidayHit {
  /** Calendar day, "2026-02-17". */
  date: string;
  name: string;
}

/** Rules served by the backend so the frontend does not hard-code them. */
export interface Limits {
  min_duration_minutes: number;
  max_duration_minutes: number;
  default_timezone: string;
}

/** Whether Google Calendar syncing is available, and how. */
export interface GoogleStatus {
  mode: string;
  enabled: boolean;
  calendar_id: string;
  detail: string | null;
}
