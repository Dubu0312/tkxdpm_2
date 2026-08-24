import {
  dayKeyInZone,
  formatDate,
  formatDuration,
  formatRange,
  formatTime,
  listTimezones,
  nowInputValue,
  offsetLabel,
  sameZone,
  toInputValue,
} from "./format";
import type { Schedule, ScheduleInput } from "./types";

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
    container.append(el("h3", "day", formatDate(`${day}T12:00:00Z`, "UTC")));
    for (const schedule of items) {
      const card = el("button", "card");
      card.type = "button";
      if (schedule.id === selectedId) card.classList.add("card--active");
      card.setAttribute("aria-current", schedule.id === selectedId ? "true" : "false");

      card.append(
        el(
          "span",
          "card__time",
          `${formatTime(schedule.start_time, viewTimezone)} – ` +
            `${formatTime(schedule.end_time, viewTimezone)}`,
        ),
      );
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

export function renderDetail(
  schedule: Schedule,
  handlers: { onEdit: () => void; onDelete: () => void },
  viewTimezone: string,
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
  addFact("Múi giờ", schedule.timezone);
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
    };
  }
  return {
    title: "",
    description: null,
    location: null,
    start_time: nowInputValue(60, defaultTimezone),
    end_time: nowInputValue(120, defaultTimezone),
    timezone: defaultTimezone,
  };
}

export function renderForm(
  schedule: Schedule | null,
  handlers: { onSubmit: (input: ScheduleInput) => void; onCancel: () => void },
  draft: ScheduleInput | null = null,
  defaultTimezone: string = "UTC",
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

  form.append(
    field("Tiêu đề *", title),
    field("Múi giờ *", timezone, "Giờ nhập bên dưới được hiểu theo múi giờ này."),
    field("Bắt đầu *", start),
    field("Kết thúc *", end, "Phải sau thời gian bắt đầu."),
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

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    handlers.onSubmit({
      title: title.value.trim(),
      description: description.value.trim() || null,
      location: location.value.trim() || null,
      start_time: start.value,
      end_time: end.value,
      timezone: timezone.value,
    });
  });

  return form;
}

export function renderPlaceholder(text: string): HTMLElement {
  const panel = el("article", "panel panel--placeholder");
  panel.append(el("p", "empty", text));
  return panel;
}


export function renderError(error: ApiError, viewTimezone: string = "UTC"): HTMLElement {
  const box = el("div", "error__body");

  if (error.conflicts.length === 0) {
    box.append(el("p", "error__text", error.message));
    return box;
  }

  box.append(
    el(
      "p",
      "error__text",
      error.conflicts.length === 1
        ? "Khung giờ này bị trùng với một lịch đã có:"
        : `Khung giờ này bị trùng với ${error.conflicts.length} lịch đã có:`,
    ),
  );

  const list = el("ul", "error__list");
  for (const conflict of error.conflicts) {
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
