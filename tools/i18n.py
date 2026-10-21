#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The web pages' translations (0.47.0): what to translate, the catalogues, and the review sheets.

The English text is the key. This tool finds every key in the pages' own files, the same way the pages look them up
(flightinfo/static/i18n.js), and keeps the catalogues flightinfo/static/i18n/<lang>/<page>.json in step:

  python3 tools/i18n.py keys [PAGE]          the English keys, in the order the pages use them
  python3 tools/i18n.py check [LANG...]      what is missing, left over, or broken ({placeholders}, <tags>); exit 1 if
                                             anything is (a shipped language must be complete)
  python3 tools/i18n.py sync LANG            add the new keys (empty: the page shows the English), drop the old ones
  python3 tools/i18n.py review LANG          write docs/translations/LANG.csv: the English beside the translation, an
                                             empty column for the correction, one for a comment
  python3 tools/i18n.py apply FILE.csv       take the corrections of a review sheet back into the catalogues (a copy of
                                             each catalogue changed is kept as .bak); the sheet is then written again

Pages: console (console.js, console.html, the action labels and the answers of console_actions.py and console.py),
stats (stats.js, stats.html, the period names the wall's server sends), graphs (graphs1090's page). i18n.js's own
words (the language menu) belong to all three.
"""
import ast
import csv
import html.parser
import io
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "flightinfo", "static")
CATALOGUES = os.environ.get("ZB_I18N_DIR") or os.path.join(STATIC, "i18n")             # the tests use copies
REVIEW = os.environ.get("ZB_I18N_REVIEW_DIR") or os.path.join(ROOT, "docs", "translations")
LANGS = ("fr", "de", "nl", "it", "es", "pt-BR", "id", "ru", "uk", "ja", "ko", "zh-Hans", "zh-Hant")
PAGES = {
    "console": ["flightinfo/static/i18n.js", "flightinfo/static/console.html", "flightinfo/static/console.js",
                "flightinfo/console_actions.py", "flightinfo/console.py"],
    "stats": ["flightinfo/static/i18n.js", "flightinfo/static/stats.html", "flightinfo/static/stats.js", "flightinfo/server.py"],
    "graphs": ["flightinfo/static/i18n.js", "tools/graphs1090-look/zenithboard.js"],
}

JS_STR = r'"((?:[^"\\\n]|\\.)*)"'
JS_T = re.compile(r'(?<![\w.$])t\(\s*(?:[\w.$\[\]"]+\s*\|\|\s*)?' + JS_STR)
JS_TN = re.compile(r'(?<![\w.$])tn\(\s*[^"]+?,\s*' + JS_STR + r',\s*' + JS_STR)
PLACEHOLDER = re.compile(r"\{(\w+)\}")
TAG = re.compile(r"</?(\w+)>")


def strip_js_comments(src):
    """The source with its comments blanked out (same length, same lines): an example in a comment is not a key."""
    out, i, n, q = [], 0, len(src), None
    while i < n:
        c = src[i]
        if q:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(src[i + 1]); i += 2; continue
            if c == q or c == "\n":
                q = None
            i += 1
            continue
        if c in "\"'":
            q = c; out.append(c); i += 1; continue
        if src.startswith("//", i):
            j = src.find("\n", i); j = n if j < 0 else j
            out.append(" " * (j - i)); i = j; continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2); j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", src[i:j])); i = j; continue
        out.append(c); i += 1
    return "".join(out)


def js_unescape(s):
    return json.loads('"' + s + '"')


def norm(s):
    return re.sub(r"[ \t\r\n]+", " ", s).strip(" ")


class HtmlKeys(html.parser.HTMLParser):
    """Keys of a page: each element marked data-t (its text, inner tags kept bare, as i18n.js's keyOf), the
    aria-label, title and placeholder attributes, and the <title>."""
    VOID = {"br", "img", "input", "meta", "link", "hr", "source", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.keys, self.stack, self.in_title = [], [], False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for name in ("aria-label", "title", "placeholder"):
            if a.get(name):
                self.keys.append((a[name], self.getpos()[0]))
        if tag == "title":
            self.in_title = True
        if tag in self.VOID:
            return
        if self.stack:
            self.stack[-1][1].append("<%s>" % tag)
            self.stack.append((None, self.stack[-1][1], tag))
        elif "data-t" in a:
            self.stack.append((self.getpos()[0], [], tag))

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if not self.stack or tag in self.VOID:
            return
        line, buf, t = self.stack.pop()
        if line is None:
            buf.append("</%s>" % t)
        else:
            self.keys.append((norm("".join(buf)), line))

    def handle_data(self, data):
        if self.stack:
            self.stack[-1][1].append(data)
        elif self.in_title and data.strip():
            self.keys.append((norm(data), self.getpos()[0]))


def keys_of_file(rel):
    """[(key, plural-or-None, 'file:line')] in the order of the file."""
    path = os.path.join(ROOT, rel)
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    out = []
    line_of = lambda pos: src.count("\n", 0, pos) + 1
    if rel.endswith(".js"):
        src = strip_js_comments(src)
        for m in JS_TN.finditer(src):
            out.append((js_unescape(m.group(2)), js_unescape(m.group(1)), "%s:%d" % (os.path.basename(rel), line_of(m.start())), m.start()))
        for m in JS_T.finditer(src):
            out.append((js_unescape(m.group(1)), None, "%s:%d" % (os.path.basename(rel), line_of(m.start())), m.start()))
        out.sort(key=lambda k: k[3])
        return [k[:3] for k in out]
    if rel.endswith(".html"):
        p = HtmlKeys()
        p.feed(src)
        return [(k, None, "%s:%d" % (os.path.basename(rel), ln)) for k, ln in p.keys]
    tree = ast.parse(src)
    base = os.path.basename(rel)
    if base == "console_actions.py":            # the sections' and the actions' names, shown by the console
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "SECTIONS":
                for elt in node.value.elts:
                    out.append((elt.elts[1].value, None, "%s:%d" % (base, elt.lineno)))
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "ACTIONS":
                for v in node.value.values:
                    out.append((v.elts[1].value, None, "%s:%d" % (base, v.lineno)))
    elif base == "console.py":                  # the answers the console shows as they are (a sentence, not a code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and k.value == "error" and isinstance(v, ast.Constant) \
                            and isinstance(v.value, str) and v.value[:1].isupper():
                        out.append((v.value, None, "%s:%d" % (base, v.lineno)))
        out.sort(key=lambda k: int(k[2].split(":")[1]))
    elif base == "server.py":                   # the periods' names and notes the statistics page shows as they are
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "RANGES":
                for v in node.value.values:
                    out.append((v.elts[1].value, None, "%s:%d" % (base, v.lineno)))
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "note" and isinstance(node.value, ast.Constant):
                out.append((node.value.value, None, "%s:%d" % (base, node.lineno)))
        out.sort(key=lambda k: int(k[2].split(":")[1]))
    return out


def page_keys(page):
    """OrderedDict-like list of (key, plural one-form or None, [where...]) for one page, duplicates merged."""
    seen, order = {}, []
    for rel in PAGES[page]:
        for key, one, where in keys_of_file(rel):
            if not key.strip():
                continue
            if key not in seen:
                seen[key] = [one, []]
                order.append(key)
            seen[key][1].append(where)
            if one:
                seen[key][0] = one
    return [(k, seen[k][0], seen[k][1]) for k in order]


def cat_path(lang, page):
    return os.path.join(CATALOGUES, lang, page + ".json")


def load(lang, page):
    try:
        with open(cat_path(lang, page), encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}


def save(lang, page, data):
    os.makedirs(os.path.dirname(cat_path(lang, page)), exist_ok=True)
    with open(cat_path(lang, page), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, indent=1) + "\n")


def shape(s):
    return sorted(PLACEHOLDER.findall(s)), sorted(TAG.findall(s))


def problems(lang):
    """[(page, kind, key, detail)] for one language: missing, left over, a placeholder or a tag not the English's."""
    out = []
    for page in PAGES:
        keys = page_keys(page)
        known = {k for k, _, _ in keys}
        cat = load(lang, page)
        for k, one, _ in keys:
            v = cat.get(k)
            if v in (None, "", {}):
                out.append((page, "missing", k, ""))
                continue
            forms = v.values() if isinstance(v, dict) else [v]
            if isinstance(v, dict) and "other" not in v:
                out.append((page, "plural", k, "a plural needs its 'other' form"))
            for f in forms:
                if not isinstance(f, str):
                    out.append((page, "type", k, repr(f)))
                    continue
                want = shape(k)
                if one and isinstance(v, dict):
                    want = (sorted(set(want[0]) | set(shape(one)[0])), want[1])
                    got = (sorted(set(shape(f)[0])), shape(f)[1])
                    want = (sorted(set(want[0])), want[1])
                    ok = set(got[0]) <= set(want[0]) and got[1] == want[1]
                else:
                    got = shape(f)
                    ok = got == want
                if not ok:
                    out.append((page, "shape", k, "%r has %s / %s, the English %s / %s" % (f, got[0], got[1], want[0], want[1])))
        for k in cat:
            if k not in known:
                out.append((page, "left over", k, ""))
    return out


def shipped():
    try:
        return sorted(d for d in os.listdir(CATALOGUES) if os.path.isfile(cat_path(d, "console")))
    except FileNotFoundError:
        return []


def cmd_check(langs):
    langs = langs or shipped()
    bad = 0
    for lang in langs:
        p = problems(lang)
        for page, kind, k, detail in p:
            print("%s %s %-9s %s%s" % (lang, page, kind, json.dumps(k, ensure_ascii=False)[:110], (" — " + detail) if detail else ""))
        total = sum(len(page_keys(pg)) for pg in PAGES)
        print("%s: %d keys, %d problem(s)" % (lang, total, len(p)))
        bad += len(p)
    return 1 if bad else 0


def cmd_sync(lang):
    for page in PAGES:
        cat, keys = load(lang, page), page_keys(page)
        new = {}
        for k, one, _ in keys:
            new[k] = cat.get(k, {"one": "", "other": ""} if one else "")
        save(lang, page, new)
        print("%s/%s: %d keys, %d new, %d dropped" % (lang, page, len(new), sum(1 for k in new if k not in cat),
                                                      sum(1 for k in cat if k not in new)))
    return 0


FIELDS = ["id", "page", "where", "english", "translation", "correction", "comment"]


def review_rows(lang):
    rows, n = [], 0
    for page in PAGES:
        cat = load(lang, page)
        for k, one, where in page_keys(page):
            v = cat.get(k, "")
            forms = [("other", one, v.get("other", "")), ] if isinstance(v, dict) else [(None, None, v)]
            if isinstance(v, dict):
                forms = [(f, one if f == "one" else k, v.get(f, "")) for f in sorted(v, key=lambda x: ["zero", "one", "two", "few", "many", "other"].index(x) if x in ("zero", "one", "two", "few", "many", "other") else 9)]
            for form, eng, tr in forms:
                n += 1
                rows.append({"id": "%s-%d" % (page, n), "page": page + ("" if form is None else " [plural: %s]" % form),
                             "where": ", ".join(sorted(set(w.split(":")[0] for w in where))), "english": k if form is None else (eng or k),
                             "translation": tr, "correction": "", "comment": ""})
    return rows


def cmd_review(lang):
    os.makedirs(REVIEW, exist_ok=True)
    path = os.path.join(REVIEW, lang + ".csv")
    buf = io.StringIO()
    w = csv.DictWriter(buf, FIELDS, lineterminator="\n")
    w.writeheader()
    rows = review_rows(lang)
    w.writerows(rows)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:   # with its mark, so a spreadsheet reads the accents
        fh.write(buf.getvalue())
    print("%s: %d rows" % (os.path.relpath(path, ROOT), len(rows)))
    return 0


def read_sheet(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        text = fh.read()
    try:
        dialect = csv.Sniffer().sniff(text.split("\n", 1)[0], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return list(csv.DictReader(io.StringIO(text), dialect=dialect))


def cmd_apply(path):
    lang = os.path.splitext(os.path.basename(path))[0].split(".")[0]
    if lang not in LANGS:
        print("The file's name says its language (fr.csv, pt-BR.csv): %s is not one" % lang)
        return 1
    rows, changed, refused = read_sheet(path), {}, []
    cats = {page: load(lang, page) for page in PAGES}
    for r in rows:
        fix = (r.get("correction") or "").strip()
        if not fix:
            continue
        page_field = (r.get("page") or "").strip()
        page = page_field.split(" ")[0]
        form = re.search(r"plural: (\w+)", page_field)
        eng = r.get("english") or ""
        if page not in cats:
            refused.append((r.get("id"), "no page %r" % page))
            continue
        key = eng
        if form:      # a plural's row: the key is the English plural, the row may show its singular
            key = next((k for k, one, _ in page_keys(page) if one and (k == eng or one == eng)), None)
        if key is None or key not in cats[page]:
            refused.append((r.get("id"), "no such English text any more (changed since the sheet was made)"))
            continue
        want = shape(key)
        if not form and shape(fix) != want:
            refused.append((r.get("id"), "keep the same {placeholders} and <tags> as the English: %s %s" % want))
            continue
        if form:
            v = cats[page][key] if isinstance(cats[page][key], dict) else {"other": cats[page][key]}
            v[form.group(1)] = fix
            cats[page][key] = v
        else:
            cats[page][key] = fix
        changed.setdefault(page, 0)
        changed[page] += 1
    for page, n in changed.items():
        if os.path.exists(cat_path(lang, page)):
            shutil.copyfile(cat_path(lang, page), cat_path(lang, page) + ".bak")
        save(lang, page, cats[page])
        print("%s/%s: %d correction(s) taken" % (lang, page, n))
    for rid, why in refused:
        print("row %s refused: %s" % (rid, why))
    if not changed:
        print("No correction in %s (the 'correction' column is empty)." % path)
    cmd_review(lang)
    return 1 if refused else 0


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd, rest = argv[1], argv[2:]
    if cmd == "keys":
        for page in (rest or list(PAGES)):
            for k, one, where in page_keys(page):
                print("%s\t%s\t%s" % (page, json.dumps(k, ensure_ascii=False), ", ".join(where)))
        return 0
    if cmd == "check":
        return cmd_check(rest)
    if cmd == "sync" and len(rest) == 1:
        return cmd_sync(rest[0])
    if cmd == "review" and len(rest) == 1:
        return cmd_review(rest[0])
    if cmd == "apply" and len(rest) == 1:
        return cmd_apply(rest[0])
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
