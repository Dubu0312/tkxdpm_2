import "./style.css";
import {
  ApiError,
  createSchedule,
  deleteSchedule,
  listSchedules,
  updateSchedule,
} from "./api";
import { toApiValue } from "./format";
import type { Schedule, ScheduleInput } from "./types";
import { renderDetail, renderForm, renderList, renderPlaceholder } from "./views";

type View =
  | { name: "none" }
  | { name: "detail"; id: number }
  | { name: "create" }
  | { name: "edit"; id: number };

interface State {
  schedules: Schedule[];
  view: View;
  loading: boolean;
  error: string | null;
}

const state: State = { schedules: [], view: { name: "none" }, loading: true, error: null };

const listSlot = document.querySelector<HTMLElement>("#list")!;
const panelSlot = document.querySelector<HTMLElement>("#panel")!;
const errorSlot = document.querySelector<HTMLElement>("#error")!;
const countSlot = document.querySelector<HTMLElement>("#count")!;
const createButton = document.querySelector<HTMLButtonElement>("#create")!;

function find(id: number): Schedule | undefined {
  return state.schedules.find((schedule) => schedule.id === id);
}

function setView(view: View): void {
  state.view = view;
  render();
}

function fail(error: unknown): void {
  state.error = error instanceof ApiError ? error.message : String(error);
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
    state.schedules = await listSchedules();
    state.error = null;
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
    state.error = null;
    state.schedules = await listSchedules();
    setView({ name: "detail", id: created.id });
  } catch (error) {
    fail(error);
  }
}

async function submitEdit(id: number, input: ScheduleInput): Promise<void> {
  try {
    await updateSchedule(id, toPayload(input));
    state.error = null;
    state.schedules = await listSchedules();
    setView({ name: "detail", id });
  } catch (error) {
    fail(error);
  }
}

async function confirmDelete(schedule: Schedule): Promise<void> {
  if (!window.confirm(`Xóa lịch “${schedule.title}”?`)) return;
  try {
    await deleteSchedule(schedule.id);
    state.error = null;
    state.schedules = await listSchedules();
    setView({ name: "none" });
  } catch (error) {
    fail(error);
  }
}

function renderPanel(): HTMLElement {
  switch (state.view.name) {
    case "create":
      return renderForm(null, {
        onSubmit: (input) => void submitCreate(input),
        onCancel: () => setView({ name: "none" }),
      });
    case "edit": {
      const schedule = find(state.view.id);
      if (!schedule) return renderPlaceholder("Lịch không còn tồn tại.");
      const id = schedule.id;
      return renderForm(schedule, {
        onSubmit: (input) => void submitEdit(id, input),
        onCancel: () => setView({ name: "detail", id }),
      });
    }
    case "detail": {
      const schedule = find(state.view.id);
      if (!schedule) return renderPlaceholder("Lịch không còn tồn tại.");
      return renderDetail(schedule, {
        onEdit: () => setView({ name: "edit", id: schedule.id }),
        onDelete: () => void confirmDelete(schedule),
      });
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
      : renderList(state.schedules, selectedId, (id) => setView({ name: "detail", id })),
  );

  panelSlot.replaceChildren(renderPanel());

  countSlot.textContent = `${state.schedules.length} lịch`;

  errorSlot.textContent = state.error ?? "";
  errorSlot.hidden = state.error === null;
}

createButton.addEventListener("click", () => setView({ name: "create" }));

void refresh();
