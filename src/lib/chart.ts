/** A y-axis from zero to a round number above `max`, with evenly spaced ticks. */
export function niceScale(max: number, tickCount = 5): { top: number; ticks: number[] } {
  const safe = max > 0 && Number.isFinite(max) ? max : 1;
  const rough = safe / tickCount;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((candidate) => candidate >= rough) ?? 10 * magnitude;
  const top = Math.ceil(safe / step) * step;
  const ticks: number[] = [];
  for (let value = 0; value <= top + step / 1000; value += step) ticks.push(Number(value.toFixed(10)));
  return { top, ticks };
}
