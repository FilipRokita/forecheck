"""The page and the API must carry the same attribution, word for word."""

from pathlib import Path

from forecheck.application import attribution

SOURCE = (Path(__file__).resolve().parents[2] / "src" / "lib" / "attribution.ts").read_text(
    encoding="utf-8"
)


def test_the_page_repeats_the_imgw_wording_exactly() -> None:
    assert f'"{attribution.IMGW_SOURCE}"' in SOURCE
    assert f'"{attribution.IMGW_PROCESSED}"' in SOURCE


def test_the_page_repeats_the_open_meteo_credit() -> None:
    assert f'"{attribution.OPEN_METEO}"' in SOURCE
    assert attribution.OPEN_METEO_URL in SOURCE
    assert attribution.IMGW_URL in SOURCE
