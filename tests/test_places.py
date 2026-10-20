# SPDX-License-Identifier: GPL-3.0-or-later
"""0.27.0: the region's own list of places, made on the Pi from GeoNames' country files (tools/make_local_places.py),
and the maps naming from it. The lines below are real lines of GeoNames' ID.txt and LU.txt (download.geonames.org,
20 October 2026), cut to the columns that matter; in ID.txt 257 515 of 258 055 populated places have no population."""
import gzip
import io
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
sys.path.insert(0, os.path.join(HERE, "..", "flightinfo"))
import make_local_places as mlp  # noqa: E402

try:
    import social_card
except ImportError:                # Pillow missing
    social_card = None


def line(name, lat, lon, fclass, fcode, cc, pop):
    f = ["1", name, name, "", str(lat), str(lon), fclass, fcode, cc, "", "", "", "", "", str(pop), "", "0", "Asia/Makassar", "2026-01-01"]
    return "\t".join(f) + "\n"


SUMBA = [line("Waingapu", -9.6567, 120.2641, "P", "PPLA2", "ID", 0),
         line("Kawangu", -9.6833, 120.3333, "P", "PPLA3", "ID", 0),
         line("Laau", -9.80, 120.36, "P", "PPL", "ID", 0),
         line("Waingapu Kota", -9.6600, 120.2700, "P", "PPLX", "ID", 0),          # a part of the town: left out
         line("Old Waingapu", -9.70, 120.20, "P", "PPLH", "ID", 0),               # historical: left out
         line("Sungai Kawangu", -9.70, 120.30, "H", "STM", "ID", 0),              # a river: not a place
         line("Waingapu Pasar", -9.6580, 120.2660, "P", "PPL", "ID", 0),          # 0.3 km from the town: a part of it
         line("Kupang", -10.17, 123.58, "P", "PPLA", "ID", 0)]                    # 360 km away: out of 200 km


