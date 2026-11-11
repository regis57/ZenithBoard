#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_docs.sh
# The wiki's command reference must keep up with the program: every command bin/zenithboard accepts, and every
# line its own help prints, has to appear in docs/wiki/Command-reference.md. Adding a command without documenting
# it fails here, in CI, instead of in a user's terminal.
set -u
cd "$(dirname "$0")/.." || exit 1
page=docs/wiki/Command-reference.md
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

# 1. every top-level command in the case statement (aliases such as color|colour: the first name is enough)
cmds=$(awk '/^case "\$\{1:-\}" in/,/^esac/' bin/zenithboard | grep -oE '^  [a-z][a-z0-9|-]*\)' | tr -d ' )' | cut -d'|' -f1 | sort -u)
[ -n "$cmds" ] || { echo "FAIL could not read the commands from bin/zenithboard"; exit 1; }
for c in $cmds; do
  if grep -q "zenithboard $c\b" "$page"; then ok "documented: zenithboard $c"; else bad "NOT documented: zenithboard $c"; fi
done

# 2. every "zenithboard WORD WORD" line of the built-in help
while read -r a b; do
  [ -n "$a" ] || continue
  # the help writes alternatives as on|off: the page writes them as `on` · `off` - so look for the first one
  b1=${b%%|*}
  if grep -qE "zenithboard $a( [^|]*)?\b$b1\b" "$page" || grep -q "zenithboard $a $b1" "$page"; then ok "help line: zenithboard $a $b1"
  else bad "help line missing from the page: zenithboard $a $b1"; fi
done < <(sed -n '/^usage()/,/^USAGE/p' bin/zenithboard | grep -oE '^  zenithboard [a-z-]+ [a-z0-9-]+' | awk '{print $2, $3}' | sort -u | grep -vE ' [A-Z0-9]')     # skip values (radius 1|2|5...) and placeholders

# ---- the release notes are one version's CHANGELOG section, exactly
# shellcheck disable=SC2034  # used inside the eval-ed check strings
n=$(bash tools/release-notes.sh 0.14.3)
check "release notes: the section asked for"           'printf "%s" "$n" | grep -q "No more bright frame"'
check "release notes: not the one before or after"     '! printf "%s" "$n" | grep -q "turns continuously\|Beluga"'
check "release notes: no heading, no blank edges"      '! printf "%s" "$n" | grep -q "^## " && [ -n "$(printf "%s" "$n" | head -1)" ]'
check "release notes: unknown version prints nothing"  '[ -z "$(bash tools/release-notes.sh 9.9.9)" ]'
check "release workflow reads ZB_VERSION and tags v<version>" 'grep -q "ZB_VERSION" .github/workflows/release.yml && grep -q "gh release create \"v\$V\"" .github/workflows/release.yml'

# ---- 0.41.0: the fresh install page, a 1.0 proof, is reachable from the README, the wiki's sidebar and home page
check "Fresh-install: the page exists, with its checklist"   'grep -q "^## The 1.0 checklist" docs/wiki/Fresh-install.md'
check "Fresh-install: linked from README, sidebar and home" 'grep -q "wiki/Fresh-install" README.md && grep -q "(Fresh-install)" docs/wiki/_Sidebar.md && grep -q "(Fresh-install)" docs/wiki/Home.md'

# ---- 0.44.0: the menu page and the move for non-specialists, linked, their pictures in the repository
check "The-menu and Moving-to-a-new-card linked from the sidebar" 'grep -q "(The-menu)" docs/wiki/_Sidebar.md && grep -q "(Moving-to-a-new-card)" docs/wiki/_Sidebar.md'
check "every menu picture the docs show is in docs/images" '( for f in $(grep -ho "docs/images/menu-[a-z]*\.png" README.md docs/wiki/*.md | sort -u); do [ -f "$f" ] || exit 1; done )'
check "the move names WinSCP and the typed word" 'grep -q "WinSCP" docs/wiki/Moving-to-a-new-card.md && grep -q "RESTORE" docs/wiki/Moving-to-a-new-card.md'

# ---- 0.53.6: CI runs every test file. Its list is written by hand on purpose (a new test shows in the diff), so a file
# left off it fails here instead of going unrun: five suites, the console's and the translations' among them, were
# never run there between 0.39.0 and 0.53.5
for f in tests/test_*.sh tests/test_*.js; do
  # anchored: a commented-out line does not count (the review of 0.99.8)
  check "CI runs $f" 'grep -qE "^[[:space:]]+(bash|node) $f\$" .github/workflows/ci.yml'
