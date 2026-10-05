# SPDX-License-Identifier: GPL-3.0-or-later
import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "acars"))
import acars_ingest as a  # noqa: E402


class AcarsTests(unittest.TestCase):
    def test_parse_and_filter(self):
        msg = json.dumps({"timestamp": 1.7e9, "freq": 131.525, "label": "H1", "tail": ".F-GKXA", "flight": "AF1234", "text": "hi"})
        row = a.parse_message(msg, ("_d",), True)
        self.assertEqual((row[0], row[4], row[6], row[7], row[11]), (1700000000, "H1", "F-GKXA", "AF1234", "hi"))
        self.assertIsNone(a.parse_message(json.dumps({"label": "_d", "text": "x"}), ("_d",), True))   # ignored label
        self.assertIsNone(a.parse_message('{"label":"H1","text":""}', (), True))                    # empty text
        self.assertIsNotNone(a.parse_message('{"label":"H1","text":""}', (), False))
        self.assertIsNone(a.parse_message("garbage"))

    def test_rolling_retention(self):
        with tempfile.TemporaryDirectory() as d:
            conn = a.open_db(os.path.join(d, "acars.db"))
            now = time.time()
            for age in (1, 6, 8, 30):
                conn.execute("INSERT INTO messages(ts,text) VALUES(?,?)", (int(now - age * 86400), "x"))
            conn.commit()
            self.assertEqual(a.purge(conn, 7, now), 2)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 2)

    def test_dashboard_json_valid(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "acars", "grafana-dashboard.json")) as fh:
            d = json.load(fh)
        self.assertEqual(d["uid"], "zenithboard-acars")
        self.assertTrue(all(p["datasource"]["uid"] == "zenithboard-acars" for p in d["panels"]))


if __name__ == "__main__":
    unittest.main()
