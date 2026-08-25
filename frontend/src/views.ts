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
import type { Country, GoogleStatus, Limits, Schedule, ScheduleInput } from "./types";

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
  onCreate?: () => void,
): HTMLElement {
  const container = el("div", "list");

  if (schedules.length === 0) {
    const state = el("div", "emptystate");
    state.append(el("span", "emptystate__icon", "🗓"));
    state.append(el("p", "emptystate__title empty", "Chưa có lịch nào"));
    state.append(
      el("p", "empty", "Tạo lịch đầu tiên để bắt đầu theo dõi thời gian của bạn."),
    );
    if (onCreate) {
      const cta = el("button", "btn btn--primary btn--sm", "Tạo lịch");
      cta.type = "button";
      cta.addEventListener("click", onCreate);
      state.append(cta);
    }
    container.append(state);
    return container;
  }

  for (const [day, items] of groupByDay(schedules, viewTimezone)) {
    container.append(el("h3", "day", formatDay(day)));
    for (const schedule of items) {
      container.append(renderCard(schedule, selectedId, onSelect, viewTimezone));
    }
  }
  return container;
}

function renderCard(
  schedule: Schedule,
  selectedId: number | null,
  onSelect: (id: number) => void,
  viewTimezone: string,
): HTMLElement {
  const card = el("button", "card");
  card.type = "button";
  if (schedule.id === selectedId) card.classList.add("card--active");
  card.setAttribute("aria-current", schedule.id === selectedId ? "true" : "false");
  card.title = formatRange(schedule.start_time, schedule.end_time, viewTimezone);

  // Start over end in a fixed-width gutter, so times line up down the list.
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
  card.append(el("span", "card__title", schedule.title));

  const meta = [
    schedule.location,
    sameZone(schedule.timezone, viewTimezone) ? null : schedule.timezone,
  ]
    .filter(Boolean)
    .join(" · ");
  if (meta) card.append(el("span", "card__meta", meta));

  const badges = el("div", "card__badges");
  if (schedule.reminder_minutes !== null) {
    badges.append(el("span", "badge", `Nhắc ${formatMinutes(schedule.reminder_minutes)}`));
  }
  if (schedule.country) badges.append(el("span", "badge", schedule.country));
  if (schedule.google_event_id !== null) {
    badges.append(
      el(
        "span",
        schedule.google_out_of_date ? "badge badge--warning" : "badge badge--success",
        schedule.google_out_of_date ? "Google · cần đồng bộ" : "Google",
      ),
    );
  }
  if (badges.childElementCount > 0) card.append(badges);

  card.addEventListener("click", () => onSelect(schedule.id));
  return card;
}

/** Placeholder cards while the first load is in flight. */
export function renderSkeleton(count = 3): HTMLElement {
  const box = el("div", "skeleton");
  box.setAttribute("aria-hidden", "true");
  for (let i = 0; i < count; i++) box.append(el("div", "skeleton__card"));
  return box;
}

/** Wording for each reminder state, so nothing promises a notification twice. */
const REMINDER_WORDS: Record<Schedule["reminder_status"], string> = {
  none: "",
  scheduled: "chưa gửi",
  sent: "đã gửi",
  // Its moment passed while the schedule was already under way: it never fired
  // and never will, which is not the same as "waiting to be sent".
  missed: "đã qua, không nhắc nữa",
};

/**
 * "15 phút trước · 10/05/2026 08:45 · đã gửi" — when the reminder fires, shown
 * in the timezone being viewed, plus what became of it.
 */
export function reminderSummary(schedule: Schedule, viewTimezone: string): string {
  if (schedule.reminder_minutes === null || schedule.notify_at === null) return "—";

  const when =
    `${formatDate(schedule.notify_at, viewTimezone)} ` +
    `${formatTime(schedule.notify_at, viewTimezone)}`;
  return (
    `${formatMinutes(schedule.reminder_minutes)} trước · ${when} · ` +
    REMINDER_WORDS[schedule.reminder_status]
  );
}

/** "Vietnam (VN)" when the country list is loaded, otherwise just the code. */
export function countryLabel(code: string, countries: Country[]): string {
  const match = countries.find((country) => country.code === code);
  return match ? `${match.name} (${match.code})` : code;
}

