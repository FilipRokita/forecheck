const LOCALE = "en-GB";
const DASH = "–";

/** A fixed number of decimals, with a plain decimal point. Returns an en dash for a missing value. */
export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  return new Intl.NumberFormat(LOCALE, { minimumFractionDigits: digits, maximumFractionDigits: digits, useGrouping: false }).format(value);
}

/** A share between 0 and 1 as a whole percent. */
export function formatPercent(share: number | null | undefined): string {
  if (share === null || share === undefined || Number.isNaN(share)) return DASH;
  return `${Math.round(share * 100)}%`;
}

/** A value with its unit, for example "1.3 °C". Percent and bare numbers need no space. */
export function formatWithUnit(value: number | null | undefined, unit: string, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  return `${formatNumber(value, digits)} ${unit}`;
}

/** "20 Oct 2026" from a YYYY-MM-DD string, read as a calendar date (no time zone shifts). */
export function formatDay(day: string | null | undefined): string {
  if (!day) return DASH;
  const [year, month, date] = day.split("-").map(Number);
  if (!year || !month || !date) return DASH;
  return new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(
    new Date(Date.UTC(year, month - 1, date)),
  );
}

export function plural(count: number, one: string, many: string): string {
  return count === 1 ? one : many;
}
