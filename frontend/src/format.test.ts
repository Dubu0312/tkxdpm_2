import { describe, expect, it } from "vitest";

import {
  browserTimezone,
  canonicalTimezone,
  dayKeyInZone,
  formatDate,
  formatDuration,
  formatRange,
  formatTime,
  listTimezones,
  nowInputValue,
  offsetLabel,
  sameZone,
  toApiValue,
  toInputValue,
  wallClockInZone,
} from "./format";

const TOKYO = "Asia/Tokyo"; // +09:00
const SAIGON = "Asia/Ho_Chi_Minh"; // +07:00
const NEW_YORK = "America/New_York"; // -05:00 / -04:00

// 2026-09-01T09:00:00+09:00 is 00:00 UTC, i.e. 07:00 in Saigon.
const START = "2026-09-01T09:00:00+09:00";
const END = "2026-09-01T10:30:00+09:00";

describe("form value conversion", () => {
  it("takes the wall clock straight from the API string", () => {
    expect(toInputValue(START)).toBe("2026-09-01T09:00");
  });

  it("adds seconds back for the API", () => {
    expect(toApiValue("2026-09-01T09:00")).toBe("2026-09-01T09:00:00");
    expect(toApiValue("2026-09-01T09:00:00")).toBe("2026-09-01T09:00:00");
  });

  it("round-trips the typed time without shifting it", () => {
    expect(toApiValue(toInputValue(START))).toBe("2026-09-01T09:00:00");
  });

  it("builds a datetime-local value in the requested zone", () => {
    const instant = new Date("2026-09-01T00:00:00Z");
    expect(wallClockInZone(instant, TOKYO)).toBe("2026-09-01T09:00");
    expect(wallClockInZone(instant, SAIGON)).toBe("2026-09-01T07:00");
    expect(wallClockInZone(instant, "UTC")).toBe("2026-09-01T00:00");
  });

  it("prefills the form with a valid value in the chosen zone", () => {
    expect(nowInputValue(60, TOKYO)).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
  });
});

describe("viewing one instant from different timezones", () => {
  it("shows the same instant as a different wall clock", () => {
    expect(formatTime(START, TOKYO)).toBe("09:00");
    expect(formatTime(START, SAIGON)).toBe("07:00");
    expect(formatTime(START, "UTC")).toBe("00:00");
    expect(formatTime(START, NEW_YORK)).toBe("20:00"); // previous day
  });

  it("can land on a different calendar day", () => {
    expect(dayKeyInZone(START, TOKYO)).toBe("2026-09-01");
    expect(dayKeyInZone(START, NEW_YORK)).toBe("2026-08-31");
    expect(formatDate(START, NEW_YORK)).toContain("31/08/2026");
  });

  it("keeps the real duration whatever zone it is read in", () => {
    expect(formatDuration(START, END)).toBe("1 giờ 30 phút");
    expect(formatDuration("2026-09-01T09:00:00+09:00", "2026-09-01T03:00:00+00:00")).toBe(
      "3 giờ",
    );
  });

  it("collapses a same-day range but splits one that crosses midnight in view", () => {
    const sameDay = formatRange(START, END, TOKYO);
    expect(sameDay).toContain("09:00 – 10:30");
    expect(sameDay.match(/2026/g)).toHaveLength(1);

    // In New York the same range starts on 31/08 and ends on 31/08 too, but a
    // range crossing local midnight keeps both dates.
    const crossing = formatRange("2026-09-01T23:30:00+09:00", "2026-09-02T00:30:00+09:00", TOKYO);
    expect(crossing.match(/2026/g)).toHaveLength(2);
  });

  it("labels the offset in effect at that instant", () => {
    expect(offsetLabel(START, TOKYO)).toBe("UTC+09:00");
    expect(offsetLabel(START, "UTC")).toBe("UTC+00:00");
    // DST: New York is -04:00 in July and -05:00 in January.
    expect(offsetLabel("2026-07-15T12:00:00Z", NEW_YORK)).toBe("UTC-04:00");
    expect(offsetLabel("2026-01-15T12:00:00Z", NEW_YORK)).toBe("UTC-05:00");
  });
});

describe("timezone lookup", () => {
  it("reports a usable browser timezone", () => {
    expect(browserTimezone()).toMatch(/^[A-Za-z_]+(\/[A-Za-z_+-]+)*$/);
  });

  it("lists real IANA zones and always offers UTC", () => {
    const zones = listTimezones();
    expect(zones.length).toBeGreaterThan(5);
    expect(zones).toContain("Asia/Tokyo");
    // supportedValuesOf omits plain "UTC" even though every runtime accepts it.
    expect(zones).toContain("UTC");
  });

  it("resolves alias identifiers to the runtime's canonical name", () => {
    // Asia/Ho_Chi_Minh and Asia/Saigon are the same zone under different ids.
    expect(canonicalTimezone(SAIGON)).toBe(canonicalTimezone("Asia/Saigon"));
    expect(canonicalTimezone(TOKYO)).toBe(TOKYO);
  });

  it("returns an unknown identifier unchanged instead of throwing", () => {
    expect(canonicalTimezone("Mars/Olympus")).toBe("Mars/Olympus");
  });

  it("treats aliases as the same zone", () => {
    expect(sameZone(SAIGON, "Asia/Saigon")).toBe(true);
    expect(sameZone(TOKYO, TOKYO)).toBe(true);
    expect(sameZone(TOKYO, SAIGON)).toBe(false);
  });
});
