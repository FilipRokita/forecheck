import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VerdictCards } from "@/components/VerdictCards";
import { PERIOD_30, PRECIPITATION, TEMPERATURE, rainVerdict, ranked, verdict } from "@/test/fixtures";

function show(overrides = {}, rain = rainVerdict()) {
  render(<VerdictCards variable={TEMPERATURE} period={PERIOD_30} verdict={verdict(overrides)} rain={rain} wetThresholdMm={0.1} />);
}

describe("VerdictCards", () => {
  it("names the best model and compares it with the others", () => {
    show();
    expect(screen.getByText("ECMWF", { selector: "div" })).toBeInTheDocument();
    const card = screen.getByText(/Most accurate model/).parentElement as HTMLElement;
    expect(card).toHaveTextContent("Mean error 1.3 °C against 1.4 °C (ICON) and 1.8 °C (GFS) at Kraków over the last 30 days.");
  });

  it("shows how often tomorrow's rain call is right, whatever is selected", () => {
    show();
    const card = screen.getByText("Rain tomorrow").parentElement as HTMLElement;
    expect(within(card).getByText("81%")).toBeInTheDocument();
    expect(card).toHaveTextContent("(ECMWF)");
    expect(card).toHaveTextContent("at least 0.1 mm");
  });

  it("states the trust horizon with its rule", () => {
    show();
    const card = screen.getByText("How far to trust it").parentElement as HTMLElement;
    expect(card).toHaveTextContent("3 days");
    expect(card).toHaveTextContent("Temperature error under 2.0 °C, for ECMWF.");
  });

  it("uses the singular for one day", () => {
    show({ trust_days: 1 });
    expect(screen.getByText("How far to trust it").parentElement).toHaveTextContent("1 day");
  });

  it("says so when even tomorrow fails the bar", () => {
    show({ trust_days: 0 });
    const card = screen.getByText("How far to trust it").parentElement as HTMLElement;
    expect(card).toHaveTextContent("Not even 1 day");
    expect(card).toHaveTextContent("misses the bar");
  });

  it("says it is too early when there is no ranking yet", () => {
    show({ best_model: null, best_model_label: null, trust_days: null, next_day: null, ranking: [ranked("icon", "ICON", null)], scored_days: 0 }, rainVerdict({ next_day: null, ranking: [] }));
    expect(screen.getByText("Too early")).toBeInTheDocument();
    expect(screen.getByText("Rain tomorrow").parentElement).toHaveTextContent("No scored rain forecasts yet.");
    expect(screen.getByText("How far to trust it").parentElement).toHaveTextContent("Not enough scored days yet to say.");
  });

  it("describes the rule in terms of right calls for precipitation", () => {
    render(
      <VerdictCards
        variable={PRECIPITATION}
        period={PERIOD_30}
        verdict={rainVerdict({ trust_days: 2, best_model_label: "ECMWF" })}
        rain={rainVerdict()}
        wetThresholdMm={0.1}
      />,
    );
    expect(screen.getByText("How far to trust it").parentElement).toHaveTextContent("At least 80% of rain calls right, for ECMWF.");
    expect(screen.getByText(/Most accurate model/).parentElement).toHaveTextContent("Accuracy 81%");
  });
});
