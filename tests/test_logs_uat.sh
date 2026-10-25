#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_logs_uat.sh   Log limit file, 978 MHz dongle configuration and region logic, on throw-away files.
# shellcheck disable=SC2034  # variables are used inside the eval-ed check strings
set -u
cd "$(dirname "$0")/.." || exit 1
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/adsb.sh
. lib/adsb.sh
# shellcheck source=lib/logs.sh
. lib/logs.sh
# shellcheck source=lib/uat.sh
. lib/uat.sh
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZB_SKIP_SERVICES=1 ZB_SYSTEMD_DIR="$t/units"     # 0.54.13: never the real units, even run as root
mkdir -p "$t/units"

# ---- logs: limit file
JOURNALD_DIR="$t/journald.conf.d"; JOURNALD_CONF="$JOURNALD_DIR/zenithboard.conf"
check "no limit at first"                  '[ -z "$(logs_limit_mb)" ]'
logs_set_limit 50 >/dev/null
check "limit 50 MB is written"             '[ "$(logs_limit_mb)" = 50 ] && grep -qx "RuntimeMaxUse=50M" "$JOURNALD_CONF" && grep -qx "\[Journal\]" "$JOURNALD_CONF"'
logs_set_limit 80 >/dev/null
check "a new limit replaces the old one"   '[ "$(logs_limit_mb)" = 80 ] && [ "$(grep -c SystemMaxUse "$JOURNALD_CONF")" = 1 ]'
for bad_v in 5 99999 abc "" 12.5 -3; do
  logs_set_limit "$bad_v" >/dev/null 2>&1; rc=$?
  check "limit '$bad_v' is refused and nothing changes" '[ "$rc" -ne 0 ] && [ "$(logs_limit_mb)" = 80 ]'
done
logs_set_limit default >/dev/null
check "default removes the file"           '[ ! -e "$JOURNALD_CONF" ]'
logs_clean abc >/dev/null 2>&1; rc=$?
check "clean refuses nonsense"             '[ "$rc" -ne 0 ]'

logs_clean 7 >/dev/null 2>&1; rc=$?
check "clean no longer takes a number of days" '[ "$rc" -ne 0 ]'
# ---- logs: automatic cleaning (opt-in, daily, keeps 7 days)
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC"; touch "$ZENITHBOARD_ETC/config.env"; ZB_CONFIG="$ZENITHBOARD_ETC/config.env"; ZB_ETC="$ZENITHBOARD_ETC"
mkdir -p "$t/bin" "$t/home/systemd"; printf '#!/bin/bash\necho "$*" >> %s/sc.log\n' "$t" > "$t/bin/systemctl"; chmod +x "$t/bin/systemctl"
printf '#!/bin/bash\necho "$*" >> %s/jc.log\n' "$t" > "$t/bin/journalctl"; chmod +x "$t/bin/journalctl"
PATH="$t/bin:$PATH"
check "auto cleaning is off by default"    '[ "$(logs_auto_state)" = OFF ]'
ZB_HOME="$t/home"; : > "$ZB_HOME/systemd/zenithboard-logs-clean.service"; : > "$ZB_HOME/systemd/zenithboard-logs-clean.timer"
check "unit files are shipped"             '[ -f systemd/zenithboard-logs-clean.service ] && [ -f systemd/zenithboard-logs-clean.timer ] && grep -q "OnCalendar=daily" systemd/zenithboard-logs-clean.timer && grep -q "auto-run" systemd/zenithboard-logs-clean.service'
logs_auto_on 2>/dev/null
check "auto on is remembered"              '[ "$(cfg_get LOG_AUTOCLEAN)" = 1 ] && logs_auto_state | grep -q "^ON"'
check "auto on enables the timer"          'grep -q "enable --now zenithboard-logs-clean.timer" "$t/sc.log"'
logs_auto_run
check "the run keeps 7 days"               'grep -qx -- "--vacuum-time=7d" "$t/jc.log"'
logs_auto_off 2>/dev/null
check "auto off is remembered"             '[ "$(cfg_get LOG_AUTOCLEAN)" = 0 ] && [ "$(logs_auto_state)" = OFF ]'
check "auto off disables the timer"        'grep -q "disable --now zenithboard-logs-clean.timer" "$t/sc.log"'

