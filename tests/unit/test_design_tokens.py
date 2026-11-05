"""The contrast claims in docs/design.md, checked against the real tokens in globals.css."""

import re
from pathlib import Path

import pytest

CSS = (Path(__file__).resolve().parents[2] / "src" / "app" / "globals.css").read_text(
    encoding="utf-8"
)
TOKENS = dict(re.findall(r"--color-([a-z-]+):\s*(#[0-9a-fA-F]{6});", CSS))


def luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted(
        (luminance(TOKENS[foreground]), luminance(TOKENS[background])), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


TEXT_ON_BACKGROUND = [
    ("fg", "bg"),
    ("fg", "surface"),
    ("fg", "highlight"),
    ("fg", "selected"),
    ("fg-soft", "surface"),
    ("fg-muted", "bg"),
    ("fg-muted", "surface"),
    ("fg-muted", "surface-raised"),
    ("fg-muted", "highlight"),
    ("fg-muted", "selected"),
    ("warn", "warn-bg"),
    ("model-icon", "surface"),
    ("model-ecmwf", "surface"),
    ("model-gfs", "surface"),
]


@pytest.mark.parametrize(("foreground", "background"), TEXT_ON_BACKGROUND)
def test_text_meets_the_wcag_aa_ratio_of_4_5_to_1(foreground: str, background: str) -> None:
    assert contrast(foreground, background) >= 4.5


def test_the_three_models_are_told_apart_by_lightness_as_well_as_hue() -> None:
    lightness = sorted(
        luminance(TOKENS[name]) for name in ("model-icon", "model-ecmwf", "model-gfs")
    )
    assert lightness[1] - lightness[0] > 0.05
    assert lightness[2] - lightness[1] > 0.05
