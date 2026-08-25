import "./style.css";
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
  updateSchedule,
} from "./api";
import { browserTimezone, toApiValue, wallClockDeltaMinutes } from "./format";
import type { Country, GoogleStatus, Limits, Schedule, ScheduleInput } from "./types";
import {
  renderDetail,
  renderError,
  renderForm,
  renderList,
  renderPlaceholder,
  renderSkeleton,
  renderToast,
  timezoneSelect,
} from "./views";

type View =
  | { name: "none" }
  | { name: "detail"; id: number }
  | { name: "create" }
  | { name: "edit"; id: number };

interface State {
  schedules: Schedule[];
  view: View;
  loading: boolean;
  error: ApiError | null;
  /** Values of a submission the backend rejected, so the form keeps them. */
  draft: ScheduleInput | null;
  /** Timezone every listed time is displayed in; defaults to the browser's. */
  viewTimezone: string;
  /** Countries the backend can check holidays for; loaded once at startup. */
  countries: Country[];
  /** Duration limits served by the backend; null until they are loaded. */
  limits: Limits | null;
  /** Whether Google Calendar syncing is available; null until loaded. */
  google: GoogleStatus | null;
  /** A short confirmation of the last successful action. */
  notice: string | null;
  /** True while a delete is waiting for confirmation in the detail panel. */
  confirmingDelete: boolean;
  /** True while an action is in flight, so its buttons cannot be pressed twice. */
  busy: boolean;
}

const state: State = {
  schedules: [],
  view: { name: "none" },
  loading: true,
  error: null,
  draft: null,
  viewTimezone: browserTimezone(),
  countries: [],
  limits: null,
  google: null,
  notice: null,
  confirmingDelete: false,
  busy: false,
};

const listSlot = document.querySelector<HTMLElement>("#list")!;
const panelSlot = document.querySelector<HTMLElement>("#panel")!;
const errorSlot = document.querySelector<HTMLElement>("#error")!;
const countSlot = document.querySelector<HTMLElement>("#count")!;
const createButton = document.querySelector<HTMLButtonElement>("#create")!;
const timezoneSlot = document.querySelector<HTMLElement>("#timezone")!;
const toastSlot = document.querySelector<HTMLElement>("#toast")!;

let noticeTimer: ReturnType<typeof setTimeout> | undefined;

/** Show a short confirmation that clears itself. */
function notify(message: string): void {
  state.notice = message;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => {
    state.notice = null;
    render();
  }, 4000);
}

function find(id: number): Schedule | undefined {
  return state.schedules.find((schedule) => schedule.id === id);
}

function setView(view: View): void {
  state.view = view;
  state.error = null;
  state.draft = null;
  state.confirmingDelete = false;
  render();
  revealPanel(view);
}

/**
 * Below the two-column breakpoint the panel sits under the list, so opening a
 * schedule would otherwise change something off-screen.
 */
function revealPanel(view: View): void {
  if (view.name === "none") return;
  if (typeof window.matchMedia !== "function") return;
  if (!window.matchMedia("(max-width: 900px)").matches) return;
  if (typeof panelSlot.scrollIntoView !== "function") return;
  panelSlot.scrollIntoView({ block: "start" });
}

function fail(error: unknown, draft: ScheduleInput | null = null): void {
  state.error = error instanceof ApiError ? error : new ApiError(String(error), 0);
  state.draft = draft;
  state.busy = false;
  render();
}

/**
 * Catch an obviously bad length before making a round trip.
 *
 * This compares the wall-clock values, which equals the real duration except
 * across a DST change in the chosen timezone. The backend measures between the
 * instants and stays the authority — this only saves a request.
 */
function checkDuration(input: ScheduleInput): ApiError | null {
  const limits = state.limits;
  if (limits === null) return null;

  const minutes = wallClockDeltaMinutes(input.start_time, input.end_time);
  if (minutes <= 0) return null; // "end must be after start" is the backend's message
  if (minutes >= limits.min_duration_minutes && minutes <= limits.max_duration_minutes) {
    return null;
  }
  return new ApiError(`Schedule lasts ${minutes} minutes`, 422, {
    kind: "duration",
    durationMinutes: minutes,
    minMinutes: limits.min_duration_minutes,
    maxMinutes: limits.max_duration_minutes,
  });
}

function toPayload(input: ScheduleInput): ScheduleInput {
  return {
    ...input,
    start_time: toApiValue(input.start_time),
    end_time: toApiValue(input.end_time),
  };
}

async function refresh(): Promise<void> {
  state.loading = true;
  render();
  try {
    // Neither the country list nor the limits change while the page is open.
    if (state.countries.length === 0) {
      state.countries = await listCountries();
    }
    if (state.limits === null) {
      state.limits = await fetchLimits();
    }
    if (state.google === null) {
      state.google = await fetchGoogleStatus();
    }
    state.schedules = await listSchedules();
    state.error = null;
    // The draft belongs to the form, not to this load: a refresh finishing in
    // the background must not discard what the user is in the middle of typing.
  } catch (error) {
    // Clear the loading flag before rendering the failure: fail() re-renders,
    // and a list still marked as loading stays stuck on "Đang tải…" for good.
    state.loading = false;
    fail(error);
    return;
  }
  state.loading = false;
  // Drop a selection that no longer exists (e.g. removed in another tab).
  if ((state.view.name === "detail" || state.view.name === "edit") && !find(state.view.id)) {
    state.view = { name: "none" };
  }
  render();
}

