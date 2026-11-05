"use client";

import { useCallback, useEffect, useState } from "react";

export type Loadable<T> =
  | { status: "loading" }
  | { status: "error"; error: Error; retry: () => void }
  /** `stale` marks the previous answer, kept on screen while the next one loads (see `keepWhile`). */
  | { status: "ready"; data: T; stale?: boolean };

/**
 * Runs `load` whenever `key` changes and cancels the request that is left behind. The previous result is
 * dropped while the next one loads, so the page never shows figures for a different selection than the one chosen.
 *
 * One exception, opt-in: while `keepWhile` stays the same, the previous answer stays on screen marked `stale`. Use it
 * only when the part of the selection that changes is named in the answer itself (a station), never for what the
 * view formats the figures with (a quantity or a period).
 */
export function useApi<T>(key: string, load: (signal: AbortSignal) => Promise<T>, keepWhile?: string): Loadable<T> {
  const [state, setState] = useState<{ key: string; keep: string | undefined; result: Loadable<T> }>({ key, keep: keepWhile, result: { status: "loading" } });
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => {
    // Show that something is happening: otherwise the error stays on screen until the answer arrives.
    setState((current) => ({ ...current, result: { status: "loading" } }));
    setAttempt((n) => n + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal)
      .then((data) => {
        // A request that was cancelled may still resolve later: its answer is for a selection no longer shown.
        if (controller.signal.aborted) return;
        setState({ key, keep: keepWhile, result: { status: "ready", data } });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setState({ key, keep: keepWhile, result: { status: "error", error: error instanceof Error ? error : new Error(String(error)), retry } });
      });
    return () => controller.abort();
    // `load` is a fresh closure on every render by design; the key says when its inputs change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, attempt]);

  if (state.key === key) return state.result;
  if (keepWhile !== undefined && state.keep === keepWhile && state.result.status === "ready") return { ...state.result, stale: true };
  return { status: "loading" };
}
