import { formatDate, formatDuration, formatRange, formatTime, nowInputValue, toInputValue } from "./format";
import type { Schedule, ScheduleInput } from "./types";

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

/** Groups schedules by calendar day, preserving the backend's start-time order. */
function groupByDay(schedules: Schedule[]): [string, Schedule[]][] {
  const groups = new Map<string, Schedule[]>();
  for (const schedule of schedules) {
    const day = schedule.start_time.slice(0, 10);
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
): HTMLElement {
  const container = el("div", "list");

  if (schedules.length === 0) {
    container.append(el("p", "empty", "Chưa có lịch nào. Bấm “Tạo lịch” để thêm."));
    return container;
  }

  for (const [day, items] of groupByDay(schedules)) {
    container.append(el("h3", "day", formatDate(`${day}T00:00:00`)));
    for (const schedule of items) {
      const card = el("button", "card");
      card.type = "button";
      if (schedule.id === selectedId) card.classList.add("card--active");
      card.setAttribute("aria-current", schedule.id === selectedId ? "true" : "false");

      card.append(el("span", "card__time", `${formatTime(schedule.start_time)} – ${formatTime(schedule.end_time)}`));
      card.append(el("span", "card__title", schedule.title));
      if (schedule.location) card.append(el("span", "card__meta", schedule.location));

      card.addEventListener("click", () => onSelect(schedule.id));
      container.append(card);
    }
  }
  return container;
}

export function renderDetail(
  schedule: Schedule,
  handlers: { onEdit: () => void; onDelete: () => void },
): HTMLElement {
  const panel = el("article", "panel");
  panel.append(el("h2", undefined, schedule.title));
  panel.append(el("p", "panel__when", formatRange(schedule.start_time, schedule.end_time)));
  panel.append(el("p", "panel__duration", `Thời lượng: ${formatDuration(schedule.start_time, schedule.end_time)}`));

  const facts = el("dl", "facts");
  const addFact = (label: string, value: string) => {
    facts.append(el("dt", undefined, label), el("dd", undefined, value));
  };
  addFact("Địa điểm", schedule.location || "—");
  addFact("Mô tả", schedule.description || "—");
  addFact("Tạo lúc", `${formatDate(schedule.created_at)} ${formatTime(schedule.created_at)}`);
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

export function renderForm(
  schedule: Schedule | null,
  handlers: { onSubmit: (input: ScheduleInput) => void; onCancel: () => void },
): HTMLElement {
  const form = el("form", "panel form");
  form.append(el("h2", undefined, schedule ? "Chỉnh sửa lịch" : "Tạo lịch mới"));

  const title = el("input");
  title.type = "text";
  title.required = true;
  title.maxLength = 200;
  title.value = schedule?.title ?? "";
  title.placeholder = "Ví dụ: Họp nhóm dự án";

  const start = el("input");
  start.type = "datetime-local";
  start.required = true;
  start.value = schedule ? toInputValue(schedule.start_time) : nowInputValue(60);

  const end = el("input");
  end.type = "datetime-local";
  end.required = true;
  end.value = schedule ? toInputValue(schedule.end_time) : nowInputValue(120);

  const location = el("input");
  location.type = "text";
  location.maxLength = 200;
  location.value = schedule?.location ?? "";
  location.placeholder = "Ví dụ: Phòng A1 / Google Meet";

  const description = el("textarea");
  description.rows = 4;
  description.maxLength = 5000;
  description.value = schedule?.description ?? "";
  description.placeholder = "Ghi chú thêm (không bắt buộc)";

  form.append(
    field("Tiêu đề *", title),
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
    });
  });

  return form;
}

export function renderPlaceholder(text: string): HTMLElement {
  const panel = el("article", "panel panel--placeholder");
  panel.append(el("p", "empty", text));
  return panel;
}
