import { Card, CardSubtitle, CardTitle } from "@/components/Card";
import { Fade } from "@/components/Fade";
import { ModelName } from "@/components/ModelName";
import { headline } from "@/components/metric";
import type { Horizon, ModelHorizon, Variable } from "@/lib/api/types";
import { niceScale } from "@/lib/chart";
import { formatNumber, formatPercent } from "@/lib/format";
import { modelColor } from "@/lib/models";

const LEADS = [1, 2, 3, 4, 5, 6, 7] as const;

type Props = { horizon: Horizon; variable: Variable; periodLabel: string };

/** The figure a bar shows: the error in the variable's unit, or the share of right calls as a percentage. */
function barValue(variable: Variable, figure: { mae: number | null; accuracy: number | null } | undefined): number | null {
  if (!figure) return null;
  return variable.metric === "accuracy" ? (figure.accuracy === null ? null : figure.accuracy * 100) : figure.mae;
}

function leadOf(model: ModelHorizon, lead: number) {
  return model.leads.find((entry) => entry.lead_days === lead);
}

export function HorizonChart({ horizon, variable, periodLabel }: Props) {
  const isShare = variable.metric === "accuracy";
  const threshold = isShare ? horizon.trust_threshold * 100 : horizon.trust_threshold;
  const values = horizon.models.flatMap((model) => LEADS.map((lead) => barValue(variable, leadOf(model, lead)))).filter((v): v is number => v !== null);
  const { top, ticks } = isShare ? { top: 100, ticks: [0, 25, 50, 75, 100] } : niceScale(Math.max(threshold * 1.25, ...values, 0));
  const hasData = values.length > 0;
  const heading = isShare ? "Accuracy by forecast horizon" : `${variable.label} error by forecast horizon`;
  const axisUnit = isShare ? "% right" : variable.unit;
  const thresholdLabel = isShare ? `${formatNumber(threshold, 0)}% bar` : `${formatNumber(threshold, 1)} ${variable.unit} limit`;

  return (
    <Card as="section" delay={200} className="flex-[3_1_100%] lg:flex-[3_1_34rem]">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
        <div>
          <CardTitle>
              <Fade id={heading}>{heading}</Fade>
            </CardTitle>
          <CardSubtitle>
            <Fade id={`${heading}|${periodLabel}`}>
              {isShare ? "Share of right wet/dry calls" : "Mean absolute error"} ({axisUnit}), last {periodLabel}
            </Fade>
          </CardSubtitle>
        </div>
        <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-fg-soft" aria-label="Legend">
          {horizon.models.map((model) => (
            <li key={model.model}>
              <ModelName id={model.model} label={model.label} />
            </li>
          ))}
          <li className="flex items-center gap-2">
            <span aria-hidden="true" className="inline-block h-0 w-4 border-t border-dashed border-fg-soft" />
            <Fade id={thresholdLabel}>{thresholdLabel}</Fade>
          </li>
        </ul>
      </div>

      {hasData ? (
        <>
          <div className="mt-6" aria-hidden="true">
            <div className="relative ml-9 h-44">
              {ticks.map((tick, index) => (
                <div
                  key={index}
                  className="absolute inset-x-0 animate-fade border-t border-grid transition-[bottom] duration-700 ease-out-soft"
                  style={{ bottom: `${(tick / top) * 100}%` }}
                >
                  <span className="absolute -left-9 -top-2.5 w-7 text-right font-mono text-[11px] text-fg-muted">{formatNumber(tick, tick % 1 === 0 ? 0 : 1)}</span>
                </div>
              ))}
              <div
                className="absolute inset-x-0 border-t border-dashed border-fg-soft transition-[bottom] duration-700 ease-out-soft"
                style={{ bottom: `${(Math.min(threshold, top) / top) * 100}%` }}
              />
              <div className="absolute inset-0 flex items-end">
                {LEADS.map((lead) => (
                  <div key={lead} className="flex h-full flex-1 items-end justify-center gap-[3px]">
                    {horizon.models.map((model) => {
                      const value = barValue(variable, leadOf(model, lead));
                      const height = value === null ? 0 : Math.max((value / top) * 100, 1);
                      return (
                        <div key={model.model} className="group relative flex h-full items-end">
                          <div
                            className="w-2 origin-bottom animate-grow rounded-t-[3px] transition-[height,background-color,opacity,filter] duration-700 ease-out-soft group-hover:brightness-125 sm:w-3.5"
                            style={{ height: `${height}%`, opacity: value === null ? 0 : 1, background: modelColor(model.model), animationDelay: `${lead * 60}ms` }}
                          />
                          {value === null ? null : (
                            <span
                              style={{ bottom: `${height}%` }}
                              className="pointer-events-none absolute left-1/2 z-10 mb-1 -translate-x-1/2 whitespace-nowrap rounded-md border border-border-strong bg-surface-raised px-2 py-1 font-mono text-[11px] text-fg opacity-0 shadow-lg transition-opacity group-hover:opacity-100"
                            >
                              {model.label} {isShare ? formatPercent(value / 100) : `${formatNumber(value, 1)} ${variable.unit}`}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
            <div className="ml-9 mt-2 flex">
              {LEADS.map((lead) => (
                <span key={lead} className="flex-1 text-center font-mono text-xs text-fg-muted">
                  {lead} d
                </span>
              ))}
            </div>
          </div>

          <details className="mt-4 text-fg-soft">
            <summary className="flex min-h-11 cursor-pointer items-center focus-visible:outline-2 focus-visible:outline-model-ecmwf">Show the data as a table</summary>
            <div className="overflow-x-auto">
              <table className="mt-2 w-full border-collapse tabular-nums">
                <caption className="sr-only">
                  {heading} by model and days ahead
                </caption>
                <thead>
                  <tr className="text-left text-xs text-fg-muted">
                    <th scope="col" className="px-3 py-2 font-medium">
                      Days ahead
                    </th>
                    {horizon.models.map((model) => (
                      <th key={model.model} scope="col" className="px-3 py-2 text-right font-medium">
                        {model.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="font-mono">
                  {LEADS.map((lead) => (
                    <tr key={lead} className="border-t border-border">
                      <th scope="row" className="px-3 py-2 text-left font-normal">
                        {lead}
                      </th>
                      {horizon.models.map((model) => {
                        const figure = leadOf(model, lead);
                        return (
                          <td key={model.model} className="px-3 py-2 text-right">
                            {figure ? (isShare ? formatPercent(figure.accuracy) : headline(variable, figure)) : "–"}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      ) : (
        <p className="mt-6 text-fg-muted">No scored forecasts in this window yet.</p>
      )}
    </Card>
  );
}
