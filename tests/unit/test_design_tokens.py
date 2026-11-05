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


def contrast_of(foreground_hex: str, background_hex: str) -> float:
    lighter, darker = sorted((luminance(foreground_hex), luminance(background_hex)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def contrast(foreground: str, background: str) -> float:
    return contrast_of(TOKENS[foreground], TOKENS[background])


def blend(top: str, bottom: str, share: float) -> str:
    """`top` laid over `bottom` at `share` of its strength, as CSS color-mix does in sRGB."""
    channels = [
        round(int(top[i : i + 2], 16) * share + int(bottom[i : i + 2], 16) * (1 - share))
        for i in (1, 3, 5)
    ]
    return "#" + "".join(f"{c:02x}" for c in channels)


# The row of the best model is washed in that model's colour at this strength (`modelTint` in src/lib/models.ts).
TINT_SHARE = 0.10


TEXT_ON_BACKGROUND = [
    ("fg", "bg"),
    ("fg", "surface"),
    ("fg-soft", "surface"),
    ("fg-muted", "bg"),
    ("fg-muted", "surface"),
    ("fg-muted", "surface-raised"),
    ("warn", "warn-bg"),
    ("model-icon", "surface"),
    ("model-ecmwf", "surface"),
    ("model-gfs", "surface"),
]


@pytest.mark.parametrize(("foreground", "background"), TEXT_ON_BACKGROUND)
def test_text_meets_the_wcag_aa_ratio_of_4_5_to_1(foreground: str, background: str) -> None:
    assert contrast(foreground, background) >= 4.5


@pytest.mark.parametrize("model", ["model-icon", "model-ecmwf", "model-gfs"])
@pytest.mark.parametrize("text", ["fg", "fg-muted"])
def test_text_on_a_row_washed_in_a_models_colour_meets_the_ratio(model: str, text: str) -> None:
    wash = blend(TOKENS[model], TOKENS["surface"], TINT_SHARE)
    assert contrast_of(TOKENS[text], wash) >= 4.5


def test_the_three_models_are_told_apart_by_lightness_as_well_as_hue() -> None:
    lightness = sorted(
        luminance(TOKENS[name]) for name in ("model-icon", "model-ecmwf", "model-gfs")
    )
    assert lightness[1] - lightness[0] > 0.05
    assert lightness[2] - lightness[1] > 0.05
