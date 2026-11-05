import { act, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CountUpNumber } from "@/components/CountUp";

const one = (n: number) => n.toFixed(1);

describe("CountUpNumber", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("writes the value at once where there is no motion", () => {
    const { container } = render(<CountUpNumber value={12.34} format={one} />);
    expect(container).toHaveTextContent("12.3");
  });

  it("writes a dash for a missing value", () => {
    const { container } = render(<CountUpNumber value={null} format={one} />);
    expect(container).toHaveTextContent("–");
  });

  it("counts up from zero, then from the old value to the new one", () => {
    vi.useFakeTimers({ toFake: ["requestAnimationFrame", "cancelAnimationFrame", "performance"] });
    vi.stubGlobal("matchMedia", () => ({ matches: false }));
    const { container, rerender } = render(<CountUpNumber value={10} format={one} />);
    expect(container).toHaveTextContent("0.0");
    act(() => void vi.advanceTimersByTime(1000));
    expect(container).toHaveTextContent("10.0");
    rerender(<CountUpNumber value={20} format={one} />);
    act(() => void vi.advanceTimersByTime(200));
    const midway = Number(container.textContent);
    expect(midway).toBeGreaterThan(10);
    expect(midway).toBeLessThan(20);
    act(() => void vi.advanceTimersByTime(1000));
    expect(container).toHaveTextContent("20.0");
  });

  it("does not move when the system asks for less motion", () => {
    vi.stubGlobal("matchMedia", () => ({ matches: true }));
    const { container } = render(<CountUpNumber value={7} format={one} />);
    expect(container).toHaveTextContent("7.0");
  });
});
