# SPDX-License-Identifier: GPL-3.0-or-later
"""The posts' language (0.51.0, asked for by the owner on 22 October 2026): SOCIAL_LANG, English until it is set.

The words come from a catalogue per language, flightinfo/static/i18n/LANG/posts.json, written and reviewed like the
web pages' (tools/i18n.py, the English is the key): every sentence of the aircraft posts and the summaries is a
template there, with {tags} and [parts left out when one of their tags is empty]. What is not words comes from the
Unicode CLDR through flightinfo/data/post-locale.json (tools/make_post_locale.js): the decimal and group signs, the
day-and-month pattern and its month names, a span of days, the weekdays, the country names. The plural forms follow
CLDR's rules, written here for the twenty-one languages and held to Node's Intl by tests/test_post_lang.py.

English keeps the posts' own style, unchanged since before 0.51.0: "11 280 m" with a space that does not break,
"12 October", "12–18 October". Standard library only, like the rest of the service.

The same template language serves the owner's own post templates (social.py, the "custom" style): render() and
check_template() here.
"""
import datetime
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
I18N_DIR = os.environ.get("ZB_I18N_DIR") or os.path.join(HERE, "static", "i18n")
LOCALE_FILE = os.path.join(HERE, "data", "post-locale.json")
# the same codes as the web pages (lib/common.sh ZB_LANG_CODES, console_actions.LANGS, i18n.js)
LANGS = ("en", "fr", "de", "nl", "it", "es", "pt-BR", "pl", "fi", "et", "lv", "lt", "id", "sw", "ru", "uk", "ar", "ja", "ko",
         "zh-Hans", "zh-Hant")
NBSP = " "
EN_UNITS = {"meter": "m", "kilometer": "km", "kilometer-per-hour": "km/h"}
EN_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
EN_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December")


def N_(text):
    """A sentence of the posts written where it is defined (a table), looked up later: tools/i18n.py finds it."""
    return text


def offered():
    """The languages a post can be written in: English, and each with a posts catalogue that is not held back
    (a draft.txt in its folder: complete but held back, as Swahili was until 0.53.1)."""
    out = ["en"]
    for code in LANGS[1:]:
        d = os.path.join(I18N_DIR, code)
        if os.path.isfile(os.path.join(d, "posts.json")) and not os.path.exists(os.path.join(d, "draft.txt")):
            out.append(code)
    return out


# --------------------------------------------------------------------------- plurals (CLDR, integers)
def plural(code, n):
    """CLDR's plural category of a whole number in that language: one, two, few, many, zero or other."""
    n = abs(int(n))
    if code in ("ja", "ko", "zh-Hans", "zh-Hant", "id"):
        return "other"
    if code in ("fr", "pt-BR"):
        if n in (0, 1):
            return "one"
        return "many" if n % 1000000 == 0 else "other"
    if code in ("it", "es"):
        if n == 1:
            return "one"
        return "many" if n and n % 1000000 == 0 else "other"
    if code in ("pl",):
        if n == 1:
            return "one"
        return "few" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else "many"
    if code in ("ru", "uk"):
        if n % 10 == 1 and n % 100 != 11:
            return "one"
        return "few" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else "many"
    if code == "lt":
        if n % 10 == 1 and n % 100 not in range(11, 20):
            return "one"
        return "few" if n % 10 in range(2, 10) and n % 100 not in range(11, 20) else "other"
    if code == "lv":
        if n % 10 == 0 or n % 100 in range(11, 20):
            return "zero"
        return "one" if n % 10 == 1 and n % 100 != 11 else "other"
    if code == "ar":
        if n in (0, 1, 2):
            return ("zero", "one", "two")[n]
        if n % 100 in range(3, 11):
            return "few"
        return "many" if n % 100 in range(11, 100) else "other"
    return "one" if n == 1 else "other"          # en, de, nl, fi, et, sw


# --------------------------------------------------------------------------- templates
_SEG = re.compile(r"\[([^\[\]]*)\]")
_TAG = re.compile(r"\{(\w+)((?:\|\w+)*)\}")
FILTERS = ("a", "cap")
_ELIDE = re.compile(r"(?:^|(?<=[\s(«\"]))([DdLl]e|[Ll]a|[Qq]ue) $")
_VOWEL = re.compile(r"^[AEIOUÀÂÄÆÉÈÊËÎÏÔÖŒÙÛÜaeiouàâäæéèêëîïôöœùûü]")


def a_or_an(word):
    """"an Airbus", "an easyJet", but "a Eurowings", "a United": a vowel said as "you" takes "a" (social._a since 0.29.0)."""
    w = word.lower()
    vowel = w[:1] in "aeiou" and not w.startswith(("eu", "uni", "us", "one"))
    return ("an " if vowel else "a ") + word


