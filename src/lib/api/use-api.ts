"use client";

import { useCallback, useEffect, useState } from "react";

export type Loadable<T> =
  | { status: "loading" }
  | { status: "error"; error: Error; retry: () => void }
  | { status: "ready"; data: T };

/**
 * Runs `load` whenever `key` changes and cancels the request that is left behind. The previous result is
 * dropped while the next one loads, so the page never shows figures for a different selection than the one chosen.
 */
export function useApi<T>(key: string, load: (signal: AbortSignal) => Promise<T>): Loadable<T> {
  const [state, setState] = useState<{ key: string; result: Loadable<T> }>({ key, result: { status: "loading" } });
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal)
      .then((data) => {
        // A request that was cancelled may still resolve later: its answer is for a selection no longer shown.
        if (controller.signal.aborted) return;
        setState({ key, result: { status: "ready", data } });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setState({ key, result: { status: "error", error: error instanceof Error ? error : new Error(String(error)), retry } });
      });
    return () => controller.abort();
    // `load` is a fresh closure on every render by design; the key says when its inputs change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, attempt]);

  return state.key === key ? state.result : { status: "loading" };
}
