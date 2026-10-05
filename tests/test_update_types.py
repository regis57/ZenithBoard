# SPDX-License-Identifier: GPL-3.0-or-later
"""Monthly aircraft-data refresh tool (no network: uses file:// URLs)."""
import gzip
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import update_types  # noqa: E402


def sample(n=600):
    d = {"A%03d" % i: ["MODEL %d" % i, "L2J", "M"] for i in range(n)}
    d["B748"] = ["BOEING 747-8", "L4J", "H"]
    return d


class UpdateTypesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = os.path.join(self.tmp.name, "data", "types.json")

    def _read(self):
        with open(self.out) as fh:
            return fh.read()

    def _src(self, payload, compress=True):
        path = os.path.join(self.tmp.name, "src.js")
        with open(path, "wb") as fh:
            raw = json.dumps(payload).encode()
            fh.write(gzip.compress(raw) if compress else raw)
        return "file://" + path

    def test_downloads_and_writes(self):
        rc = update_types.main(["--url", self._src(sample()), "--out", self.out, "--quiet"])
        self.assertEqual(rc, 0)
        with open(self.out) as fh:
            data = json.load(fh)
        self.assertEqual(data["types"]["B748"], ["BOEING 747-8", "L4J", "H"])
        self.assertEqual(data["count"], len(data["types"]))
        self.assertRegex(data["updated"], r"^\d{4}-\d{2}-\d{2}$")

    def test_accepts_plain_json(self):
        self.assertEqual(update_types.main(["--url", self._src(sample(), compress=False), "--out", self.out, "--quiet"]), 0)

    def test_bad_download_keeps_previous_file(self):
        update_types.main(["--url", self._src(sample()), "--out", self.out, "--quiet"])
        before = self._read()
        self.assertEqual(update_types.main(["--url", self._src(sample(10)), "--out", self.out, "--quiet"]), 1)   # too few entries
        self.assertEqual(update_types.main(["--url", "file:///nonexistent/x", "--out", self.out, "--quiet"]), 1)
        self.assertEqual(self._read(), before)

    def test_server_uses_downloaded_list(self):
        update_types.main(["--url", self._src(dict(sample(), ZZ99=["NEW WIDEBODY", "L2J", "H"])), "--out", self.out, "--quiet"])
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "flightinfo"))
        import server
        cfg = dict(server.DEFAULTS, USER_DATA_DIR=self.tmp.name)
        types = server.load_types(cfg)
        info = server.describe_type({"t": "ZZ99"}, types)
        self.assertEqual((info["shape"], info["type_name"]), ("wide", "NEW WIDEBODY"))
        self.assertEqual(server.describe_type({"t": "ZZ99"}, {})["shape"], "narrow")     # without the list: unknown -> narrow


if __name__ == "__main__":
    unittest.main()
