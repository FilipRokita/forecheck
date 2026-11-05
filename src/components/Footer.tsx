import { attribution } from "@/lib/attribution";
import { REPOSITORY } from "@/lib/links";


/** The attributions the data licences require, word for word, and a one-line note on the delay and that this is not an official forecast. */
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
        Scores run about two weeks behind. Not an official forecast.{" "}
        <a href={REPOSITORY} className="underline underline-offset-2 hover:text-fg" rel="noreferrer">
          How it works
        </a>
        .
      </p>
    </footer>
  );
}
