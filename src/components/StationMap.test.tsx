import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StationMap } from "@/components/StationMap";
import { KRAKOW, RZESZOW } from "@/test/fixtures";

const rows = [
  { station: KRAKOW, best_model: "ecmwf", best_model_label: "ECMWF", figures: null },
  { station: RZESZOW, best_model: null, best_model_label: null, figures: null },
];

describe("StationMap", () => {
  it("draws a dot for every station", () => {
    const { container } = render(<StationMap rows={rows} selectedStation="12566" />);
    expect(container.querySelectorAll("[data-station]")).toHaveLength(2);
  });

  it("names the open station and the models it shows", () => {
    const { container, getByText } = render(<StationMap rows={rows} selectedStation="12566" />);
    expect(container.querySelector("text")).toHaveTextContent("Kraków");
    expect(getByText("ECMWF")).toBeInTheDocument();
  });

  it("names a station the pointer is over", () => {
    const { container } = render(<StationMap rows={rows} selectedStation="12566" />);
    fireEvent.mouseEnter(container.querySelector('[data-station="12580"]') as Element);
    expect(container.querySelector("text")).toHaveTextContent("Rzeszów");
  });

  it("is hidden from assistive technology, because the table says the same", () => {
    const { container } = render(<StationMap rows={rows} selectedStation="12566" />);
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });
});
