import "./style.css";
import {
  ApiError,
  createSchedule,
  deleteSchedule,
  listCountries,
  listSchedules,
  updateSchedule,
} from "./api";
import { browserTimezone, toApiValue } from "./format";
import type { Country, Schedule, ScheduleInput } from "./types";
import {
  renderDetail,
  renderError,
  renderForm,
  renderList,
  renderPlaceholder,
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
}

const state: State = {
  schedules: [],
  view: { name: "none" },
  loading: true,
  error: null,
  draft: null,
  viewTimezone: browserTimezone(),
  countries: [],
};

const listSlot = document.querySelector<HTMLElement>("#list")!;
const panelSlot = document.querySelector<HTMLElement>("#panel")!;
const errorSlot = document.querySelector<HTMLElement>("#error")!;
const countSlot = document.querySelector<HTMLElement>("#count")!;
const createButton = document.querySelector<HTMLButtonElement>("#create")!;
const timezoneSlot = document.querySelector<HTMLElement>("#timezone")!;

function find(id: number): Schedule | undefined {
  return state.schedules.find((schedule) => schedule.id === id);
}

function setView(view: View): void {
  state.view = view;
  state.error = null;
  state.draft = null;
  render();
}

function fail(error: unknown, draft: ScheduleInput | null = null): void {
  state.error = error instanceof ApiError ? error : new ApiError(String(error), 0);
  state.draft = draft;
  render();
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
    // The country list never changes while the page is open, so load it once.
    if (state.countries.length === 0) {
      state.countries = await listCountries();
    }
    state.schedules = await listSchedules();
    state.error = null;
    state.draft = null;
  } catch (error) {
    fail(error);
    return;
  } finally {
    state.loading = false;
  }
  // Drop a selection that no longer exists (e.g. removed in another tab).
  if ((state.view.name === "detail" || state.view.name === "edit") && !find(state.view.id)) {
    state.view = { name: "none" };
  }
  render();
}

async function submitCreate(input: ScheduleInput): Promise<void> {
  try {
    const created = await createSchedule(toPayload(input));
    state.schedules = await listSchedules();
    setView({ name: "detail", id: created.id });
  } catch (error) {
    fail(error, input);
  }
}

async function submitEdit(id: number, input: ScheduleInput): Promise<void> {
  try {
    await updateSchedule(id, toPayload(input));
    state.schedules = await listSchedules();
    setView({ name: "detail", id });
  } catch (error) {
    fail(error, input);
  }
}

async function confirmDelete(schedule: Schedule): Promise<void> {
  if (!window.confirm(`Xóa lịch “${schedule.title}”?`)) return;
  try {
    await deleteSchedule(schedule.id);
    state.schedules = await listSchedules();
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
      );
    }
    case "detail": {
      const schedule = find(state.view.id);
      if (!schedule) return renderPlaceholder("Lịch không còn tồn tại.");
      return renderDetail(
        schedule,
        {
          onEdit: () => setView({ name: "edit", id: schedule.id }),
          onDelete: () => void confirmDelete(schedule),
        },
        state.viewTimezone,
        state.countries,
      );
    }
    default:
      return renderPlaceholder("Chọn một lịch ở danh sách bên trái để xem chi tiết.");
  }
}

function render(): void {
  const selectedId =
    state.view.name === "detail" || state.view.name === "edit" ? state.view.id : null;

  listSlot.replaceChildren(
    state.loading && state.schedules.length === 0
      ? Object.assign(document.createElement("p"), {
          className: "empty",
          textContent: "Đang tải…",
        })
      : renderList(
          state.schedules,
          selectedId,
          (id) => setView({ name: "detail", id }),
          state.viewTimezone,
        ),
  );

  panelSlot.replaceChildren(renderPanel());

  countSlot.textContent = `${state.schedules.length} lịch`;

  errorSlot.replaceChildren(
    ...(state.error ? [renderError(state.error, state.viewTimezone, state.countries)] : []),
  );
  errorSlot.hidden = state.error === null;
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
