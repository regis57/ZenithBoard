# SPDX-License-Identifier: GPL-3.0-or-later
"""The settings' rules as the web console reads them (lot 0 after 1.0): lib/rules.tsv, the one table the command, the
menus, the presets and the import read through lib/common.sh. The console had its own copies (the units, the colours,
the radius choices, the antenna's altitude) and one of them already disagreed with the command. tests/test_rules.py
holds this reader and the shell's to the same answers."""
import os
import re

FILE = os.environ.get("ZB_RULES_FILE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib", "rules.tsv")
_NUMBER = re.compile(r"-?[0-9]+([.][0-9]+)?\Z")       # \Z, not $: a value ending in a line feed is not a number
_table = None


def table():
    """{KEY: (kind, rule, offered)}, read once."""
    global _table
    if _table is None:
        t = {}
        with open(FILE, encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue
                f = line.split("\t")
                t[f[0]] = (f[1], f[2], f[3] if len(f) > 3 else "")
        _table = t
    return _table


def known(key):
    return key in table()


def ok(key, value):
    """May `value` be stored for `key`? A key with no rule: False."""
    kind, rule, _ = table().get(key, ("", "", ""))
    v = str(value)
    if kind == "enum":
        return v in rule.split(" ")
    if kind == "int":
        lo, hi = rule.split(" ")
        return bool(re.match(r"-?[0-9]{1,6}\Z", v)) and int(lo) <= int(v) <= int(hi)
    if kind == "float":
        lo, hi = rule.split(" ")
        return bool(_NUMBER.match(v)) and float(lo) <= float(v) <= float(hi)
    if kind == "re":
        return bool(re.search(rule, v)) and "\n" not in v
    if kind == "number":
        return bool(_NUMBER.match(v))
    if kind == "words":                       # all, or some of the words, comma-separated, each once
        if v == "all":
            return True
        got = v.split(",")
        return bool(re.match(r"[a-z]+(,[a-z]+)*\Z", v)) and len(set(got)) == len(got) and all(w in rule.split(" ") for w in got)
    return False


def choices(key):
    """The values the command and the console offer for `key`: its shorter list when it has one, else an enum's values."""
    kind, rule, offered = table().get(key, ("", "", ""))
    return tuple((offered or (rule if kind in ("enum", "words") else "")).split())


def offered(key, value):
    c = choices(key)
    return str(value) in c if c and table().get(key, ("",))[0] != "words" else ok(key, value)


def bounds(key):
    """(lowest, highest) of an int or float rule, as numbers."""
    kind, rule, _ = table()[key]
    lo, hi = rule.split(" ")
    return (int(lo), int(hi)) if kind == "int" else (float(lo), float(hi))
