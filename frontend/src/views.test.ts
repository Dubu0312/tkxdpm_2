import { describe, expect, it, vi } from "vitest";

import type { Schedule } from "./types";
import { ApiError } from "./api";
import { renderDetail, renderError, renderForm, renderList, timezoneSelect } from "./views";

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
    // First fact is the timezone; the two optional fields follow.
    expect([...node.querySelectorAll("dd")].map((dd) => dd.textContent).slice(1, 3)).toEqual([
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
    expect(form.querySelector("select")!.value).toBe(TOKYO);
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
    const node = renderError(new ApiError("overlap", 409, [schedule()]), TOKYO);
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
      new ApiError("overlap", 409, [
        schedule({ id: 1 }),
        schedule({ id: 2, title: "Lịch thứ hai" }),
      ]),
      TOKYO,
    );
    expect(node.querySelector(".error__text")?.textContent).toContain("2 lịch đã có");
    expect(node.querySelectorAll(".error__list li")).toHaveLength(2);
  });

  it("renders conflict titles as text, not markup", () => {
    const node = renderError(new ApiError("overlap", 409, [schedule({ title: "<b>x</b>" })]), TOKYO);
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
    };
    const form = renderForm(schedule(), { onSubmit: () => {}, onCancel: () => {} }, draft);
    const inputs = form.querySelectorAll<HTMLInputElement>("input");
    expect(inputs[0]!.value).toBe("Tiêu đề đang nhập");
    expect(inputs[1]!.value).toBe("2026-09-05T14:00");
    expect(inputs[2]!.value).toBe("2026-09-05T15:00");
    expect(inputs[3]!.value).toBe("Phòng B");
    expect(form.querySelector("textarea")!.value).toBe("ghi chú");
    expect(form.querySelector("select")!.value).toBe(SAIGON);
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
    const node = renderError(new ApiError("overlap", 409, [schedule()]), SAIGON);
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
    expect(form.querySelector("select")!.value).toBe(SAIGON);
  });
});
