import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HorizonChart } from "@/components/HorizonChart";
import { PRECIPITATION, TEMPERATURE, figure, horizon } from "@/test/fixtures";

describe("HorizonChart", () => {
  it("names the quantity, the unit and the period", () => {
    render(<HorizonChart horizon={horizon()} variable={TEMPERATURE} periodLabel="30 days" />);
    expect(screen.getByRole("heading", { name: "Temperature error by forecast horizon" })).toBeInTheDocument();
    expect(screen.getByText("Mean absolute error (°C), last 30 days")).toBeInTheDocument();
  });

  it("labels every model and the limit, so colour is never the only cue", () => {
    render(<HorizonChart horizon={horizon()} variable={TEMPERATURE} periodLabel="30 days" />);
    const legend = screen.getByRole("list", { name: "Legend" });
    for (const name of ["ICON", "ECMWF", "GFS", "2.0 °C limit"]) expect(within(legend).getByText(name)).toBeInTheDocument();
  });

  it("offers the same numbers as a table", () => {
    render(<HorizonChart horizon={horizon()} variable={TEMPERATURE} periodLabel="30 days" />);
    const table = screen.getByRole("table", { name: /by model and days ahead/ });
    expect(within(table).getAllByRole("row")).toHaveLength(1 + 7);
    expect(within(table).getByRole("columnheader", { name: "ECMWF" })).toBeInTheDocument();
    const dayOne = within(table).getAllByRole("row")[1] as HTMLElement;
    expect(dayOne).toHaveTextContent("1.1 °C");
  });

  it("shows accuracy as a percentage for precipitation", () => {
    const rainy = horizon({
      metric: "accuracy",
      trust_threshold: 0.8,
      models: [{ model: "ecmwf", label: "ECMWF", leads: [{ lead_days: 1, ...figure({ mae: null, accuracy: 0.9 }) }] }],
    });
    render(<HorizonChart horizon={rainy} variable={PRECIPITATION} periodLabel="30 days" />);
    expect(screen.getByRole("heading", { name: "Accuracy by forecast horizon" })).toBeInTheDocument();
    expect(screen.getByText("80% bar")).toBeInTheDocument();
    expect(screen.getByRole("table")).toHaveTextContent("90%");
  });

  it("says so when nothing is scored", () => {
    const empty = horizon({ models: [{ model: "ecmwf", label: "ECMWF", leads: [] }] });
    render(<HorizonChart horizon={empty} variable={TEMPERATURE} periodLabel="30 days" />);
    expect(screen.getByText("No scored forecasts in this window yet.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("leaves a gap where a lead has no scores instead of drawing a zero", () => {
    const partial = horizon({ models: [{ model: "ecmwf", label: "ECMWF", leads: [{ lead_days: 1, ...figure({ mae: 1 }) }] }] });
    render(<HorizonChart horizon={partial} variable={TEMPERATURE} periodLabel="30 days" />);
    const rows = within(screen.getByRole("table")).getAllByRole("row");
    expect(rows[2]).toHaveTextContent("–");
  });
});
