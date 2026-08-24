/**
 * Regressions found while reviewing the app (Round 9), exercised through the
 * real entry point with fetch stubbed out.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

function shell() {
  document.body.innerHTML = `
    <div id="app">
      <header><span id="count"></span><label><span id="timezone"></span></label>
      <button id="create" type="button">Tạo lịch</button></header>
      <div id="error" hidden></div>
      <main><section id="list"></section><section id="panel"></section></main>
    </div>`;
}

const json = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }));

/** A backend that answers every startup call. */
function workingBackend(schedules: unknown[] = []) {
  return vi.fn((url: string) => {
    if (url.includes("/api/countries")) return json([{ code: "VN", name: "Vietnam" }]);
    if (url.includes("/api/config/google"))
      return json({ mode: "disabled", enabled: false, calendar_id: "primary", detail: "off" });
    if (url.includes("/api/config"))
      return json({ min_duration_minutes: 15, max_duration_minutes: 10080, default_timezone: "UTC" });
    return json(schedules);
  });
}

async function settle(ms = 150) {
  await new Promise((r) => setTimeout(r, ms));
}

beforeEach(() => {
  vi.resetModules();
  shell();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("a failed initial load", () => {
  it("does not leave the list stuck on the loading placeholder", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))));
    await import("./main");
    await settle();

    const list = document.querySelector("#list")!;
    expect(list.textContent).not.toContain("Đang tải");
    expect(list.textContent).toContain("Chưa có lịch nào");
  });

  it("still explains what went wrong", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))));
    await import("./main");
    await settle();

    const error = document.querySelector<HTMLElement>("#error")!;
    expect(error.hidden).toBe(false);
    expect(error.textContent).toContain("Không kết nối được backend");
  });
});

describe("a response that is not JSON", () => {
  it("blames the address instead of leaking a parser error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response("<!doctype html><html></html>", { status: 200 }))),
    );
    await import("./main");
    await settle();

    const error = document.querySelector<HTMLElement>("#error")!;
    expect(error.textContent).toContain("VITE_API_BASE_URL");
    expect(error.textContent).not.toContain("SyntaxError");
  });
});

describe("the normal startup path still works", () => {
  it("loads the list, the countries, the limits and the Google status", async () => {
    const schedule = {
      id: 1,
      title: "Họp nhóm",
      description: null,
      location: null,
      start_time: "2026-09-01T09:00:00+07:00",
      end_time: "2026-09-01T10:00:00+07:00",
      timezone: "Asia/Saigon",
      country: null,
      reminder_minutes: null,
      notify_at: null,
      notified_at: null,
      google_event_id: null,
      google_calendar_id: null,
      google_synced_at: null,
      google_out_of_date: false,
      created_at: "2026-08-25T00:00:00+00:00",
      updated_at: "2026-08-25T00:00:00+00:00",
    };
    vi.stubGlobal("fetch", workingBackend([schedule]));
    await import("./main");
    await settle();

    expect(document.querySelector<HTMLElement>("#error")!.hidden).toBe(true);
    expect(document.querySelector("#list")!.textContent).toContain("Họp nhóm");
    expect(document.querySelector("#count")!.textContent).toBe("1 lịch");

    // The form is populated from what the backend served, not from constants.
    document.querySelector<HTMLButtonElement>("#create")!.click();
    const form = document.querySelector("#panel")!.querySelector("form")!;
    expect(form.querySelectorAll("select")[2]!.options.length).toBe(2); // "none" + Vietnam
    expect(
      [...form.querySelectorAll(".field__hint")].some((n) =>
        n.textContent?.includes("Thời lượng từ 15 phút đến 7 ngày"),
      ),
    ).toBe(true);
  });

  it("blocks a schedule that is too short before making a request", async () => {
    const fetchMock = workingBackend([]);
    vi.stubGlobal("fetch", fetchMock);
    await import("./main");
    await settle();

    const callsBefore = fetchMock.mock.calls.length;
    document.querySelector<HTMLButtonElement>("#create")!.click();
    const form = document.querySelector("#panel")!.querySelector("form")!;
    const inputs = form.querySelectorAll<HTMLInputElement>("input");
    inputs[0]!.value = "Quá ngắn";
    inputs[1]!.value = "2026-09-01T09:00";
    inputs[1]!.dispatchEvent(new Event("change"));
    inputs[2]!.value = "2026-09-01T09:05";
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    await settle();

    expect(document.querySelector("#error")!.textContent).toContain("Lịch quá ngắn");
    expect(fetchMock.mock.calls.length).toBe(callsBefore); // nothing was sent
  });
});
