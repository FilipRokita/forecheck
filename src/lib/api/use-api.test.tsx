import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useApi } from "@/lib/api/use-api";

describe("useApi", () => {
  it("is loading, then ready with the data", async () => {
    const { result } = renderHook(() => useApi("a", async () => 42));
    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current).toEqual({ status: "ready", data: 42 }));
  });

  it("drops the old result as soon as the key changes", async () => {
    const { result, rerender } = renderHook(({ key }) => useApi(key, async () => key), { initialProps: { key: "a" } });
    await waitFor(() => expect(result.current).toEqual({ status: "ready", data: "a" }));
    rerender({ key: "b" });
    expect(result.current.status).toBe("loading");
    await waitFor(() => expect(result.current).toEqual({ status: "ready", data: "b" }));
  });

  it("reports an error and can try again", async () => {
    const load = vi.fn().mockRejectedValueOnce(new Error("boom")).mockResolvedValueOnce("ok");
    const { result } = renderHook(() => useApi("a", load));
    await waitFor(() => expect(result.current.status).toBe("error"));
    if (result.current.status !== "error") throw new Error("expected an error");
    expect(result.current.error.message).toBe("boom");
    act(() => (result.current.status === "error" ? result.current.retry() : undefined));
    await waitFor(() => expect(result.current).toEqual({ status: "ready", data: "ok" }));
    expect(load).toHaveBeenCalledTimes(2);
  });

  it("goes back to loading as soon as the user retries", async () => {
    let release: (value: string) => void = () => undefined;
    const load = vi
      .fn()
      .mockRejectedValueOnce(new Error("boom"))
      .mockReturnValueOnce(new Promise<string>((resolve) => (release = resolve)));
    const { result } = renderHook(() => useApi("a", load));
    await waitFor(() => expect(result.current.status).toBe("error"));
    act(() => (result.current.status === "error" ? result.current.retry() : undefined));
    expect(result.current.status).toBe("loading");
    await act(async () => release("ok"));
    await waitFor(() => expect(result.current).toEqual({ status: "ready", data: "ok" }));
  });

  it("keeps the old answer, marked stale, while keepWhile is unchanged", async () => {
    let release: (value: string) => void = () => undefined;
    const { result, rerender } = renderHook(
      ({ key }) => useApi(key, () => (key === "a" ? Promise.resolve("a") : new Promise<string>((resolve) => (release = resolve))), "same"),
      { initialProps: { key: "a" } },
    );
    await waitFor(() => expect(result.current).toEqual({ status: "ready", data: "a" }));
    rerender({ key: "b" });
    expect(result.current).toEqual({ status: "ready", data: "a", stale: true });
    await act(async () => release("b"));
    await waitFor(() => expect(result.current).toEqual({ status: "ready", data: "b" }));
  });

  it("drops the old answer when keepWhile changes too", async () => {
    const { result, rerender } = renderHook(({ key, group }) => useApi(key, async () => key, group), { initialProps: { key: "a", group: "one" } });
    await waitFor(() => expect(result.current).toEqual({ status: "ready", data: "a" }));
    rerender({ key: "b", group: "two" });
    expect(result.current.status).toBe("loading");
  });

  it("cancels the request it leaves behind and never shows its late answer", async () => {
    let first: AbortSignal | undefined;
    const slow = new Promise<string>((resolve) => setTimeout(() => resolve("slow"), 30));
    const { result, rerender } = renderHook(
      ({ key }) =>
        useApi(key, (signal) => {
          if (key === "a") {
            first = signal;
            return slow;
          }
          return Promise.resolve("fast");
        }),
      { initialProps: { key: "a" } },
    );
    rerender({ key: "b" });
    await waitFor(() => expect(result.current).toEqual({ status: "ready", data: "fast" }));
    expect(first?.aborted).toBe(true);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(result.current).toEqual({ status: "ready", data: "fast" });
  });
});
