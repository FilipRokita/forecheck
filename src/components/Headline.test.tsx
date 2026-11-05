import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Headline } from "@/components/Headline";
import { TEMPERATURE, ranked, verdict } from "@/test/fixtures";

/** The sentence is split into spans (the changing words fade), so it is found by its element. */
const sentence = () => screen.getByText((_, element) => element?.tagName === "P");

describe("Headline", () => {
  it("names the best model and how far to rely on it", () => {
    render(<Headline variable={TEMPERATURE} verdict={verdict({ trust_days: 3 })} />);
    expect(sentence()).toHaveTextContent(
      "At Kraków, ECMWF is the most accurate model for temperature. Rely on it for up to 3 days ahead.",
    );
  });

  it("uses the singular for one day", () => {
    render(<Headline variable={TEMPERATURE} verdict={verdict({ trust_days: 1 })} />);
    expect(sentence()).toHaveTextContent("up to 1 day ahead.");
  });

  it("says so when even tomorrow misses the bar", () => {
    render(<Headline variable={TEMPERATURE} verdict={verdict({ trust_days: 0 })} />);
    expect(sentence()).toHaveTextContent("But even tomorrow's forecast falls short of the bar.");
  });

  it("says nothing about trust when it is not known", () => {
    render(<Headline variable={TEMPERATURE} verdict={verdict({ trust_days: null })} />);
    expect(sentence()).not.toHaveTextContent("Rely on it");
  });

  it("says nothing while no model is ranked", () => {
    const { container } = render(<Headline variable={TEMPERATURE} verdict={verdict({ ranking: [ranked("gfs", "GFS", null)] })} />);
    expect(container).toBeEmptyDOMElement();
  });
});
