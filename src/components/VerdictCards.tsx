import { Card, Eyebrow } from "@/components/Card";
import { CountUpInt, CountUpNumber, CountUpPercent } from "@/components/CountUp";
import { Fade } from "@/components/Fade";
import { headlineFormat, headlineNumber, trustRule } from "@/components/metric";
import type { Figure, Period, Variable, Verdict } from "@/lib/api/types";
import type { Loadable } from "@/lib/api/use-api";
import { formatNumber, formatPercent, plural } from "@/lib/format";
import { modelColor } from "@/lib/models";

type Props = {
  variable: Variable;
  period: Period;
  verdict: Verdict;
  /** The precipitation verdict for the same station and period: the "rain tomorrow" card is about rain whatever is selected.
   * It is a separate request, so the other cards do not wait for it and do not fail with it. */
  rain: Loadable<Verdict>;
  /** A day counts as wet from this much rain, in mm. */
  wetThresholdMm: number;
};

const BIG = "text-[40px] font-semibold leading-[1.05] tracking-tight sm:text-[56px]";

export function VerdictCards({ variable, period, verdict, rain, wetThresholdMm }: Props) {
  return (
    <section aria-label="Verdict" className="flex flex-wrap gap-3 sm:gap-4">
      <BestModel variable={variable} period={period} verdict={verdict} />
      <RainTomorrow rain={rain} verdict={verdict} wetThresholdMm={wetThresholdMm} />
      <TrustHorizon variable={variable} verdict={verdict} />
    </section>
  );
}

function BestModel({ variable, period, verdict }: Pick<Props, "variable" | "period" | "verdict">) {
  const best = verdict.ranking.find((model) => model.rank === 1);
  const others = verdict.ranking.filter((model) => model.rank !== null && model.rank !== 1);
  const range = `${verdict.lead_from}–${verdict.lead_to} day forecasts`;
  const noun = variable.metric === "accuracy" ? "Accuracy" : "Mean error";

  return (
    <Card
      className="flex-[2_1_100%] sm:flex-[2_1_26rem]"
      style={best ? { boxShadow: `0 0 70px -28px ${modelColor(best.model)}` } : undefined}
    >
      <Eyebrow>
        <Fade id={`${variable.id}|${range}`}>
          Most accurate model · {variable.label.toLowerCase()} · {range}
        </Fade>
      </Eyebrow>
      {best ? (
        <>
          <div key={best.model} className={`my-3 animate-fade ${BIG}`} style={{ color: modelColor(best.model) }}>
            {best.label}
          </div>
          <p className="max-w-prose text-fg-soft">
            {noun}{" "}
            <Mono>
              <Value variable={variable} figure={best} />
            </Mono>
            {others.length ? (
              <>
                {" "}
                against{" "}
                {others.map((model, index) => (
                  <span key={model.model}>
                    {index > 0 ? (index === others.length - 1 ? " and " : ", ") : ""}
                    <Mono>
                      <Value variable={variable} figure={model} />
                    </Mono>{" "}
                    ({model.label})
                  </span>
                ))}
              </>
            ) : null}{" "}
            at {verdict.station.name} over the last {period.label}.
          </p>
        </>
      ) : (
        <>
          <div className={`my-3 ${BIG} text-fg-muted`}>Too early</div>
          <p className="max-w-prose text-fg-soft">
            Not enough scored days yet at {verdict.station.name}. A forecast is scored once IMGW publishes the month it was
            about, which takes about two weeks after the month ends.
          </p>
        </>
      )}
    </Card>
  );
}

function RainTomorrow({ rain: received, verdict, wetThresholdMm }: { rain: Loadable<Verdict>; verdict: Verdict; wetThresholdMm: number }) {
  // The rain answer may still be the previous station's or period's. It is shown only once it matches the verdict beside it.
  const state: Loadable<Verdict> =
    received.status === "ready" && (received.data.station.id !== verdict.station.id || received.data.period !== verdict.period)
      ? { status: "loading" }
      : received;
  if (state.status !== "ready") {
    return (
      <Card delay={70} className="flex-[1_1_100%] sm:flex-[1_1_16rem]">
        <Eyebrow>Rain tomorrow</Eyebrow>
        <div className={`my-3 font-mono ${BIG} text-fg-muted`}>–</div>
        {state.status === "loading" ? (
          <p role="status" className="text-fg-soft">
            Loading rain scores.
          </p>
        ) : (
          <div role="alert">
            <p className="text-fg-soft">Could not load rain scores.</p>
            <button type="button" onClick={state.retry} className="mt-3 min-h-11 rounded-lg border border-border-strong px-4 hover:bg-surface-raised focus-visible:outline-2 focus-visible:outline-model-ecmwf">
              Try again
            </button>
          </div>
        )}
      </Card>
    );
  }
  const rain = state.data;
  const best = rain.ranking.find((model) => model.rank === 1);
  const share = rain.next_day?.accuracy ?? null;
  return (
    <Card delay={70} className="flex-[1_1_100%] sm:flex-[1_1_16rem]">
      <Eyebrow>Rain tomorrow</Eyebrow>
      <div className={`my-3 font-mono ${BIG}`}>{share === null ? formatPercent(share) : <CountUpPercent share={share} />}</div>
      <p className="text-fg-soft">
        {best && share !== null ? (
          <>
            of day-ahead rain calls are right ({best.label}). Wet means at least <Mono>{formatNumber(wetThresholdMm, 1)} mm</Mono>.
          </>
        ) : (
          "No scored rain forecasts yet."
        )}
      </p>
    </Card>
  );
}

function TrustHorizon({ variable, verdict }: Pick<Props, "variable" | "verdict">) {
  const days = verdict.trust_days;
  return (
    <Card delay={140} className="flex-[1_1_100%] sm:flex-[1_1_16rem]">
      <Eyebrow>How far to trust it</Eyebrow>
      <div className={`my-3 ${BIG}`}>
        {days === null ? (
          "–"
        ) : days === 0 ? (
          "< 1 day"
        ) : (
          <>
            <span className="font-mono">
              <CountUpInt value={days} />
            </span>{" "}
            {plural(days, "day", "days")}
          </>
        )}
      </div>
      <p className="text-fg-soft">
        <Fade id={`${variable.id}|${days}|${verdict.best_model}`}>
        {days === null
          ? "Not enough scored days yet to say."
          : days === 0
            ? `Even tomorrow's forecast misses the bar: ${trustRule(variable)}.`
            : `${capitalise(trustRule(variable))}, for ${verdict.best_model_label ?? "the best model"}.`}
        </Fade>
      </p>
    </Card>
  );
}

/** A figure's headline number, counting from the old value to the new one when the selection changes. */
function Value({ variable, figure }: { variable: Variable; figure: Pick<Figure, "mae" | "accuracy"> }) {
  return <CountUpNumber value={headlineNumber(variable, figure)} format={headlineFormat(variable)} />;
}

function Mono({ children }: { children: React.ReactNode }) {
  return <span className="font-mono">{children}</span>;
}

function capitalise(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
