import { API_BASE_URL } from "./env";
import type {
  Country,
  GoogleStatus,
  HolidayHit,
  Limits,
  Schedule,
  ScheduleInput,
} from "./types";

export interface HealthResponse {
  status: string;
  database: string;
  detail: string | null;
}

/** Why the backend refused a schedule, when it said so in a structured way. */
export type RefusalDetail =
  | { kind: "conflict"; conflicts: Schedule[] }
  | { kind: "holiday"; country: string; holidays: HolidayHit[] }
  | { kind: "duration"; durationMinutes: number; minMinutes: number; maxMinutes: number };

/** Error carrying the message the backend sent back. */
export class ApiError extends Error {
  readonly status: number;
  /** Structured reason for an HTTP 409, or null for every other error. */
  readonly detail: RefusalDetail | null;

  constructor(message: string, status: number, detail: RefusalDetail | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

interface ValidationItem {
  msg?: string;
  loc?: (string | number)[];
}

interface ConflictBody {
  code: "schedule_conflict";
  message: string;
  conflicts: Schedule[];
}

interface HolidayBody {
  code: "holiday_conflict";
  message: string;
  country: string;
  holidays: HolidayHit[];
}

interface DurationBody {
  code: "duration_out_of_range";
  message: string;
  duration_minutes: number;
  min_minutes: number;
  max_minutes: number;
}

function hasCode(detail: unknown, code: string): boolean {
  return (
    typeof detail === "object" && detail !== null && (detail as { code?: unknown }).code === code
  );
}

function isConflictBody(detail: unknown): detail is ConflictBody {
  return hasCode(detail, "schedule_conflict") && Array.isArray((detail as ConflictBody).conflicts);
}

function isHolidayBody(detail: unknown): detail is HolidayBody {
  return hasCode(detail, "holiday_conflict") && Array.isArray((detail as HolidayBody).holidays);
}

function isDurationBody(detail: unknown): detail is DurationBody {
  return (
    hasCode(detail, "duration_out_of_range") &&
    typeof (detail as DurationBody).duration_minutes === "number"
  );
}

/** Turns a FastAPI error body into an ApiError, keeping any conflict payload. */
function errorFromBody(body: unknown, status: number, fallback: string): ApiError {
  const detail =
    typeof body === "object" && body !== null && "detail" in body
      ? (body as { detail: unknown }).detail
      : undefined;

  if (isConflictBody(detail)) {
    return new ApiError(detail.message, status, {
      kind: "conflict",
      conflicts: detail.conflicts,
    });
  }
  if (isDurationBody(detail)) {
    return new ApiError(detail.message, status, {
      kind: "duration",
      durationMinutes: detail.duration_minutes,
      minMinutes: detail.min_minutes,
      maxMinutes: detail.max_minutes,
    });
  }
  if (isHolidayBody(detail)) {
    return new ApiError(detail.message, status, {
      kind: "holiday",
      country: detail.country,
      holidays: detail.holidays,
    });
  }
  if (typeof detail === "string") {
    return new ApiError(detail, status);
  }
  if (Array.isArray(detail)) {
    const messages = (detail as ValidationItem[])
      .map((item) => {
        const field = item.loc?.filter((part) => part !== "body").join(".");
        return field ? `${field}: ${item.msg ?? ""}` : (item.msg ?? "");
      })
      .filter(Boolean);
    if (messages.length > 0) return new ApiError(messages.join("; "), status);
  }
  return new ApiError(fallback, status);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: init?.body ? { "Content-Type": "application/json" } : undefined,
      ...init,
    });
  } catch {
    throw new ApiError(`Không kết nối được backend tại ${API_BASE_URL}`, 0);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw errorFromBody(body, response.status, `Yêu cầu thất bại (HTTP ${response.status})`);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const fetchHealth = (): Promise<HealthResponse> => request<HealthResponse>("/health");

export const listSchedules = (): Promise<Schedule[]> => request<Schedule[]>("/api/schedules");

export const getSchedule = (id: number): Promise<Schedule> =>
  request<Schedule>(`/api/schedules/${id}`);

export const createSchedule = (input: ScheduleInput): Promise<Schedule> =>
  request<Schedule>("/api/schedules", { method: "POST", body: JSON.stringify(input) });

export const updateSchedule = (id: number, input: ScheduleInput): Promise<Schedule> =>
  request<Schedule>(`/api/schedules/${id}`, { method: "PUT", body: JSON.stringify(input) });

export const deleteSchedule = (id: number): Promise<void> =>
  request<void>(`/api/schedules/${id}`, { method: "DELETE" });

export const listCountries = (): Promise<Country[]> => request<Country[]>("/api/countries");

export const fetchLimits = (): Promise<Limits> => request<Limits>("/api/config");

export const fetchGoogleStatus = (): Promise<GoogleStatus> =>
  request<GoogleStatus>("/api/config/google");

export const syncToGoogle = (id: number): Promise<Schedule> =>
  request<Schedule>(`/api/schedules/${id}/google`, { method: "POST" });

export const unlinkFromGoogle = (id: number): Promise<Schedule> =>
  request<Schedule>(`/api/schedules/${id}/google`, { method: "DELETE" });
