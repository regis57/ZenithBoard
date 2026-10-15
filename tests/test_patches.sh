#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_patches.sh   Debian security patches: the rule that is written, exactly what it allows, and
# that `off` puts the Pi back the way it was. apt-get and dpkg are stubs that record what they were asked.
# shellcheck disable=SC2034
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/apt"; touch "$ZENITHBOARD_ETC/config.env"
export ZB_SKIP_SERVICES=1 ZB_APT_CONF_DIR="$t/apt" ZB_UU_LOG="$t/uu.log"
printf '#!/bin/bash\necho "apt-get $*" >> "$T/apt.log"; [ "$2" = install ] && touch "$T/uu-installed"; [ "$2" = purge ] && rm -f "$T/uu-installed"; exit 0\n' > "$t/bin/apt-get"
printf '#!/bin/bash\n[ "$2" = unattended-upgrades ] && [ -f "$T/uu-installed" ] && exit 0; exit 1\n' > "$t/bin/dpkg"
chmod +x "$t"/bin/*; export T="$t" PATH="$t/bin:$PATH"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/patches.sh
. lib/patches.sh
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

check "off at first"                                   '[ "$(patches_state)" = off ]'

# ---- a Pi without unattended-upgrades: on installs it, writes the rule; off removes both
out=$(patches_on)
check "on: installs unattended-upgrades"               'grep -q "install -y unattended-upgrades" "$t/apt.log"'
check "on: remembers it installed the package"         '[ "$(cfg_get PATCHES_PKG_BY_ZB)" = 1 ]'
check "on: state on, setting on"                       '[ "$(patches_state)" = on ] && [ "$(cfg_get PATCHES)" = 1 ]'
check "on: says feeders alone, no reboot"              'printf "%s" "$out" | grep -q "feeders are left alone" && printf "%s" "$out" | grep -q "never rebooted"'
c="$PATCHES_CONF"
check "rule: daily"                                    'grep -q "APT::Periodic::Unattended-Upgrade \"1\"" "$c"'
check "rule: Debian security channel only"             'grep -q "codename=\${distro_codename}-security,label=Debian-Security" "$c"'
check "rule: any other origin list is cleared first"   'grep -q "^#clear Unattended-Upgrade::Origins-Pattern" "$c"'
check "rule: no stable, no raspbian, no third party"   '! grep -qi "raspbian\|flightaware\|flightradar\|planefinder\|adsbexchange.com\|stable" "$c"'
check "rule: never reboots"                            'grep -q "Automatic-Reboot \"false\"" "$c"'
for p in dump1090-fa piaware fr24feed pfclient adsbexchange-feed readsb; do
  check "rule: $p on the blacklist"                    'grep -q "\"$p\";" "$c"'
done
check "rule: mode 644"                                 '[ "$(stat -c %a "$c")" = 644 ]'
check "apt-config parses the rule"                     '! command -v apt-config >/dev/null || APT_CONFIG=/dev/null apt-config -c "$c" dump >/dev/null 2>&1'
out=$(patches_status)
check "status: on, no run yet"                         'printf "%s" "$out" | grep -q "patches: on" && printf "%s" "$out" | grep -q "No run yet"'
echo "2026-10-15 03:12:01,500 INFO Packages that will be upgraded: openssl" > "$t/uu.log"
out=$(patches_status)
check "status: shows the log once there is one"        'printf "%s" "$out" | grep -q "openssl"'

out=$(patches_off)
check "off: rule removed"                              '[ ! -e "$c" ] && [ "$(patches_state)" = off ]'
check "off: the package it installed is removed again" 'grep -q "purge -y unattended-upgrades" "$t/apt.log" && [ ! -e "$t/uu-installed" ]'
check "off: says so"                                   'printf "%s" "$out" | grep -q "was removed again"'
check "off: setting off, marker cleared"               '[ "$(cfg_get PATCHES)" = 0 ] && [ "$(cfg_get PATCHES_PKG_BY_ZB)" = 0 ]'

# ---- a Pi that already had unattended-upgrades: on leaves the package alone, off leaves it in place
: > "$t/apt.log"; touch "$t/uu-installed"
patches_on >/dev/null
check "pre-installed: on does not reinstall"           '! grep -q install "$t/apt.log"'
check "pre-installed: not marked as ours"              '[ "$(cfg_get PATCHES_PKG_BY_ZB 0)" = 0 ]'
out=$(patches_off)
check "pre-installed: off keeps the package"           '! grep -q purge "$t/apt.log" && [ -e "$t/uu-installed" ]'
check "pre-installed: off says it was left as it was"  'printf "%s" "$out" | grep -q "left as it was"'

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
