const LOCALE = "en-GB";

/** A fixed number of decimals, with a plain minus sign. Returns an en dash for a missing value. */
export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  return new Intl.NumberFormat(LOCALE, { minimumFractionDigits: digits, maximumFractionDigits: digits, useGrouping: false }).format(value);
}

/** A share between 0 and 1 as a whole percent. */
export function formatPercent(share: number | null | undefined): string {
  if (share === null || share === undefined || Number.isNaN(share)) return "–";
  return `${Math.round(share * 100)}%`;
}