class ListTests(unittest.TestCase):
    def test_weight_population_first_then_rank(self):
        self.assertEqual(mlp.weight("PPLA2", 0), 50000)
        self.assertEqual(mlp.weight("PPLA3", 0), 10000)
        self.assertEqual(mlp.weight("PPL", 0), 100)
        self.assertEqual(mlp.weight("PPLA3", 126), 126, "a known population wins: Winseler, Luxembourg")

    def test_places_in_a_country_file(self):
        got = mlp.places_in(SUMBA, -9.65, 120.26, 200)
        self.assertEqual({r[0] for r in got}, {"Waingapu", "Kawangu", "Laau", "Waingapu Pasar"})
        kept = mlp.thin(got)
        self.assertEqual([r[0] for r in kept], ["Waingapu", "Kawangu", "Laau"], "heaviest first, a part of the town out")

    def test_countries_within_reach(self):
        self.assertEqual(mlp.countries_near(-9.65, 120.26, 400), ["ID"])
        self.assertEqual(mlp.countries_near(-9.65, 120.26, 600), ["ID", "TL"])
        near = mlp.countries_near(49.2489, 6.2332, 400)
        self.assertTrue({"FR", "DE", "LU", "BE", "NL", "CH"} <= set(near), near)
        self.assertNotIn("ES", near)
        # 0.27.2, the reference Pi: the Czech and British files gave no place within 400 km (nearest places of 500:
        # Deal and Dover at 408 km, Krásná at 440 km)
        self.assertNotIn("CZ", near)
        self.assertNotIn("GB", near)

    def test_make_writes_the_list_and_keeps_the_old_one_on_failure(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("ID.txt", "".join(SUMBA))
            z.writestr("readme.txt", "x")
        asked = []

        class Resp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def opener(req, timeout=None):
            asked.append(req.full_url)
            if "TL" in req.full_url:
                b = io.BytesIO()
                with zipfile.ZipFile(b, "w") as z:
                    z.writestr("TL.txt", "")
                return Resp(b.getvalue())
            return Resp(buf.getvalue())
        out = os.path.join(d, "places-local.tsv.gz")
        n = mlp.make(-9.65, 120.26, out, 200, opener, grid={"step": 0.1, "points": {"ID": [-97, 1203], "TL": [-94, 1215]}}, log=lambda *a: None)
        self.assertEqual(n, 3)
        self.assertEqual(asked, ["https://download.geonames.org/export/dump/ID.zip", "https://download.geonames.org/export/dump/TL.zip"])
        text = gzip.open(out, "rt", encoding="utf-8").read()
        self.assertIn("# centre -9.65 120.26 200", text)
        self.assertIn("Waingapu\t-9.6567\t120.2641\t50000", text)
        self.assertIn("Creative Commons Attribution 4.0", text)
        self.assertEqual(os.stat(out).st_mode & 0o777, 0o600, "the centre is the receiver's position: not world-readable")

        def down(req, timeout=None):
            raise OSError("no internet")
        with self.assertRaises(OSError):
            mlp.make(-9.65, 120.26, out, 200, down, grid={"step": 0.1, "points": {"ID": [-97, 1203]}}, log=lambda *a: None)
        self.assertEqual(gzip.open(out, "rt", encoding="utf-8").read(), text, "a failed run leaves the list as it was")

    def test_a_receiver_without_position_is_refused(self):
        self.assertEqual(mlp.main(["x", "0", "0", "/tmp/never.tsv.gz"]), 2)


@unittest.skipIf(social_card is None, "Pillow not installed here")
class MapTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d)
        self.addCleanup(setattr, social_card, "LOCAL_PLACES_FILE", None)
        rows = mlp.thin(mlp.places_in(SUMBA, -9.65, 120.26, 200))
        self.local = os.path.join(self.d, "places-local.tsv.gz")
        mlp.write(rows, self.local, -9.65, 120.26, 200, ["ID"])

    def names(self, trace, local):
        social_card.LOCAL_PLACES_FILE = local
        got = []
        real = social_card.ImageDraw.ImageDraw.text

        def spy(d, xy, text, *a, **k):
            got.append(text)
            return real(d, xy, text, *a, **k)
        social_card.ImageDraw.ImageDraw.text = spy
        try:
            import io as _io
            from PIL import Image

            def tile(*a):
                b = _io.BytesIO()
                Image.new("RGB", (256, 256), (230, 230, 230)).save(b, "JPEG")
                return b.getvalue()
            social_card.draw_map(trace, {"track": 315}, "#00e0e0", mode="normal", fetch=tile, w=420, h=840)
        finally:
            social_card.ImageDraw.ImageDraw.text = real
        return got

    def test_sumba_named_from_the_region_list_only(self):
        # a test render over Sumba: the shipped lists name nothing there; the region's list does, villages included
        # the shipped lists know Waingapu (35 932) and nothing else in East Sumba
        tr = [[-9.80 + i * 0.004, 120.20 + i * 0.004, 3000, i * 5] for i in range(25)]
        self.assertIn("Waingapu", self.names(tr, self.local))
        east = [[-9.85 + i * 0.004, 120.45 - i * 0.004, 3000, i * 5] for i in range(25)]
        self.assertFalse({"Kawangu", "Laau"} & set(self.names(east, None)))
        got = self.names(east, self.local)
        self.assertEqual(got.count("Kawangu"), 1, "named once, though two tiers offer it")
        self.assertIn("Laau", got)

    def test_the_empty_parts_get_a_village(self):
        # 0.27.3, SWR3AG over the Moselle plateau: seven towns on the edges, nothing in the middle. A village goes
        # where no name is within GAP_PX of it; one next to a named town does not.
        rows = [("Bigtown A", 49.30, 6.20, 50000), ("Bigtown B", 49.30, 6.70, 40000), ("Bigtown C", 48.80, 6.20, 30000),
                ("Bigtown D", 48.80, 6.70, 20000), ("Middle", 49.05, 6.45, 300), ("Nextdoor", 49.295, 6.215, 900)]
        path = os.path.join(self.d, "plateau.tsv.gz")
        mlp.write(rows, path, 49.0, 6.4, 200, ["FR"])
        tr = [[48.85 + i * 0.018, 6.60 - i * 0.012, 2700, i * 12] for i in range(25)]
        got = self.names(tr, path)
        self.assertIn("Middle", got)
        self.assertNotIn("Nextdoor", got)

    def test_names_along_the_track_first(self):
        # 0.28.0, RYR5ZK (Brussels → Pisa): a dozen towns in the north of the map, far from the track. Places away
        # from the track are named only when the track's surroundings give fewer than three.
        rows = [("Northcity", 49.10, 6.30, 500000), ("Alongone", 49.30, 6.42, 8000), ("Alongtwo", 49.10, 6.45, 6000),
                ("Alongthree", 48.95, 6.47, 5500), ("Lonely", 48.60, 6.10, 2000)]
        path = os.path.join(self.d, "along.tsv.gz")
        mlp.write(rows, path, 49.2, 6.4, 200, ["FR"])
        tr = [[48.85 + i * 0.022, 6.48 - i * 0.003, 10000, i * 30] for i in range(25)]
        got = self.names(tr, path)
        self.assertTrue({"Alongone", "Alongtwo", "Alongthree"} <= set(got), got)
        self.assertIn("Northcity", got, "a city of 500 000 off the track: one of the few named around it")
        small_city = os.path.join(self.d, "smallcity.tsv.gz")
        mlp.write([r if r[0] != "Northcity" else ("Northcity", r[1], r[2], 9000) for r in rows], small_city, 49.2, 6.4, 200, ["FR"])
        self.assertNotIn("Northcity", self.names(tr, small_city), "a town of 9 000 off the track is not")
        few = os.path.join(self.d, "few.tsv.gz")
        mlp.write([r for r in rows if not r[0].startswith("Along")], few, 49.2, 6.4, 200, ["FR"])
        self.assertIn("Northcity", self.names(tr, few), "nothing along the track: the whole map, as before")

    def test_outside_the_region_the_shipped_lists(self):
        metz = [[48.95 + i * 0.0125, 6.2, 30000, i * 5] for i in range(37)]
        self.assertIn("Metz", self.names(metz, self.local))


if __name__ == "__main__":
    unittest.main()
