import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StationMap } from "@/components/StationMap";
import { KRAKOW, RZESZOW } from "@/test/fixtures";

const rows = [
  { station: KRAKOW, best_model: "ecmwf", best_model_label: "ECMWF", figures: null },
  { station: RZESZOW, best_model: null, best_model_label: null, figures: null },
];

/** The names that are not faded out. Every name is in the picture, so only the opaque ones are shown. */
function visibleNames(container: HTMLElement) {
  return [...container.querySelectorAll("text")].filter((label) => label.style.opacity === "1").map((label) => label.textContent).sort();
}

describe("StationMap", () => {
  it("draws a dot for every station", () => {
    const { container } = render(<StationMap rows={rows} selectedStation="12566" />);
    expect(container.querySelectorAll("[data-station]")).toHaveLength(2);
  });

  it("names the open station and the models it shows", () => {
    const { container, getByText } = render(<StationMap rows={rows} selectedStation="12566" />);
    expect(visibleNames(container)).toEqual(["Kraków"]);
    expect(getByText("ECMWF")).toBeInTheDocument();
  });

  it("names a station the pointer is over and keeps naming the open one", () => {
    const { container } = render(<StationMap rows={rows} selectedStation="12566" />);
    fireEvent.mouseEnter(container.querySelector('[data-station="12580"]') as Element);
    expect(visibleNames(container)).toEqual(["Kraków", "Rzeszów"]);
    fireEvent.mouseLeave(container.querySelector('[data-station="12580"]') as Element);
    expect(visibleNames(container)).toEqual(["Kraków"]);
  });

  it("is hidden from assistive technology, because the table says the same", () => {
    const { container } = render(<StationMap rows={rows} selectedStation="12566" />);
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });
});
