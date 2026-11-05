import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StationComparison } from "@/components/StationComparison";
import { PERIOD_30, TEMPERATURE, comparison } from "@/test/fixtures";

describe("StationComparison", () => {
  it("lists every station with its best model and error", () => {
    render(<StationComparison comparison={comparison()} variable={TEMPERATURE} period={PERIOD_30} selectedStation="12566" />);
    expect(screen.getByRole("row", { name: /Kraków.*ECMWF.*1\.0 °C/ })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Rzeszów.*Too few days/ })).toBeInTheDocument();
  });

  it("marks the open station", () => {
    render(<StationComparison comparison={comparison()} variable={TEMPERATURE} period={PERIOD_30} selectedStation="12566" />);
    expect(screen.getByRole("row", { name: /Kraków/ })).toHaveAttribute("aria-current", "true");
    expect(screen.getByRole("row", { name: /Rzeszów/ })).not.toHaveAttribute("aria-current");
  });

  it("is only to look at: nothing in it can be pressed", () => {
    render(<StationComparison comparison={comparison()} variable={TEMPERATURE} period={PERIOD_30} selectedStation="12566" />);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });
});
