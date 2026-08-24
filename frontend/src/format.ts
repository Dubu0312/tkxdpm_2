/**
 * Timezone-aware datetime helpers.
 *
 * The API returns instants with an explicit offset, in each schedule's own
 * timezone (`2026-09-01T09:00:00+09:00`). Two directions matter here:
 *
 * - **Display**: an instant is formatted in whatever timezone the user is
 *   looking at, via `Intl.DateTimeFormat` — the browser owns the offset rules.
 * - **Input**: `<input type="datetime-local">` yields a naive wall-clock value,
 *   which is sent unchanged together with the chosen `timezone`; the backend
 *   resolves it to an instant. No offset arithmetic happens in the browser.
 */

const FALLBACK_ZONES = [
  "UTC",
  "Asia/Ho_Chi_Minh",
  "Asia/Bangkok",
  "Asia/Tokyo",
  "Asia/Singapore",
  "Europe/London",
  "Europe/Paris",
  "America/New_York",
  "America/Los_Angeles",
  "Australia/Sydney",
];

/** The viewer's own timezone, e.g. "Asia/Ho_Chi_Minh". */
export function browserTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
}

/**
 * Every IANA zone the runtime knows about, with a small fallback list.
 *
 * `supportedValuesOf` reports canonical ids only, so aliases (`Asia/Ho_Chi_Minh`
 * for `Asia/Saigon`) and plain `UTC` are missing from it even though both are
 * accepted everywhere — `UTC` is added back here, aliases are handled by
 * `sameZone` / `timezoneSelect`.
 */
export function listTimezones(): string[] {
  const supported = (Intl as { supportedValuesOf?: (key: string) => string[] }).supportedValuesOf;
  const zones = supported ? supported.call(Intl, "timeZone") : FALLBACK_ZONES;
  if (zones.length === 0) return FALLBACK_ZONES;
  return zones.includes("UTC") ? zones : ["UTC", ...zones];
}

/**
 * The runtime's canonical id for a zone, or the input if it is not a valid zone.
 * Used for comparison only — what the user picked is what gets stored.
 */
export function canonicalTimezone(name: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, { timeZone: name }).resolvedOptions().timeZone;
  } catch {
    return name;
  }
}

/** True when two identifiers name the same zone, aliases included. */
export function sameZone(a: string, b: string): boolean {
  return a === b || canonicalTimezone(a) === canonicalTimezone(b);
}

export function parseInstant(iso: string): Date {
  return new Date(iso);
}

interface ZonedParts {
  year: string;
  month: string;
  day: string;
  hour: string;
  minute: string;
}

function partsInZone(instant: Date, timeZone: string): ZonedParts {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
  const parts: Record<string, string> = {};
  for (const part of formatter.formatToParts(instant)) {
    if (part.type !== "literal") parts[part.type] = part.value;
  }
  return parts as unknown as ZonedParts;
}

/** "2026-09-01" — the calendar day the instant falls on in `timeZone`. */
export function dayKeyInZone(iso: string, timeZone: string): string {
  const { year, month, day } = partsInZone(parseInstant(iso), timeZone);
  return `${year}-${month}-${day}`;
}

/** "2026-09-01T09:00" — wall-clock value for a datetime-local input. */
export function wallClockInZone(instant: Date, timeZone: string): string {
  const { year, month, day, hour, minute } = partsInZone(instant, timeZone);
  return `${year}-${month}-${day}T${hour}:${minute}`;
}

/**
 * Wall-clock value of an API datetime in its own timezone.
 *
 * The API already renders it there, so this is a slice, not a conversion — the
 * edit form shows exactly the time that was typed.
 */
export function toInputValue(iso: string): string {
  return iso.slice(0, 16);
}

/**
 * Whole calendar days between the two instants as seen from `timeZone`.
 *
 * 0 for a schedule that starts and ends on the same local day, 1 for one that
 * runs past midnight, and more for a longer range. Because it compares local
 * days, the answer follows the timezone being viewed.
 */
