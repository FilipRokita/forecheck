import { plural } from "@/lib/format";
import type { Variable, Verdict } from "@/lib/api/types";
import { modelColor } from "@/lib/models";

/** The whole verdict in one sentence, above the cards. Nothing is said while no model is ranked yet. */
export function Headline({ variable, verdict }: { variable: Variable; verdict: Verdict }) {
  const best = verdict.ranking.find((model) => model.rank === 1);
  if (!best) return null;
  const days = verdict.trust_days;
  return (
    <p className="max-w-3xl text-xl font-medium leading-snug tracking-tight sm:text-2xl">
      At {verdict.station.name}, <span style={{ color: modelColor(best.model) }}>{best.label}</span> is the most accurate model for{" "}
      {variable.label.toLowerCase()}.{" "}
      <span className="text-fg-muted">
        {days === null
          ? ""
          : days === 0
            ? "Even tomorrow's forecast misses the bar."
            : `Rely on it for up to ${days} ${plural(days, "day", "days")} ahead.`}
      </span>
    </p>
  );
}
