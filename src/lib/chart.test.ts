import { describe, expect, it } from "vitest";
import { niceScale } from "@/lib/chart";

describe("niceScale", () => {
  it("rounds the top up to a tidy number and starts at zero", () => {
    const { top, ticks } = niceScale(3.7);
    expect(top).toBeGreaterThanOrEqual(3.7);
    expect(ticks[0]).toBe(0);
    expect(ticks.at(-1)).toBe(top);
  });

  it("spaces ticks evenly", () => {
    const { ticks } = niceScale(8.2);
    const gaps = ticks.slice(1).map((tick, i) => Number((tick - (ticks[i] ?? 0)).toFixed(6)));
    expect(new Set(gaps).size).toBe(1);
  });

  it("copes with zero, negative and non-finite maxima", () => {
    for (const max of [0, -3, Number.NaN, Number.POSITIVE_INFINITY]) {
      const { top, ticks } = niceScale(max);
      expect(top).toBeGreaterThan(0);
      expect(ticks.length).toBeGreaterThan(1);
    }
  });
});
