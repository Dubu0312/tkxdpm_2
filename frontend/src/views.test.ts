import { describe, expect, it, vi } from "vitest";

import type { Schedule } from "./types";
import { ApiError } from "./api";
import { setTimezoneAliases } from "./format";
import {
  countryLabel,
  countrySelect,
  friendlyMessage,
  renderSkeleton,
  renderToast,
  googleSummary,
  reminderSelect,
  reminderSummary,
  renderDetail,
  renderError,
  renderForm,
  renderList,
  timezoneSelect,
} from "./views";

const TOKYO = "Asia/Tokyo";
const SAIGON = "Asia/Ho_Chi_Minh";

// The zone-naming table the backend serves at startup; without it the views
// would read "Asia/Saigon" and "Asia/Ho_Chi_Minh" as two different places.
setTimezoneAliases({ "Asia/Saigon": SAIGON });

/** The value of a detail fact row, looked up by its label. */
function fact(panel: HTMLElement, label: string): string | null {
  const terms = [...panel.querySelectorAll("dt")];
  const index = terms.findIndex((dt) => dt.textContent === label);
  return index === -1 ? null : ([...panel.querySelectorAll("dd")][index]?.textContent ?? null);
}

/** Text of every badge chip in a panel. */
function badges(panel: HTMLElement): string[] {
  return [...panel.querySelectorAll(".panel__badges .badge")].map((b) => b.textContent ?? "");
}

function schedule(overrides: Partial<Schedule> = {}): Schedule {
  return {
    id: 1,
    title: "Họp nhóm",
    description: "Review sprint",
    location: "Phòng A1",
    start_time: "2026-09-01T09:00:00+09:00",
    end_time: "2026-09-01T10:30:00+09:00",
    timezone: TOKYO,
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
    ...overrides,
  };
}

describe("renderList", () => {
  it("shows an empty state when there is nothing to list", () => {
    const node = renderList([], null, () => {}, TOKYO);
    expect(node.querySelector(".empty")?.textContent).toContain("Chưa có lịch nào");
    expect(node.querySelectorAll(".card")).toHaveLength(0);
  });

  it("groups cards by day", () => {
    const node = renderList(
      [
        schedule({ id: 1 }),
        schedule({ id: 2, start_time: "2026-09-01T14:00:00", end_time: "2026-09-01T15:00:00" }),
        schedule({ id: 3, start_time: "2026-09-02T09:00:00", end_time: "2026-09-02T10:00:00" }),
      ],
      null,
      () => {},
      TOKYO,
    );
    expect(node.querySelectorAll(".day")).toHaveLength(2);
    expect(node.querySelectorAll(".card")).toHaveLength(3);
  });

  it("marks the selected card and reports clicks", () => {
    const onSelect = vi.fn();
    const node = renderList([schedule({ id: 7 })], 7, onSelect, TOKYO);
    const card = node.querySelector<HTMLButtonElement>(".card")!;
    expect(card.classList.contains("card--active")).toBe(true);
    card.click();
    expect(onSelect).toHaveBeenCalledWith(7);
  });

  it("renders titles as text, not markup", () => {
    const node = renderList([schedule({ title: "<img src=x onerror=alert(1)>" })], null, () => {}, TOKYO);
    expect(node.querySelector("img")).toBeNull();
    expect(node.querySelector(".card__title")?.textContent).toBe("<img src=x onerror=alert(1)>");
  });
});

describe("renderDetail", () => {
  it("shows the schedule fields and wires the actions", () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const node = renderDetail(schedule(), { onEdit, onDelete }, TOKYO);

    expect(node.querySelector("h2")?.textContent).toBe("Họp nhóm");
    expect(node.querySelector(".panel__when")?.textContent).toContain("09:00 – 10:30");
    expect(node.querySelector(".panel__duration")?.textContent).toContain("1 giờ 30 phút");
    expect(node.textContent).toContain("Phòng A1");
    expect(node.textContent).toContain("Review sprint");

    const [edit, remove] = [...node.querySelectorAll<HTMLButtonElement>(".actions .btn")];
    edit!.click();
    remove!.click();
    expect(onEdit).toHaveBeenCalledOnce();
    expect(onDelete).toHaveBeenCalledOnce();
  });

  it("leaves out rows for fields that are empty", () => {
    const node = renderDetail(
      schedule({ location: null, description: null }),
      { onEdit: () => {}, onDelete: () => {} },
      TOKYO,
    );
    expect(fact(node, "Địa điểm")).toBeNull();
    expect(fact(node, "Mô tả")).toBeNull();
    expect(fact(node, "Tạo lúc")).not.toBeNull();
  });

  it("keeps the rows for fields that have a value", () => {
    const node = renderDetail(schedule(), { onEdit: () => {}, onDelete: () => {} }, TOKYO);
    expect(fact(node, "Địa điểm")).toBe("Phòng A1");
    expect(fact(node, "Mô tả")).toBe("Review sprint");
  });
});

