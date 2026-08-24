/**
 * Datetime helpers. The backend speaks naive local wall-clock ISO strings
 * ("2026-09-01T09:00:00"), which is exactly what <input type="datetime-local">
 * produces — so conversion is string slicing, never a timezone shift.
 */

/** "2026-09-01T09:00:00" -> "2026-09-01T09:00" (value for datetime-local). */
export function toInputValue(iso: string): string {
  return iso.slice(0, 16);
}

/** "2026-09-01T09:00" -> "2026-09-01T09:00:00" (payload for the API). */
export function toApiValue(inputValue: string): string {
  return inputValue.length === 16 ? `${inputValue}:00` : inputValue;
}

const dateFormatter = new Intl.DateTimeFormat("vi-VN", {
  weekday: "short",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

function parseLocal(iso: string): Date {
  const [datePart, timePart = "00:00:00"] = iso.split("T");
  const [year, month, day] = datePart.split("-").map(Number);
  const [hour, minute] = timePart.split(":").map(Number);
  return new Date(year, month - 1, day, hour, minute);
}

export function formatDate(iso: string): string {
  return dateFormatter.format(parseLocal(iso));
}

export function formatTime(iso: string): string {
  return iso.slice(11, 16);
}

/** "Thứ Ba, 01/09/2026 · 09:00 – 10:30" (or with both dates when they differ). */
export function formatRange(startIso: string, endIso: string): string {
  const sameDay = startIso.slice(0, 10) === endIso.slice(0, 10);
  if (sameDay) {
    return `${formatDate(startIso)} · ${formatTime(startIso)} – ${formatTime(endIso)}`;
  }
  return `${formatDate(startIso)} ${formatTime(startIso)} – ${formatDate(endIso)} ${formatTime(endIso)}`;
}

/** Rounded duration such as "1 giờ 30 phút". */
export function formatDuration(startIso: string, endIso: string): string {
  const minutes = Math.round(
    (parseLocal(endIso).getTime() - parseLocal(startIso).getTime()) / 60000,
  );
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${rest} phút`;
  if (rest === 0) return `${hours} giờ`;
  return `${hours} giờ ${rest} phút`;
}

/** Local "now" as a datetime-local input value, used to prefill the form. */
export function nowInputValue(offsetMinutes = 0): string {
  const now = new Date(Date.now() + offsetMinutes * 60000);
  now.setSeconds(0, 0);
  const pad = (value: number) => String(value).padStart(2, "0");
  return (
    `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}` +
    `T${pad(now.getHours())}:${pad(now.getMinutes())}`
  );
}
