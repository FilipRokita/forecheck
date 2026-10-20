import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StationPicker } from "@/components/StationPicker";
import { KRAKOW, RZESZOW } from "@/test/fixtures";

describe("StationPicker", () => {
  it("shows the chosen station on its button", () => {
    render(<StationPicker stations={[KRAKOW, RZESZOW]} value="12566" onChange={() => {}} />);
    expect(screen.getByRole("button", { name: /IMGW station\s*Kraków/ })).toBeInTheDocument();
  });

  it("opens a list, picks a station and closes", async () => {
    const onChange = vi.fn();
    render(<StationPicker stations={[KRAKOW, RZESZOW]} value="12566" onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: /IMGW station/ }));
    const dialog = screen.getByRole("dialog", { name: "Choose a station" });
    expect(dialog).toHaveAttribute("open");
    await userEvent.click(screen.getByRole("button", { name: "Rzeszów" }));
    expect(onChange).toHaveBeenCalledWith("12580");
    expect(dialog).not.toHaveAttribute("open");
  });

  it("marks the current station in the list", async () => {
    render(<StationPicker stations={[KRAKOW, RZESZOW]} value="12566" onChange={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /IMGW station/ }));
    expect(screen.getByRole("button", { name: /Kraków.*Selected/ })).toHaveAttribute("aria-current", "true");
  });

  it("closes without choosing", async () => {
    const onChange = vi.fn();
    render(<StationPicker stations={[KRAKOW]} value="12566" onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: /IMGW station/ }));
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onChange).not.toHaveBeenCalled();
  });
});
