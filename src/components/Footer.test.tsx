import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Footer } from "@/components/Footer";
import { attribution } from "@/lib/attribution";

describe("Footer", () => {
  it("credits Open-Meteo with a link and the licence", () => {
    render(<Footer />);
    expect(screen.getByRole("link", { name: "Weather data by Open-Meteo.com" })).toHaveAttribute("href", "https://open-meteo.com/");
    expect(screen.getByRole("link", { name: "CC BY 4.0" })).toBeInTheDocument();
  });

  it("carries both IMGW notices word for word, as the regulation requires", () => {
    render(<Footer />);
    expect(screen.getByText(new RegExp(attribution.imgwSource))).toBeInTheDocument();
    expect(screen.getByText(`${attribution.imgwProcessed}.`)).toBeInTheDocument();
  });

  it("marks the Polish lines as Polish", () => {
    render(<Footer />);
    expect(screen.getByText(`${attribution.imgwProcessed}.`)).toHaveAttribute("lang", "pl");
  });

  it("says the scores run behind and are not an official forecast", () => {
    render(<Footer />);
    expect(screen.getByText(/about two weeks behind/)).toBeInTheDocument();
    expect(screen.getByText(/Not an official forecast/)).toBeInTheDocument();
  });
});
