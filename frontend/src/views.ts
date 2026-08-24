import {
  dayKeyInZone,
  dayOffsetInZone,
  formatDate,
  formatDay,
  formatDuration,
  formatMinutes,
  formatRange,
  formatTime,
  listTimezones,
  nowInputValue,
  offsetLabel,
  sameZone,
  shiftWallClock,
  toInputValue,
  wallClockDeltaMinutes,
} from "./format";
import type { Country, Schedule, ScheduleInput } from "./types";

import type { ApiError } from "./api";

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className?: string,
  text?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

/**
 * Groups schedules by the calendar day they fall on *in the view timezone*,
 * preserving the backend's start-instant order. A schedule can therefore land
 * on a different day than the one its own timezone shows.
 */
function groupByDay(schedules: Schedule[], viewTimezone: string): [string, Schedule[]][] {
  const groups = new Map<string, Schedule[]>();
  for (const schedule of schedules) {
    const day = dayKeyInZone(schedule.start_time, viewTimezone);
    const bucket = groups.get(day);
    if (bucket) bucket.push(schedule);
    else groups.set(day, [schedule]);
  }
  return [...groups.entries()];
}

export function renderList(
  schedules: Schedule[],
  selectedId: number | null,
  onSelect: (id: number) => void,
  viewTimezone: string,
): HTMLElement {
  const container = el("div", "list");

  if (schedules.length === 0) {
    container.append(el("p", "empty", "Chưa có lịch nào. Bấm “Tạo lịch” để thêm."));
    return container;
  }

  for (const [day, items] of groupByDay(schedules, viewTimezone)) {
    container.append(el("h3", "day", formatDay(day)));
    for (const schedule of items) {
      const card = el("button", "card");
      card.type = "button";
      if (schedule.id === selectedId) card.classList.add("card--active");
      card.setAttribute("aria-current", schedule.id === selectedId ? "true" : "false");

      const time = el(
        "span",
        "card__time",
        `${formatTime(schedule.start_time, viewTimezone)} – ` +
          `${formatTime(schedule.end_time, viewTimezone)}`,
      );
      // A schedule running past midnight would otherwise read as ending hours
      // before it starts, so say how many days later the end time is.
      const dayOffset = dayOffsetInZone(schedule.start_time, schedule.end_time, viewTimezone);
      if (dayOffset > 0) {
        const marker = el("span", "card__next-day", `+${dayOffset}`);
        marker.title = `Kết thúc sau ${dayOffset} ngày`;
        time.append(" ", marker);
      }
      card.append(time);
      card.title = formatRange(schedule.start_time, schedule.end_time, viewTimezone);
      card.append(el("span", "card__title", schedule.title));

      const meta = [
        schedule.location,
        sameZone(schedule.timezone, viewTimezone) ? null : schedule.timezone,
      ]
        .filter(Boolean)
        .join(" · ");
      if (meta) card.append(el("span", "card__meta", meta));

      card.addEventListener("click", () => onSelect(schedule.id));
      container.append(card);
    }
  }
  return container;
}

/**
 * "15 phút trước · 10/05/2026 08:45 · đã gửi" — when the reminder fires, shown
 * in the timezone being viewed, plus whether it has already gone out.
 */
export function reminderSummary(schedule: Schedule, viewTimezone: string): string {
  if (schedule.reminder_minutes === null || schedule.notify_at === null) return "—";

  const when =
    `${formatDate(schedule.notify_at, viewTimezone)} ` +
    `${formatTime(schedule.notify_at, viewTimezone)}`;
  const status = schedule.notified_at !== null ? "đã gửi" : "chưa gửi";
  return `${formatMinutes(schedule.reminder_minutes)} trước · ${when} · ${status}`;
}

/** "Vietnam (VN)" when the country list is loaded, otherwise just the code. */
export function countryLabel(code: string, countries: Country[]): string {
  const match = countries.find((country) => country.code === code);
  return match ? `${match.name} (${match.code})` : code;
}