# ---- 978 MHz: dongle option in /etc/default/dump978-fa
f="$t/dump978-fa"
printf 'ENABLED=yes\nRECEIVER_OPTIONS="--sdr driver=rtlsdr --sdr-gain 48"\nDECODER_OPTIONS="--raw-port 30978"\n' > "$f"
uat978_set_sdr 00000978 "$f"
check "serial put in RECEIVER_OPTIONS, other options kept" 'grep -qx "RECEIVER_OPTIONS=\"--sdr driver=rtlsdr,serial=00000978  *--sdr-gain 48\"" "$f" || grep -q "serial=00000978" "$f"'
check "exactly one --sdr option"           '[ "$(grep -o -e "--sdr " "$f" | wc -l)" = 1 ]'
check "...and --sdr-gain survived"         'grep -q -e "--sdr-gain 48" "$f"'
uat978_set_sdr 00000979 "$f"
check "changing the serial replaces it"    'grep -q "serial=00000979" "$f" && ! grep -q "serial=00000978" "$f" && [ "$(grep -o -e "--sdr " "$f" | wc -l)" = 1 ]'
check "DECODER_OPTIONS untouched"          'grep -qx "DECODER_OPTIONS=\"--raw-port 30978\"" "$f"'
printf 'ENABLED=yes\n' > "$f"
uat978_set_sdr 00000978 "$f"
check "a file without RECEIVER_OPTIONS gets one" 'grep -qx "RECEIVER_OPTIONS=\"--sdr driver=rtlsdr,serial=00000978\"" "$f"'
uat978_set_sdr 123 "$t/missing" >/dev/null 2>&1; rc=$?
check "missing file: warning, non-zero, nothing created" '[ "$rc" -ne 0 ] && [ ! -e "$t/missing" ]'

# ---- region
ZB_CONFIG="$t/config.env"; : > "$ZB_CONFIG"
check "default region is world: no UAT offered" '! is_region_us'
cfg_set REGION us
check "region us offers UAT"               'is_region_us'
cfg_set REGION world
check "back to world"                      '! is_region_us'
check "defaults carry REGION and UAT978"   'cfg_defaults; [ "$(cfg_get REGION)" = world ] && [ "$(cfg_get UAT978)" = 0 ]'
check "cfg_defaults does not overwrite the region" 'cfg_set REGION us; cfg_defaults; [ "$(cfg_get REGION)" = us ]'

# ---- readsb cannot be uninstalled: say it, do not pretend
is_readsb()   { return 0; }     # pretend readsb is installed
is_dump1090() { return 1; }
out=$(remove_decoder 2>&1)
check "removing readsb warns instead of failing silently" 'grep -qi "NOT removed" <<<"$out"'
check "it says why"                                       'grep -qi "no uninstaller" <<<"$out"'
check "it prints the commands to do it by hand"           'grep -q "systemctl disable --now readsb" <<<"$out" && grep -q "deluser --system readsb" <<<"$out"'
check "it points at the tar1090 uninstaller"              'grep -q "tar1090" <<<"$out"'
check "it never downloads a page that does not exist"     '! grep -qi "readsb-uninstall" <<<"$out"'
unset -f is_readsb is_dump1090

# ---- 0.54.6: a failing feeder had no log to read; one that is not installed says so, not journalctl's bare "-- No entries --"
mkdir -p "$t/lb" "$t/letc"; touch "$t/letc/config.env"
printf '#!/bin/bash\nif [ "$1" = list-unit-files ]; then [ "$2" = fr24feed.service ] && echo "fr24feed.service enabled"; exit 0; fi\nexit 0\n' > "$t/lb/systemctl"
printf '#!/bin/bash\necho "journalctl $*"\n' > "$t/lb/journalctl"; chmod +x "$t/lb/systemctl" "$t/lb/journalctl"
out=$(ZENITHBOARD_ETC="$t/letc" PATH="$t/lb:$PATH" bash bin/zenithboard logs piaware 2>&1)
check "logs piaware: not installed, said so" 'grep -q "piaware is not installed on this Pi" <<<"$out" && ! grep -q "journalctl" <<<"$out"'
out=$(ZENITHBOARD_ETC="$t/letc" PATH="$t/lb:$PATH" bash bin/zenithboard logs fr24 2>&1)
check "logs fr24: installed, its service's journal" 'grep -q "journalctl -u fr24feed" <<<"$out"'
out=$(ZENITHBOARD_ETC="$t/letc" PATH="$t/lb:$PATH" bash bin/zenithboard logs adsbexchange 2>&1)
check "logs adsbexchange: the unit the status screen names" 'grep -q "adsbexchange-feed is not installed" <<<"$out"'
# 0.54.16: 978 MHz UAT and the Bluesky service too
out=$(ZENITHBOARD_ETC="$t/letc" PATH="$t/lb:$PATH" bash bin/zenithboard logs uat 2>&1)
check "logs uat: not installed, said so"   'grep -q "978 MHz UAT (dump978-fa) is not installed on this Pi" <<<"$out" && ! grep -q journalctl <<<"$out"'
out=$(ZENITHBOARD_ETC="$t/letc" PATH="$t/lb:$PATH" bash bin/zenithboard logs social 2>&1)
check "logs social: not installed, said so" 'grep -q "Bluesky posting (zenithboard-social) is not installed" <<<"$out"'

