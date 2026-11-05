import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

  it("explains every column in a window, with the first model's own numbers", async () => {
    render(<RankingTable variable={TEMPERATURE} verdict={verdict()} rain={rainVerdict()} />);
    await userEvent.click(screen.getByRole("button", { name: "What do these columns mean?" }));
    const guide = screen.getByRole("dialog", { name: "How to read the ranking" });
    expect(guide).toHaveAttribute("open");
    expect(within(guide).getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["Error (°C)", "Bias (°C)", "Rain accuracy", "Brier"]);
    expect(within(guide).getByText(/Score for rain chances, from 0 \(perfect\) to 1/)).toBeInTheDocument();
    expect(within(guide).getByText(/Aim for 0/)).toBeInTheDocument();
    expect(guide).toHaveTextContent(/Examples are from the model ranked first:\s*ECMWF/);
    await userEvent.click(within(guide).getByRole("button", { name: "Close" }));
    expect(guide).not.toHaveAttribute("open");
  });

  it("says so when there is nothing to rank", () => {
    render(<RankingTable variable={TEMPERATURE} verdict={verdict({ ranking: [] })} rain={rainVerdict()} />);
    expect(screen.getByText("No scored forecasts in this window yet.")).toBeInTheDocument();
  });
});
