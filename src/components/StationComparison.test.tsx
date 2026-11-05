import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StationComparison } from "@/components/StationComparison";
import { PERIOD_30, TEMPERATURE, comparison } from "@/test/fixtures";

describe("StationComparison", () => {
  it("lists every station with its best model and error", () => {
    render(<StationComparison comparison={comparison()} variable={TEMPERATURE} period={PERIOD_30} selectedStation="12566" onSelect={() => {}} />);
    expect(screen.getByRole("row", { name: /Kraków.*ECMWF.*1\.0 °C/ })).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Rzeszów.*Too few days/ })).toBeInTheDocument();
  });

  it("marks the open station", () => {
    render(<StationComparison comparison={comparison()} variable={TEMPERATURE} period={PERIOD_30} selectedStation="12566" onSelect={() => {}} />);
    expect(screen.getByRole("button", { name: "Kraków" })).toHaveAttribute("aria-current", "true");
    expect(screen.getByRole("button", { name: "Rzeszów" })).not.toHaveAttribute("aria-current");
  });

  it("opens a station when its name is pressed", async () => {
    const onSelect = vi.fn();
    render(<StationComparison comparison={comparison()} variable={TEMPERATURE} period={PERIOD_30} selectedStation="12566" onSelect={onSelect} />);
    await userEvent.click(screen.getByRole("button", { name: "Rzeszów" }));
    expect(onSelect).toHaveBeenCalledWith("12580");
  });

  it("opens a station when anywhere in its row is pressed, once", async () => {
    const onSelect = vi.fn();
    render(<StationComparison comparison={comparison()} variable={TEMPERATURE} period={PERIOD_30} selectedStation="12566" onSelect={onSelect} />);
    await userEvent.click(screen.getByText("Too few days"));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("12580");
  });

  it("opens a station from the keyboard", async () => {
    const onSelect = vi.fn();
    render(<StationComparison comparison={comparison()} variable={TEMPERATURE} period={PERIOD_30} selectedStation="12566" onSelect={onSelect} />);
    screen.getByRole("button", { name: "Rzeszów" }).focus();
    await userEvent.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledTimes(1);
  });
});
