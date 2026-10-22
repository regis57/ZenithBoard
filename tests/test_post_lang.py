# SPDX-License-Identifier: GPL-3.0-or-later
# Run: python3 -m unittest tests/test_post_lang.py   The posts' language (0.51.0, flightinfo/post_lang.py): the plural
# rules held to Node's Intl (tests/fixtures/plurals.json, made by tools/make_post_locale.js), numbers, dates and
# countries as CLDR writes them, the template language ([parts], {tag|cap}, French's elision), the owner's templates
# checked, and every shipped catalogue turned into real posts and summaries that fit and leave nothing unfilled.
import datetime
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "flightinfo"))
import post_lang  # noqa: E402
import social  # noqa: E402
import social_week as week  # noqa: E402

SHIPPED = os.path.join(HERE, "..", "flightinfo", "static", "i18n")


class StandIns(unittest.TestCase):
    """Empty catalogues in a folder of their own: the language's numbers and dates, the English words."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        for code in post_lang.LANGS[1:]:
            os.makedirs(os.path.join(self.dir, code))
            with open(os.path.join(self.dir, code, "posts.json"), "w") as fh:
                fh.write("{}")
        self.addCleanup(setattr, post_lang, "I18N_DIR", post_lang.I18N_DIR)
        post_lang.I18N_DIR = self.dir
        post_lang._CACHE.clear()
        self.addCleanup(post_lang._CACHE.clear)


class PluralTest(unittest.TestCase):
    def test_every_language_as_intl_says(self):
        with open(os.path.join(HERE, "fixtures", "plurals.json")) as fh:
            want = json.load(fh)
        self.assertEqual(sorted(want), sorted(post_lang.LANGS))
        for code, rows in want.items():
            for n, cat in rows:
                self.assertEqual(post_lang.plural(code, n), cat, (code, n))


class LocaleTest(StandIns):
    def test_numbers(self):
        g = post_lang.get
        self.assertEqual(g("en").num(11280), "11\u00a0280", "English as the posts always wrote it")
        self.assertEqual(g("fr").num(11280), "11\u202f280")
        self.assertEqual(g("de").num(11280), "11.280")
        self.assertEqual((g("es").num(1000), g("es").num(10000)), ("1000", "10.000"), "Spanish groups from five figures")
        self.assertEqual((g("en").dec(10.64), g("fr").dec(10.64), g("ja").dec(10.64)), ("10.6", "10,6", "10.6"))
        self.assertEqual(g("ar").num(11280), "11,280", "Arabic in Western digits, as the pages")

    def test_dates(self):
        g = post_lang.get
        self.assertEqual(g("en").day_month("2026-10-12"), "12 October")
        self.assertEqual(g("en").span("2026-10-12", "2026-10-18"), "12–18 October")
        self.assertEqual(g("en").span("2026-09-28", "2026-10-04"), "28 September – 4 October")
        self.assertEqual(g("fr").span("2026-10-12", "2026-10-18"), "12–18 octobre")
        self.assertEqual(g("ru").day_month("2026-10-12"), "12 октября", "the month as it is said with a day")
        self.assertEqual(g("de").span("2026-09-28", "2026-10-04"), "28. September\u2009–\u20094. Oktober", "CLDR's thin spaces")
        self.assertEqual(g("lt").day_month("2026-10-12"), "spalio 12 d.")
        self.assertEqual(g("ja").span("2026-10-12", "2026-10-18"), "10月12日～10月18日", "not ICU's 10/12～10/18")
        self.assertEqual(g("ko").span("2026-09-28", "2026-10-04"), "9월 28일 ~ 10월 4일")
        self.assertEqual((g("en").weekday("2026-10-23"), g("fr").weekday("2026-10-23")), ("Friday", "vendredi"))

    def test_countries(self):
        g = post_lang.get
        self.assertEqual(g("fr").country("DE", "Germany"), "Allemagne")
        self.assertEqual(g("zh-Hant").country("DE", "Germany"), "德國")
        self.assertEqual(g("en").country("DE", "Germany"), "Germany")
        self.assertEqual(g("fr").country("", "Unknown country"), "Unknown country")

    def test_a_language_with_no_catalogue_is_english(self):
        os.remove(os.path.join(self.dir, "it", "posts.json"))
        post_lang._CACHE.clear()
        self.assertEqual(post_lang.get("it").code, "en")
        self.assertEqual(post_lang.get("xx").code, "en")
        self.assertEqual(post_lang.of({}).code, "en")


class TemplateTest(StandIns):
    def test_parts_and_filters(self):
        en = post_lang.get("en")
        t = "{what|a|cap}[ bound for {to} from {from}] has just crossed the sky[ {area}][, {alt} up].[ {cs}]"
        self.assertEqual(en.render(t, {"what": "Airbus A320", "to": "Pisa", "from": "", "area": "above Trémery", "alt": "", "cs": "#X1"}),
                         "An Airbus A320 has just crossed the sky above Trémery. #X1")
        self.assertEqual(post_lang.get("fr").render("{w|a|cap}", {"w": "avion"}), "Avion", "|a is English's alone")

    def test_french_elision(self):
        fr = post_lang.get("fr")
        self.assertEqual(fr.render("au-dessus de {p}", {"p": "Ennery"}), "au-dessus d'Ennery")
        self.assertEqual(fr.render("de {p}", {"p": "Hambourg"}), "de Hambourg", "an h aspiré: no elision")
        self.assertEqual(fr.render("Le {x} de {y}", {"x": "A380", "y": "Emirates"}), "L'A380 d'Emirates")
        self.assertEqual(post_lang.get("de").render("de {p}", {"p": "Ennery"}), "de Ennery", "French alone")

    def test_the_owners_templates_are_checked(self):
        tags = social.TEMPLATE_TAGS
        self.assertIsNone(post_lang.check_template("{flag} {airline} {flight}[, {from} → {to}] · {type|cap}", tags))
        self.assertEqual(post_lang.check_template("{airline} {distance}", tags), "unknown tag {distance}",
                         "no tag gives a distance from the antenna")
        self.assertEqual(post_lang.check_template("[{from} [{to}]]", tags), "a [part] inside another")
        self.assertEqual(post_lang.check_template("{from}]", tags), "a ] without its [")
        self.assertEqual(post_lang.check_template("{airline|up}", tags), "unknown filter |up in {airline|up}")
        self.assertEqual(post_lang.check_template("{airline", tags), "a { or } that is not a tag")
        self.assertEqual(post_lang.check_template("  ", tags), "empty")


class OfferedTest(unittest.TestCase):
    def test_what_a_post_can_be_written_in(self):
        got = post_lang.offered()
        self.assertEqual(got[0], "en")
        self.assertIn("fr", got)
        self.assertNotIn("sw", got, "Swahili waits for a native review (draft.txt)")


# Every shipped catalogue, as the service would post with it
RYR = {"hex": "4ca7b1", "flight": "RYR5ZK", "registration": "EI-ENK", "type": "B738", "type_name": "BOEING 737-800",
       "shape": "narrow", "airline": "Ryanair", "airline_icao": "RYR", "alt_ft": 34680, "gs_kt": 389, "track": 160, "vrate_fpm": -800,
       "distance_km": 6.2, "bearing": 300, "route": {"from": {"city": "Amsterdam", "iata": "AMS"}, "to": {"city": "Pisa", "iata": "PSA"}}}
MIL = dict(RYR, airline="MILITARY", military=True, flight="RCH123", type_name="BOEING C-17A Globemaster III", registration="", route={})
HELI = dict(RYR, airline="", shape="heli", flight="", registration="D-HABC", type_name="AIRBUS HELICOPTERS H145", route={})
WEEK = {"period": "weekly", "dates": ["2026-09-28", "2026-10-04"], "aircraft": 3587, "messages": 58700000, "best_day": ["2026-10-02", 612],
        "busiest_hour": 17, "airlines": [("Ryanair", 412), ("easyJet", 211)], "models": [("Boeing 737-800", 300), ("Unknown type", 20)],
        "posted": 41, "shown": True, "cargo_total": 21, "bizjet_total": 1, "cargo": [("DHL", 9)], "bizjets": [("Cessna Citation", 1)],
        "cargo_models": {"DHL": ("Boeing 757-200", 5)}, "bizjet_countries": [("CH", 1)], "military_total": 12,
        "military": [{"cc": "DE", "country": "Germany", "total": 8, "models": [("Eurofighter", 5), ("Unknown type", 3)]}],
        "misc": {"heli": {"total": 2, "models": [("Airbus H145", 2)]}, "light": {"total": 1, "models": [("Cessna 172", 1)]}}}


class EveryLanguageTest(unittest.TestCase):
    def setUp(self):
        post_lang._CACHE.clear()
        self.addCleanup(post_lang._CACHE.clear)

    def langs(self):
        return [c for c in post_lang.LANGS if os.path.isfile(os.path.join(SHIPPED, c, "posts.json"))]

    def assertFilled(self, text, what):
        for ch in "{}[]":
            self.assertNotIn(ch, text, what)
        self.assertNotIn("  ", text.replace("\n", " ").replace("  #", " #"), what)
        self.assertLessEqual(len(text), social.POST_MAX, what)

    def test_aircraft_posts(self):
        self.assertIn("fr", self.langs())
        for code in self.langs():
            c = dict(SOCIAL_AREA="Trémery", SOCIAL_HASHTAGS="#ADSB #avgeek #ZenithBoard", SOCIAL_LANG=code, UNITS="metric")
            self.assertEqual(post_lang.of(c).code, code)
            for p, why in ((RYR, None), (RYR, "rare"), (MIL, "military"), (HELI, "helicopter")):
                for shape in social.SENTENCES:
                    t = social.post_text(p, c, why, shape=shape)
                    self.assertFilled(t, (code, shape, why, t))
                    self.assertNotIn("6.2", t, "never the distance")
                    self.assertTrue(t.rstrip().endswith("#ZenithBoard"), (code, shape, t))
            t = social.post_text(dict(RYR, distance_km=332), c, "farthest")
            self.assertFilled(t, (code, "record", t))
            self.assertNotIn("332", t)
            styled = social.styled_text("story", RYR, c)
            self.assertIsNotNone(styled, (code, "the story fits in 220 characters"))
            self.assertIn("Trémery", styled)
            a = social.alt_text(RYR, c, [(0, 0, 0, 0), (0, 0, 0, 600)], "flap", {"map_words": "a satellite map", "credit_full": "EOX"})
            self.assertNotIn("{", a, code)

    def test_every_map_described_in_every_language(self):
        # found in review: "a plain dark background" was not in any catalogue
        import social_card
        words = [st["words"] for st in social_card.MAP_STYLES.values() if st["words"]] + ["a plain dark background"]
        for code in self.langs():
            if code == "en":
                continue
            L = post_lang.get(code)
            for w in words:
                self.assertIn(w, L.words, (code, w))

    def test_summaries(self):
        for code in self.langs():
            c = dict(SOCIAL_AREA="Trémery", SOCIAL_LANG=code)
            L = post_lang.of(c)
            area = social.area_words(c, L)
            for w in (WEEK, dict(WEEK, period="daily", messages=812345, posted=1)):
                self.assertFilled(week.text(w, c, area, "#ADSB", social.fit_post), (code, w["period"]))
            for f in (week.text_second, week.text_military, week.text_misc):
                self.assertFilled(f(WEEK, area, "#ADSB", social.fit_post, L), (code, f.__name__))
            for f in (week.alt, week.alt_second, week.alt_military, week.alt_misc):
                self.assertNotIn("{", f(WEEK, area, L), (code, f.__name__))

    def test_french_reads_french(self):
        c = dict(SOCIAL_AREA="Ennery", SOCIAL_HASHTAGS="#ADSB", SOCIAL_LANG="fr", UNITS="metric")
        self.assertTrue(social.post_text(RYR, c, None, shape="factual").startswith(
            "Vol Ryanair #RYR5ZK · Boeing 737-800 · Amsterdam → Pisa · altitude 10\u202f570\u00a0m · au-dessus d'Ennery"))
        self.assertIn("Un Boeing 737-800 de Ryanair en route d'Amsterdam vers Pisa", social.post_text(RYR, c, None, shape="story"))
        L = post_lang.of(c)
        self.assertTrue(week.text(WEEK, c, social.area_words(c, L), "", social.fit_post).startswith(
            "La semaine au-dessus d'Ennery, 28 septembre\u2009\u2013\u20094 octobre\u00a0: 3\u202f587 avions, 58,7 millions de messages."))


if __name__ == "__main__":
    unittest.main()
