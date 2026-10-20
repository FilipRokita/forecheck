import { beforeEach, describe, expect, it } from "vitest";
import { DEFAULT_SELECTION, readSelection, writeSelection } from "@/lib/selection";

const allowed = { stations: ["12566", "12580"], variables: ["temperature", "precipitation"], periods: ["30d", "90d"] };

beforeEach(() => {
  window.localStorage.clear();
  window.history.replaceState(null, "", "/");
});

describe("readSelection", () => {
  it("falls back to the default", () => {
    expect(readSelection("", allowed)).toEqual(DEFAULT_SELECTION);
  });

  it("reads the address", () => {
    expect(readSelection("?station=12580&variable=precipitation&period=90d", allowed)).toEqual({
      station: "12580",
      variable: "precipitation",
      period: "90d",
    });
  });

  it("uses what this browser last used for whatever the address leaves out", () => {
    window.localStorage.setItem("forecheck:selection", JSON.stringify({ station: "12580", period: "90d" }));
    expect(readSelection("?variable=precipitation", allowed)).toEqual({ station: "12580", variable: "precipitation", period: "90d" });
  });

  it("lets the address win over the stored choice", () => {
    window.localStorage.setItem("forecheck:selection", JSON.stringify({ station: "12580" }));
    expect(readSelection("?station=12566", allowed).station).toBe("12566");
  });

  it("replaces values the API does not know", () => {
    expect(readSelection("?station=00000&variable=humidity&period=7d", allowed)).toEqual(DEFAULT_SELECTION);
  });

  it("uses the first option when even the default is not offered", () => {
    expect(readSelection("", { stations: ["12580"], variables: ["wind"], periods: ["90d"] })).toEqual({
      station: "12580",
      variable: "wind",
      period: "90d",
    });
  });

  it("ignores a stored value that is not what was written", () => {
    window.localStorage.setItem("forecheck:selection", "{not json");
    expect(readSelection("", allowed)).toEqual(DEFAULT_SELECTION);
    window.localStorage.setItem("forecheck:selection", JSON.stringify({ station: 5 }));
    expect(readSelection("", allowed)).toEqual(DEFAULT_SELECTION);
  });
});

describe("writeSelection", () => {
  it("puts the choice in the address and remembers it", () => {
    writeSelection({ station: "12580", variable: "wind", period: "90d" });
    expect(window.location.search).toBe("?station=12580&variable=wind&period=90d");
    expect(JSON.parse(window.localStorage.getItem("forecheck:selection") ?? "null")).toEqual({
      station: "12580",
      variable: "wind",
      period: "90d",
    });
  });
});
