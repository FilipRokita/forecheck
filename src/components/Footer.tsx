import { attribution } from "@/lib/attribution";
import { REPOSITORY } from "@/lib/links";


/** The attributions the data licences require, word for word, and a note on how to read the numbers. */
export function Footer() {
  return (
    <footer className="mt-2 flex max-w-3xl flex-col gap-3 pb-6 text-xs text-fg-muted">
      <p>
        <a href={attribution.openMeteo.href} className="underline underline-offset-2 hover:text-fg" rel="noreferrer">
          {attribution.openMeteo.label}
        </a>{" "}
        (
        <a href={attribution.openMeteoLicence.href} className="underline underline-offset-2 hover:text-fg" rel="noreferrer">
          {attribution.openMeteoLicence.label}
        </a>
        ).
      </p>
      <p lang="pl">
        {attribution.imgwSource}.{" "}
        <a href={attribution.imgwHref} className="underline underline-offset-2 hover:text-fg" rel="noreferrer">
          danepubliczne.imgw.pl
        </a>
      </p>
      <p lang="pl">{attribution.imgwProcessed}.</p>
      <p>
        Each score compares a forecast issued ahead of time with what a station then measured. Figures are more reliable the
        more days they rest on. Scores run about two weeks behind, because IMGW publishes a month of measurements after it
        ends. Not an official forecast.{" "}
        <a href={REPOSITORY} className="underline underline-offset-2 hover:text-fg" rel="noreferrer">
          How it works
        </a>
        .
      </p>
    </footer>
  );
}
