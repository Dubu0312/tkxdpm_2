import { describe, expect, it, vi } from "vitest";

import type { Schedule } from "./types";
import { renderDetail, renderForm, renderList } from "./views";

function schedule(overrides: Partial<Schedule> = {}): Schedule {
  return {
    id: 1,
    title: "Họp nhóm",
    description: "Review sprint",
    location: "Phòng A1",
    start_time: "2026-09-01T09:00:00",
    end_time: "2026-09-01T10:30:00",
    created_at: "2026-08-25T08:00:00",
    updated_at: "2026-08-25T08:00:00",
    ...overrides,
  };
}

describe("renderList", () => {
  it("shows an empty state when there is nothing to list", () => {
    const node = renderList([], null, () => {});
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
    );
    expect(node.querySelectorAll(".day")).toHaveLength(2);
    expect(node.querySelectorAll(".card")).toHaveLength(3);
  });

  it("marks the selected card and reports clicks", () => {
    const onSelect = vi.fn();
    const node = renderList([schedule({ id: 7 })], 7, onSelect);
    const card = node.querySelector<HTMLButtonElement>(".card")!;
    expect(card.classList.contains("card--active")).toBe(true);
    card.click();
    expect(onSelect).toHaveBeenCalledWith(7);
  });

  it("renders titles as text, not markup", () => {
    const node = renderList([schedule({ title: "<img src=x onerror=alert(1)>" })], null, () => {});
    expect(node.querySelector("img")).toBeNull();
    expect(node.querySelector(".card__title")?.textContent).toBe("<img src=x onerror=alert(1)>");
  });
});

describe("renderDetail", () => {
  it("shows the schedule fields and wires the actions", () => {
    const onEdit = vi.fn();
    const onDelete = vi.fn();
    const node = renderDetail(schedule(), { onEdit, onDelete });

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
    const node = renderDetail(schedule({ location: null, description: null }), {
      onEdit: () => {},
      onDelete: () => {},
    });
    expect([...node.querySelectorAll("dd")].map((dd) => dd.textContent).slice(0, 2)).toEqual([
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
