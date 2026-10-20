import { describe, expect, it } from "vitest";
import { formatDay, formatNumber, formatPercent, formatWithUnit, plural } from "@/lib/format";

describe("formatNumber", () => {
  it("uses a decimal point and the given number of digits", () => {
    expect(formatNumber(1.25, 1)).toBe("1.3");
    expect(formatNumber(2, 2)).toBe("2.00");
  });

  it("does not group thousands", () => {
    expect(formatNumber(1013.25, 1)).toBe("1013.3");
  });

  it("shows an en dash for a missing value", () => {
    expect(formatNumber(null)).toBe("–");
    expect(formatNumber(undefined)).toBe("–");
    expect(formatNumber(Number.NaN)).toBe("–");
  });
});

describe("formatPercent", () => {
  it("rounds a share to a whole percent", () => {
    expect(formatPercent(0.814)).toBe("81%");
    expect(formatPercent(1)).toBe("100%");
  });

  it("shows an en dash for a missing value", () => {
    expect(formatPercent(null)).toBe("–");
  });
});

describe("formatWithUnit", () => {
  it("puts a space between the value and its unit", () => {
    expect(formatWithUnit(1.34, "°C")).toBe("1.3 °C");
    expect(formatWithUnit(null, "°C")).toBe("–");
  });
});

describe("formatDay", () => {
  it("reads a calendar date without shifting it by the time zone", () => {
    expect(formatDay("2026-09-30")).toBe("30 Sept 2026");
    expect(formatDay("2026-01-01")).toBe("1 Jan 2026");
  });

  it("shows an en dash for a missing or malformed day", () => {
    expect(formatDay(null)).toBe("–");
    expect(formatDay("soon")).toBe("–");
  });
});

describe("plural", () => {
  it("picks the singular only for one", () => {
    expect(plural(1, "day", "days")).toBe("day");
    expect(plural(0, "day", "days")).toBe("days");
    expect(plural(3, "day", "days")).toBe("days");
  });
});
