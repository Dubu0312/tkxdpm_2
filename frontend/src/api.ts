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

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface ValidationItem {
  msg?: string;
  loc?: (string | number)[];
}

function messageFromBody(body: unknown, fallback: string): string {
  if (typeof body !== "object" || body === null || !("detail" in body)) {
    return fallback;
  }
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = (detail as ValidationItem[])
      .map((item) => {
        const field = item.loc?.filter((part) => part !== "body").join(".");
        return field ? `${field}: ${item.msg ?? ""}` : (item.msg ?? "");
      })
      .filter(Boolean);
    if (messages.length > 0) return messages.join("; ");
  }
  return fallback;
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
    throw new ApiError(
      messageFromBody(body, `Yêu cầu thất bại (HTTP ${response.status})`),
      response.status,
    );
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
