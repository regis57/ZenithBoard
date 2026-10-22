#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_adsbx_stats.sh   0.52.0: ADSB Exchange's stats package, off by default.
# - `on` refuses without ADSB Exchange's feed, runs their script from the pinned address, and notes the packages it
#   added and whether the adsbexchange user was in the video group.
# - `off` runs their uninstaller and removes those packages only (never one something else now needs). It takes the
#   user out of the video group when it was not in it, and keeps the feed's UUID.
# - Removing ADSB Exchange removes the stats first.
# Stubs: systemctl, dpkg-query, apt-get, id, gpasswd. A script stands in for theirs, writing under a folder that
# stands in for / what their install.sh writes (read on 22 October 2026, commit 11647f2).
# shellcheck disable=SC2034
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc" T="$t" ZB_AXS_ROOT="$t/root" ZB_AXS_CLONE="$t/tmp/adsbexchange-stats-git"
mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/root/usr/local/share/adsbexchange" "$t/root/etc/systemd/system" "$t/root/usr/local/bin" "$t/tmp"
touch "$ZENITHBOARD_ETC/config.env"
echo "0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0" > "$t/root/usr/local/share/adsbexchange/adsbx-uuid"
# installed packages; "jq" was removed earlier with its settings left (rc): not counted as there
printf 'installed bash\ninstalled curl\ninstalled git\ninstalled perl\ninstalled gzip\nconfig-files jq\n' > "$t/pkgs"
: > "$t/extra"; echo "adsbexchange" > "$t/groups"
printf '#!/bin/bash\necho "systemctl $*" >> "$T/log"\n[ "$1" = is-active ] && { echo active; exit 0; }\nexit 0\n' > "$t/bin/systemctl"
printf '#!/bin/bash\nsed "s/^/x /" "$T/pkgs" | while read -r _ s p; do echo "$s $p"; done\n' > "$t/bin/dpkg-query"
cat > "$t/bin/apt-get" <<'S'
#!/bin/bash
echo "apt-get $*" >> "$T/log"
if [ "$1" = -s ]; then shift 2; for p in "$@" $(cat "$T/extra"); do echo "Remv $p [1.0]"; done; exit 0; fi
[ "$1" = remove ] || exit 0
shift 2; for p in "$@"; do sed -i "/ $p\$/d" "$T/pkgs"; done
S
cat > "$t/bin/id" <<'S'
#!/bin/bash
[ "$1 $2" = "-nG adsbexchange" ] && { cat "$T/groups"; exit 0; }
exec /usr/bin/id "$@"
S
printf '#!/bin/bash\necho "gpasswd $*" >> "$T/log"\n[ "$1" = -d ] && echo adsbexchange > "$T/groups"\nexit 0\n' > "$t/bin/gpasswd"
chmod +x "$t"/bin/*; export PATH="$t/bin:$PATH"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/versions.sh
. lib/versions.sh
# shellcheck source=lib/adsb.sh
. lib/adsb.sh
# shellcheck source=lib/adsbxstats.sh
. lib/adsbxstats.sh
feed=0; is_adsbx() { [ "$feed" = 1 ]; }
# their stats.sh and install.sh, as far as what they leave on the Pi goes
fetch() {
  echo "fetch $1" >> "$T/log"
  [ -f "$T/fetch-fails" ] && return 1
  cat > "$2" <<'S'
R="$ZB_AXS_ROOT"
mkdir -p "$ZB_AXS_CLONE"; echo x > "$ZB_AXS_CLONE/install.sh"
sed -i '/ jq$/d' "$T/pkgs"; printf 'installed jq\ninstalled bind9-host\ninstalled bash-builtins\n' >> "$T/pkgs"
mkdir -p "$R/usr/local/share/adsbexchange-stats"
echo json-status > "$R/usr/local/share/adsbexchange-stats/json-status"
printf 'echo "uninstall.sh ran" >> "$T/log"; rm -f "%s/etc/systemd/system/adsbexchange-stats.service"; rm -rf "%s/usr/local/share/adsbexchange-stats"; rm "%s/usr/local/bin/adsbexchange-showurl"\n' "$R" "$R" "$R" > "$R/usr/local/share/adsbexchange-stats/uninstall.sh"
echo "[Service]" > "$R/etc/systemd/system/adsbexchange-stats.service"
echo showurl > "$R/usr/local/bin/adsbexchange-showurl"
echo "adsbexchange video" > "$T/groups"
echo "their script ran" >> "$T/log"
S
}
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }
R="$t/root"
URL="https://www.adsbexchange.com/api/feeders/?feed=0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0"

check "off by default"                                    '[ "$(adsbx_stats_state)" = off ] && adsbx_stats_status | grep -q "needs\|need ADSB Exchange"'
check "off when off: nothing done"                        'adsbx_stats_off | grep -q "already off" && [ ! -s "$t/log" ]'
check "on without the feed: refused, nothing changed"     '! adsbx_stats_on >/dev/null 2>&1 && [ ! -f "$AXS_STATE" ] && ! grep -q fetch "$t/log" 2>/dev/null'
feed=1
check "status with the feed: how to switch it on"         'adsbx_stats_status | grep -q "sudo zenithboard adsbx-stats on"'
out=$(adsbx_stats_on 2>&1)
check "on: their script, from the pinned address"         'grep -q "^fetch https://adsbexchange.com/stats.sh$" "$t/log" && grep -q "their script ran" "$t/log" && [ "$(adsbx_stats_state)" = on ]'
check "on: notes exactly the packages it added (jq was only rc)" '[ "$(axs_state_get ADDED)" = "bash-builtins bind9-host jq" ]'
check "on: notes the user was not in the video group"    '[ "$(axs_state_get VIDEO)" = 0 ]'
check "on: says what is sent, and the link"               'printf "%s" "$out" | grep -q "Every 5 seconds" && printf "%s" "$out" | grep -qF "$URL" && printf "%s" "$out" | grep -q "Keep it to yourself"'
check "on: their clone in /tmp is cleaned up"             '[ ! -e "$ZB_AXS_CLONE" ]'
check "on again: already on, nothing downloaded"          'adsbx_stats_on | grep -q "already on" && [ "$(grep -c "^fetch" "$t/log")" = 1 ]'
check "url: the link their adsbexchange-showurl prints"   '[ "$(adsbx_stats_url)" = "$URL" ]'
check "status: on, running, the link"                     'adsbx_stats_status | grep -q "ON, active" && adsbx_stats_status | grep -qF "$URL"'
adsbx_stats_update >/dev/null 2>&1
check "update: their script again, the list unchanged"    '[ "$(grep -c "^fetch" "$t/log")" = 2 ] && [ "$(axs_state_get ADDED)" = "bash-builtins bind9-host jq" ] && [ "$(axs_state_get VIDEO)" = 0 ]'

: > "$t/log"
out=$(adsbx_stats_off 2>&1)
check "off: their uninstaller ran, unit and files gone"   'grep -q "uninstall.sh ran" "$t/log" && [ ! -e "$AXS_UNIT" ] && [ ! -e "$AXS_HOME" ] && [ ! -e "$AXS_SHOWURL" ]'
check "off: the added packages removed, never purged"     'grep -q "^apt-get remove -y bash-builtins bind9-host jq$" "$t/log" && ! grep -q purge "$t/log" && ! grep -q " jq$" "$t/pkgs" && grep -q " perl$" "$t/pkgs"'
check "off: out of the video group it was not in"         'grep -q "^gpasswd -d adsbexchange video$" "$t/log"'
check "off: the feed's UUID is kept"                      'grep -q "^0f1e2d3c" "$R/usr/local/share/adsbexchange/adsbx-uuid" && printf "%s" "$out" | grep -q "same map"'
check "off: state gone"                                   '[ ! -f "$AXS_STATE" ] && [ "$(adsbx_stats_state)" = off ]'

# something installed since needs one of them: apt would take it too, so nothing is removed
adsbx_stats_on >/dev/null 2>&1; echo kodi > "$t/extra"; : > "$t/log"
out=$(adsbx_stats_off 2>&1)
check "a package now needed elsewhere: all kept, said"    '! grep -q "^apt-get remove -y" "$t/log" && printf "%s" "$out" | grep -q "would also remove: kodi" && grep -q " jq$" "$t/pkgs"'
: > "$t/extra"

# installed by hand with their two lines, before ZenithBoard knew: off removes it and nothing else
sed -i '/ jq$\| bind9-host$\| bash-builtins$/d' "$t/pkgs"
bash "$(f=$(mktemp "$t/x.XXXX"); fetch x "$f"; echo "$f")"; : > "$t/log"
check "by hand: seen as on"                               '[ "$(adsbx_stats_state)" = on ]'
adsbx_stats_off >/dev/null 2>&1
check "by hand: off runs their uninstaller, no package or group taken" 'grep -q "uninstall.sh ran" "$t/log" && ! grep -q "apt-get" "$t/log" && ! grep -q gpasswd "$t/log" && [ "$(adsbx_stats_state)" = off ]'

# their script cannot be downloaded: said, and `off` puts back the rest
touch "$t/fetch-fails"; : > "$t/log"
out=$(adsbx_stats_on 2>&1); rc=$?
check "download fails: not on, the way back said"         '[ "$rc" != 0 ] && [ "$(adsbx_stats_state)" = off ] && printf "%s" "$out" | grep -q "adsbx-stats off"'
check "download fails: off still cleans its notes"        'adsbx_stats_off >/dev/null 2>&1; [ ! -f "$AXS_STATE" ]'
rm -f "$t/fetch-fails"

# a link where their clone goes is somebody else's: never followed
mkdir -p "$t/elsewhere"; echo keep > "$t/elsewhere/file"; rm -rf "$ZB_AXS_CLONE"; ln -s "$t/elsewhere" "$ZB_AXS_CLONE"
fetch() {
  echo "fetch $1" >> "$T/log"
  printf 'mkdir -p "%s/usr/local/share/adsbexchange-stats"; echo "[Service]" > "%s/etc/systemd/system/adsbexchange-stats.service"\n' "$R" "$R" > "$2"
}
adsbx_stats_on >/dev/null 2>&1
check "a link in /tmp: not followed, not removed"         '[ -L "$ZB_AXS_CLONE" ] && [ -f "$t/elsewhere/file" ]'
rm -f "$ZB_AXS_CLONE"

# the UUID: only a real one makes a link
printf '{0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0}\n' > "$R/usr/local/share/adsbexchange/adsbx-uuid"
check "UUID in braces: the link without them"             '[ "$(adsbx_stats_url)" = "$URL" ]'
printf 'not-a-uuid"; rm -rf /\n' > "$R/usr/local/share/adsbexchange/adsbx-uuid"
check "UUID broken: no link, and status says why"         '! adsbx_stats_url >/dev/null && adsbx_stats_status 2>&1 | grep -q "missing or unreadable"'
echo "0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0" > "$R/usr/local/share/adsbexchange/adsbx-uuid"

# removing ADSB Exchange takes the stats first (their feed uninstaller leaves them running)
: > "$t/log"; ADSBX_UNINSTALL="$t/none"
remove_adsbx >/dev/null 2>&1
check "remove ADSB Exchange: the stats go first"          '[ "$(adsbx_stats_state)" = off ] && [ ! -f "$AXS_STATE" ] && grep -n "adsbexchange-stats\|adsbexchange-feed" "$t/log" | head -1 | grep -q stats'

# the rest of ZenithBoard knows it
check "command: adsbx-stats on|off|status|url"            'grep -q "on)     root_or_die; adsbx_stats_on" bin/zenithboard && grep -q "zenithboard adsbx-stats on|off|status|url" bin/zenithboard'
check "menu 1: in the networks checklist, off unless on"  'grep -q "ADSBX_STATS \"ADSB Exchange stats: their map of your aircraft\" \"\$st_axs\"" lib/adsb.sh && grep -q "st_axs=OFF; is_adsbx_stats && st_axs=ON" lib/adsb.sh'
check "update: their script again when on"                'grep -q "is_adsbx_stats; then log \"ADSB Exchange stats\"; adsbx_stats_update" lib/update.sh'
check "status, logs, console: the service is known"       'grep -q "ADSB Exchange stats\" true adsbexchange-stats" bin/zenithboard && grep -q "u adsbexchange-stats" lib/logs.sh && grep -q "adsbexchange-feed adsbexchange-stats" lib/console.sh'
check "the address is checked monthly"                    'grep -q "ADSBX_STATS_URL" tools/check-links.sh'
check "both entry points load it"                         'grep -q "lib/adsbxstats.sh" bin/zenithboard && grep -q "lib/adsbxstats.sh" install.sh'
check "never purge, never apt_remove (purge)"             '! grep -v "^ *#" lib/adsbxstats.sh | grep -q "purge\|apt_remove"'
check "status never prints the UUID (it is pasted in chats)" '! sed -n "/^cmd_status()/,/^}/p" bin/zenithboard | grep -q "adsbx_stats_url\|adsbx_stats_where"'

[ "$fail" = 0 ] && echo "ALL OK"; exit "$fail"
