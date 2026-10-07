#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_logs_uat.sh   Log limit file, 978 MHz dongle configuration and region logic, on throw-away files.
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
export ZB_SKIP_SERVICES=1

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
exit "$fail"
