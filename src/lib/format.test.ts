import { describe, expect, it } from "vitest";
import { formatNumber, formatPercent } from "@/lib/format";

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