done
# 0.99.18: and the full local CI that CLAUDE.md gives a session (its step 4) runs every JavaScript test too
for f in tests/test_*.js; do
  n=${f#tests/test_}; n=${n%.js}
  check "CLAUDE.md's local CI runs $f" 'grep -qE "for j in ([a-z0-9_]+ )*$n( [a-z0-9_ ]*)?; do node tests/test_\\\$j.js" CLAUDE.md'
done
# 0.99.21 (review B14, T8): and say in a word what each suite covers. Ten suites, test_units.sh and test_security.sh
# among them, had no row on the Testing page; a new file without one fails here
for f in tests/test_*.sh tests/test_*.js tests/test_*.py; do
  check "Testing.md has a row for $f" 'grep -qF "\`${f#tests/}\`" docs/wiki/Testing.md'
done
# and the local loops say which suite failed instead of scrolling past it
check "CLAUDE.md's shell and node loops print FAIL" 'grep -qF "do bash \$t || echo \"FAIL \$t\"; done" CLAUDE.md && grep -qF "do node tests/test_\$j.js || echo \"FAIL \$j\"; done" CLAUDE.md'

# 0.99.25 (the owner, 11 November 2026: "es-tu sûr que tu ne casses rien dans le menu et la console ? pour ne rien casser
# en 1.1"): the old command names of Command reference -> Old names are still accepted, and nothing ZenithBoard runs or
# prints uses one: the console's actions, the menus, the services, the messages, the translated pages, the wiki. When
# 1.1 removes them, only the table and the old_name lines in bin/zenithboard have to go; this check says if anything else
# still needed them.
old_out=$(python3 - <<'PY'
import glob, os, re, subprocess, sys, importlib.util
ref = open("docs/wiki/Command-reference.md", encoding="utf-8").read().split("## Old names", 1)[1]
olds = []
for row in ref.splitlines():
    if not row.startswith("| `zenithboard"): continue
    cell = row.split("|")[1]
    first = re.match(r"\s*`zenithboard ([a-z -]+?)(?: …)?`", cell)
    cmd = first.group(1).split()
    olds.append(cmd)
    for extra in re.findall(r"·\s*`([a-z -]+?)(?: …)?`", cell):
        e = extra.split()
        olds.append(e if e[0] in ("social", "telegram", "preset", "gain") else [cmd[0]] + e)
bad = []
if len(olds) < 14: bad.append("the Old names table reads %d old names, expected 14" % len(olds))
# 1. still accepted, with the old_name line (until 1.1)
env = dict(os.environ)
for o in olds:
    probe = o + (["list"] if o[-1] in ("presets",) else [])
    if o in (["show"], ["threads"], ["style"], ["gain", "check"]):
        r = subprocess.run(["bash", "bin/zenithboard"] + probe, capture_output=True, text=True, env=env, timeout=60)
        if "old name" not in r.stderr: bad.append("%s: no old-name line (%r)" % (" ".join(o), r.stderr[-120:]))
    elif not re.search(r"(?m)^\s+[a-z|\"-]*\b%s\b[a-z|\"-]*\).*?old_name|old_name \"?%s" % (re.escape(o[-1]), re.escape(" ".join(o))), open("bin/zenithboard").read()):
        bad.append("%s: not answered by bin/zenithboard with an old-name line" % " ".join(o))
# 2. the console sends none of them
spec = importlib.util.spec_from_file_location("ca", "flightinfo/console_actions.py"); ca = importlib.util.module_from_spec(spec)
sys.path.insert(0, "flightinfo"); spec.loader.exec_module(ca)
for name, a in ca.ACTIONS.items():
    argv = [t for t in (a[2] or []) if not t.startswith("{")]
    for o in olds:
        if argv[:len(o)] == o: bad.append("console action %s sends the old name %s" % (name, " ".join(o)))
# 3. nothing ZenithBoard runs or prints, nor the wiki's current pages, names one
files = ["install.sh", "README.md", "bin/zenithboard-demo"] + glob.glob("lib/*.sh") + glob.glob("systemd/*") + glob.glob("flightinfo/*.py") + \
        glob.glob("flightinfo/static/*.js") + glob.glob("flightinfo/static/*.html") + glob.glob("flightinfo/static/i18n/*/*.json") + \
        glob.glob("tools/*.py") + glob.glob("tools/*.sh") + [f for f in glob.glob("docs/wiki/*.md") if os.path.basename(f) not in ("Command-reference.md", "Project-status.md", "Roadmap.md")]
for f in files:
    text = open(f, encoding="utf-8", errors="replace").read()
    for o in olds:
        for m in re.finditer(r"zenithboard %s\b(?![-|])" % re.escape(" ".join(o)), text):
            line = text[: m.start()].count("\n") + 1
            if "old name" in text.splitlines()[line - 1] or "old_name" in text.splitlines()[line - 1]: continue
            bad.append("%s:%d names the old %s" % (f, line, " ".join(o)))
print("\n".join(bad) if bad else "OK %d old names" % len(olds))
PY
)
check "old names: still accepted, and nothing uses them ($old_out)" '[ "${old_out#OK}" != "$old_out" ]'
[ "${old_out#OK}" != "$old_out" ] || printf '%s\n' "$old_out" >&2

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
