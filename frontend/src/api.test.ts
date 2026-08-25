import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  createSchedule,
  deleteSchedule,
  fetchGoogleStatus,
  fetchLimits,
  listCountries,
  listSchedules,
  syncToGoogle,
  unlinkFromGoogle,
} from "./api";

const INPUT = {
  title: "Họp",
  description: null,
  location: null,
  start_time: "2026-09-01T09:00:00",
  end_time: "2026-09-01T10:00:00",
  timezone: "Asia/Tokyo",
  country: null,
  reminder_minutes: null,
};

function mockFetch(response: Response | Error) {
  const fn = vi.fn((_url: string, _init?: RequestInit) =>
    response instanceof Error ? Promise.reject(response) : Promise.resolve(response),
  );
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("parses a list response", async () => {
    mockFetch(new Response("[]", { status: 200 }));
    expect(await listSchedules()).toEqual([]);
  });

  it("sends JSON with the right content type", async () => {
    const fetchMock = mockFetch(new Response(JSON.stringify({ id: 1 }), { status: 201 }));
    await createSchedule(INPUT);
    const init = fetchMock.mock.calls[0]![1]!;
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    const sent = JSON.parse(init.body as string);
    expect(sent.title).toBe("Họp");
    // Wall clock and zone travel together; the browser does no offset maths.
    expect(sent.start_time).toBe("2026-09-01T09:00:00");
    expect(sent.timezone).toBe("Asia/Tokyo");
  });

  it("treats 204 as an empty result", async () => {
    mockFetch(new Response(null, { status: 204 }));
    await expect(deleteSchedule(1)).resolves.toBeUndefined();
  });

  it("surfaces a string detail from the backend", async () => {
    mockFetch(new Response(JSON.stringify({ detail: "Schedule not found" }), { status: 404 }));
    await expect(listSchedules()).rejects.toThrowError("Schedule not found");
  });

  it("flattens FastAPI validation details", async () => {
    const body = { detail: [{ loc: ["body", "end_time"], msg: "end_time must be after start_time" }] };
    mockFetch(new Response(JSON.stringify(body), { status: 422 }));
    await expect(createSchedule(INPUT)).rejects.toThrowError(
      "end_time: end_time must be after start_time",
    );
  });

  it("keeps the conflicting schedules from a 409 response", async () => {
    const conflict = {
      id: 3,
      title: "Họp nhóm",
      description: null,
      location: null,
      start_time: "2026-09-01T09:00:00+07:00",
      end_time: "2026-09-01T10:00:00+07:00",
      timezone: "Asia/Ho_Chi_Minh",
      country: null,
      reminder_minutes: null,
      notify_at: null,
      notified_at: null,
      reminder_status: "none",
      google_event_id: null,
      google_calendar_id: null,
      google_synced_at: null,
      google_out_of_date: false,
      created_at: "2026-08-25T08:00:00+00:00",
      updated_at: "2026-08-25T08:00:00+00:00",
    };
    const body = {
      detail: {
        code: "schedule_conflict",
        message: "Time range overlaps 1 existing schedule",
        conflicts: [conflict],
      },
    };
    mockFetch(new Response(JSON.stringify(body), { status: 409 }));

    const error = (await createSchedule(INPUT).catch((err: unknown) => err)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(409);
    expect(error.message).toBe("Time range overlaps 1 existing schedule");
    expect(error.detail).toEqual({ kind: "conflict", conflicts: [conflict] });
  });

  it("keeps the holidays from a 409 holiday response", async () => {
    const body = {
      detail: {
        code: "holiday_conflict",
        message: "VN observes 1 public holiday in this time range",
        country: "VN",
        holidays: [{ date: "2026-02-17", name: "Lunar New Year" }],
      },
    };
    mockFetch(new Response(JSON.stringify(body), { status: 409 }));

    const error = (await createSchedule(INPUT).catch((err: unknown) => err)) as ApiError;
    expect(error.status).toBe(409);
    expect(error.detail).toEqual({
      kind: "holiday",
      country: "VN",
      holidays: [{ date: "2026-02-17", name: "Lunar New Year" }],
    });
  });

  it("keeps the limits from a 422 duration response", async () => {
    const body = {
      detail: {
        code: "duration_out_of_range",
        message: "Schedule lasts 5 minutes, below the minimum of 15",
        duration_minutes: 5,
        min_minutes: 15,
        max_minutes: 10080,
      },
    };
    mockFetch(new Response(JSON.stringify(body), { status: 422 }));

    const error = (await createSchedule(INPUT).catch((err: unknown) => err)) as ApiError;
    expect(error.status).toBe(422);
    expect(error.detail).toEqual({
      kind: "duration",
      durationMinutes: 5,
      minMinutes: 15,
      maxMinutes: 10080,
    });
  });

  it("still flattens an ordinary 422 validation body", async () => {
    const body = { detail: [{ loc: ["body", "end_time"], msg: "end_time must be after start_time" }] };
    mockFetch(new Response(JSON.stringify(body), { status: 422 }));
    const error = (await createSchedule(INPUT).catch((err: unknown) => err)) as ApiError;
    expect(error.detail).toBeNull();
    expect(error.message).toContain("end_time must be after start_time");
  });

  it("fetches the Google status", async () => {
    const status = { mode: "memory", enabled: true, calendar_id: "primary", detail: null };
    mockFetch(new Response(JSON.stringify(status), { status: 200 }));
    expect(await fetchGoogleStatus()).toEqual(status);
  });

  it("posts to sync a schedule and deletes to unlink it", async () => {
    const first = mockFetch(new Response(JSON.stringify({ id: 1 }), { status: 200 }));
    await syncToGoogle(1);
    expect(first.mock.calls[0]![0]).toContain("/api/schedules/1/google");
    expect(first.mock.calls[0]![1]?.method).toBe("POST");

    const second = mockFetch(new Response(JSON.stringify({ id: 1 }), { status: 200 }));
    await unlinkFromGoogle(1);
    expect(second.mock.calls[0]![1]?.method).toBe("DELETE");
  });

  it("surfaces a 503 when the integration is off", async () => {
    mockFetch(new Response(JSON.stringify({ detail: "Google Calendar integration is disabled." }), { status: 503 }));
    const error = (await syncToGoogle(1).catch((err: unknown) => err)) as ApiError;
    expect(error.status).toBe(503);
    expect(error.message).toContain("disabled");
  });

  it("fetches the duration limits", async () => {
    const limits = { min_duration_minutes: 15, max_duration_minutes: 10080, default_timezone: "UTC" };
    mockFetch(new Response(JSON.stringify(limits), { status: 200 }));
    expect(await fetchLimits()).toEqual(limits);
  });

  it("keeps the reason a daylight-saving jump gave for refusing a time", async () => {
    const body = {
      detail: [
        {
          type: "nonexistent_local_time",
          loc: ["body", "start_time"],
          msg: "2026-03-08T02:30:00 does not exist in America/New_York",
          ctx: {
            timezone: "America/New_York",
            local_time: "2026-03-08T02:30:00",
            gap_minutes: 60,
            next_valid: "2026-03-08T03:30:00",
          },
        },
      ],
    };
    mockFetch(new Response(JSON.stringify(body), { status: 422 }));
    const error = (await createSchedule(INPUT).catch((e) => e)) as ApiError;
    expect(error.detail).toEqual({
      kind: "nonexistentTime",
      field: "start_time",
      timezone: "America/New_York",
      localTime: "2026-03-08T02:30:00",
      gapMinutes: 60,
      nextValid: "2026-03-08T03:30:00",
    });
  });

  it("falls back to the plain message when that reason has no context", async () => {
    const body = { detail: [{ type: "nonexistent_local_time", loc: ["body"], msg: "nope" }] };
    mockFetch(new Response(JSON.stringify(body), { status: 422 }));
    const error = (await createSchedule(INPUT).catch((e) => e)) as ApiError;
    expect(error.detail).toBeNull();
    expect(error.message).toBe("nope");
  });

  it("leaves the detail empty for other errors", async () => {
    mockFetch(new Response(JSON.stringify({ detail: "Schedule not found" }), { status: 404 }));
    const error = (await listSchedules().catch((err: unknown) => err)) as ApiError;
    expect(error.detail).toBeNull();
  });

  it("fetches the country list", async () => {
    const countries = [{ code: "VN", name: "Vietnam" }];
    mockFetch(new Response(JSON.stringify(countries), { status: 200 }));
    expect(await listCountries()).toEqual(countries);
  });

  it("reports an unreachable backend instead of throwing a raw fetch error", async () => {
    mockFetch(new TypeError("Failed to fetch"));
    const error = await listSchedules().catch((err: unknown) => err);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(0);
    expect((error as ApiError).message).toContain("Không kết nối được backend");
  });
});