/** "Đã đồng bộ · 25/08/2026 10:15" / "Cần đồng bộ lại" / "Chưa đồng bộ". */
export function googleSummary(schedule: Schedule, viewTimezone: string): string {
  if (schedule.google_event_id === null) return "Chưa đồng bộ";
  if (schedule.google_out_of_date) return "Đã đổi sau lần đồng bộ cuối — cần đồng bộ lại";
  if (schedule.google_synced_at === null) return "Đã liên kết";
  return (
    `Đã đồng bộ · ${formatDate(schedule.google_synced_at, viewTimezone)} ` +
    `${formatTime(schedule.google_synced_at, viewTimezone)}`
  );
}

export function renderDetail(
  schedule: Schedule,
  handlers: {
    onEdit: () => void;
    onDelete: () => void;
    onDeleteConfirm?: () => void;
    onDeleteCancel?: () => void;
    onGoogleSync?: () => void;
    onGoogleUnlink?: () => void;
  },
  viewTimezone: string,
  countries: Country[] = [],
  google: GoogleStatus | null = null,
  options: { confirmingDelete?: boolean; busy?: boolean } = {},
): HTMLElement {
  const panel = el("article", "panel");
  panel.append(el("h2", undefined, schedule.title));

  // Chips carry the at-a-glance facts; the list below carries the details.
  const badges = el("div", "panel__badges");
  badges.append(el("span", "badge", schedule.timezone));
  if (schedule.country) {
    badges.append(el("span", "badge", countryLabel(schedule.country, countries)));
  }
  if (schedule.reminder_minutes !== null) {
    const lead = formatMinutes(schedule.reminder_minutes);
    const sent = schedule.reminder_status === "sent";
    badges.append(
      el(
        "span",
        sent ? "badge badge--success" : "badge",
        sent
          ? `Đã nhắc trước ${lead}`
          : schedule.reminder_status === "missed"
            ? `Nhắc trước ${lead} · đã qua`
            : `Nhắc trước ${lead}`,
      ),
    );
  }
  if (google !== null && schedule.google_event_id !== null) {
    badges.append(
      el(
        "span",
        schedule.google_out_of_date ? "badge badge--warning" : "badge badge--success",
        schedule.google_out_of_date ? "Google · cần đồng bộ lại" : "Google · đã đồng bộ",
      ),
    );
  }
  panel.append(badges);

  // The "when" block: the single most important thing about a schedule.
  const when = el("div", "when");
  when.append(
    el("p", "panel__when", formatRange(schedule.start_time, schedule.end_time, viewTimezone)),
  );
  when.append(
    el(
      "p",
      "panel__duration",
      `${viewTimezone} (${offsetLabel(schedule.start_time, viewTimezone)}) · ` +
        `Thời lượng: ${formatDuration(schedule.start_time, schedule.end_time)}`,
    ),
  );
  // The same instant shown in the timezone the schedule was created in.
  if (!sameZone(schedule.timezone, viewTimezone)) {
    when.append(
      el(
        "p",
        "panel__origin",
        `Giờ gốc (${schedule.timezone}): ` +
          formatRange(schedule.start_time, schedule.end_time, schedule.timezone),
      ),
    );
  }
  panel.append(when);

  // Only rows that say something: a column of "—" is noise, not information.
  const facts = el("dl", "facts");
  const addFact = (label: string, value: string) => {
    facts.append(el("dt", undefined, label), el("dd", undefined, value));
  };
  if (schedule.location) addFact("Địa điểm", schedule.location);
  if (schedule.description) addFact("Mô tả", schedule.description);
  if (schedule.reminder_minutes !== null) {
    addFact("Nhắc trước", reminderSummary(schedule, viewTimezone));
  }
  if (google !== null && schedule.google_event_id !== null) {
    addFact("Google Calendar", googleSummary(schedule, viewTimezone));
  }
  addFact(
    "Tạo lúc",
    `${formatDate(schedule.created_at, viewTimezone)} ` +
      `${formatTime(schedule.created_at, viewTimezone)}`,
  );
  panel.append(facts);

  const actions = el("div", "actions");
  const edit = el("button", "btn btn--primary", "Chỉnh sửa");
  edit.type = "button";
  edit.disabled = options.busy === true;
  edit.addEventListener("click", handlers.onEdit);
  actions.append(edit);

  if (google !== null && google.enabled) {
    const label = schedule.google_event_id === null ? "Đồng bộ Google" : "Đồng bộ lại";
    const sync = el("button", "btn", label);
    sync.type = "button";
    sync.disabled = options.busy === true;
    if (handlers.onGoogleSync) sync.addEventListener("click", handlers.onGoogleSync);
    actions.append(sync);

    if (schedule.google_event_id !== null) {
      const unlink = el("button", "btn", "Bỏ liên kết");
      unlink.type = "button";
      unlink.disabled = options.busy === true;
      if (handlers.onGoogleUnlink) unlink.addEventListener("click", handlers.onGoogleUnlink);
      actions.append(unlink);
    }
  }

  // Destructive action sits apart from the rest.
  actions.append(el("span", "actions__spacer"));
  const remove = el("button", "btn btn--danger", "Xóa");
  remove.type = "button";
  remove.disabled = options.busy === true;
  remove.addEventListener("click", handlers.onDelete);
  actions.append(remove);

  panel.append(actions);

  if (options.confirmingDelete) {
    panel.append(renderDeleteConfirm(schedule, handlers));
  }

  // Say why syncing is unavailable, or that this is only the stand-in mode,
  // rather than hiding the feature silently.
  if (google !== null && google.detail) {
    panel.append(el("p", "panel__note", google.detail));
  }

  return panel;
}