class Lang(object):
    def __init__(self, code):
        self.code = code if code in LANGS else "en"
        self.words = {}
        if self.code != "en":
            try:
                with open(os.path.join(I18N_DIR, self.code, "posts.json"), encoding="utf-8") as fh:
                    self.words = {k: v for k, v in json.load(fh).items() if v not in ("", None)}
            except (OSError, ValueError):
                self.code, self.words = "en", {}       # no catalogue, or a broken one: the posts stay English
        self.loc = {}
        if self.code != "en":
            try:
                with open(LOCALE_FILE, encoding="utf-8") as fh:
                    self.loc = json.load(fh).get(self.code) or {}
            except (OSError, ValueError):
                self.loc = {}
        self.bcp47 = self.code                      # what the Bluesky record declares: "fr", "pt-BR", "zh-Hant"

    # ---- words
    def t(self, key, **values):
        """The template of that English key in this language, filled ([parts] dropped when a tag inside is empty)."""
        got = self.words.get(key, key)
        if isinstance(got, dict):                   # a plural entry used as a plain string: its "other"
            got = got.get("other") or key
        return self.render(got, values)

    def tn(self, count, one, other, **values):
        """One of a plural pair, by count's category in this language; {n} is count written this language's way unless
        given (58,7 for 58.7 million). The catalogue keeps it under the English "other" form, as the web pages do."""
        values.setdefault("n", self.num(count))
        if self.code == "en":
            return self.render(one if count == 1 else other, values)
        got = self.words.get(other)
        if isinstance(got, dict):
            form = got.get(plural(self.code, count)) or got.get("other") or (one if count == 1 else other)
        elif isinstance(got, str):
            form = got
        else:
            form = one if count == 1 else other
        return self.render(form, values)

    def join(self, items, how="{a}, {b}"):
        """Words in a list, with the language's own comma (、 in Japanese and Chinese, ، in Arabic): the catalogue's
        "{a}, {b}" (or "{a}; {b}"), applied pair by pair."""
        items = [x for x in items if x]
        if not items:
            return ""
        out = items[0]
        for x in items[1:]:
            out = self.t(how, a=out, b=x)
        return out

    def render(self, template, values):
        """{tag} replaced by its value, {tag|a} with English's article, {tag|cap} with a capital; a [part] is left out
        when one of its tags is empty. French says d'Ennery, l'Airbus: "de", "le", "la", "que" before a vowel."""
        values = values or {}

        def value(name, filters):
            v = values.get(name)
            v = "" if v is None else str(v)
            if not v:
                return ""
            for f in filters:
                if f == "a" and self.code == "en":
                    v = a_or_an(v)
                elif f == "cap":
                    v = v[:1].upper() + v[1:]
            return v

        def fill(text):
            out, pos = [], 0
            for m in _TAG.finditer(text):
                before = text[pos:m.start()]
                v = value(m.group(1), [f for f in m.group(2).split("|") if f])
                if self.code == "fr" and v and _VOWEL.match(v):
                    joined = "".join(out) + before
                    e = _ELIDE.search(joined)
                    if e:
                        word = e.group(1)
                        joined = joined[:e.start(1)] + {"de": "d'", "De": "D'", "le": "l'", "Le": "L'", "la": "l'", "La": "L'",
                                                        "que": "qu'", "Que": "Qu'"}[word]
                        out, before = [joined], ""
                out.append(before)
                out.append(v)
                pos = m.end()
            out.append(text[pos:])
            return "".join(out)

        def segment(m):
            inner = m.group(1)
            tags = _TAG.findall(inner)
            if tags and any(not value(name, [f for f in fl.split("|") if f]) for name, fl in tags):
                return ""
            return inner
        return fill(_SEG.sub(segment, str(template)))

    # ---- numbers
    def num(self, n):
        """A whole number: 11 280 in English (a space that does not break), 11 280 in French, 11.280 in German,
        1000 but 10.000 in Spanish."""
        n = int(round(n))
        if self.code == "en":
            return "{:,}".format(n).replace(",", NBSP)
        s = str(abs(n))
        group = self.loc.get("group", NBSP)
        if len(s) > 3 and not (self.loc.get("min_group", 1) == 2 and len(s) == 4):
            head, rest = s[:len(s) % 3 or 3], s[len(s) % 3 or 3:]
            s = group.join([head] + [rest[i:i + 3] for i in range(0, len(rest), 3)])
        return ("-" if n < 0 else "") + s

    def myriad(self, n):
        """Japanese, Korean and Chinese count big numbers in tens of thousands: 5,870万 (58 700 000), 1.2億; "" below
        ten thousand and in the other languages."""
        units = {"ja": ("万", "億"), "zh-Hans": ("万", "亿"), "zh-Hant": ("萬", "億"), "ko": ("만", "억")}.get(self.code)
        if not units or n < 10000:
            return ""
        if n >= 1e8:
            return ("%.1f" % (n / 1e8)).rstrip("0").rstrip(".") + units[1]
        return self.num(int(round(n / 1e4))) + units[0]

    def dec(self, x, digits=1):
        """10.6 in English, 10,6 in French."""
        s = "%.*f" % (digits, x)
        if self.code == "en":
            return s
        whole, _, frac = s.partition(".")
        return self.num(int(whole)) + ((self.loc.get("decimal", ".") + frac) if frac else "")

    # ---- units and the clock (0.52.1)
    def unit(self, n, unit, text=None):
        """A metric figure with its unit as the language writes it: 10 670 m, 839 км/ч, 839 km/u, 10 670米, 839km/h;
        Arabic's metre by the count (متر, أمتار, مترًا). text is n already written (lang.num, lang.dec); English keeps
        its own: the figure, a space that does not break, m, km or km/h. Feet and knots stay ft and kt, as in aviation."""
        text = self.num(n) if text is None else text
        pat = (self.loc.get("units") or {}).get(unit) if self.code != "en" else None
        if isinstance(pat, dict):
            pat = pat.get(plural(self.code, int(round(abs(n))))) or pat.get("other")
        if not isinstance(pat, str) or "{n}" not in pat:
            return text + NBSP + EN_UNITS.get(unit, unit)
        return pat.replace("{n}", text)

    def clock(self, h, m=0):
        """A time of day, 24-hour: 13:50; 13.50 in Indonesian and Finnish (the owner, 22 October 2026: "pukul 13:50";
        Indonesian spelling separates hours and minutes with a full stop, as CLDR has it)."""
        pat = self.loc.get("clock") if self.code != "en" else None
        if not isinstance(pat, str) or "{h}" not in pat or "{m}" not in pat:
            pat = "{h}:{m}"
        return pat.replace("{h}", "%02d" % int(h)).replace("{m}", "%02d" % int(m))

    # ---- dates
    def _month(self, d):
        return EN_MONTHS[d.month - 1] if self.code == "en" else (self.loc.get("months") or EN_MONTHS)[d.month - 1]

    def day_month(self, d):
        """12 October, 12 octobre, 12. Oktober, 12 октября, 10月12日."""
        d = _date(d)
        if self.code == "en":
            return "%d %s" % (d.day, EN_MONTHS[d.month - 1])
        return self.loc.get("day_month", "{d} {M}").replace("{d}", str(d.day)).replace("{M}", self._month(d))

    def span(self, a, b):
        """A span of days: 12–18 October; 28 September – 4 October."""
        a, b = _date(a), _date(b)
        if self.code == "en":
            if a.month == b.month:
                return "%d–%d %s" % (a.day, b.day, EN_MONTHS[b.month - 1])
            return "%d %s – %d %s" % (a.day, EN_MONTHS[a.month - 1], b.day, EN_MONTHS[b.month - 1])
        pat = self.loc.get("span_one_month" if (a.month, a.year) == (b.month, b.year) else "span_two_months",
                           "{d1} {M1} – {d2} {M2}")
        return (pat.replace("{d1}", str(a.day)).replace("{d2}", str(b.day))
                .replace("{M1}", self._month(a)).replace("{M2}", self._month(b)))

    def weekday(self, d):
        d = _date(d)
        days = EN_DAYS if self.code == "en" else (self.loc.get("weekdays") or EN_DAYS)
        return days[d.weekday()]

    def country(self, cc, english=None):
        """The country's name in this language (CLDR), else the English one given."""
        if self.code != "en":
            got = (self.loc.get("countries") or {}).get(str(cc or "").upper())
            if got:
                return got
        return english or cc or ""


