"""Attribution the data providers require, word for word.

The IMGW lines are a licence condition (regulation § 5 of https://danepubliczne.imgw.pl/regulations):
do not paraphrase them. ``src/lib/attribution.ts`` repeats them for the page, and a test keeps the
two copies equal.
"""

OPEN_METEO = "Weather data by Open-Meteo.com"
OPEN_METEO_URL = "https://open-meteo.com/"
OPEN_METEO_LICENCE = "CC BY 4.0"
IMGW_SOURCE = "Źródłem pochodzenia danych jest Instytut Meteorologii i Gospodarki Wodnej – Państwowy Instytut Badawczy"  # noqa: E501
IMGW_PROCESSED = "Dane Instytutu Meteorologii i Gospodarki Wodnej – Państwowego Instytutu Badawczego zostały przetworzone"  # noqa: E501
IMGW_URL = "https://danepubliczne.imgw.pl/"

LINES = (f"{OPEN_METEO} ({OPEN_METEO_URL}), {OPEN_METEO_LICENCE}", IMGW_SOURCE, IMGW_PROCESSED)
