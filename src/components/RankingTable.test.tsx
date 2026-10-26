import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RankingTable } from "@/components/RankingTable";
import { PRECIPITATION, TEMPERATURE, rainVerdict, ranked, verdict } from "@/test/fixtures";

describe("RankingTable", () => {
  it("ranks models with their error and bias, and takes rain scores from the rain verdict", () => {
    render(<RankingTable variable={TEMPERATURE} verdict={verdict()} rain={rainVerdict()} />);
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Model", "Error (°C)", "Bias (°C)", "Rain accuracy", "Brier"]);
    const first = within(table).getAllByRole("row")[1] as HTMLElement;
    expect(first).toHaveTextContent("1");
    expect(first).toHaveTextContent("ECMWF");
    expect(first).toHaveTextContent("1.3");
    expect(first).toHaveTextContent("81%");
    expect(first).toHaveTextContent("0.14");
  });

  it("writes a negative bias with a proper minus", () => {
    render(<RankingTable variable={TEMPERATURE} verdict={verdict()} rain={rainVerdict()} />);
    expect(within(screen.getByRole("table")).getAllByText("−0.2").length).toBeGreaterThan(0);
  });

  it("shows yes/no scores when the quantity is rain", () => {
    render(<RankingTable variable={PRECIPITATION} verdict={rainVerdict()} rain={rainVerdict()} />);
    const headers = within(screen.getByRole("table")).getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual(["Model", "Accuracy", "Rain caught", "False alarms", "Brier"]);
  });

  it("lists a model with too few days but does not rank it", () => {
    const v = verdict({ ranking: [ranked("ecmwf", "ECMWF", 1), ranked("gfs", "GFS", null, { n: 3 })] });
    render(<RankingTable variable={TEMPERATURE} verdict={v} rain={rainVerdict()} />);
    expect(within(screen.getByRole("table")).getByText("too few days")).toBeInTheDocument();
  });

  it("also offers a card per model for a phone", () => {
    render(<RankingTable variable={TEMPERATURE} verdict={verdict()} rain={rainVerdict()} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(3);
  });

  it("says so when there is nothing to rank", () => {
    render(<RankingTable variable={TEMPERATURE} verdict={verdict({ ranking: [] })} rain={rainVerdict()} />);
    expect(screen.getByText("No scored forecasts in this window yet.")).toBeInTheDocument();
  });
});
