"use client";

import { useEffect, useRef, useState } from "react";

const DURATION_MS = 700;

/** Animation is skipped where it cannot run or is unwanted: no matchMedia (tests), or the user asked for less motion. */
function motionAllowed(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Counts from the number on screen to `target` with an ease-out curve. Without motion it is simply `target`. */
function useCountUp(target: number | null): number | null {
  const animate = motionAllowed();
  const [value, setValue] = useState(animate ? 0 : (target ?? 0));
  const shown = useRef(value);

  useEffect(() => {
    if (!animate || target === null) return;
    const from = shown.current;
    const start = performance.now();
    let frame = 0;
    const step = (now: number) => {
      const progress = Math.min((now - start) / DURATION_MS, 1);
      const next = from + (target - from) * (1 - (1 - progress) ** 3);
      shown.current = next;
      setValue(next);
      if (progress < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [target, animate]);

  if (target === null) return null;
  return animate ? value : target;
}

/** A number that counts from its old value to its new one, written by `format`. A missing value is a dash. */
export function CountUpNumber({ value, format }: { value: number | null; format: (n: number) => string }) {
  const shown = useCountUp(value);
  return <>{shown === null ? "–" : format(shown)}</>;
}

/** A whole number that counts up when it appears and whenever it changes. */
export function CountUpInt({ value }: { value: number }) {
  return <CountUpNumber value={value} format={(n) => String(Math.round(n))} />;
}

/** A share between 0 and 1, shown as a whole percent. */
export function CountUpPercent({ share }: { share: number }) {
  return <CountUpNumber value={share} format={(n) => `${Math.round(n * 100)}%`} />;
}
