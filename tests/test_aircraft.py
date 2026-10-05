# SPDX-License-Identifier: GPL-3.0-or-later
"""Aircraft type -> silhouette class. Run: python3 -m unittest discover -s tests -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "flightinfo"))
import aircraft as A  # noqa: E402

TABLES = ["HELI", "FIGHTER", "DELTA", "BOMBER", "AIRLIFTER", "QUAD", "WIDE", "REARJET", "BIZJET", "TURBOPROP",
          "LIGHT", "TWINPROP", "GLIDER", "BALLOON"]


class AircraftTests(unittest.TestCase):
    def test_tables_do_not_overlap(self):
        seen = {}
        for name in TABLES:
            for code in getattr(A, name):
                self.assertNotIn(code, seen, "%s is in both %s and %s" % (code, seen.get(code), name))
                seen[code] = name

    def test_all_classes_are_known(self):
        for name in TABLES:
            for code in getattr(A, name):
                self.assertIn(A.classify(code)[0], A.CLASSES)

    def test_airliners(self):
        self.assertEqual(A.classify("A320"), ("narrow", None))
        self.assertEqual(A.classify("B738"), ("narrow", None))
        self.assertEqual(A.classify("B77W"), ("wide", None))
        self.assertEqual(A.classify("B789"), ("wide", None))
        self.assertEqual(A.classify("MD11"), ("wide", "tri"))
        self.assertEqual(A.classify("B748"), ("quad", "hump"))
        self.assertEqual(A.classify("A388"), ("quad", "deck"))
        self.assertEqual(A.classify("A346"), ("quad", None))
        self.assertEqual(A.classify("B463"), ("quad", "hiwing"))
        self.assertEqual(A.classify("CRJ9"), ("rearjet", None))
        self.assertEqual(A.classify("B722"), ("rearjet", "tri"))
        self.assertEqual(A.classify("AT72"), ("turboprop", None))
        self.assertEqual(A.classify("DH8D"), ("turboprop", None))
        self.assertEqual(A.classify("A3ST"), ("wide", "beluga"))

    def test_general_aviation(self):
        self.assertEqual(A.classify("C172"), ("light", "high"))
        self.assertEqual(A.classify("SR22"), ("light", None))
        self.assertEqual(A.classify("PA34"), ("twinprop", None))
        self.assertEqual(A.classify("C25C"), ("bizjet", None))
        self.assertEqual(A.classify("GLF6"), ("bizjet", None))
        self.assertEqual(A.classify("EC35"), ("heli", None))
        self.assertEqual(A.classify("H47"), ("heli", "tandem"))
        self.assertEqual(A.classify("V22"), ("heli", "tilt"))
        self.assertEqual(A.classify("GLID"), ("glider", None))

    def test_military(self):
        self.assertEqual(A.classify("F16")[0], "fighter")
        self.assertEqual(A.classify("F35")[0], "fighter")
        self.assertEqual(A.classify("EUFI")[0], "delta")
        self.assertEqual(A.classify("RFAL")[0], "delta")
        self.assertEqual(A.classify("B52")[0], "bomber")
        self.assertEqual(A.classify("C130")[0], "airlifter")
        self.assertEqual(A.classify("C17"), ("airlifter", "jet"))
        self.assertEqual(A.classify("A400")[0], "airlifter")
        self.assertEqual(A.classify("K35R")[0], "quad")           # a 707 derivative looks like one
        self.assertTrue(A.is_military("fighter"))
        self.assertTrue(A.is_military("narrow", 1))               # readsb database flag
        self.assertFalse(A.is_military("narrow", 0))
        self.assertFalse(A.is_military("narrow", None))

    def test_falls_back_on_description_then_category(self):
        # unknown code, but the downloaded list says: twin-engine jet, heavy
        self.assertEqual(A.classify("ZZ99", None, "FUTURE AIRBUS", "L2J", "H"), ("wide", None))
        self.assertEqual(A.classify("ZZ99", None, "NEW TURBOPROP", "L2T", "M"), ("turboprop", None))
        self.assertEqual(A.classify("ZZ99", None, "FOUR PROP", "L4P", "M"), ("twinprop", "quad"))
        self.assertEqual(A.classify("ZZ99", None, "SOME CHOPPER", "H2T", "L"), ("heli", None))
        self.assertEqual(A.classify("ZZ99", None, "NEW JET", "L2J", "L"), ("bizjet", None))
        self.assertEqual(A.classify("ZZ99", None, "PLACEHOLDER", "L0-", "-")[0], "narrow")    # unknown placeholder, no category
        # no type at all: ADS-B category decides
        self.assertEqual(A.classify(None, "A7")[0], "heli")
        self.assertEqual(A.classify(None, "A6")[0], "fighter")
        self.assertEqual(A.classify(None, "A5")[0], "wide")
        self.assertEqual(A.classify(None, "A1")[0], "light")
        self.assertEqual(A.classify(None, None)[0], "narrow")
        self.assertEqual(A.classify("", "B2")[0], "balloon")

    def test_names(self):
        self.assertEqual(A.type_name("A320"), "Airbus A320")
        self.assertEqual(A.type_name("a320"), "Airbus A320")
        self.assertIsNone(A.type_name("ZZ99"))
        self.assertEqual(A.type_name("ZZ99", {"ZZ99": "Long Name"}), "Long Name")
        self.assertEqual(A.type_name("A320", {"A320": "AIRBUS A-320"}), "AIRBUS A-320")


if __name__ == "__main__":
    unittest.main()
