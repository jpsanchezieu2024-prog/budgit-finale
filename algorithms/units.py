"""
Unit conversion + price-per-unit math.

Budgit lets users record an optional `size_value` and `size_unit` on
each item — for example "milk, 1, L" or "rice, 500, g". This module
normalises those into a single comparable base per category so the app
can rank prices fairly across variants of different sizes:

    weight  → kg     (g  → kg / 1000)
    volume  → L      (ml → L  / 1000)
    count   → unit   (no conversion)

When two entries land in the same base unit, we compare their
price-per-base-unit and the user can see at a glance whether
"€0.50 for 0.5L milk" beats "€0.89 for 1L milk" (it doesn't —
the 1L is cheaper per litre).

This module is *pure*: no Streamlit, no Firestore. Everything else
calls into here when it needs the conversion.
"""

from __future__ import annotations

# Mapping every accepted unit to (base_unit, multiplier_to_base).
UNIT_TO_BASE: dict[str, tuple[str, float]] = {
    "g":    ("kg", 0.001),
    "kg":   ("kg", 1.0),
    "ml":   ("L",  0.001),
    "L":    ("L",  1.0),
    "unit": ("unit", 1.0),
}

# Order shown in dropdowns (most common first).
UNIT_OPTIONS: tuple[str, ...] = ("unit", "L", "ml", "kg", "g")


def base_unit(unit: str) -> str:
    """Return the comparable base for a unit (kg, L, or unit)."""
    return UNIT_TO_BASE.get(unit, ("unit", 1.0))[0]


def to_base(size_value: float, size_unit: str) -> tuple[str, float]:
    """
    Convert a (value, unit) pair into its base form.
    Returns (base_unit, value_in_base_units).
    Example: (500, "g") → ("kg", 0.5)
    """
    base, factor = UNIT_TO_BASE.get(size_unit, ("unit", 1.0))
    return base, float(size_value) * factor


def price_per_base_unit(price: float, size_value: float, size_unit: str) -> tuple[str, float]:
    """
    Return (base_unit, €/base_unit) so callers can show "€0.89/L".
    Falls back to the absolute price when size info is missing or zero.
    """
    base, total_in_base = to_base(size_value, size_unit)
    if total_in_base <= 0:
        return base, float(price)
    return base, float(price) / total_in_base


def comparable(unit_a: str, unit_b: str) -> bool:
    """True when two units share a base — so €/kg is comparable
    across (g, kg) but not across (kg, L)."""
    return base_unit(unit_a) == base_unit(unit_b)


def format_size(size_value: float, size_unit: str) -> str:
    """Render a size+unit nicely (e.g. '1 L', '500 g'). Returns empty
    string when the values are the no-op default (1 unit) so trivially
    sized items don't get cluttered with redundant labels."""
    if size_unit == "unit" and float(size_value) == 1.0:
        return ""
    # Drop trailing zeros for readability.
    if float(size_value).is_integer():
        return f"{int(size_value)} {size_unit}"
    return f"{size_value:g} {size_unit}"


def format_price_per_unit(price: float, size_value: float, size_unit: str) -> str:
    """Render '€0.89/L'. Returns empty string for trivial 1-unit sizes."""
    if size_unit == "unit" and float(size_value) == 1.0:
        return ""
    base, ppu = price_per_base_unit(price, size_value, size_unit)
    return f"€{ppu:.2f}/{base}"
