import { formatNumber, formatPercent, formatWithUnit } from "@/lib/format";
import type { Figure, Variable } from "@/lib/api/types";

/** The headline number of a figure for a variable: the mean error in its unit, or the share of right wet/dry calls. */
export function headline(variable: Pick<Variable, "metric" | "unit">, figure: Pick<Figure, "mae" | "accuracy">): string {
  return variable.metric === "accuracy" ? formatPercent(figure.accuracy) : formatWithUnit(figure.mae, variable.unit);
}

/** The number behind `headline`, for views that animate it. */
export function headlineNumber(variable: Pick<Variable, "metric">, figure: Pick<Figure, "mae" | "accuracy">): number | null {
  return variable.metric === "accuracy" ? figure.accuracy : figure.mae;
}

/** Writes a `headlineNumber` the way `headline` does. */
export function headlineFormat(variable: Pick<Variable, "metric" | "unit">): (value: number) => string {
  return variable.metric === "accuracy" ? formatPercent : (value) => formatWithUnit(value, variable.unit);
}

/** The same without the unit, for table cells whose header carries it. */
export function headlineValue(variable: Pick<Variable, "metric">, figure: Pick<Figure, "mae" | "accuracy">): string {
  return variable.metric === "accuracy" ? formatPercent(figure.accuracy) : formatNumber(figure.mae);
}

/** What "trusted" means for a variable, in words. */
export function trustRule(variable: Pick<Variable, "metric" | "unit" | "label" | "trust_threshold">): string {
  return variable.metric === "accuracy"
    ? `at least ${formatPercent(variable.trust_threshold)} of rain calls right`
    : `${variable.label.toLowerCase()} error under ${formatWithUnit(variable.trust_threshold, variable.unit)}`;
}
