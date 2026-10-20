import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SegmentedControl } from "@/components/SegmentedControl";

const options = [
  { id: "30d", label: "30 days" },
  { id: "90d", label: "90 days" },
];

describe("SegmentedControl", () => {
  it("is a labelled group of real buttons with the chosen one pressed", () => {
    render(<SegmentedControl label="Period" options={options} value="30d" onChange={() => {}} />);
    expect(screen.getByRole("group", { name: "Period" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "30 days" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "90 days" })).toHaveAttribute("aria-pressed", "false");
  });

  it("reports the choice", async () => {
    const onChange = vi.fn();
    render(<SegmentedControl label="Period" options={options} value="30d" onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "90 days" }));
    expect(onChange).toHaveBeenCalledWith("90d");
  });
});
