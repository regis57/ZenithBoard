# SPDX-License-Identifier: GPL-3.0-or-later
"""The units, in one place for everything written in Python (lot 0 after 1.0; the review of 0.99.8): the wall's
server, the Bluesky posts, their pictures and the Telegram messages each carried the factors and the test "is it feet
and knots?", five copies with the pages' two, and each unit added so far missed one of them (aviation units in 0.55.0,
the miles of a range record in 0.99.16). The pages have the same table in static/units.js; tests/units_table.json
holds both to the same figures.

Inside ZenithBoard everything is as the decoder gives it: distances in kilometres, altitudes in feet, speeds in knots.
Only what is shown is converted."""

KM_PER_MI = 1.609344
KM_PER_NM = 1.852
KMH_PER_KT = 1.852
M_PER_FT = 0.3048

SYSTEMS = ("metric", "imperial", "aviation")        # 0.55.0: aviation = nautical miles, knots, feet
_KM_PER = {"metric": 1.0, "imperial": KM_PER_MI, "aviation": KM_PER_NM}
_LABEL = {"metric": "km", "imperial": "mi", "aviation": "NM"}


def system(value, default="metric"):
    """A setting's value as one of SYSTEMS, or `default` when it is none of them (empty, mistyped)."""
    u = str(value or "").strip().lower()
    return u if u in SYSTEMS else default


def feet_and_knots(units):
    """Imperial and aviation both show feet and knots; they differ by the distance only."""
    return units in ("imperial", "aviation")


def distance(km, units):
    """Kilometres in the system's distance unit (km, miles, nautical miles), not rounded."""
    f = _KM_PER.get(units)
    return km / f if f and units != "metric" else km          # metric, or an unknown system: the figure as it is


def to_km(value, units):
    """A distance typed in the system's unit (a radius), in kilometres."""
    f = _KM_PER.get(units)
    return value * f if f and units != "metric" else value


def distance_label(units):
    return _LABEL.get(units, "km")


def metres(feet):
    return feet * M_PER_FT


def kmh(knots):
    return knots * KMH_PER_KT
