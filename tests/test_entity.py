"""Tests for the NeoPool base entity helpers."""

from custom_components.neopool.entity import NeoPoolEntity


def test_slugify_empty_returns_empty_string() -> None:
    """slugify('') falls into the early return for falsy input."""
    assert NeoPoolEntity.slugify("") == ""


def test_slugify_strips_mbf_par_prefix() -> None:
    """Slugify drops the leading 'mbf_' and 'par_' prefix segments."""
    assert NeoPoolEntity.slugify("MBF_PAR_FILT_MODE") == "filt_mode"


def test_decode_modules_none_returns_unknown() -> None:
    """decode_modules(None) returns 'Unknown'."""
    assert NeoPoolEntity.decode_modules(None) == "Unknown"


def test_decode_modules_lists_every_known_bit() -> None:
    """Every known capability bit appears in the human-readable string."""
    # Set all known bits; the resulting string must include each label.
    bitmask = 0x0001 | 0x0002 | 0x0004 | 0x0008 | 0x0010 | 0x0020 | 0x0040 | 0x0080
    decoded = NeoPoolEntity.decode_modules(bitmask)
    for label in ("Ionization", "Hydro/Electrolysis", "UV Lamp"):
        assert label in decoded, f"expected {label!r} in {decoded!r}"


def test_decode_modules_zero_returns_none_label() -> None:
    """decode_modules(0) yields the 'None' label (no modules detected)."""
    assert NeoPoolEntity.decode_modules(0) == "None"
