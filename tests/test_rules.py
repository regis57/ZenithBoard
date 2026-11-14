# SPDX-License-Identifier: GPL-3.0-or-later
"""The one table of rules for the settings' values (lib/rules.tsv, lot 0 after 1.0): its two readers give the same
answer for every key and every value tried (the shell's rule_ok and rule_offered in lib/common.sh, used by the command,
the menus, the presets and the import; flightinfo/rules.py, used by the web console), and the console's actions take
their choices and ranges from it instead of carrying their own."""
import os, subprocess, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "flightinfo"))
import rules  # noqa: E402
import console_actions  # noqa: E402

SAMPLES = ["", "0", "1", "2", "7", "08", "10", "15", "50", "60", "61", "500", "500.1", "0.05", "0.1", "-1", "-90", "90", "90.1", "-180", "180.5",
           "-500", "-501", "9000", "9001", "2.5", "1e3", "+5", " 5", "5 ", "metric", "imperial", "aviation", "Metric", "nautical", "amber",
           "turquoise", "blue", "dots", "flap", "readsb", "dump1090-fa", "FR", "fr", "FRA", "00000001", "stick_1-b", "a;b", "a b", "$(id)",
           "x" * 33, "1234567", "-0", "0.0", "1.", ".5", "é"]


def shell(fn):
    """{(key, value): True/False} from the shell reader, every key against every sample in one bash."""
    keys = sorted(rules.table())
    script = '. "$1/lib/common.sh"; shift; fn=$1; shift; n=$1; shift; keys=("${@:1:$n}"); shift "$n"; ' \
             'for k in "${keys[@]}" NO_SUCH_KEY; do for v in "$@"; do if "$fn" "$k" "$v"; then printf 1; else printf 0; fi; done; echo; done'
    out = subprocess.run(["bash", "-c", script, "bash", ROOT, fn, str(len(keys))] + keys + SAMPLES, capture_output=True, text=True, check=True).stdout.split("\n")
    return {(k, v): out[i][j] == "1" for i, k in enumerate(keys + ["NO_SUCH_KEY"]) for j, v in enumerate(SAMPLES)}


class Rules(unittest.TestCase):
    def test_the_shell_and_python_readers_agree_on_every_key_and_value(self):
        for fn, py in (("rule_ok", rules.ok), ("rule_offered", rules.offered)):
            got = shell(fn)
            differ = ["%s %s %r: shell %s, python %s" % (fn, k, v, got[(k, v)], py(k, v)) for (k, v) in sorted(got) if got[(k, v)] != py(k, v)]
            self.assertEqual(differ, [])

    def test_the_rules_themselves(self):
        ok, off = rules.ok, rules.offered
        self.assertTrue(ok("UNITS", "aviation") and not ok("UNITS", "nautical"))
        self.assertTrue(ok("CYCLE_SECONDS", "2") and ok("CYCLE_SECONDS", "60") and not ok("CYCLE_SECONDS", "61") and not ok("CYCLE_SECONDS", "2.5"))
        # the radius: a tablet's preset or an import may hold any radius up to 500, the command and the console offer seven
        self.assertTrue(ok("RADIUS", "7") and not off("RADIUS", "7") and off("RADIUS", "10") and not ok("RADIUS", "0") and not ok("RADIUS", "501"))
        self.assertEqual(rules.choices("RADIUS"), ("1", "2", "5", "10", "15", "30", "50"))
        # the antenna's altitude: one range for the command, the import and the console (they had two)
        self.assertTrue(ok("ALT_M", "-500") and ok("ALT_M", "9000") and not ok("ALT_M", "-501") and not ok("ALT_M", "9001"))
        self.assertEqual(rules.bounds("ALT_M"), (-500, 9000))
        self.assertFalse(ok("ADSB_SDR", "a;b") or ok("ADSB_SDR", "$(id)") or ok("THEME", "blue") or ok("NO_SUCH_KEY", "1"))
        self.assertTrue(ok("FLAGS", "2") and not off("FLAGS", "2") and off("FLAGS", "1"))
        self.assertFalse(ok("CYCLE_SECONDS", "5\n") or ok("RADIUS", "10\n") or ok("PORT", "8080\n") or ok("ADSB_SDR", "abc\n"))

    def test_the_console_takes_its_choices_and_ranges_from_the_table(self):
        A = console_actions.ACTIONS
        self.assertIs(A["units"][3][0][2], console_actions.UNIT_SYSTEMS)
        self.assertEqual(console_actions.UNIT_SYSTEMS, rules.choices("UNITS"))
        self.assertEqual(A["color"][3][0][2], rules.choices("THEME"))
        self.assertEqual(A["radius"][3][0][2], rules.choices("RADIUS"))
        self.assertEqual(A["mode"][3][0][2], rules.choices("DISPLAY_MODE"))
        self.assertEqual(A["cycle"][3][0][2], rules.bounds("CYCLE_SECONDS"))
        self.assertEqual([p[2] for p in A["location"][3]], [rules.bounds("LAT"), rules.bounds("LON"), rules.bounds("ALT_M")])
        self.assertEqual(A["social-units"][3][0][2], rules.choices("UNITS") + ("wall",))
        self.assertEqual(A["telegram-units"][3][0][2], ("posts",) + rules.choices("UNITS"))
        # and no copy of the lists is left written out in the console's file
        with open(os.path.join(ROOT, "flightinfo", "console_actions.py"), encoding="utf-8") as fh:
            src = fh.read()
        for copy in ('"metric", "imperial"', '"amber", "green"', '"dots", "flap"', '("1", "2", "5"'):
            self.assertNotIn(copy, src)

    def test_every_key_has_a_kind_the_readers_know(self):
        for k, (kind, rule, offered) in rules.table().items():
            self.assertIn(kind, ("enum", "int", "float", "re", "number"), k)
            self.assertTrue(rule, k)


if __name__ == "__main__":
    unittest.main()
