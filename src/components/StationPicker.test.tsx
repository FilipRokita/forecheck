import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StationPicker } from "@/components/StationPicker";
import { KRAKOW, RZESZOW } from "@/test/fixtures";

const LODZ = { id: "12465", name: "Łódź", latitude: 51.77, longitude: 19.47 };
const STATIONS = [KRAKOW, RZESZOW, LODZ];

function setup(onChange = vi.fn()) {
  render(<StationPicker stations={STATIONS} value="12566" onChange={onChange} />);
  return { onChange, opener: screen.getByRole("button", { name: /IMGW station/ }) };
}

describe("StationPicker", () => {
  it("shows the chosen station on its button and starts closed", () => {
    setup();
    expect(screen.getByRole("button", { name: /IMGW station\s*Kraków/ })).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("opens a dropdown with a search box in focus and every station", async () => {
    const { opener } = setup();
    await userEvent.click(opener);
    expect(opener).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("combobox", { name: "Search stations" })).toHaveFocus();
    expect(within(screen.getByRole("listbox")).getAllByRole("option").map((o) => o.textContent)).toEqual(["Kraków", "Rzeszów", "Łódź"]);
  });

  it("marks the current station", async () => {
    const { opener } = setup();
    await userEvent.click(opener);
    expect(screen.getByRole("option", { name: "Kraków" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("option", { name: "Rzeszów" })).toHaveAttribute("aria-selected", "false");
  });

  it("picks a station with the pointer and closes", async () => {
    const { onChange, opener } = setup();
    await userEvent.click(opener);
    await userEvent.click(screen.getByRole("option", { name: "Rzeszów" }));
    expect(onChange).toHaveBeenCalledWith("12580");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });

  it("filters as you type, ignoring case and accents", async () => {
    const { opener } = setup();
    await userEvent.click(opener);
    await userEvent.type(screen.getByRole("combobox"), "LODZ");
    expect(screen.getAllByRole("option").map((o) => o.textContent)).toEqual(["Łódź"]);
  });

  it("says so when nothing matches", async () => {
    const { opener } = setup();
    await userEvent.click(opener);
    await userEvent.type(screen.getByRole("combobox"), "zzz");
    expect(screen.queryAllByRole("option")).toHaveLength(0);
    expect(screen.getByText("No station matches")).toBeInTheDocument();
  });

  it("picks with the arrow keys and Enter", async () => {
    const { onChange, opener } = setup();
    await userEvent.click(opener);
    await userEvent.keyboard("{ArrowDown}{Enter}");
    expect(onChange).toHaveBeenCalledWith("12580");
  });

  it("picks the first match when Enter follows typing", async () => {
    const { onChange, opener } = setup();
    await userEvent.click(opener);
    await userEvent.type(screen.getByRole("combobox"), "rze{Enter}");
    expect(onChange).toHaveBeenCalledWith("12580");
  });

  it("closes on Escape, gives the focus back and chooses nothing", async () => {
    const { onChange, opener } = setup();
    await userEvent.click(opener);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
    expect(onChange).not.toHaveBeenCalled();
  });

  it("closes when the page outside it is pressed", async () => {
    const { opener } = setup();
    await userEvent.click(opener);
    await userEvent.click(document.body);
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("starts the next search from an empty box", async () => {
    const { opener } = setup();
    await userEvent.click(opener);
    await userEvent.type(screen.getByRole("combobox"), "kra");
    await userEvent.keyboard("{Escape}");
    await userEvent.click(opener);
    expect(screen.getByRole("combobox")).toHaveValue("");
  });

  it("closes on Escape even when the focus is still on the button, as on a phone where the box is not focused", async () => {
    vi.stubGlobal("matchMedia", () => ({ matches: true }));
    const { opener } = setup();
    await userEvent.click(opener);
    expect(screen.getByRole("combobox")).not.toHaveFocus();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("keeps a valid highlight when nothing matches and the box is cleared again", async () => {
    const { onChange, opener } = setup();
    await userEvent.click(opener);
    const box = screen.getByRole("combobox");
    await userEvent.type(box, "zzz{ArrowDown}{ArrowDown}");
    expect(box).not.toHaveAttribute("aria-activedescendant");
    await userEvent.clear(box);
    await userEvent.keyboard("{Enter}");
    expect(onChange).toHaveBeenCalledWith("12566");
  });
});
