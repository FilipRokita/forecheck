import { CountUpInt } from "@/components/CountUp";
import { Fade } from "@/components/Fade";
import { plural } from "@/lib/format";
import type { Variable, Verdict } from "@/lib/api/types";
import { modelColor } from "@/lib/models";

/** The whole verdict in one sentence, above the cards. Nothing is said while no model is ranked yet. */
export function Headline({ variable, verdict }: { variable: Variable; verdict: Verdict }) {
  const best = verdict.ranking.find((model) => model.rank === 1);
  if (!best) return null;
  const days = verdict.trust_days;
  return (
    <p className="max-w-3xl text-xl font-medium leading-normal tracking-tight sm:text-2xl">
      At <Fade id={verdict.station.name}>{verdict.station.name}</Fade>,{" "}
      <span key={best.model} className="animate-fade" style={{ color: modelColor(best.model) }}>
        {best.label}
      </span>{" "}
      is the most accurate model for <Fade id={variable.id}>{variable.label.toLowerCase()}</Fade>.{" "}
      <span className="mt-1 block text-fg-muted">
        {days === null ? null : days === 0 ? (
          "Even tomorrow's forecast misses the bar."
        ) : (
          <>
            Rely on it for up to <CountUpInt value={days} /> {plural(days, "day", "days")} ahead.
          </>
        )}
      </span>
    </p>
  );
}
