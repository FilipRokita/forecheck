/**
 * Attribution the data providers require. The wording is a licence condition, so do not paraphrase it.
 *
 * - IMGW-PIB: regulation of data sharing, § 5 (https://danepubliczne.imgw.pl/regulations). The source notice is
 *   mandatory on every work or product that uses the data, and the processing notice is mandatory when the data
 *   was processed, as the scores here are.
 * - Open-Meteo: CC BY 4.0, a link "Weather data by Open-Meteo.com" next to the data (https://open-meteo.com/en/terms).
 */
export const attribution = {
  openMeteo: { label: "Weather data by Open-Meteo.com", href: "https://open-meteo.com/" },
  openMeteoLicence: { label: "CC BY 4.0", href: "https://creativecommons.org/licenses/by/4.0/" },
  imgwSource: "Źródłem pochodzenia danych jest Instytut Meteorologii i Gospodarki Wodnej – Państwowy Instytut Badawczy",
  imgwProcessed: "Dane Instytutu Meteorologii i Gospodarki Wodnej – Państwowego Instytutu Badawczego zostały przetworzone",
  imgwHref: "https://danepubliczne.imgw.pl/",
} as const;
