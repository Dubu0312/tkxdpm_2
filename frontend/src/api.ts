import { API_BASE_URL } from "./env";
import type { Schedule, ScheduleInput } from "./types";

export interface HealthResponse {
  status: string;
  database: string;
  detail: string | null;
}

/** Error carrying the message the backend sent back. */
export class ApiError extends Error {
  readonly status: number;
  /** Schedules the rejected time range overlaps (HTTP 409 only). */
  readonly conflicts: Schedule[];

  constructor(message: string, status: number, conflicts: Schedule[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.conflicts = conflicts;
  }
}

interface ValidationItem {
  msg?: string;
  loc?: (string | number)[];
}

interface ConflictDetail {
  code: "schedule_conflict";
  message: string;
  conflicts: Schedule[];
}

function isConflictDetail(detail: unknown): detail is ConflictDetail {
  return (
    typeof detail === "object" &&
    detail !== null &&
    (detail as { code?: unknown }).code === "schedule_conflict" &&
    Array.isArray((detail as { conflicts?: unknown }).conflicts)
  );
}

/** Turns a FastAPI error body into an ApiError, keeping any conflict payload. */
function errorFromBody(body: unknown, status: number, fallback: string): ApiError {
  const detail =
    typeof body === "object" && body !== null && "detail" in body
      ? (body as { detail: unknown }).detail
      : undefined;

  if (isConflictDetail(detail)) {
    return new ApiError(detail.message, status, detail.conflicts);
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