describe("renderForm", () => {
  it("prefills the fields when editing", () => {
    const form = renderForm(schedule(), { onSubmit: () => {}, onCancel: () => {} });
    const inputs = form.querySelectorAll<HTMLInputElement>("input");
    expect(form.querySelector("h2")?.textContent).toBe("Chỉnh sửa lịch");
    expect(inputs[0]!.value).toBe("Họp nhóm");
    expect(inputs[1]!.value).toBe("2026-09-01T09:00");
    expect(inputs[2]!.value).toBe("2026-09-01T10:30");
    expect(form.querySelectorAll("select")[0]!.value).toBe(TOKYO);
  });

  it("starts blank with default times when creating", () => {
    const form = renderForm(null, { onSubmit: () => {}, onCancel: () => {} });
    expect(form.querySelector("h2")?.textContent).toBe("Tạo lịch mới");
    expect(form.querySelectorAll<HTMLInputElement>("input")[0]!.value).toBe("");
  });

  it("emits trimmed values and nulls for blank optional fields", () => {
    const onSubmit = vi.fn();
    const form = renderForm(schedule({ location: "", description: "" }), {
      onSubmit,
      onCancel: () => {},
    });
    const inputs = form.querySelectorAll<HTMLInputElement>("input");
    inputs[0]!.value = "  Tiêu đề mới  ";
    form.dispatchEvent(new Event("submit", { cancelable: true }));

    expect(onSubmit).toHaveBeenCalledWith({
      title: "Tiêu đề mới",
      description: null,
      location: null,
      start_time: "2026-09-01T09:00",
      end_time: "2026-09-01T10:30",
      timezone: TOKYO,
      country: null,
      reminder_minutes: null,
    });
  });

  it("cancels without submitting", () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();
    const form = renderForm(null, { onSubmit, onCancel });
    form.querySelectorAll<HTMLButtonElement>(".actions .btn")[1]!.click();
    expect(onCancel).toHaveBeenCalledOnce();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

describe("renderError", () => {
  it("shows a plain message when there is no conflict payload", () => {
    const node = renderError(new ApiError("Không kết nối được backend", 0), TOKYO);
    expect(node.querySelector(".error__text")?.textContent).toBe("Không kết nối được backend");
    expect(node.querySelector(".error__list")).toBeNull();
  });

  it("lists the conflicting schedule with its time range", () => {
    const node = renderError(new ApiError("overlap", 409, { kind: "conflict", conflicts: [schedule()] }), TOKYO);
    expect(node.querySelector(".error__text")?.textContent).toContain("trùng với một lịch đã có");

    const items = [...node.querySelectorAll(".error__list li")];
    expect(items).toHaveLength(1);
    expect(items[0]!.textContent).toContain("Họp nhóm");
    expect(items[0]!.textContent).toContain("09:00 – 10:30");
    expect(node.querySelector(".error__hint")?.textContent).toContain(
      "bắt đầu đúng lúc lịch khác kết thúc",
    );
  });

  it("counts multiple conflicts", () => {
    const node = renderError(
      new ApiError("overlap", 409, {
        kind: "conflict",
        conflicts: [schedule({ id: 1 }), schedule({ id: 2, title: "Lịch thứ hai" })],
      }),
      TOKYO,
    );
    expect(node.querySelector(".error__text")?.textContent).toContain("2 lịch đã có");
    expect(node.querySelectorAll(".error__list li")).toHaveLength(2);
  });

  it("renders conflict titles as text, not markup", () => {
    const node = renderError(new ApiError("overlap", 409, { kind: "conflict", conflicts: [schedule({ title: "<b>x</b>" })] }), TOKYO);
    expect(node.querySelector("b")).toBeNull();
  });
});

describe("renderForm draft", () => {
  it("restores a rejected submission instead of the stored values", () => {
    const draft = {
      title: "Tiêu đề đang nhập",
      description: "ghi chú",
      location: "Phòng B",
      start_time: "2026-09-05T14:00",
      end_time: "2026-09-05T15:00",
      timezone: SAIGON,
      country: "VN",
      reminder_minutes: 30,
    };
    const form = renderForm(schedule(), { onSubmit: () => {}, onCancel: () => {} }, draft);
    const inputs = form.querySelectorAll<HTMLInputElement>("input");
    expect(inputs[0]!.value).toBe("Tiêu đề đang nhập");
    expect(inputs[1]!.value).toBe("2026-09-05T14:00");
    expect(inputs[2]!.value).toBe("2026-09-05T15:00");
    expect(inputs[3]!.value).toBe("Phòng B");
    expect(form.querySelector("textarea")!.value).toBe("ghi chú");
    expect(form.querySelectorAll("select")[0]!.value).toBe(SAIGON);
  });

  it("falls back to the stored schedule when there is no draft", () => {
    const form = renderForm(schedule(), { onSubmit: () => {}, onCancel: () => {} }, null);
    expect(form.querySelectorAll<HTMLInputElement>("input")[0]!.value).toBe("Họp nhóm");
  });
});

describe("viewing schedules in another timezone", () => {
  it("shows the same instant as a different wall clock in the list", () => {
    const inTokyo = renderList([schedule()], null, () => {}, TOKYO);
    expect(inTokyo.querySelector(".card__time")?.textContent).toBe("09:00 – 10:30");

    const inSaigon = renderList([schedule()], null, () => {}, SAIGON);
    expect(inSaigon.querySelector(".card__time")?.textContent).toBe("07:00 – 08:30");
  });

  it("groups by the day the schedule falls on in the view timezone", () => {
    // 09:00 Tokyo is still 31/08 in New York.
    const list = renderList([schedule()], null, () => {}, "America/New_York");
    expect(list.querySelector(".day")?.textContent).toContain("31/08/2026");
  });

  it("names the schedule's own timezone on the card only when it differs", () => {
    const sameZone = renderList([schedule({ location: null })], null, () => {}, TOKYO);
    expect(sameZone.querySelector(".card__meta")).toBeNull();

    const otherZone = renderList([schedule({ location: null })], null, () => {}, SAIGON);
    expect(otherZone.querySelector(".card__meta")?.textContent).toBe(TOKYO);
  });

  it("treats an alias of the view timezone as the same zone", () => {
    const saigonSchedule = schedule({
      timezone: "Asia/Ho_Chi_Minh",
      start_time: "2026-09-01T09:00:00+07:00",
      end_time: "2026-09-01T10:00:00+07:00",
      location: null,
    });
    const node = renderDetail(saigonSchedule, { onEdit: () => {}, onDelete: () => {} }, "Asia/Saigon");
    expect(node.querySelector(".panel__origin")).toBeNull();

    const list = renderList([saigonSchedule], null, () => {}, "Asia/Saigon");
    expect(list.querySelector(".card__meta")).toBeNull();
  });

  it("shows the original wall clock in the detail panel when zones differ", () => {
    const handlers = { onEdit: () => {}, onDelete: () => {} };

    const inTokyo = renderDetail(schedule(), handlers, TOKYO);
    expect(inTokyo.querySelector(".panel__when")?.textContent).toContain("09:00 – 10:30");
    expect(inTokyo.querySelector(".panel__origin")).toBeNull();

    const inSaigon = renderDetail(schedule(), handlers, SAIGON);
    expect(inSaigon.querySelector(".panel__when")?.textContent).toContain("07:00 – 08:30");
    const origin = inSaigon.querySelector(".panel__origin")?.textContent ?? "";
    expect(origin).toContain(TOKYO);
    expect(origin).toContain("09:00 – 10:30");
  });

  it("keeps the real duration and the offset label in the detail panel", () => {
    const inSaigon = renderDetail(schedule(), { onEdit: () => {}, onDelete: () => {} }, SAIGON);
    const line = inSaigon.querySelector(".panel__duration")?.textContent ?? "";
    expect(line).toContain("1 giờ 30 phút");
    expect(line).toContain("UTC+07:00");
  });

  it("renders conflicting schedules in the view timezone", () => {
    const node = renderError(new ApiError("overlap", 409, { kind: "conflict", conflicts: [schedule()] }), SAIGON);
    expect(node.querySelector(".error__list li")?.textContent).toContain("07:00 – 08:30");
  });
});

describe("timezoneSelect", () => {
  it("preselects the given zone", () => {
    const select = timezoneSelect(TOKYO);
    expect(select.value).toBe(TOKYO);
    expect(select.options.length).toBeGreaterThan(5);
  });

  it("keeps a zone the runtime does not list selectable", () => {
    const select = timezoneSelect("Mars/Olympus");
    expect(select.value).toBe("Mars/Olympus");
  });

  it("defaults a new schedule's form to the view timezone", () => {
    const form = renderForm(null, { onSubmit: () => {}, onCancel: () => {} }, null, SAIGON);
    expect(form.querySelectorAll("select")[0]!.value).toBe(SAIGON);
  });
});

const COUNTRIES = [
  { code: "JP", name: "Japan" },
  { code: "US", name: "United States" },
  { code: "VN", name: "Vietnam" },
];

describe("country selection", () => {
  it("offers an explicit no-country option first", () => {
    const select = countrySelect(COUNTRIES, null);
    expect(select.value).toBe("");
    expect(select.options[0]!.textContent).toContain("Không kiểm tra ngày nghỉ");
    expect(select.options.length).toBe(COUNTRIES.length + 1);
  });

  it("preselects the schedule's country", () => {
    expect(countrySelect(COUNTRIES, "VN").value).toBe("VN");
  });

  it("labels a country by name, falling back to the bare code", () => {
    expect(countryLabel("VN", COUNTRIES)).toBe("Vietnam (VN)");
    expect(countryLabel("VN", [])).toBe("VN");
  });

  it("puts the country in the submitted values", () => {
    const onSubmit = vi.fn();
    const form = renderForm(
      schedule({ country: "US" }),
      { onSubmit, onCancel: () => {} },
      null,
      TOKYO,
      COUNTRIES,
    );
    expect(form.querySelectorAll<HTMLSelectElement>("select")[2]!.value).toBe("US");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    expect(onSubmit.mock.calls[0]![0].country).toBe("US");
  });

  it("submits null when no country is chosen", () => {
    const onSubmit = vi.fn();
    const form = renderForm(schedule(), { onSubmit, onCancel: () => {} }, null, TOKYO, COUNTRIES);
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    expect(onSubmit.mock.calls[0]![0].country).toBeNull();
  });

  it("shows the country as a chip in the detail panel", () => {
    const handlers = { onEdit: () => {}, onDelete: () => {} };
    const withCountry = renderDetail(schedule({ country: "VN" }), handlers, TOKYO, COUNTRIES);
    expect(badges(withCountry)).toContain("Vietnam (VN)");

    const without = renderDetail(schedule(), handlers, TOKYO, COUNTRIES);
    expect(badges(without)).not.toContain("Vietnam (VN)");
  });
});

describe("renderError for holidays", () => {
  const holidayError = (holidays: { date: string; name: string }[]) =>
    new ApiError("holiday", 409, { kind: "holiday", country: "VN", holidays });

  it("names the holiday, its date and the country", () => {
    const node = renderError(
      holidayError([{ date: "2026-02-17", name: "Lunar New Year" }]),
      TOKYO,
      COUNTRIES,
    );
    expect(node.querySelector(".error__text")?.textContent).toContain(
      "ngày nghỉ chính thức của Vietnam (VN)",
    );
    const items = [...node.querySelectorAll(".error__list li")];
    expect(items).toHaveLength(1);
    expect(items[0]!.textContent).toContain("17/02/2026");
    expect(items[0]!.textContent).toContain("Lunar New Year");
  });

  it("says how to proceed", () => {
    const node = renderError(holidayError([{ date: "2026-02-17", name: "Tết" }]), TOKYO, COUNTRIES);
    expect(node.querySelector(".error__hint")?.textContent).toContain("bỏ chọn quốc gia");
  });

  it("lists every holiday in a multi-day range", () => {
    const node = renderError(
      holidayError([
        { date: "2026-02-16", name: "Lunar New Year's Eve" },
        { date: "2026-02-17", name: "Lunar New Year" },
      ]),
      TOKYO,
      COUNTRIES,
    );
    expect(node.querySelector(".error__text")?.textContent).toContain("2 ngày nghỉ");
    expect(node.querySelectorAll(".error__list li")).toHaveLength(2);
  });

  it("formats the holiday date independently of the view timezone", () => {
    const inTokyo = renderError(holidayError([{ date: "2026-02-17", name: "Tết" }]), TOKYO, COUNTRIES);
    const inNewYork = renderError(
      holidayError([{ date: "2026-02-17", name: "Tết" }]),
      "America/New_York",
      COUNTRIES,
    );
    expect(inTokyo.querySelector(".error__list li")?.textContent).toBe(
      inNewYork.querySelector(".error__list li")?.textContent,
    );
  });

  it("renders holiday names as text, not markup", () => {
    const node = renderError(holidayError([{ date: "2026-02-17", name: "<b>x</b>" }]), TOKYO, COUNTRIES);
    expect(node.querySelector("b")).toBeNull();
  });
});

describe("schedules that run past midnight", () => {
  const overnight = (overrides = {}) =>
    schedule({
      title: "Ca đêm",
      timezone: SAIGON,
      start_time: "2026-03-10T23:30:00+07:00",
      end_time: "2026-03-11T01:00:00+07:00",
      location: null,
      ...overrides,
    });

  it("marks the card so the end time does not read as earlier than the start", () => {
    const list = renderList([overnight()], null, () => {}, SAIGON);
    const time = list.querySelector(".card__time")!;
    expect(time.textContent).toContain("23:30 – 01:00");

    const marker = time.querySelector(".card__next-day")!;
    expect(marker.textContent).toBe("+1");
    expect(marker.getAttribute("title")).toContain("1 ngày");
  });

  it("spells out the full range in the card tooltip", () => {
    const list = renderList([overnight()], null, () => {}, SAIGON);
    const title = list.querySelector<HTMLButtonElement>(".card")!.title;
    expect(title.match(/2026/g)).toHaveLength(2);
    expect(title).toContain("23:30");
    expect(title).toContain("01:00");
  });

  it("leaves a same-day schedule unmarked", () => {
    const list = renderList([schedule()], null, () => {}, TOKYO);
    expect(list.querySelector(".card__next-day")).toBeNull();
  });

  it("counts the days in the view timezone, not the schedule's", () => {
    // The same instants are 01:30-03:00 on a single day in Tokyo.
    const inTokyo = renderList([overnight()], null, () => {}, TOKYO);
    expect(inTokyo.querySelector(".card__next-day")).toBeNull();
    expect(inTokyo.querySelector(".card__time")?.textContent?.trim()).toBe("01:30 – 03:00");

    const inSaigon = renderList([overnight()], null, () => {}, SAIGON);
    expect(inSaigon.querySelector(".card__next-day")?.textContent).toBe("+1");
  });

  it("marks a multi-day range with the number of days", () => {
    const long = overnight({
      start_time: "2026-04-01T09:00:00+07:00",
      end_time: "2026-04-03T09:00:00+07:00",
    });
    expect(renderList([long], null, () => {}, SAIGON).querySelector(".card__next-day")?.textContent).toBe(
      "+2",
    );
  });

  it("groups the schedule under the day it starts", () => {
    const list = renderList([overnight()], null, () => {}, SAIGON);
    expect([...list.querySelectorAll(".day")]).toHaveLength(1);
    expect(list.querySelector(".day")?.textContent).toContain("10/03/2026");
  });

  it("shows both dates and the real duration in the detail panel", () => {
    const panel = renderDetail(overnight(), { onEdit: () => {}, onDelete: () => {} }, SAIGON);
    expect(panel.querySelector(".panel__when")?.textContent?.match(/2026/g)).toHaveLength(2);
    expect(panel.querySelector(".panel__duration")?.textContent).toContain("1 giờ 30 phút");
  });

  it("prefills the edit form with both wall-clock values", () => {
    const form = renderForm(overnight(), { onSubmit: () => {}, onCancel: () => {} }, null, SAIGON, []);
    const inputs = form.querySelectorAll<HTMLInputElement>("input");
    expect(inputs[1]!.value).toBe("2026-03-10T23:30");
    expect(inputs[2]!.value).toBe("2026-03-11T01:00");
  });
});

describe("the form keeps the duration when the start moves", () => {
  function freshForm() {
    const form = renderForm(
      schedule({ start_time: "2026-03-10T09:00:00+07:00", end_time: "2026-03-10T10:00:00+07:00" }),
      { onSubmit: () => {}, onCancel: () => {} },
      null,
      SAIGON,
      [],
    );
    const inputs = form.querySelectorAll<HTMLInputElement>("input");
    return { form, start: inputs[1]!, end: inputs[2]! };
  }

  it("rolls the end into the next day for a late start", () => {
    const { start, end } = freshForm();
    start.value = "2026-03-10T23:30";
    start.dispatchEvent(new Event("change"));
    expect(end.value).toBe("2026-03-11T00:30"); // the 1 hour length is kept
  });

  it("keeps a longer duration intact", () => {
    const { start, end } = freshForm();
    end.value = "2026-03-10T12:00"; // three hours long
    start.value = "2026-03-10T22:00";
    start.dispatchEvent(new Event("change"));
    expect(end.value).toBe("2026-03-11T01:00");
  });

  it("moves the end back too when the start moves earlier", () => {
    const { start, end } = freshForm();
    start.value = "2026-03-09T08:00";
    start.dispatchEvent(new Event("change"));
    expect(end.value).toBe("2026-03-09T09:00");
  });

  it("leaves an already invalid range alone instead of guessing", () => {
    const { start, end } = freshForm();
    end.value = "2026-03-10T08:00"; // end before start: the user is mid-edit
    start.value = "2026-03-10T23:30";
    start.dispatchEvent(new Event("change"));
    expect(end.value).toBe("2026-03-10T08:00");
  });

  it("submits the rolled-over end", () => {
    const onSubmit = vi.fn();
    const form = renderForm(
      schedule({ start_time: "2026-03-10T09:00:00+07:00", end_time: "2026-03-10T10:00:00+07:00" }),
      { onSubmit, onCancel: () => {} },
      null,
      SAIGON,
      [],
    );
    const start = form.querySelectorAll<HTMLInputElement>("input")[1]!;
    start.value = "2026-03-10T23:30";
    start.dispatchEvent(new Event("change"));
    form.dispatchEvent(new Event("submit", { cancelable: true }));

    expect(onSubmit.mock.calls[0]![0].start_time).toBe("2026-03-10T23:30");
    expect(onSubmit.mock.calls[0]![0].end_time).toBe("2026-03-11T00:30");
  });
});

describe("reminders", () => {
  const withReminder = (overrides = {}) =>
    schedule({
      timezone: SAIGON,
      start_time: "2026-05-10T09:00:00+07:00",
      end_time: "2026-05-10T10:00:00+07:00",
      reminder_minutes: 30,
      notify_at: "2026-05-10T08:30:00+07:00",
      reminder_status: "scheduled",
      ...overrides,
    });

  it("offers an explicit no-reminder option first", () => {
    const select = reminderSelect(null);
    expect(select.value).toBe("");
    expect(select.options[0]!.textContent).toContain("Không nhắc");
    expect([...select.options].map((o) => o.value)).toContain("15");
  });

  it("preselects the schedule's lead time and labels it in words", () => {
    const select = reminderSelect(30);
    expect(select.value).toBe("30");
    expect([...select.options].find((o) => o.value === "1440")?.textContent).toBe("1 ngày trước");
  });

  it("keeps a lead time that is not one of the presets", () => {
    const select = reminderSelect(7);
    expect(select.value).toBe("7");
    expect([...select.options].map((o) => o.value)).toEqual(
      ["", "5", "7", "10", "15", "30", "60", "120", "1440"],
    );
  });

  it("defaults a new schedule to a 15 minute reminder", () => {
    const form = renderForm(null, { onSubmit: () => {}, onCancel: () => {} }, null, SAIGON, []);
    expect(form.querySelectorAll<HTMLSelectElement>("select")[1]!.value).toBe("15");
  });

  it("submits the chosen lead time, and null for no reminder", () => {
    const onSubmit = vi.fn();
    const form = renderForm(withReminder(), { onSubmit, onCancel: () => {} }, null, SAIGON, []);
    const reminder = form.querySelectorAll<HTMLSelectElement>("select")[1]!;
    expect(reminder.value).toBe("30");

    form.dispatchEvent(new Event("submit", { cancelable: true }));
    expect(onSubmit.mock.calls[0]![0].reminder_minutes).toBe(30);

    reminder.value = "";
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    expect(onSubmit.mock.calls[1]![0].reminder_minutes).toBeNull();
  });

  it("summarises when the reminder fires and whether it went out", () => {
    const pending = reminderSummary(withReminder(), SAIGON);
    expect(pending).toContain("30 phút trước");
    expect(pending).toContain("08:30");
    expect(pending).toContain("chưa gửi");

    const sent = reminderSummary(
      withReminder({ notified_at: "2026-05-10T01:30:00+00:00", reminder_status: "sent" }),
      SAIGON,
    );
    expect(sent).toContain("đã gửi");
  });

  it("shows the reminder moment in the timezone being viewed", () => {
    // 08:30 in Saigon is 10:30 in Tokyo — the same instant.
    expect(reminderSummary(withReminder(), TOKYO)).toContain("10:30");
  });

  it("stops claiming a missed reminder is still coming", () => {
    // BUG-03: the panel used to read "chưa gửi" forever for a reminder whose
    // moment had passed while the schedule was already under way.
    const missed = withReminder({ reminder_status: "missed" });
    expect(reminderSummary(missed, SAIGON)).toContain("đã qua, không nhắc nữa");
    expect(reminderSummary(missed, SAIGON)).not.toContain("chưa gửi");
  });

  it("marks a missed reminder on the chip too", () => {
    const panel = renderDetail(
      withReminder({ reminder_status: "missed" }),
      { onEdit: () => {}, onDelete: () => {} },
      SAIGON,
    );
    expect(badges(panel)).toContain("Nhắc trước 30 phút · đã qua");
  });

  it("still says a reminder is waiting when it really is", () => {
    expect(reminderSummary(withReminder(), SAIGON)).toContain("chưa gửi");
  });

  it("says nothing when there is no reminder", () => {
    expect(reminderSummary(schedule(), SAIGON)).toBe("—");
  });

  it("shows the reminder both as a chip and as a detail row", () => {
    const panel = renderDetail(withReminder(), { onEdit: () => {}, onDelete: () => {} }, SAIGON);
    expect(badges(panel)).toContain("Nhắc trước 30 phút");
    expect(fact(panel, "Nhắc trước")).toContain("30 phút trước");
  });

  it("says so on the chip once the reminder has gone out", () => {
    const panel = renderDetail(
      withReminder({ notified_at: "2026-05-10T01:30:00+00:00", reminder_status: "sent" }),
      { onEdit: () => {}, onDelete: () => {} },
      SAIGON,
    );
    expect(badges(panel)).toContain("Đã nhắc trước 30 phút");
  });

  it("handles a reminder that falls on the previous local day", () => {
    // A 00:15 start with a 30 minute lead fires at 23:45 the day before.
    const overnight = withReminder({
      start_time: "2026-05-11T00:15:00+07:00",
      end_time: "2026-05-11T01:15:00+07:00",
      notify_at: "2026-05-10T23:45:00+07:00",
    });
    const summary = reminderSummary(overnight, SAIGON);
    expect(summary).toContain("10/05/2026");
    expect(summary).toContain("23:45");
  });
});

describe("duration limits", () => {
  const LIMITS = {
    min_duration_minutes: 15,
    max_duration_minutes: 10080,
    default_timezone: SAIGON,
    timezone_aliases: { "Asia/Saigon": SAIGON },
  };

  const durationError = (minutes: number) =>
    new ApiError("too short or long", 422, {
      kind: "duration",
      durationMinutes: minutes,
      minMinutes: 15,
      maxMinutes: 10080,
    });

  it("says a schedule is too short and names the allowed range", () => {
    const node = renderError(durationError(5), SAIGON, COUNTRIES);
    expect(node.querySelector(".error__text")?.textContent).toBe("Lịch quá ngắn: 5 phút.");
    expect(node.querySelector(".error__hint")?.textContent).toBe(
      "Thời lượng phải từ 15 phút đến 7 ngày.",
    );
  });

  it("says a schedule is too long", () => {
    const node = renderError(durationError(20160), SAIGON, COUNTRIES);
    expect(node.querySelector(".error__text")?.textContent).toBe("Lịch quá dài: 14 ngày.");
  });

  it("explains a time the clocks skipped instead of echoing the API", () => {
    const node = renderError(
      new ApiError("does not exist", 422, {
        kind: "nonexistentTime",
        field: "start_time",
        timezone: "America/New_York",
        localTime: "2026-03-08T02:30:00",
        gapMinutes: 60,
        nextValid: "2026-03-08T03:30:00",
      }),
      SAIGON,
    );
    const text = node.querySelector(".error__text")?.textContent ?? "";
    expect(text).toContain("Giờ bắt đầu");
    expect(text).toContain("02:30");
    expect(text).toContain("08/03/2026");
    expect(text).toContain("America/New_York");

    const hint = node.querySelector(".error__hint")?.textContent ?? "";
    expect(hint).toContain("1 giờ");
    expect(hint).toContain("03:30");
  });

  it("names the end time when that is the one that does not exist", () => {
    const node = renderError(
      new ApiError("does not exist", 422, {
        kind: "nonexistentTime",
        field: "end_time",
        timezone: "Europe/London",
        localTime: "2026-03-29T01:30:00",
        gapMinutes: 60,
        nextValid: "2026-03-29T02:30:00",
      }),
      SAIGON,
    );
    expect(node.querySelector(".error__text")?.textContent).toContain("Giờ kết thúc");
  });

  it("shows the limits in the form before anything is submitted", () => {
    const form = renderForm(
      null,
      { onSubmit: () => {}, onCancel: () => {} },
      null,
      SAIGON,
      [],
      LIMITS,
    );
    const hints = [...form.querySelectorAll(".field__hint")].map((n) => n.textContent);
    expect(hints.some((h) => h?.includes("Thời lượng từ 15 phút đến 7 ngày"))).toBe(true);
  });

  it("falls back to the plain hint when the limits are not loaded yet", () => {
    const form = renderForm(null, { onSubmit: () => {}, onCancel: () => {} }, null, SAIGON, []);
    const hints = [...form.querySelectorAll(".field__hint")].map((n) => n.textContent);
    expect(hints.some((h) => h?.includes("Thời lượng từ"))).toBe(false);
    expect(hints.some((h) => h?.includes("ngày hôm sau"))).toBe(true);
  });
});

describe("Google Calendar in the detail panel", () => {
  const handlers = { onEdit: () => {}, onDelete: () => {} };
  const enabled = { mode: "memory", enabled: true, calendar_id: "primary", detail: null };
  const disabled = {
    mode: "disabled",
    enabled: false,
    calendar_id: "primary",
    detail: "Google Calendar integration is disabled. Set GOOGLE_CALENDAR_MODE…",
  };
  const linked = (overrides = {}) =>
    schedule({
      google_event_id: "tkdpm1",
      google_calendar_id: "primary",
      google_synced_at: "2026-08-25T03:15:00+00:00",
      google_out_of_date: false,
      ...overrides,
    });

  it("summarises the sync state", () => {
    expect(googleSummary(schedule(), TOKYO)).toBe("Chưa đồng bộ");
    expect(googleSummary(linked(), TOKYO)).toContain("Đã đồng bộ");
    expect(googleSummary(linked({ google_out_of_date: true }), TOKYO)).toContain(
      "cần đồng bộ lại",
    );
  });

  it("shows the sync time in the timezone being viewed", () => {
    // 03:15 UTC is 12:15 in Tokyo and 10:15 in Saigon.
    expect(googleSummary(linked(), TOKYO)).toContain("12:15");
    expect(googleSummary(linked(), SAIGON)).toContain("10:15");
  });

  it("says nothing about Google when the status has not loaded", () => {
    const panel = renderDetail(schedule(), handlers, TOKYO, COUNTRIES);
    expect(panel.textContent).not.toContain("Google Calendar");
  });

  it("offers a sync button when the integration is on", () => {
    const panel = renderDetail(schedule(), handlers, TOKYO, COUNTRIES, enabled);
    const labels = [...panel.querySelectorAll(".actions .btn")].map((b) => b.textContent);
    expect(labels).toContain("Đồng bộ Google");
    expect(labels).not.toContain("Bỏ liên kết");
  });

  it("offers re-sync and unlink once the schedule is linked", () => {
    const panel = renderDetail(linked(), handlers, TOKYO, COUNTRIES, enabled);
    const labels = [...panel.querySelectorAll(".actions .btn")].map((b) => b.textContent);
    expect(labels).toContain("Đồng bộ lại");
    expect(labels).toContain("Bỏ liên kết");
  });

  it("explains why syncing is unavailable instead of hiding it", () => {
    const panel = renderDetail(schedule(), handlers, TOKYO, COUNTRIES, disabled);
    const labels = [...panel.querySelectorAll(".actions .btn")].map((b) => b.textContent);
    expect(labels).not.toContain("Đồng bộ Google");
    expect(panel.querySelector(".panel__note")?.textContent).toContain("GOOGLE_CALENDAR_MODE");
  });

  it("reports the clicks", () => {
    const onGoogleSync = vi.fn();
    const onGoogleUnlink = vi.fn();
    const panel = renderDetail(
      linked(),
      { ...handlers, onGoogleSync, onGoogleUnlink },
      TOKYO,
      COUNTRIES,
      enabled,
    );
    const buttons = [...panel.querySelectorAll<HTMLButtonElement>(".actions .btn")];
    buttons.find((b) => b.textContent === "Đồng bộ lại")!.click();
    buttons.find((b) => b.textContent === "Bỏ liên kết")!.click();
    expect(onGoogleSync).toHaveBeenCalledOnce();
    expect(onGoogleUnlink).toHaveBeenCalledOnce();
  });
});

describe("empty, loading and placeholder states", () => {
  it("invites the user to create the first schedule", () => {
    const onCreate = vi.fn();
    const node = renderList([], null, () => {}, TOKYO, onCreate);

    expect(node.querySelector(".empty")?.textContent).toContain("Chưa có lịch nào");
    const cta = node.querySelector<HTMLButtonElement>(".emptystate .btn")!;
    expect(cta.textContent).toBe("Tạo lịch");
    cta.click();
    expect(onCreate).toHaveBeenCalledOnce();
  });

  it("leaves out the call to action when there is nothing to call", () => {
    const node = renderList([], null, () => {}, TOKYO);
    expect(node.querySelector(".emptystate .btn")).toBeNull();
  });

  it("shows placeholder cards while loading, hidden from screen readers", () => {
    const node = renderSkeleton(3);
    expect(node.querySelectorAll(".skeleton__card")).toHaveLength(3);
    expect(node.getAttribute("aria-hidden")).toBe("true");
  });
});

describe("badges on the list", () => {
  const chips = (node: HTMLElement) =>
    [...node.querySelectorAll(".card__badges .badge")].map((b) => b.textContent);

  it("shows nothing extra for a plain schedule", () => {
    const node = renderList([schedule()], null, () => {}, TOKYO);
    expect(node.querySelector(".card__badges")).toBeNull();
  });

  it("flags a reminder, a country and a Google link", () => {
    const node = renderList(
      [schedule({ reminder_minutes: 30, reminder_status: "scheduled", country: "VN", google_event_id: "tkdpm1" })],
      null,
      () => {},
      TOKYO,
    );
    expect(chips(node)).toEqual(["Nhắc 30 phút", "VN", "Google"]);
  });

  it("warns on the card when a synced schedule has drifted", () => {
    const node = renderList(
      [schedule({ google_event_id: "tkdpm1", google_out_of_date: true })],
      null,
      () => {},
      TOKYO,
    );
    expect(chips(node)).toEqual(["Google · cần đồng bộ"]);
    expect(node.querySelector(".card__badges .badge--warning")).not.toBeNull();
  });
});

describe("deleting asks in the panel", () => {
  const handlers = { onEdit: () => {}, onDelete: () => {} };

  it("does not show the confirmation until it is asked for", () => {
    const panel = renderDetail(schedule(), handlers, TOKYO);
    expect(panel.querySelector(".confirm")).toBeNull();
  });

  it("names the schedule and warns that it cannot be undone", () => {
    const panel = renderDetail(schedule(), handlers, TOKYO, [], null, { confirmingDelete: true });
    const text = panel.querySelector(".confirm__text")?.textContent ?? "";
    expect(text).toContain("Họp nhóm");
    expect(text).toContain("không hoàn tác");
  });

  it("reports confirm and cancel separately", () => {
    const onDeleteConfirm = vi.fn();
    const onDeleteCancel = vi.fn();
    const panel = renderDetail(
      schedule(),
      { ...handlers, onDeleteConfirm, onDeleteCancel },
      TOKYO,
      [],
      null,
      { confirmingDelete: true },
    );
    const buttons = [...panel.querySelectorAll<HTMLButtonElement>(".confirm__actions .btn")];
    expect(buttons.map((b) => b.textContent)).toEqual(["Xóa lịch này", "Giữ lại"]);
    buttons[0]!.click();
    buttons[1]!.click();
    expect(onDeleteConfirm).toHaveBeenCalledOnce();
    expect(onDeleteCancel).toHaveBeenCalledOnce();
  });

  it("disables the actions while one is in flight", () => {
    const panel = renderDetail(schedule(), handlers, TOKYO, [], null, { busy: true });
    const buttons = [...panel.querySelectorAll<HTMLButtonElement>(".actions .btn")];
    expect(buttons.every((b) => b.disabled)).toBe(true);
  });
});

describe("friendly error messages", () => {
  const apiError = (message: string, status = 400) => new ApiError(message, status);

  it("rewrites the backend's wording into something actionable", () => {
    expect(friendlyMessage(apiError("Value error, end_time must be after start_time", 422)).text)
      .toBe("Thời gian kết thúc phải sau thời gian bắt đầu.");
    expect(friendlyMessage(apiError("Schedule not found", 404)).text).toContain(
      "không còn tồn tại",
    );
    expect(friendlyMessage(apiError("Unknown timezone: 'Mars/Olympus'", 422)).text).toContain(
      "Múi giờ không hợp lệ",
    );
    expect(friendlyMessage(apiError("Unknown country: 'XX'", 422)).text).toContain(
      "Quốc gia không hợp lệ",
    );
  });

  it("keeps the technical detail as a secondary line", () => {
    const off = friendlyMessage(apiError("Google Calendar integration is disabled…", 503));
    expect(off.text).toBe("Chưa bật đồng bộ Google Calendar.");
    expect(off.hint).toContain("disabled");

    const broken = friendlyMessage(apiError("Yêu cầu thất bại (HTTP 500)", 500));
    expect(broken.text).toContain("Máy chủ đang gặp sự cố");
  });

  it("passes through a message that is already written for people", () => {
    const message = "Không kết nối được backend tại http://127.0.0.1:8001";
    expect(friendlyMessage(apiError(message, 0)).text).toBe(message);
  });

  it("is what the error panel renders", () => {
    const node = renderError(new ApiError("Schedule not found", 404), TOKYO, COUNTRIES);
    expect(node.querySelector(".error__text")?.textContent).toContain("không còn tồn tại");
  });
});

describe("renderToast", () => {
  it("carries the message", () => {
    expect(renderToast("Đã tạo lịch.").textContent).toBe("Đã tạo lịch.");
  });
});