# ---- the position, written into the decoder's and the feeders' own files (0.54.13: never run by a test before)
mkdir -p "$t/etc" "$t/default"; ZB_ETC="$t/etc"; ZB_CONFIG="$t/etc/config.env"; touch "$ZB_CONFIG"
printf 'ENABLED=yes\nDECODER_OPTIONS="--lat 1.0 --lon 2.0 --max-range 360"\n' > "$t/default/dump1090-fa"
printf 'LATITUDE=1\nLONGITUDE=2\nALTITUDE=10m\nUSER=x\n' > "$t/default/adsbexchange"
printf '{"latitude": 1.0, "longitude": 2.0, "sharecode": "abc"}\n' > "$t/pf.json"
(
  is_readsb() { return 1; }; is_dump1090() { return 0; }; is_adsbx() { return 0; }; is_piaware() { return 1; }
  is_fr24() { return 1; }; is_planefinder() { return 0; }; systemctl() { :; }; restart_flightinfo() { :; }
  ZB_DEFAULT_DIR="$t/default" ZB_PF_CONFIG="$t/pf.json" zb_apply_location 49.25 6.2 180 > "$t/loc.out" 2>&1
)
check "position: dump1090-fa's options get the new one, once, the rest kept" 'grep -qx "DECODER_OPTIONS=\"--lat 49.25 --lon 6.2 --max-range 360\"" "$t/default/dump1090-fa"'
check "position: ADSB Exchange's file, altitude with its unit glued" 'grep -qx "LATITUDE=\"49.25\"" "$t/default/adsbexchange" && grep -qx "LONGITUDE=\"6.2\"" "$t/default/adsbexchange" && grep -qx "ALTITUDE=\"180m\"" "$t/default/adsbexchange" && grep -qx "USER=x" "$t/default/adsbexchange"'
check "position: Plane Finder's JSON, its other keys kept" 'python3 -c "import json,sys; d=json.load(open(sys.argv[1])); assert d[\"latitude\"]==49.25 and d[\"longitude\"]==6.2 and d[\"sharecode\"]==\"abc\"" "$t/pf.json"'
check "position: kept in config.env too" '[ "$(cfg_get LAT)" = 49.25 ] && [ "$(cfg_get ALT_M)" = 180 ]'

# ---- the ADS-B step itself (0.54.14, the audit of 22-23 October 2026: its plan, REMOVE, the US-only UAT line and the
# MLAT guard had no test). The screens answer from a script; installing and removing only say what they would do.
adsb_run() {   # adsb_run REGION FEEDERS-TICKED YES|NO -> what was shown and done, in $t/adsb.log
  : > "$t/adsb.log"
  (
    cfg_set REGION "$1"
    installed_decoder() { echo readsb; }; is_readsb() { return 0; }; is_dump1090() { return 1; }; is_adsbx() { return 0; }
    is_piaware() { return 0; }; is_fr24() { return 1; }; is_planefinder() { return 1; }; is_adsbx_stats() { return 1; }
    is_uat978() { return 1; }; is_low_mem() { return 1; }; AXS_STATE="$t/none"
    wt_radio() { echo readsb; }; wt_input() { echo ""; }
    answer=$3; wt_yesno() { printf 'PLAN %s\n' "$1" >> "$t/adsb.log"; [ "$answer" = YES ]; }
    for f in install_piaware remove_piaware install_fr24 remove_fr24 install_planefinder remove_planefinder install_adsbx \
             install_decoder remove_decoder install_uat978 remove_uat978 zb_mlat_guard; do eval "$f() { echo \"DID $f\" >> \"$t/adsb.log\"; }"; done
    wt_check() { printf 'CHECKLIST %s\n' "$*" >> "$t/adsb.log"; echo "$ADSB_TICK"; }
    ADSB_TICK="$2" adsb_menu < /dev/null > /dev/null 2>&1
    echo "CANCELLED=${ADSB_CANCELLED:-}" >> "$t/adsb.log"
  )
}
adsb_run world '"ADSBX" "FR24"' YES
check "adsb: the plan says what goes and what comes"  'grep -q "PLAN.*REMOVE FLIGHTAWARE" "$t/adsb.log" && grep -q "PLAN.*Install FR24" "$t/adsb.log"'
check "adsb: and does it, then guards MLAT"           'grep -q "DID remove_piaware" "$t/adsb.log" && grep -q "DID install_fr24" "$t/adsb.log" && grep -q "DID zb_mlat_guard" "$t/adsb.log" && ! grep -q "DID install_planefinder" "$t/adsb.log"'
check "adsb: no 978 MHz line outside the United States" '! grep -q "CHECKLIST.*UAT978" "$t/adsb.log"'
adsb_run us '"ADSBX" "FLIGHTAWARE"' YES
check "adsb: the United States are offered 978 MHz UAT" 'grep -q "CHECKLIST.*UAT978" "$t/adsb.log"'
adsb_run world '"ADSBX"' NO
check "adsb: No at the plan does nothing, and says it was left" '! grep -q "^DID" "$t/adsb.log" && grep -q "CANCELLED=1" "$t/adsb.log"'

exit "$fail"
