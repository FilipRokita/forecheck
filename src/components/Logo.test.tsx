import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Logo } from "@/components/Logo";

describe("Logo", () => {
  afterEach(() => vi.restoreAllMocks());

  it("is a link named Forecheck", () => {
    render(<Logo />);
    expect(screen.getByRole("link", { name: "Forecheck" })).toBeInTheDocument();
  });

  it("scrolls smoothly to the top instead of reloading the page", async () => {
    const scrollTo = vi.fn();
    vi.stubGlobal("scrollTo", scrollTo);
    render(<Logo />);
    await userEvent.click(screen.getByRole("link", { name: "Forecheck" }));
    expect(scrollTo).toHaveBeenCalledWith({ top: 0, behavior: "smooth" });
  });
});
