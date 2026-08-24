import { describe, expect, it } from "vitest";

import {
  formatDuration,
  formatRange,
  formatTime,
  nowInputValue,
  toApiValue,
  toInputValue,
} from "./format";

describe("datetime conversion", () => {
  it("strips seconds for datetime-local inputs", () => {
    expect(toInputValue("2026-09-01T09:00:00")).toBe("2026-09-01T09:00");
  });

  it("adds seconds back for the API", () => {
    expect(toApiValue("2026-09-01T09:00")).toBe("2026-09-01T09:00:00");
  });

  it("leaves an already complete value untouched", () => {
    expect(toApiValue("2026-09-01T09:00:00")).toBe("2026-09-01T09:00:00");
  });

  it("round-trips without shifting the wall-clock time", () => {
    expect(toApiValue(toInputValue("2026-09-01T23:30:00"))).toBe("2026-09-01T23:30:00");
  });
});

describe("display helpers", () => {
  it("shows the time part as typed", () => {
    expect(formatTime("2026-09-01T09:05:00")).toBe("09:05");
  });

  it("collapses a same-day range to one date", () => {
    const text = formatRange("2026-09-01T09:00:00", "2026-09-01T10:30:00");
    expect(text).toContain("09:00 – 10:30");
    expect(text.match(/2026/g)).toHaveLength(1);
  });

  it("keeps both dates for a multi-day range", () => {
    const text = formatRange("2026-09-01T23:00:00", "2026-09-02T01:00:00");
    expect(text.match(/2026/g)).toHaveLength(2);
  });

  it("formats durations", () => {
    expect(formatDuration("2026-09-01T09:00:00", "2026-09-01T09:45:00")).toBe("45 phút");
    expect(formatDuration("2026-09-01T09:00:00", "2026-09-01T11:00:00")).toBe("2 giờ");
    expect(formatDuration("2026-09-01T09:00:00", "2026-09-01T10:30:00")).toBe("1 giờ 30 phút");
  });

  it("produces a valid datetime-local value for the form default", () => {
    expect(nowInputValue(60)).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
  });
});
