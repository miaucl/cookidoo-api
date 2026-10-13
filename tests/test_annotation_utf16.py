"""Regression tests for Cookidoo's UTF-16 annotation positions."""

import pytest

from cookidoo_api import (
    Cookidoo,
    CookidooAnnotation,
    CookidooCustomAnnotation,
    CookidooIngredientAnnotation,
    CookidooInstruction,
    CookidooModeAnnotation,
    CookidooTTSAnnotation,
)
from cookidoo_api.helpers import _parse_custom_recipe_annotation


@pytest.mark.parametrize(
    "annotation",
    [
        CookidooIngredientAnnotation("Mix 🍚", "Mix 🍚"),
        CookidooTTSAnnotation("Mix 🍚", time=30, speed="1"),
        CookidooModeAnnotation("Mix 🍚", mode="dough", time=30),
        CookidooCustomAnnotation("CUSTOM", "Mix 🍚", {"preserved": True}),
    ],
)
def test_annotation_offsets_and_lengths_use_utf16(
    annotation: CookidooAnnotation,
) -> None:
    """Non-BMP characters before and inside a span round-trip exactly."""
    instruction = CookidooInstruction("🍲 Mix 🍚 now", annotations=[annotation])
    result = Cookidoo._process_recipe_steps([instruction], ingredients=["Mix 🍚"])
    position = result[0]["annotations"][0]["position"]

    assert position == {"offset": 3, "length": 6}
    encoded = instruction.text.encode("utf-16-le")
    start = position["offset"] * 2
    end = start + position["length"] * 2
    assert encoded[start:end].decode("utf-16-le") == annotation.slot
    assert annotation.slot == "Mix 🍚"
    parsed = _parse_custom_recipe_annotation(
        result[0]["annotations"][0], instruction.text
    )
    assert parsed is not None
    assert parsed.slot == annotation.slot
    assert (
        Cookidoo._process_recipe_steps(
            [CookidooInstruction(instruction.text, annotations=[parsed])], ["Mix 🍚"]
        )
        == result
    )


def test_bmp_annotation_positions_remain_unchanged() -> None:
    """Accents and degree signs still occupy one UTF-16 unit each."""
    instruction = CookidooInstruction(
        "Añadir: 100 °C", annotations=[CookidooTTSAnnotation("100 °C", time=30)]
    )
    result = Cookidoo._process_recipe_steps([instruction], ingredients=[])
    assert result[0]["annotations"][0]["position"] == {"offset": 8, "length": 6}


@pytest.mark.parametrize(
    ("offset", "length"),
    [(1, 1), (0, 1), (-1, 2), (0, -1), (0, 99), (True, 2), (0, False)],
)
def test_invalid_utf16_spans_do_not_produce_partial_slots(
    offset: int | bool,
    length: int | bool,
) -> None:
    """Malformed positions cannot become a misleading editable text fragment."""
    parsed = _parse_custom_recipe_annotation(
        {
            "type": "TTS",
            "data": {"time": 30},
            "position": {"offset": offset, "length": length},
        },
        "🍚 Mix",
    )
    assert parsed is not None
    assert parsed.slot == ""
