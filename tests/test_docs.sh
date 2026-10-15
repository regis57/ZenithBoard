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
cmds=$(awk '/^case "\$\{1:-\}" in/,/^esac/' bin/zenithboard | grep -oE '^  [a-z][a-z|-]*\)' | tr -d ' )' | cut -d'|' -f1 | sort -u)
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

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
