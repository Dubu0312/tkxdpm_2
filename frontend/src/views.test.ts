import { describe, expect, it, vi } from "vitest";

import type { Schedule } from "./types";
import { ApiError } from "./api";
import {
  countryLabel,
  countrySelect,
  renderDetail,
  renderError,
  renderForm,
  renderList,
  timezoneSelect,
} from "./views";

const TOKYO = "Asia/Tokyo";
const SAIGON = "Asia/Ho_Chi_Minh";

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

  it("falls back to a dash for empty optional fields", () => {
    const node = renderDetail(
      schedule({ location: null, description: null }),
      { onEdit: () => {}, onDelete: () => {} },
      TOKYO,
    );
    // Facts are timezone, country, then the two optional fields.
    expect([...node.querySelectorAll("dd")].map((dd) => dd.textContent).slice(2, 4)).toEqual([
      "—",
      "—",
    ]);
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
    expect(form.querySelectorAll<HTMLSelectElement>("select")[1]!.value).toBe("US");
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    expect(onSubmit.mock.calls[0]![0].country).toBe("US");
  });

  it("submits null when no country is chosen", () => {
    const onSubmit = vi.fn();
    const form = renderForm(schedule(), { onSubmit, onCancel: () => {} }, null, TOKYO, COUNTRIES);
    form.dispatchEvent(new Event("submit", { cancelable: true }));
    expect(onSubmit.mock.calls[0]![0].country).toBeNull();
  });

  it("shows the country in the detail panel", () => {
    const handlers = { onEdit: () => {}, onDelete: () => {} };
    const withCountry = renderDetail(schedule({ country: "VN" }), handlers, TOKYO, COUNTRIES);
    expect([...withCountry.querySelectorAll("dd")][1]!.textContent).toBe("Vietnam (VN)");

    const without = renderDetail(schedule(), handlers, TOKYO, COUNTRIES);
    expect([...without.querySelectorAll("dd")][1]!.textContent).toBe("—");
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
