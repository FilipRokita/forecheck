import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SelectionDrawer } from "@/components/SelectionDrawer";
import { KRAKOW, PERIOD_30, PRECIPITATION, RZESZOW, TEMPERATURE } from "@/test/fixtures";

const PERIOD_90 = { id: "90d", label: "90 days", days: 90 };

function setup(onChange = vi.fn()) {
  render(
    <SelectionDrawer
      stations={[KRAKOW, RZESZOW]}
      variables={[TEMPERATURE, PRECIPITATION]}
      periods={[PERIOD_30, PERIOD_90]}
      selection={{ station: KRAKOW.id, variable: "temperature", period: "30d" }}
      onChange={onChange}
    />,
  );
  return { onChange, opener: screen.getByRole("button", { name: /^Configure:/ }) };
}

describe("SelectionDrawer", () => {
  it("is one button that says what is chosen, and shows no options until it is opened", () => {
    const { opener } = setup();
    expect(opener).toHaveAccessibleName("Configure: Kraków, Temperature, 30 days");
    expect(screen.queryByRole("group", { name: "Station" })).not.toBeInTheDocument();
  });

  it("opens a drawer with the station, the quantity and the period, and marks the current choices", async () => {
    const { opener } = setup();
    await userEvent.click(opener);
    const drawer = screen.getByRole("dialog", { name: "Configure" });
    expect(drawer).toHaveAttribute("open");
    expect(within(screen.getByRole("group", { name: "Station" })).getAllByRole("button").map((b) => b.textContent)).toEqual(["Kraków", "Rzeszów"]);
    expect(within(screen.getByRole("group", { name: "Quantity" })).getByRole("button", { name: "Temperature" })).toHaveAttribute("aria-pressed", "true");
    expect(within(screen.getByRole("group", { name: "Period" })).getByRole("button", { name: "90 days" })).toHaveAttribute("aria-pressed", "false");
  });

  it("applies a choice at once and keeps the drawer open for the next one", async () => {
    const { onChange, opener } = setup();
    await userEvent.click(opener);
    await userEvent.click(screen.getByRole("button", { name: "Rzeszów" }));
    expect(onChange).toHaveBeenLastCalledWith({ station: RZESZOW.id });
    await userEvent.click(screen.getByRole("button", { name: "Precipitation" }));
    expect(onChange).toHaveBeenLastCalledWith({ variable: "precipitation" });
    await userEvent.click(screen.getByRole("button", { name: "90 days" }));
    expect(onChange).toHaveBeenLastCalledWith({ period: "90d" });
    expect(screen.getByRole("dialog", { name: "Configure" })).toHaveAttribute("open");
  });

  it("closes with Done, with the X and with Escape, each time after its exit animation", async () => {
    const { opener } = setup();
    const drawer = () => screen.getByRole("dialog", { name: "Configure" });
    const leave = () => fireEvent.animationEnd(drawer());
    await userEvent.click(opener);
    await userEvent.click(screen.getByRole("button", { name: "Done" }));
    expect(drawer()).toHaveAttribute("open");
    leave();
    expect(screen.queryByRole("group", { name: "Station" })).not.toBeInTheDocument();
    await userEvent.click(opener);
    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    leave();
    expect(screen.queryByRole("group", { name: "Station" })).not.toBeInTheDocument();
    await userEvent.click(opener);
    // Escape asks the dialog to cancel. It must not close at once.
    const cancel = new Event("cancel", { cancelable: true });
    act(() => void drawer().dispatchEvent(cancel));
    expect(cancel.defaultPrevented).toBe(true);
    expect(drawer()).toHaveAttribute("open");
    await act(async () => leave());
    expect(screen.queryByRole("group", { name: "Station" })).not.toBeInTheDocument();
  });
});
