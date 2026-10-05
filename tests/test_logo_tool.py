# SPDX-License-Identifier: GPL-3.0-or-later
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
try:
    from PIL import Image, ImageDraw
    import logo_tool
except ImportError:                    # Pillow missing: skip these tests
    Image = None


@unittest.skipIf(Image is None, "Pillow not installed")
class LogoToolTests(unittest.TestCase):
    def _transparent_logo(self):
        img = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((10, 10, 90, 90), fill=(220, 30, 30, 255))
        d.rectangle((110, 30, 190, 70), fill=(30, 90, 220, 255))
        d.rectangle((0, 0, 8, 8), fill=(5, 5, 5, 255))      # near-black speck: cannot be lit
        return img

    def test_convert_transparent(self):
        logo = logo_tool.convert_image(self._transparent_logo(), box=(36, 32), colors=6)
        self.assertLessEqual(logo["w"], 36)
        self.assertLessEqual(logo["h"], 32)
        self.assertEqual(len(logo["rows"]), logo["h"])
        self.assertTrue(all(len(r) == logo["w"] for r in logo["rows"]))
        self.assertTrue(any("." in r for r in logo["rows"]))                 # transparent areas stay unlit
        reds = [c for c in logo["palette"] if int(c[1:3], 16) > 150 and int(c[3:5], 16) < 90]
        blues = [c for c in logo["palette"] if int(c[5:7], 16) > 150 and int(c[1:3], 16) < 90]
        self.assertTrue(reds and blues)

    def test_opaque_white_card_background_removed(self):
        img = Image.new("RGB", (120, 60), (255, 255, 255))
        ImageDraw.Draw(img).ellipse((30, 5, 90, 55), fill=(0, 140, 70))
        logo = logo_tool.convert_image(img, box=(36, 32))
        flat = "".join(logo["rows"])
        self.assertGreater(flat.count("."), 0)
        self.assertNotIn("#ffffff", logo["palette"])

    def test_cli_add_list_remove(self):
        with tempfile.TemporaryDirectory() as d:
            png = os.path.join(d, "l.png")
            self._transparent_logo().save(png)
            env = dict(os.environ, ZENITHBOARD_CONFIG=os.path.join(d, "cfg.env"))
            with open(env["ZENITHBOARD_CONFIG"], "w") as fh:
                fh.write("USER_DATA_DIR=%s\n" % d)
            tool = os.path.join(HERE, "..", "tools", "logo_tool.py")
            run = lambda *a: subprocess.run([sys.executable, tool, *a], env=env, capture_output=True, text=True)
            self.assertEqual(run("add", "tst", png).returncode, 0)
            stored = os.path.join(d, "logos", "TST.json")
            self.assertTrue(os.path.isfile(stored))
            self.assertIn("TST", run("list").stdout)
            self.assertNotEqual(run("add", "../bad", png).returncode, 0)
            self.assertNotEqual(run("fetch", "TST").returncode, 0)             # no LOGO_URL_TEMPLATE configured
            self.assertEqual(run("remove", "TST").returncode, 0)
            self.assertFalse(os.path.exists(stored))


if __name__ == "__main__":
    unittest.main()