/** Asks in place, instead of handing the browser's own dialog to the user. */
function renderDeleteConfirm(
  schedule: Schedule,
  handlers: { onDeleteConfirm?: () => void; onDeleteCancel?: () => void },
): HTMLElement {
  const box = el("div", "confirm");
  box.append(
    el("p", "confirm__text", `Xóa lịch “${schedule.title}”? Thao tác này không hoàn tác được.`),
  );

  const row = el("div", "confirm__actions");
  const yes = el("button", "btn btn--danger btn--sm", "Xóa lịch này");
  yes.type = "button";
  if (handlers.onDeleteConfirm) yes.addEventListener("click", handlers.onDeleteConfirm);
  const no = el("button", "btn btn--sm", "Giữ lại");
  no.type = "button";
  if (handlers.onDeleteCancel) no.addEventListener("click", handlers.onDeleteCancel);
  row.append(yes, no);
  box.append(row);
  return box;
}

function field(
  label: string,
  control: HTMLElement,
  hint?: string,
  required = false,
): HTMLElement {
  const wrapper = el("label", "field");
  const text = el("span", "field__label", label);
  if (required) {
    const mark = el("span", "field__required", "*");
    mark.title = "Bắt buộc";
    text.append(mark);
  }
  wrapper.append(text, control);
  if (hint) wrapper.append(el("span", "field__hint", hint));
  return wrapper;
}

