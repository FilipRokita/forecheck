"use client";

import { useEffect, useRef, useState } from "react";

const DURATION_MS = 800;

/** Animation is skipped where it cannot run or is unwanted: no matchMedia (tests), or the user asked for less motion. */
function motionAllowed(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Counts from the number on screen to `target` with an ease-out curve. Without motion it is simply `target`. */
function useCountUp(target: number): number {
  const animate = motionAllowed();
  const [value, setValue] = useState(animate ? 0 : target);
  const shown = useRef(value);

  useEffect(() => {
    if (!animate) return;
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

  return animate ? value : target;
}

/** A whole number that counts up when it appears. */
export function CountUpInt({ value }: { value: number }) {
  return <>{Math.round(useCountUp(value))}</>;
}

/** A share between 0 and 1, shown as a whole percent that counts up when it appears. */
export function CountUpPercent({ share }: { share: number }) {
  return <>{Math.round(useCountUp(share * 100))}%</>;
}