export function dayOffsetInZone(startIso: string, endIso: string, timeZone: string): number {
  const start = dayKeyInZone(startIso, timeZone);
  const end = dayKeyInZone(endIso, timeZone);
  if (start === end) return 0;
  const days = (key: string) => Date.parse(`${key}T00:00:00Z`) / 86400000;
  return Math.round(days(end) - days(start));
}

/**
 * Minutes from one datetime-local value to another.
 *
 * Both are wall-clock strings, so they are parsed as UTC: the result is the
 * difference the user sees on the clock, with no timezone or DST rules mixed in.
 */
export function wallClockDeltaMinutes(from: string, to: string): number {
  return (Date.parse(`${to}:00Z`) - Date.parse(`${from}:00Z`)) / 60000;
}

/** Move a datetime-local value by whole minutes, rolling the date as needed. */
export function shiftWallClock(value: string, deltaMinutes: number): string {
  const shifted = new Date(Date.parse(`${value}:00Z`) + deltaMinutes * 60000);
  return shifted.toISOString().slice(0, 16);
}

/** "2026-09-01T09:00" -> "2026-09-01T09:00:00" (payload for the API). */
export function toApiValue(inputValue: string): string {
  return inputValue.length === 16 ? `${inputValue}:00` : inputValue;
}

/** Local "now" in `timeZone` as a datetime-local value, used to prefill the form. */
export function nowInputValue(offsetMinutes: number, timeZone: string): string {
  return wallClockInZone(new Date(Date.now() + offsetMinutes * 60000), timeZone);
}

export function formatDate(iso: string, timeZone: string): string {
  return new Intl.DateTimeFormat("vi-VN", {
    timeZone,
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(parseInstant(iso));
}

/** "Thứ Ba, 17/02/2026" from a bare day key such as "2026-02-17". */
export function formatDay(dayKey: string): string {
  // Noon UTC keeps the date stable no matter how the formatter is anchored.
  return formatDate(`${dayKey}T12:00:00Z`, "UTC");
}

export function formatTime(iso: string, timeZone: string): string {
  const { hour, minute } = partsInZone(parseInstant(iso), timeZone);
  return `${hour}:${minute}`;
}

/** "UTC+07:00" for the given instant — offsets move with DST, hence the instant. */
export function offsetLabel(iso: string, timeZone: string): string {
  const formatted = new Intl.DateTimeFormat("en-US", {
    timeZone,
    timeZoneName: "longOffset",
  }).format(parseInstant(iso));
  const offset = formatted.split(", ").pop() ?? "GMT";
  return offset.replace("GMT", "UTC") === "UTC" ? "UTC+00:00" : offset.replace("GMT", "UTC");
}

/** "Thứ Ba, 01/09/2026 · 09:00 – 10:30" as seen from `timeZone`. */
export function formatRange(startIso: string, endIso: string, timeZone: string): string {
  const sameDay = dayKeyInZone(startIso, timeZone) === dayKeyInZone(endIso, timeZone);
  if (sameDay) {
    return (
      `${formatDate(startIso, timeZone)} · ` +
      `${formatTime(startIso, timeZone)} – ${formatTime(endIso, timeZone)}`
    );
  }
  return (
    `${formatDate(startIso, timeZone)} ${formatTime(startIso, timeZone)} – ` +
    `${formatDate(endIso, timeZone)} ${formatTime(endIso, timeZone)}`
  );
}

/** A span of minutes in words: "45 phút", "2 giờ", "1 giờ 30 phút", "1 ngày". */
export function formatMinutes(minutes: number): string {
  if (minutes >= 1440 && minutes % 1440 === 0) return `${minutes / 1440} ngày`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${rest} phút`;
  if (rest === 0) return `${hours} giờ`;
  return `${hours} giờ ${rest} phút`;
}

/** Rounded real duration — independent of any timezone. */
export function formatDuration(startIso: string, endIso: string): string {
  return formatMinutes(
    Math.round((parseInstant(endIso).getTime() - parseInstant(startIso).getTime()) / 60000),
  );
}
