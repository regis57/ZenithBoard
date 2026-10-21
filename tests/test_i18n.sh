#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_i18n.sh   The web pages' languages (0.47.0): every shipped catalogue complete and in the
# English's shape ({placeholders}, <tags>), the language codes the same in the four places that list them, the review
# sheets in step with the catalogues, a reviewer's corrections taken back (and a broken one refused), the Pi's default
# (`zenithboard console lang`) refusing a language with no catalogue, graphs1090's page given its own copy, the wall's
# server saying which languages it has.
# shellcheck disable=SC2034
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }

check "every shipped catalogue complete, nothing left over, same placeholders and tags" 'python3 tools/i18n.py check > "$t/check" 2>&1 || { cat "$t/check" | grep -v " 0 problem" | head -20; false; }'
check "French is shipped"                                  'python3 tools/i18n.py check fr | grep -q "^fr: [0-9]* keys, 0 problem"'

# the codes: lib/common.sh, console_actions.py, i18n.js, tools/i18n.py
sh_codes=$(sed -n 's/^ZB_LANG_CODES="\(.*\)"$/\1/p' lib/common.sh)
py_codes=$(python3 -c 'import sys; sys.path.insert(0, "flightinfo"); import console_actions as a; print(" ".join(a.LANGS))')
js_codes=$(node -e 'global.window = {}; require("./flightinfo/static/i18n.js"); console.log(window.ZBI18N.LANGS.map(function (l) { return l[0]; }).join(" "))')
tool_codes="en $(python3 -c 'import sys; sys.path.insert(0, "tools"); import i18n; print(" ".join(i18n.LANGS))')"
check "the same fourteen codes everywhere"                 '[ "$sh_codes" = "$py_codes" ] && [ "$py_codes" = "$js_codes" ] && [ "$js_codes" = "$tool_codes" ] && [ "$(echo $sh_codes | wc -w)" = 14 ]'
check "both Chinese scripts, Italian, English with two flags" 'node -e "global.window = {}; require(\"./flightinfo/static/i18n.js\"); var L = window.ZBI18N.LANGS; var f = {}; L.forEach(function (l) { f[l[0]] = l[2].join(\"+\"); }); if (f.en !== \"GB+US\" || f[\"zh-Hans\"] !== \"CN\" || f[\"zh-Hant\"] !== \"TW\" || f.it !== \"IT\" || f[\"pt-BR\"] !== \"BR\") process.exit(1)"'
check "every flag a picture the wall carries"              'for c in GB US FR DE NL IT ES BR ID RU UA JP KR CN TW; do [ -f "flightinfo/data/flags/$c.png" ] || exit 1; done'