async function submitCreate(input: ScheduleInput): Promise<void> {
  const tooLongOrShort = checkDuration(input);
  if (tooLongOrShort) return fail(tooLongOrShort, input);

  try {
    const created = await createSchedule(toPayload(input));
    state.schedules = await listSchedules();
    notify(`Đã tạo lịch “${created.title}”.`);
    setView({ name: "detail", id: created.id });
  } catch (error) {
    fail(error, input);
  }
}

async function submitEdit(id: number, input: ScheduleInput): Promise<void> {
  const tooLongOrShort = checkDuration(input);
  if (tooLongOrShort) return fail(tooLongOrShort, input);

  try {
    const saved = await updateSchedule(id, toPayload(input));
    state.schedules = await listSchedules();
    notify(`Đã lưu thay đổi cho “${saved.title}”.`);
    setView({ name: "detail", id });
  } catch (error) {
    fail(error, input);
  }
}

async function syncGoogle(schedule: Schedule): Promise<void> {
  state.busy = true;
  render();
  try {
    await syncToGoogle(schedule.id);
    state.error = null;
    state.schedules = await listSchedules();
    state.busy = false;
    notify(`Đã đồng bộ “${schedule.title}” sang Google Calendar.`);
    render();
  } catch (error) {
    fail(error);
  }
}

async function unlinkGoogle(schedule: Schedule): Promise<void> {
  state.busy = true;
  render();
  try {
    await unlinkFromGoogle(schedule.id);
    state.error = null;
    state.schedules = await listSchedules();
    state.busy = false;
    notify(`Đã bỏ liên kết Google của “${schedule.title}”.`);
    render();
  } catch (error) {
    fail(error);
  }
}

async function removeSchedule(schedule: Schedule): Promise<void> {
  state.busy = true;
  render();
  try {
    await deleteSchedule(schedule.id);
    state.schedules = await listSchedules();
    state.busy = false;
    notify(`Đã xóa lịch “${schedule.title}”.`);
    setView({ name: "none" });
  } catch (error) {
    fail(error);
  }
}

function renderPanel(): HTMLElement {
  switch (state.view.name) {
    case "create":
      return renderForm(
        null,
        {
          onSubmit: (input) => void submitCreate(input),
          onCancel: () => setView({ name: "none" }),
        },
        state.draft,
        state.viewTimezone,
        state.countries,
        state.limits,
      );
    case "edit": {
      const schedule = find(state.view.id);
      if (!schedule) return renderPlaceholder("Lịch không còn tồn tại.");
      const id = schedule.id;
      return renderForm(
        schedule,
        {
          onSubmit: (input) => void submitEdit(id, input),
          onCancel: () => setView({ name: "detail", id }),
        },
        state.draft,
        state.viewTimezone,
        state.countries,
        state.limits,
      );
    }
    case "detail": {
      const schedule = find(state.view.id);
      if (!schedule) return renderPlaceholder("Lịch không còn tồn tại.");
      return renderDetail(
        schedule,
        {
          onEdit: () => setView({ name: "edit", id: schedule.id }),
          onDelete: () => {
            state.confirmingDelete = true;
            render();
          },
          onDeleteConfirm: () => void removeSchedule(schedule),
          onDeleteCancel: () => {
            state.confirmingDelete = false;
            render();
          },
          onGoogleSync: () => void syncGoogle(schedule),
          onGoogleUnlink: () => void unlinkGoogle(schedule),
        },
        state.viewTimezone,
        state.countries,
        state.google,
        { confirmingDelete: state.confirmingDelete, busy: state.busy },
      );
    }
    default:
      return renderPlaceholder("Chọn một lịch trong danh sách để xem chi tiết.");
  }
}

function render(): void {
  const selectedId =
    state.view.name === "detail" || state.view.name === "edit" ? state.view.id : null;

  listSlot.replaceChildren(
    state.loading && state.schedules.length === 0
      ? renderSkeleton()
      : renderList(
          state.schedules,
          selectedId,
          (id) => setView({ name: "detail", id }),
          state.viewTimezone,
          () => setView({ name: "create" }),
        ),
  );

  panelSlot.replaceChildren(renderPanel());

  countSlot.textContent = state.loading && state.schedules.length === 0
    ? "Đang tải…"
    : `${state.schedules.length} lịch`;

  errorSlot.replaceChildren(
    ...(state.error ? [renderError(state.error, state.viewTimezone, state.countries)] : []),
  );
  errorSlot.hidden = state.error === null;

  toastSlot.replaceChildren(...(state.notice ? [renderToast(state.notice)] : []));
}

createButton.addEventListener("click", () => setView({ name: "create" }));

// Changing the view timezone only re-renders: the stored instants never move.
const timezonePicker = timezoneSelect(state.viewTimezone);
timezonePicker.id = "view-timezone";
timezonePicker.setAttribute("aria-label", "Múi giờ hiển thị");
timezonePicker.addEventListener("change", () => {
  state.viewTimezone = timezonePicker.value;
  render();
});
timezoneSlot.replaceChildren(timezonePicker);

void refresh();