export function renderDetail(
  schedule: Schedule,
  handlers: { onEdit: () => void; onDelete: () => void },
  viewTimezone: string,
  countries: Country[] = [],
): HTMLElement {
  const panel = el("article", "panel");
  panel.append(el("h2", undefined, schedule.title));
  panel.append(
    el("p", "panel__when", formatRange(schedule.start_time, schedule.end_time, viewTimezone)),
  );
  panel.append(
    el(
      "p",
      "panel__duration",
      `${viewTimezone} (${offsetLabel(schedule.start_time, viewTimezone)}) · ` +
        `Thời lượng: ${formatDuration(schedule.start_time, schedule.end_time)}`,
    ),
  );

  // The same instant shown in the timezone the schedule was created in.
  if (!sameZone(schedule.timezone, viewTimezone)) {
    panel.append(
      el(
        "p",
        "panel__origin",
        `Giờ gốc (${schedule.timezone}): ` +
          formatRange(schedule.start_time, schedule.end_time, schedule.timezone),
      ),
    );
  }

  const facts = el("dl", "facts");
  const addFact = (label: string, value: string) => {
    facts.append(el("dt", undefined, label), el("dd", undefined, value));
  };
  addFact("Nhắc trước", reminderSummary(schedule, viewTimezone));
  addFact("Múi giờ", schedule.timezone);
  addFact("Quốc gia", schedule.country ? countryLabel(schedule.country, countries) : "—");
  addFact("Địa điểm", schedule.location || "—");
  addFact("Mô tả", schedule.description || "—");
  addFact(
    "Tạo lúc",
    `${formatDate(schedule.created_at, viewTimezone)} ` +
      `${formatTime(schedule.created_at, viewTimezone)}`,
  );
  panel.append(facts);

  const actions = el("div", "actions");
  const edit = el("button", "btn btn--primary", "Chỉnh sửa");
  edit.type = "button";
  edit.addEventListener("click", handlers.onEdit);
  const remove = el("button", "btn btn--danger", "Xóa");
  remove.type = "button";
  remove.addEventListener("click", handlers.onDelete);
  actions.append(edit, remove);
  panel.append(actions);

  return panel;
}

function field(label: string, control: HTMLElement, hint?: string): HTMLElement {
  const wrapper = el("label", "field");
  wrapper.append(el("span", "field__label", label));
  wrapper.append(control);
  if (hint) wrapper.append(el("span", "field__hint", hint));
  return wrapper;
}

/** A <select> listing every IANA timezone, with `selected` preselected. */
export function timezoneSelect(selected: string): HTMLSelectElement {
  const select = document.createElement("select");
  const zones = listTimezones();
  // Keep a zone the runtime does not list under that exact name (an alias such as
  // "Asia/Ho_Chi_Minh", or one stored earlier) selectable, spelled as it was given.
  for (const zone of zones.includes(selected) ? zones : [selected, ...zones]) {
    const option = document.createElement("option");
    option.value = zone;
    option.textContent = zone;
    select.append(option);
  }
  select.value = selected;
  return select;
}

/** A <select> of countries, with an explicit "no country" option first. */
export function countrySelect(countries: Country[], selected: string | null): HTMLSelectElement {
  const select = document.createElement("select");
  const none = document.createElement("option");
  none.value = "";
  none.textContent = "— Không kiểm tra ngày nghỉ —";
  select.append(none);

  for (const country of countries) {
    const option = document.createElement("option");
    option.value = country.code;
    option.textContent = `${country.name} (${country.code})`;
    select.append(option);
  }
  select.value = selected ?? "";
  return select;
}

/** Lead times offered in the form; the value is minutes before the start. */
const REMINDER_CHOICES = [5, 10, 15, 30, 60, 120, 1440];

/** Default lead time for a new schedule. */
const DEFAULT_REMINDER = 15;

/** A <select> of reminder lead times, with an explicit "no reminder" option. */
export function reminderSelect(selected: number | null): HTMLSelectElement {
  const select = document.createElement("select");
  const none = document.createElement("option");
  none.value = "";
  none.textContent = "— Không nhắc —";
  select.append(none);

  const choices = selected !== null && !REMINDER_CHOICES.includes(selected)
    ? [...REMINDER_CHOICES, selected].sort((a, b) => a - b)
    : REMINDER_CHOICES;

  for (const minutes of choices) {
    const option = document.createElement("option");
    option.value = String(minutes);
    option.textContent = `${formatMinutes(minutes)} trước`;
    select.append(option);
  }
  select.value = selected === null ? "" : String(selected);
  return select;
}

/** Values the form starts with: a rejected draft wins over the stored schedule. */
function initialValues(
  schedule: Schedule | null,
  draft: ScheduleInput | null,
  defaultTimezone: string,
): ScheduleInput {
  if (draft) return draft;
  if (schedule) {
    return {
      title: schedule.title,
      description: schedule.description,
      location: schedule.location,
      start_time: toInputValue(schedule.start_time),
      end_time: toInputValue(schedule.end_time),
      timezone: schedule.timezone,
      country: schedule.country,
      reminder_minutes: schedule.reminder_minutes,
    };
  }
  return {
    title: "",
    description: null,
    location: null,
    start_time: nowInputValue(60, defaultTimezone),
    end_time: nowInputValue(120, defaultTimezone),
    timezone: defaultTimezone,
    country: null,
    reminder_minutes: DEFAULT_REMINDER,
  };
}

