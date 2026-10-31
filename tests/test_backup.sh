#!/bin/bash
# shellcheck disable=SC2034   # m, show and out are read inside the checks' eval
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_backup.sh   Backup and restore (0.42.0): what a backup holds (and never holds), what the
# console's backup leaves out, the archives refused, the typed word, and a restore on a "new card": settings, what
# was on switched on again, statistics merged, posting history, the old card's logs, the networks' identities applied
# now or kept for their installers, graphs1090's history, and what was there before kept.
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc" ZB_SKIP_SERVICES=1 ZB_BACKUP_DATA="$t/data" ZB_STATS_OUT_DIR="$t/data/stats" \
  ZENITHBOARD_SOCIAL_DIR="$t/data/social" ZENITHBOARD_SOCIAL_SECRETS="$t/etc/social.env" ZB_JOURNAL_DIR="$t/journal" \
  ZB_MACHINE_ID_FILE="$t/machine-id" ZB_GRAPHS_ROOT="$t/g" ZB_ADSBX_UUID="$t/adsbx/adsbx-uuid" ZB_PF_CONFIG="$t/pfclient-config.json" \
  FR24_INI="$t/fr24feed.ini" ZB_PIAWARE_ID_CACHE="$t/piaware-cache" ZB_BACKUP_CMD="$t/bin/zb" ZB_CONSOLE_DIR="$t/console" \
  ZB_SYSTEMD_CONF_DIR="$t/sysconf" ZB_JOURNALD_DIR="$t/journald"
mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/console/out"; touch "$ZENITHBOARD_ETC/config.env"
printf '#!/bin/bash\necho "systemctl $*" >> "%s/systemctl.log"\n' "$t" > "$t/bin/systemctl"
printf '#!/bin/bash\nexit 0\n' > "$t/bin/nmcli"                                   # no Wi-Fi: Wi-Fi hardening is skipped
printf '#!/bin/bash\necho "$*" >> "%s/zb.log"\n' "$t" > "$t/bin/zb"
# piaware-config: answers -show feeder-id, logs a change
printf '#!/bin/bash\nif [ "$1" = -show ]; then echo 11111111-2222-3333-4444-555555555555; else echo "piaware-config $*" >> "%s/piaware.log"; fi\n' "$t" > "$t/pw"
chmod +x "$t"/bin/* "$t/pw"
export PATH="$t/bin:$PATH"
export ZB_AXS_ROOT="$t/axs"; mkdir -p "$t/axs/etc/systemd/system"; echo "[Service]" > "$t/axs/etc/systemd/system/adsbexchange-stats.service"   # 0.52.0: on
for l in common adsbxstats stats graphs reliability patches gain logs social settings wifi console backup; do
  # shellcheck disable=SC1090
  . "lib/$l.sh"
done
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }
members() { tar -tzf "$1" | sed 's|^zb/||; s|/$||' | sort; }

# ---- the old card
echo 0123456789abcdef0123456789abcdef > "$t/machine-id"
cfg_set UNITS metric; cfg_set RADIUS 15; cfg_set LAT 49.1193; cfg_set LON 6.1757; cfg_set ALT_M 180; cfg_set STATS 1; cfg_set NETWATCH 1; cfg_set FR24_KEY never-exported
mkdir -p "$t/sysconf" "$t/journald" "$t/journal/0123456789abcdef0123456789abcdef" "$t/data/stats" "$t/data/social" "$t/adsbx"
printf '[Manager]\nRuntimeWatchdogSec=10\n' > "$t/sysconf/watchdog.conf"
printf '[Journal]\nStorage=persistent\n' > "$t/journald/50-persistent.conf"
echo "old boot" > "$t/journal/0123456789abcdef0123456789abcdef/system.journal"
printf '%s\n1761000000,10,100,5,6\n1761000600,11,110,6,7\n' "$STATS_HEADER" > "$t/data/stats/stats.csv"
echo "3C6444" > "$t/data/stats/seen-2026-10-20"; echo "x" > "$t/data/stats/fleet-2026-10-20"
echo '{"posted": ["3c6444"], "summary_daily": "2026-10-21"}' > "$t/data/social/state.json"
mkdir -p "$t/etc"; echo '{airline} {flight}[, {from} → {to}]' > "$t/etc/social-templates.txt"      # 0.51.0
echo "c0ffee00-1234-4abc-8def-0123456789ab" > "$t/adsbx/adsbx-uuid"
printf 'receiver="beast-tcp"\nfr24key="ABCDEF123456"\n' > "$t/fr24feed.ini"
printf '{\n  "sharecode": "5X2X2X2X9XaX3",\n  "latitude": "49.2"\n}\n' > "$t/pfclient-config.json"
mkdir -p "$t/g/usr/share/graphs1090/html" "$t/g/var/lib/collectd/rrd/localhost"; touch "$t/g/usr/share/graphs1090/html/index.html"; echo "<rrd><lastupdate>1761000600</lastupdate></rrd>" > "$t/g/var/lib/collectd/rrd/localhost/a.xml"
printf '#!/bin/bash\ntar -C "$1" -czf "$2" .\n' > "$t/g/usr/share/graphs1090/rrd-dump.sh"
printf '#!/bin/bash\nmkdir -p "$2"; tar -C "$2" -xzf "$1"; echo restored >> "%s/rrd.log"\n' "$t" > "$t/g/usr/share/graphs1090/rrd-restore.sh"
chmod +x "$t"/g/usr/share/graphs1090/*.sh
ln -s "$t/pw" "$t/bin/piaware-config"

out=$(cd "$t" && backup_make "$t/full.tar.gz")
check "make: writes the file, owner-only"            '[ -f "$t/full.tar.gz" ] && [ "$(stat -c %a "$t/full.tar.gz")" = 600 ] && echo "$out" | grep -q "keep it to yourself"'
m=$(members "$t/full.tar.gz")
check "make: every part is in it"                    '( for x in MANIFEST settings.env features.env feeders.env pfclient-config.json graphs-xml.tar.gz stats/stats.csv stats/seen-2026-10-20 social/state.json social/templates.txt journal/0123456789abcdef0123456789abcdef/system.journal; do echo "$m" | grep -qx "$x" || exit 1; done )'
mkdir -p "$t/x"; tar -C "$t/x" -xzf "$t/full.tar.gz"
check "make: the settings without a secret"          'grep -q "^RADIUS=15$" "$t/x/zb/settings.env" && ! grep -q "never-exported" "$t/x/zb/settings.env"'
check "make: ADSB Exchange stats on (0.52.0)"        'grep -qx "adsbx_stats=on" "$t/x/zb/features.env"'
check "make: what is on, even outside config.env"    'grep -qx "stats=on" "$t/x/zb/features.env" && grep -qx "watchdog=on" "$t/x/zb/features.env" && grep -qx "keeplogs=on" "$t/x/zb/features.env" && grep -qx "netwatch=on" "$t/x/zb/features.env" && grep -qx "social=off" "$t/x/zb/features.env"'
check "make: the three identities"                   'grep -qx "ADSBX_UUID=c0ffee00-1234-4abc-8def-0123456789ab" "$t/x/zb/feeders.env" && grep -qx "PIAWARE_FEEDER_ID=11111111-2222-3333-4444-555555555555" "$t/x/zb/feeders.env" && grep -qx "FR24_KEY=ABCDEF123456" "$t/x/zb/feeders.env"'
# the review of 0.99.8: the setup outside the check, the assertion last (it ended on rm -f, so it could not fail)
echo "BLUESKY_APP_PASSWORD=zzz-social" > "$t/etc/social.env"; echo "CONSOLE_PASSWORD_HASH=zzz-console" > "$t/etc/console.env"; echo "TELEGRAM_BOT_TOKEN=zzz-telegram" > "$t/etc/telegram.env"
backup_make "$t/f2.tar.gz" >/dev/null
check "make: never the Bluesky, console or Telegram secrets" '! tar -xzOf "$t/f2.tar.gz" | grep -q "zzz-"'
rm -f "$t/etc/social.env" "$t/etc/console.env" "$t/etc/telegram.env"
show=$(backup_show "$t/full.tar.gz")
check "show: names the identities, never their values" 'echo "$show" | grep -q "Flightradar24 sharing key" && echo "$show" | grep -q "Plane Finder share code" && ! echo "$show" | grep -q "ABCDEF123456\|5X2X2X2X9XaX3\|c0ffee00"'
check "show: what is on"                             'echo "$show" | grep -q "On: Statistics, graphs1090, Hardware watchdog, Network watchdog, Logs kept after a restart"'

backup_make --console >/dev/null
check "console: in out/, readable by the wall's group" '[ -f "$t/console/out/backup.tar.gz" ] && [ "$(stat -c %a "$t/console/out/backup.tar.gz")" = 640 ]'
check "console: no identity, no key"                 'm=$(members "$t/console/out/backup.tar.gz"); ! echo "$m" | grep -q "feeders.env\|pfclient" && ! tar -xzOf "$t/console/out/backup.tar.gz" | grep -q "ABCDEF123456"'

# ---- refused archives
mkdir -p "$t/evil/zb"; echo hi > "$t/evil/zb/MANIFEST"; ln -s /etc/passwd "$t/evil/zb/stats"
tar -C "$t/evil" -czf "$t/link.tar.gz" zb
echo x > "$t/evil/other"; tar -C "$t/evil" -czf "$t/name.tar.gz" other
check "refused: a link inside"                       '! backup_show "$t/link.tar.gz" >/dev/null 2>&1'
check "refused: a name a backup does not hold"       '! backup_show "$t/name.tar.gz" >/dev/null 2>&1'
check "refused: not a tar at all"                    'echo nope > "$t/no.tar.gz"; ! backup_show "$t/no.tar.gz" >/dev/null 2>&1'

# ---- the new card: other machine id, no data, no network installed yet, a few hours of its own statistics
rm -f "$t/etc/social-templates.txt"
rm -rf "$t/data" "$t/adsbx" "$t/fr24feed.ini" "$t/pfclient-config.json" "$t/sysconf/watchdog.conf" "$t/journald/50-persistent.conf" "$t/g/var/lib/collectd" "$t/g/usr/share/graphs1090/html" "$t/bin/piaware-config"
echo fedcba9876543210fedcba9876543210 > "$t/machine-id"
: > "$ZENITHBOARD_ETC/config.env"; cfg_set RADIUS 5; cfg_set STATS 0; cfg_set NETWATCH 0
mkdir -p "$t/data/stats"; printf '%s\n1761100000,12,120,7,8\n' "$STATS_HEADER" > "$t/data/stats/stats.csv"

check "restore: anything but RESTORE changes nothing" 'echo no | backup_restore "$t/full.tar.gz" >/dev/null 2>&1; [ "$(cfg_get RADIUS)" = 5 ] && [ ! -e "$t/data/stats/seen-2026-10-20" ]'
# 0.53.8: the console's copy holds no network identity: on a card with no network yet it is said before the typed word,
# and a full backup is not told that
out=$(echo no | backup_restore "$t/console/out/backup.tar.gz" 2>&1)
check "restore: the console's copy on a bare card says it is not the one to move with" 'echo "$out" | grep -q "This is the console.s copy: it holds no network identity" && echo "$out" | grep -q "backup make" && [ "$(cfg_get RADIUS)" = 5 ]'
out=$(echo no | backup_restore "$t/full.tar.gz" 2>&1)
check "restore: a full backup is not warned"          '! echo "$out" | grep -q "console.s copy"'
zb_apply_location() { echo "$*" > "$t/location.applied"; }      # 0.44.0: the position goes everywhere it is stored
cfg_set TAILSCALE 1; ts_installed() { return 1; }        # 0.54.3: a card that used Tailscale, and has none yet
out=$(echo RESTORE | backup_restore "$t/full.tar.gz" 2>&1)
check "restore: Tailscale used before and not installed here is said, with the command" 'echo "$out" | grep -q "sudo zenithboard tailscale on"'

check "restore: the position applied everywhere, not only imported" '[ "$(cat "$t/location.applied" 2>/dev/null)" = "49.1193 6.1757 180" ]'
check "restore: the settings"                        '[ "$(cfg_get RADIUS)" = 15 ] && [ "$(cfg_get UNITS)" = metric ]'
check "restore: statistics back, both cards' samples" '[ -f "$t/data/stats/seen-2026-10-20" ] && [ "$(grep -c "^17" "$t/data/stats/stats.csv")" = 3 ] && [ "$(head -1 "$t/data/stats/stats.csv")" = "$STATS_HEADER" ]'
check "restore: what was posted (no double post)"    'grep -q 3c6444 "$t/data/social/state.json"'
check "restore: the owner's post templates (0.51.0)"  'grep -q "{airline} {flight}" "$t/etc/social-templates.txt"'
check "restore: the old card logs beside the new"   '[ -f "$t/journal/0123456789abcdef0123456789abcdef/system.journal" ] && echo "$out" | grep -q "journalctl -m"'
check "restore: ADSB Exchange's UUID written now"     '[ "$(cat "$t/adsbx/adsbx-uuid")" = c0ffee00-1234-4abc-8def-0123456789ab ]'
check "restore: networks not installed wait, root only" '[ "$(cat "$t/data/restore-pending/piaware-feeder-id")" = 11111111-2222-3333-4444-555555555555 ] && [ "$(cat "$t/data/restore-pending/fr24key")" = ABCDEF123456 ] && [ -f "$t/data/restore-pending/pfclient-config.json" ] && [ "$(stat -c %a "$t/data/restore-pending")" = 700 ] && [ "$(stat -c %a "$t/data/restore-pending/fr24key")" = 600 ]'
check "restore: what was on, switched on again"      'grep -qx "stats on" "$t/zb.log" && grep -qx "watchdog on" "$t/zb.log" && grep -qx "keeplogs on" "$t/zb.log" && grep -qx "netwatch on" "$t/zb.log" && ! grep -q "social\|console\|wifi" "$t/zb.log"'
check "restore: ADSB Exchange stats wait for its feed" '! grep -q "adsbx-stats" "$t/zb.log" && echo "$out" | grep -q "sudo zenithboard adsbx-stats on      (after ADSB Exchange: menu 1 ADS-B → 1 Decoder and networks)"'
check "restore: graphs1090's history waits for it"   'grep -qx "graphs on" "$t/zb.log" && [ -f "$t/data/restore-pending/graphs-xml.tar.gz" ] && echo "$out" | grep -q "waits for graphs1090"'
check "restore: what was here kept first"            'b=$(ls -d "$t"/data/before-restore-*); grep -q "^RADIUS=5$" "$b/config.env" && grep -q 1761100000 "$b/stats/stats.csv"'
check "restore: never prints a key"                  '! echo "$out" | grep -q "ABCDEF123456\|5X2X2X2X9XaX3\|11111111-2222"'

# ---- the installers pick the identities up
ln -s "$t/pw" "$t/bin/piaware-config"
bk_pending_apply piaware >/dev/null
check "installer: FlightAware gets the feeder ID"    'grep -q "piaware-config feeder-id 11111111-2222-3333-4444-555555555555" "$t/piaware.log" && [ ! -e "$t/data/restore-pending/piaware-feeder-id" ]'
bk_pending_apply fr24 >/dev/null
check "installer: Flightradar24 gets the key"        'grep -qx "fr24key=\"ABCDEF123456\"" "$t/fr24feed.ini" && [ ! -e "$t/data/restore-pending/fr24key" ]'
bk_pending_apply planefinder >/dev/null
check "installer: Plane Finder gets its share code"  'grep -q 5X2X2X2X9XaX3 "$t/pfclient-config.json"'
mkdir -p "$t/g/usr/share/graphs1090/html"; touch "$t/g/usr/share/graphs1090/html/index.html"        # graphs1090 installed now
bk_pending_apply graphs >/dev/null
check "installer: graphs1090 gets its history"       'grep -q restored "$t/rrd.log" && [ -f "$t/g/var/lib/collectd/rrd/localhost/a.xml" ] && [ ! -e "$t/data/restore-pending" ]'
check "installer hooks are in place"                 'grep -q "bk_pending_apply piaware" lib/adsb.sh && grep -q "bk_pending_apply fr24" lib/adsb.sh && grep -q "bk_pending_apply planefinder" lib/adsb.sh && grep -q "bk_pending_apply graphs" lib/graphs.sh'

# ---- the console: makes and serves it, never restores
check "console: backup is an action, restore is not" 'python3 -c "
import sys; sys.path.insert(0, \"flightinfo\"); import console_actions as a
assert a.build(\"backup\", {}) == [\"backup\", \"make\", \"--console\"]
assert not any(\"restore\" in (s[2] or []) for s in a.ACTIONS.values())"'
check "console: the download is the file made"       'ZB_CONSOLE_DIR="$t/console" python3 -c "
import sys; sys.path.insert(0, \"flightinfo\"); import console
i = console.backup_info(); assert i and i[\"bytes\"] > 0, i"'

# ---- 0.42.1: read back, listed newest first, the older ones deleted, the console's copy deleted
show=$(backup_show "$t/full.tar.gz")
check "check: each part read back, with its span"    'echo "$show" | grep -q "statistics: 2 samples, 1761000000 to 1761000600" && echo "$show" | grep -q "aircraft lists: 2026-10-20 to 2026-10-20" && echo "$show" | grep -q "posting history: readable" && echo "$show" | grep -q "graphs1090: 1 databases, last point 2025-10-2" && echo "$show" | grep -q "Everything in it reads back"'
mkdir -p "$t/bad/zb" && tar -C "$t/bad" -xzf "$t/full.tar.gz" && echo garbage > "$t/bad/zb/graphs-xml.tar.gz" && echo "{" > "$t/bad/zb/social/state.json" && tar -C "$t/bad" -czf "$t/bad.tar.gz" zb
check "check: a damaged part is named, rc 1"         'o=$(backup_show "$t/bad.tar.gz"); [ $? = 1 ] && echo "$o" | grep -q "NOT COMPLETE: posting-history graphs1090"'
mkdir -p "$t/home"
for d in 202610190900 202610200900 202610210900 202610211200; do f="$t/home/zenithboard-backup-rp3-${d:0:8}-${d:8:4}.tar.gz"; cp "$t/full.tar.gz" "$f"; touch -t "$d" "$f"; done
l=$(backup_list "$t/home")
check "list: newest first"                           '[ "$(echo "$l" | grep -o "rp3-[0-9-]*" | tr "\n" " ")" = "rp3-20261021-1200 rp3-20261021-0900 rp3-20261020-0900 rp3-20261019-0900 " ]'
check "clean: anything but delete deletes nothing"   'echo no | backup_clean --keep 2 "$t/home" >/dev/null 2>&1; [ "$(ls "$t/home" | wc -l)" = 4 ]'
echo delete | backup_clean --keep 2 "$t/home" >/dev/null
check "clean: the two newest kept"                   '[ "$(ls "$t/home" | tr "\n" " ")" = "zenithboard-backup-rp3-20261021-0900.tar.gz zenithboard-backup-rp3-20261021-1200.tar.gz " ]'
check "clean: --keep must be a number"               '! backup_clean --keep x "$t/home" >/dev/null 2>&1 && ! backup_clean --keep 0 "$t/home" >/dev/null 2>&1'
backup_delete_console >/dev/null
check "delete: the console's copy only"              '[ ! -e "$t/console/out/backup.tar.gz" ] && [ "$(ls "$t/home" | wc -l)" = 2 ]'
check "console: its delete is listed, asks first"    'python3 -c "
import sys; sys.path.insert(0, \"flightinfo\"); import console_actions as a
assert a.build(\"backup-delete\", {}) == [\"backup\", \"delete\", \"--console\"] and \"ask\" in a.flags(\"backup-delete\")"'
check "console: the download says host and date"     'grep -q "zenithboard-backup-%s-%s-console.tar.gz" flightinfo/console.py'

[ "$fail" = 0 ] && echo "ALL OK"
exit "$fail"