def _date(d):
    if isinstance(d, datetime.date):
        return d
    return datetime.date.fromisoformat(str(d)[:10])


_CACHE = {}


def get(code):
    """The language, read once; an unknown code, or one with no catalogue, is English."""
    code = code if code in LANGS else "en"
    if code not in _CACHE:
        _CACHE[code] = Lang(code)
    return _CACHE[code]


def of(c):
    """The posts' language as set (SOCIAL_LANG), English by default."""
    return get(str((c or {}).get("SOCIAL_LANG", "") or "en").strip())


# --------------------------------------------------------------------------- the owner's own templates
def check_template(template, tags):
    """None when the template can be used, else why not, in plain words: an unknown tag, a filter that does not
    exist, a bracket left open or one inside another."""
    s = str(template or "")
    if not s.strip():
        return "empty"
    depth = 0
    for ch in s:
        if ch == "[":
            depth += 1
            if depth > 1:
                return "a [part] inside another"
        elif ch == "]":
            depth -= 1
            if depth < 0:
                return "a ] without its ["
    if depth:
        return "a [ without its ]"
    for name, fl in _TAG.findall(s):
        if name not in tags:
            return "unknown tag {%s}" % name
        for f in (x for x in fl.split("|") if x):
            if f not in FILTERS:
                return "unknown filter |%s in {%s%s}" % (f, name, fl)
    left = _TAG.sub("", s)
    if "{" in left or "}" in left:
        return "a { or } that is not a tag"
    return None
