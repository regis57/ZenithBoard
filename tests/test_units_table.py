# SPDX-License-Identifier: GPL-3.0-or-later
"""The Python side of the one table of units (lot 0 after 1.0): flightinfo/units.py against tests/units_table.json,
the same table tests/test_units_table.js holds flightinfo/static/units.js to. And no factor written anywhere else in
the Python code: a conversion added outside units.py fails here."""
import json, os, re, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "flightinfo"))
import units  # noqa: E402

T = json.load(open(os.path.join(HERE, "units_table.json"), encoding="utf-8"))


class UnitsTable(unittest.TestCase):
    def test_factors_and_systems(self):
        for name, value in T["factors"].items():
            self.assertEqual(getattr(units, name), value, name)
        self.assertEqual(list(units.SYSTEMS), T["systems"])

    def test_system_label_feet(self):
        for given, want in T["system"]:
            self.assertEqual(units.system(given), want, repr(given))
        self.assertIsNone(units.system("nautical", None))
        for u, want in T["feet_and_knots"].items():
            self.assertEqual(units.feet_and_knots(u), want, u)
        for u, want in T["label"].items():
            self.assertEqual(units.distance_label(u), want, u)

    def test_conversions(self):
        for km, u, want in T["distance"]:
            self.assertAlmostEqual(units.distance(km, u), want, places=6, msg="%s km in %s" % (km, u))
        for v, u, want in T["to_km"]:
            self.assertAlmostEqual(units.to_km(v, u), want, places=6, msg="%s %s in km" % (v, u))
        for ft, want in T["metres"]:
            self.assertAlmostEqual(units.metres(ft), want, places=6)
        for kt, want in T["kmh"]:
            self.assertAlmostEqual(units.kmh(kt), want, places=6)

    def test_no_factor_written_outside_the_table(self):
        factor = re.compile(r"(?<![\w.])(1\.609344|1\.852|0\.3048|1609\.344|1852(?:\.0)?)(?![\w])")
        roots = [os.path.join(HERE, "..", "flightinfo"), os.path.join(HERE, "..", "tools")]
        found = []
        for root in roots:
            for name in sorted(os.listdir(root)):
                if not name.endswith(".py") or name == "units.py":
                    continue
                for n, line in enumerate(open(os.path.join(root, name), encoding="utf-8"), 1):
                    code = line.split("#", 1)[0]
                    if factor.search(code):
                        found.append("%s:%d %s" % (name, n, line.strip()[:80]))
        self.assertEqual(found, [], "a unit factor outside flightinfo/units.py")


if __name__ == "__main__":
    unittest.main()
