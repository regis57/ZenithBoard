#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_menus.sh   Every menu has exactly ONE way out: a "Back" entry in the list (no second Cancel button),
# or, for a plain picker without that entry, a Cancel button named Back. A whiptail stub records how it was called.
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC"; touch "$ZENITHBOARD_ETC/config.env"
# shellcheck source=lib/common.sh
. lib/common.sh
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }
printf '#!/bin/bash\necho "$*" > %s/args\n' "$t" > "$t/whiptail"; chmod +x "$t/whiptail"; PATH="$t:$PATH"

wt_menu "Settings" network "Network" logs "Logs" back "Return to the previous menu"
check "menu with a Back entry: no Cancel button"    'grep -q -- "--nocancel" "$t/args"'
wt_menu "Main" 1 "ADSB" 0 "Exit"
check "main menu: the 0 Exit entry is its way out"   'grep -q -- "--nocancel" "$t/args"'
wt_menu "Pick one" u1 "Wired connection" u2 "Home Wi-Fi"
check "plain picker: Cancel button is named Back"    'grep -q -- "--cancel-button Back" "$t/args" && ! grep -q -- "--nocancel" "$t/args"'
wt_menu "Item named back-up" backup "A tag that merely starts with back" other "Other"
check "a tag that only starts with 'back' does not count" 'grep -q -- "--cancel-button Back" "$t/args"'
wt_menu "Text mentioning back" a "back" b "x"
check "an item text 'back' (not a tag) does not count"    'grep -q -- "--cancel-button Back" "$t/args"'

# every menu in the code offers a way out: list entry "back"/"0", or it is a plain picker (handled by the Cancel button above)
for f in install.sh lib/*.sh; do
  [ "$f" = lib/common.sh ] && continue
  n=$(grep -c 'wt_menu "' "$f"); [ "$n" -gt 0 ] || continue
  b=$(grep -cE '(^|[ \\])(back "Return to the previous menu"|0 "Exit")' "$f")
  check "$f: $n wt_menu call(s), $b with a Back/Exit entry" '[ "$b" -ge 1 ]'
done
# the left column shows the tag and the right column the label: they must not say the same word twice ("back  Back")
check "no entry repeats its own tag as its label" '! grep -rniE "(^|[ \\])(back|exit) \"(back|exit)\"" install.sh lib/*.sh'
[ "$fail" = 0 ] && echo "ALL OK" || exit 1