# the review sheets: what is shipped, beside the English, nothing older
for f in docs/translations/*.csv; do
  l=$(basename "$f" .csv)
  mkdir -p "$t/rev"; ZB_I18N_REVIEW_DIR="$t/rev" python3 tools/i18n.py review "$l" >/dev/null
  check "review sheet $l.csv in step with its catalogue (python3 tools/i18n.py review $l)" 'cmp -s "$f" "$t/rev/$l.csv"'
done
check "a sheet starts with its mark, so a spreadsheet reads the accents" 'head -c 3 docs/translations/fr.csv | od -An -tx1 | grep -q "ef bb bf"'

# a reviewer's sheet back: one correction taken, one breaking a placeholder refused; a French Excel's semicolons read
cp -r flightinfo/static/i18n "$t/cat"
python3 - "$t" <<'EOF'
import csv, sys
t = sys.argv[1]
rows = list(csv.DictReader(open("docs/translations/fr.csv", encoding="utf-8-sig")))
for r in rows:
    if r["english"] == "Make a backup":
        r["correction"] = "Créer une sauvegarde"
    if r["english"] == "{name} is signed in.":
        r["correction"] = "Il est connecté."
with open(t + "/fr.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, list(rows[0].keys()), delimiter=";")
    w.writeheader(); w.writerows(rows)
EOF
ZB_I18N_DIR="$t/cat" ZB_I18N_REVIEW_DIR="$t/rev2" python3 tools/i18n.py apply "$t/fr.csv" > "$t/apply.out" 2>&1
check "apply: the correction is taken, the old catalogue kept as .bak" 'grep -q "\"Make a backup\": \"Créer une sauvegarde\"" "$t/cat/fr/console.json" && [ -f "$t/cat/fr/console.json.bak" ]'
check "apply: a correction losing {name} is refused, and said" 'grep -q "\"{name} is signed in.\": \"{name} est connecté.\"" "$t/cat/fr/console.json" && grep -q "refused: keep the same" "$t/apply.out"'
check "apply: the sheet is written again with the new translation" 'grep -q "Make a backup,Créer une sauvegarde" "$t/rev2/fr.csv"'

# the shell: which languages, the Pi's default, graphs1090's copy
export ZENITHBOARD_ETC="$t/etc" ZB_SKIP_SERVICES=1 ZENITHBOARD_HOME="$PWD" ZB_GRAPHS_ROOT="$t/g"
mkdir -p "$ZENITHBOARD_ETC" "$t/g/usr/share/graphs1090/html" "$t/g/etc/default"; touch "$ZENITHBOARD_ETC/config.env" "$t/g/etc/default/graphs1090"
for l in common graphs console; do
  # shellcheck disable=SC1090
  . "lib/$l.sh"
done
check "languages offered: English and those with a catalogue, as the wall's server says" '[ "$(zb_langs)" = "$(python3 -c "import sys; sys.path.insert(0, \"flightinfo\"); import server; print(\" \".join(server.web_langs()))")" ] && zb_langs | grep -qw fr'
check "not chosen by default: the console asks at its first visit" '[ -z "$(cfg_get CONSOLE_LANG)" ] && console_lang | grep -q "not chosen yet"'
check "console lang: a language with no catalogue is refused" '! console_lang xx >/dev/null 2>&1 && [ -z "$(cfg_get CONSOLE_LANG)" ]'
check "console lang fr: written, said"                    'console_lang fr | grep -q "Language of the web pages: fr" && [ "$(cfg_get CONSOLE_LANG)" = fr ]'
cp tests/fixtures/graphs1090-index.html "$t/g/usr/share/graphs1090/html/index.html" 2>/dev/null || printf '<html><head>\n\t\t<link rel="stylesheet" href="portal.css">\n</head><body><h1>Performance Graphs</h1>\n\t\t<script src="graphs.js"></script>\n</body></html>\n' > "$t/g/usr/share/graphs1090/html/index.html"
cp "$t/g/usr/share/graphs1090/html/index.html" "$t/index.orig"
graphs_look_apply >/dev/null 2>&1
h="$t/g/usr/share/graphs1090/html"
check "graphs1090: its catalogue, i18n.js and the default beside its page" '[ -f "$h/zb-i18n/fr/graphs.json" ] && [ -f "$h/i18n.js" ] && grep -q "lang: \"fr\"" "$h/zb-lang.js" && grep -q "zb-lang.js" "$h/index.html" && grep -q "i18n.css" "$h/index.html"'
graphs_look_strip
check "graphs1090: its own look again leaves nothing of ours"    'cmp -s "$h/index.html" "$t/index.orig" && [ ! -e "$h/zb-i18n" ] && [ ! -e "$h/zb-lang.js" ] && [ ! -e "$h/i18n.js" ]'

# the wall's server and the console's list of actions
check "server: the languages it has, the default when it is one of them" 'python3 -c "
import sys; sys.path.insert(0, \"flightinfo\"); import server as s
c = s.public_config({\"CONSOLE_LANG\": \"fr\"}); assert c[\"lang\"] == \"fr\" and c[\"langs\"][0] == \"en\" and \"fr\" in c[\"langs\"], c
assert s.public_config({\"CONSOLE_LANG\": \"xx\"})[\"lang\"] == \"\" and s.public_config({})[\"lang\"] == \"\""'
check "console: the default chosen from the page, one of the codes only" 'python3 -c "
import sys; sys.path.insert(0, \"flightinfo\"); import console_actions as a, console as c
assert a.build(\"console-lang\", {\"value\": \"fr\"}) == [\"console\", \"lang\", \"fr\"]
try:
    a.build(\"console-lang\", {\"value\": \"fr;reboot\"}); raise SystemExit(1)
except ValueError: pass
assert \"CONSOLE_LANG\" in c.SHOWN_KEYS"'

[ "$fail" = 0 ] && echo "ALL OK"
exit "$fail"