export function renderForm(
  schedule: Schedule | null,
  handlers: { onSubmit: (input: ScheduleInput) => void; onCancel: () => void },
  draft: ScheduleInput | null = null,
  defaultTimezone: string = "UTC",
  countries: Country[] = [],
): HTMLElement {
  const values = initialValues(schedule, draft, defaultTimezone);
  const form = el("form", "panel form");
  form.append(el("h2", undefined, schedule ? "Chỉnh sửa lịch" : "Tạo lịch mới"));

  const title = el("input");
  title.type = "text";
  title.required = true;
  title.maxLength = 200;
  title.value = values.title;
  title.placeholder = "Ví dụ: Họp nhóm dự án";

  const start = el("input");
  start.type = "datetime-local";
  start.required = true;
  start.value = values.start_time;

  const end = el("input");
  end.type = "datetime-local";
  end.required = true;
  end.value = values.end_time;

  const location = el("input");
  location.type = "text";
  location.maxLength = 200;
  location.value = values.location ?? "";
  location.placeholder = "Ví dụ: Phòng A1 / Google Meet";

  const description = el("textarea");
  description.rows = 4;
  description.maxLength = 5000;
  description.value = values.description ?? "";
  description.placeholder = "Ghi chú thêm (không bắt buộc)";

  const timezone = timezoneSelect(values.timezone);
  const country = countrySelect(countries, values.country);
  const reminder = reminderSelect(values.reminder_minutes);

  form.append(
    field("Tiêu đề *", title),
    field("Múi giờ *", timezone, "Giờ nhập bên dưới được hiểu theo múi giờ này."),
    field("Bắt đầu *", start),
    field("Kết thúc *", end, "Phải sau thời gian bắt đầu; có thể rơi vào ngày hôm sau."),
    field("Nhắc trước", reminder, "Tính từ thời điểm bắt đầu của lịch."),
    field("Quốc gia", country, "Không thể đặt lịch vào ngày nghỉ chính thức của quốc gia này."),
    field("Địa điểm", location),
    field("Mô tả", description),
  );

  const actions = el("div", "actions");
  const submit = el("button", "btn btn--primary", schedule ? "Lưu thay đổi" : "Tạo lịch");
  submit.type = "submit";
  const cancel = el("button", "btn", "Hủy");
  cancel.type = "button";
  cancel.addEventListener("click", handlers.onCancel);
  actions.append(submit, cancel);
  form.append(actions);

  // Moving the start keeps the length of the schedule, which rolls the end into
  // the next day on its own when the start is late in the evening.
  let previousStart = start.value;
  start.addEventListener("change", () => {
    const minutes = wallClockDeltaMinutes(previousStart, end.value);
    if (start.value && minutes > 0) {
      end.value = shiftWallClock(start.value, minutes);
    }
    previousStart = start.value;
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    handlers.onSubmit({
      title: title.value.trim(),
      description: description.value.trim() || null,
      location: location.value.trim() || null,
      start_time: start.value,
      end_time: end.value,
      timezone: timezone.value,
      country: country.value || null,
      reminder_minutes: reminder.value === "" ? null : Number(reminder.value),
    });
  });

  return form;
}

export function renderPlaceholder(text: string): HTMLElement {
  const panel = el("article", "panel panel--placeholder");
  panel.append(el("p", "empty", text));
  return panel;
}


export function renderError(
  error: ApiError,
  viewTimezone: string = "UTC",
  countries: Country[] = [],
): HTMLElement {
  const box = el("div", "error__body");
  const detail = error.detail;

  if (detail === null) {
    box.append(el("p", "error__text", error.message));
    return box;
  }

  if (detail.kind === "holiday") {
    const country = countryLabel(detail.country, countries);
    box.append(
      el(
        "p",
        "error__text",
        detail.holidays.length === 1
          ? `Ngày này là ngày nghỉ chính thức của ${country}:`
          : `Khoảng thời gian này rơi vào ${detail.holidays.length} ngày nghỉ chính thức của ${country}:`,
      ),
    );

    const list = el("ul", "error__list");
    for (const holiday of detail.holidays) {
      list.append(el("li", undefined, `${formatDay(holiday.date)} — ${holiday.name}`));
    }
    box.append(list);
    box.append(
      el(
        "p",
        "error__hint",
        "Hãy chọn ngày khác, hoặc bỏ chọn quốc gia nếu lịch này không theo ngày nghỉ của quốc gia đó.",
      ),
    );
    return box;
  }

  box.append(
    el(
      "p",
      "error__text",
      detail.conflicts.length === 1
        ? "Khung giờ này bị trùng với một lịch đã có:"
        : `Khung giờ này bị trùng với ${detail.conflicts.length} lịch đã có:`,
    ),
  );

  const list = el("ul", "error__list");
  for (const conflict of detail.conflicts) {
    list.append(
      el(
        "li",
        undefined,
        `${conflict.title} — ${formatRange(conflict.start_time, conflict.end_time, viewTimezone)}`,
      ),
    );
  }
  box.append(list);
  box.append(
    el(
      "p",
      "error__hint",
      "Hãy chọn khung giờ khác. Lịch bắt đầu đúng lúc lịch khác kết thúc thì vẫn hợp lệ.",
    ),
  );
  return box;
}