/** A titled group of fields, so the form reads as sections not a long stack. */
function section(legend: string, ...fields: HTMLElement[]): HTMLElement {
  const box = el("fieldset", "form__section");
  box.append(el("legend", "form__legend", legend));
  box.append(...fields);
  return box;
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

/** Hint under the end field, naming the limits the backend actually enforces. */
function endHint(limits: Limits | null): string {
  const base = "Phải sau thời gian bắt đầu; có thể rơi vào ngày hôm sau.";
  if (limits === null) return base;
  return (
    `${base} Thời lượng từ ${formatMinutes(limits.min_duration_minutes)} ` +
    `đến ${formatMinutes(limits.max_duration_minutes)}.`
  );
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
  limits: Limits | null = null,
): HTMLElement {
  const values = initialValues(schedule, draft, defaultTimezone);
  const form = el("form", "panel form");
  form.append(el("h2", undefined, schedule ? "Chỉnh sửa lịch" : "Tạo lịch mới"));
  form.append(
    el(
      "p",
      "panel__note",
      schedule
        ? "Thay đổi được lưu khi bạn bấm “Lưu thay đổi”."
        : "Các trường có dấu * là bắt buộc.",
    ),
  );

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

  const times = el("div", "form__row");
  times.append(field("Bắt đầu", start, undefined, true), field("Kết thúc", end, endHint(limits), true));

  form.append(
    field("Tiêu đề", title, undefined, true),
    section(
      "Thời gian",
      field("Múi giờ", timezone, "Giờ nhập bên dưới được hiểu theo múi giờ này.", true),
      times,
      field("Nhắc trước", reminder, "Tính từ thời điểm bắt đầu của lịch."),
    ),
    section(
      "Chi tiết",
      field("Quốc gia", country, "Không thể đặt lịch vào ngày nghỉ chính thức của quốc gia này."),
      field("Địa điểm", location),
      field("Mô tả", description),
    ),
  );

  const actions = el("div", "actions");
  const submit = el("button", "btn btn--primary", schedule ? "Lưu thay đổi" : "Tạo lịch");
  submit.type = "submit";
  const cancel = el("button", "btn btn--ghost", "Hủy");
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

/** The resting state of the detail column: quiet, centred, no direction claimed. */
export function renderPlaceholder(text: string): HTMLElement {
  const panel = el("article", "panel panel--placeholder");
  const state = el("div", "emptystate");
  state.append(el("p", "empty", text));
  panel.append(state);
  return panel;
}

/**
 * Turns a backend message into something a user can act on.
 *
 * The API answers in English and sometimes in pydantic's wording; only those
 * known phrasings are translated, anything already written for people (and any
 * message this frontend produced) passes through untouched.
 */
export function friendlyMessage(error: ApiError): { text: string; hint?: string } {
  const raw = error.message;

  if (raw.includes("end_time must be after start_time")) {
    return { text: "Thời gian kết thúc phải sau thời gian bắt đầu." };
  }
  if (raw.includes("Schedule not found")) {
    return { text: "Lịch này không còn tồn tại. Có thể nó đã bị xóa ở nơi khác." };
  }
  if (raw.includes("Unknown timezone")) {
    return { text: "Múi giờ không hợp lệ. Hãy chọn lại trong danh sách." };
  }
  if (raw.includes("Unknown country")) {
    return { text: "Quốc gia không hợp lệ. Hãy chọn lại trong danh sách." };
  }
  if (raw.includes("String should have at least 1 character")) {
    return { text: "Vui lòng nhập tiêu đề cho lịch." };
  }
  if (raw.includes("String should have at most")) {
    return { text: "Nội dung nhập vào dài quá mức cho phép." };
  }
  if (error.status === 503) {
    return { text: "Chưa bật đồng bộ Google Calendar.", hint: raw };
  }
  if (error.status >= 500) {
    return { text: "Máy chủ đang gặp sự cố. Hãy thử lại sau ít phút.", hint: raw };
  }
  return { text: raw };
}

/**
 * "02:30 ngày Chủ Nhật, 08/03/2026" from a naive "2026-03-08T02:30:00".
 *
 * The value has no offset on purpose — it names a wall clock that never
 * happened, so there is no instant to format. Slicing it is the whole job.
 */
function wallClockWords(local: string): string {
  return `${local.slice(11, 16)} ngày ${formatDay(local.slice(0, 10))}`;
}

/** A short confirmation of something that just succeeded. */
export function renderToast(message: string): HTMLElement {
  return el("div", "toast", message);
}

export function renderError(
  error: ApiError,
  viewTimezone: string = "UTC",
  countries: Country[] = [],
): HTMLElement {
  const box = el("div", "error__body");
  const detail = error.detail;

  if (detail === null) {
    const friendly = friendlyMessage(error);
    box.append(el("p", "error__text", friendly.text));
    if (friendly.hint) box.append(el("p", "error__hint", friendly.hint));
    return box;
  }

  if (detail.kind === "duration") {
    const tooShort = detail.durationMinutes < detail.minMinutes;
    box.append(
      el(
        "p",
        "error__text",
        tooShort
          ? `Lịch quá ngắn: ${formatMinutes(detail.durationMinutes)}.`
          : `Lịch quá dài: ${formatMinutes(detail.durationMinutes)}.`,
      ),
    );
    box.append(
      el(
        "p",
        "error__hint",
        `Thời lượng phải từ ${formatMinutes(detail.minMinutes)} đến ` +
          `${formatMinutes(detail.maxMinutes)}.`,
      ),
    );
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

  if (detail.kind === "nonexistentTime") {
    const which = detail.field === "end_time" ? "Giờ kết thúc" : "Giờ bắt đầu";
    box.append(
      el(
        "p",
        "error__text",
        `${which} bạn chọn không tồn tại ở ${detail.timezone}: ` +
          `${wallClockWords(detail.localTime)}.`,
      ),
    );
    box.append(
      el(
        "p",
        "error__hint",
        `Hôm đó đồng hồ ở múi giờ này được vặn nhanh ${formatMinutes(detail.gapMinutes)} để ` +
          `đổi sang giờ mùa hè (DST), nên quãng thời gian đó bị bỏ qua. Hãy chọn một giờ trước ` +
          `lúc đổi, hoặc từ ${wallClockWords(detail.nextValid)} trở đi.`,
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

