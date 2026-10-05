# SPDX-License-Identifier: GPL-3.0-or-later
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import update_airlines  # noqa: E402

SAMPLE = ('-1,"Unknown",\\N,"-","N/A",\\N,\\N,"Y"\n'
          '1,"Air France",\\N,"AF","AFR","AIRFRANS","France","Y"\n'
          '2,"Defunct Air",\\N,"DD","DDD","","France","N"\n'
          '3,"No Icao Air",\\N,"NI","","","France","Y"\n')


class UpdateTests(unittest.TestCase):
    def test_parse(self):
        d = update_airlines.parse(SAMPLE)
        self.assertEqual(d, {"AFR": {"name": "Air France", "iata": "AF"}})


if __name__ == "__main__":
    unittest.main()
