#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_stats.sh   The statistics collector, against a fake decoder: what one sample writes, how
# the day's aircraft are counted, what pruning keeps, what the terminal shows, and that off leaves the files.
# shellcheck disable=SC2034
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/run/readsb" "$t/sysd"; touch "$ZENITHBOARD_ETC/config.env"
export ZB_SKIP_SERVICES=1 ZB_STATS_OUT_DIR="$t/stats" ZB_STATS_DIR="$t/run" ZB_SYSTEMD_DIR="$t/sysd" ZB_HOME="$PWD"
printf '#!/bin/bash\necho "systemctl $*" >> "%s/systemctl.log"\n' "$t" > "$t/bin/systemctl"
printf '#!/bin/bash\necho 192.168.1.50\n' > "$t/bin/hostname"
chmod +x "$t"/bin/*; export PATH="$t/bin:$PATH"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/stats.sh
. lib/stats.sh
ZB_HOME="$PWD"          # common.sh points it at /opt; the units are read from the checkout here
cfg_set DECODER readsb
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

# ---- the decoder's two files, as readsb writes them
cat > "$t/run/readsb/stats.json" <<'J'
{"last15min":{"messages":2412,"max_distance":311900,"local":{"accepted":[2400,12],"strong_signals":60}},"total":{"messages":99}}
J
cat > "$t/run/readsb/aircraft.json" <<'J'
{"now":1,"aircraft":[{"hex":"3c6444","lat":49.1,"lon":6.2},{"hex":"4ca123","lat":49.3,"lon":6.0},{"hex":"a1b2c3"},{"hex":"~2a0001","lat":48.9,"lon":6.1}]}
J

check "off at first"                              '[ "$(stats_state)" = off ]'
out=$(stats_on)
check "on: setting, timer enabled, says where"    '[ "$(cfg_get STATS)" = 1 ] && grep -q "enable --now zenithboard-stats.timer" "$t/systemctl.log" && printf "%s" "$out" | grep -q "/stats"'
check "on: units installed"                       '[ -f "$t/sysd/zenithboard-stats.service" ] && [ -f "$t/sysd/zenithboard-stats.timer" ]'
check "on: the CSV exists with its header"        '[ "$(head -1 "$STATS_FILE")" = "$STATS_HEADER" ]'

stats_run
today=$(date '+%Y-%m-%d')
row=$(tail -1 "$STATS_FILE")
check "one sample: one line"                      '[ "$(grep -c . "$STATS_FILE")" = 2 ]'
check "sample: 2412 messages"                     '[ "$(cut -d, -f2 <<<"$row")" = 2412 ]'
check "sample: farthest 312 km (rounded from m)"  '[ "$(cut -d, -f3 <<<"$row")" = 312 ]'
check "sample: 2 aircraft with a position (the ~ one is not real)" '[ "$(cut -d, -f4 <<<"$row")" = 2 ]'
check "sample: 3 aircraft seen today"             '[ "$(cut -d, -f5 <<<"$row")" = 3 ]'
check "day file: three real hex codes, sorted"    '[ "$(tr "\n" " " < "$(stats_day_file "$today")")" = "3c6444 4ca123 a1b2c3 " ]'

# a second sample with one new aircraft and one gone: the day's count only grows
cat > "$t/run/readsb/aircraft.json" <<'J'
{"aircraft":[{"hex":"3c6444","lat":49.1,"lon":6.2},{"hex":"ff0001","lat":49.5,"lon":6.5}]}
J
stats_run
check "second sample: 4 distinct aircraft today"  '[ "$(tail -1 "$STATS_FILE" | cut -d, -f5)" = 4 ]'
check "second sample: 2 with a position now"      '[ "$(tail -1 "$STATS_FILE" | cut -d, -f4)" = 2 ]'

# dump1090-fa: no top-level messages count, accepted is a list
cat > "$t/run/readsb/stats.json" <<'J'
{"last15min":{"local":{"accepted":[1500,20]},"max_distance":0}}
J
stats_run
check "dump1090-style: messages from accepted, farthest 0" '[ "$(tail -1 "$STATS_FILE" | cut -d, -f2,3)" = "1520,0" ]'

# nothing to read: nothing written, no error
rm "$t/run/readsb/stats.json"; n=$(grep -c . "$STATS_FILE")
stats_run; r=$?
check "decoder down: silent, nothing added"       '[ $r -eq 0 ] && [ "$(grep -c . "$STATS_FILE")" = "$n" ]'

# ---- pruning: old lines and old day files go, recent ones stay
old=$(date -d "40 days ago" '+%Y-%m-%d'); recent=$(date -d "3 days ago" '+%Y-%m-%d')
printf '%s 10:00,5,100,1,1\n%s 10:00,6,110,1,1\n' "$old" "$recent" >> "$STATS_FILE"
touch "$(stats_day_file "$old")" "$(stats_day_file "$recent")"
stats_prune
check "prune: the 40-day-old line is gone, the 3-day-old stays" '! grep -q "^$old" "$STATS_FILE" && grep -q "^$recent" "$STATS_FILE"'
check "prune: the old day file is gone, the recent stays"       '[ ! -e "$(stats_day_file "$old")" ] && [ -e "$(stats_day_file "$recent")" ]'
check "prune: the header is still first"                        '[ "$(head -1 "$STATS_FILE")" = "$STATS_HEADER" ]'

# ---- the terminal view
out=$(stats_show)
check "show: today's aircraft count is the day file"  'printf "%s" "$out" | grep -q "Today  *4 aircraft seen"'
check "show: today's messages are summed"             'printf "%s" "$out" | grep -q "$((2412 + 2412 + 1520)) messages"'
check "show: farthest today"                          'printf "%s" "$out" | grep -q "farthest 312 km"'
check "show: a sparkline of 24 bars"                  '[ "$(printf "%s" "$out" | grep -E "^ [▁-█]+$" | head -1 | sed "s/ //" | wc -m)" -ge 24 ]'
check "show: says the count is a floor"               'printf "%s" "$out" | grep -q "floor"'
check "spark: heights follow the values"              '[ "$(stats_spark 0 4 8)" = "▁▅█" ]'
check "spark: all zero is all low"                    '[ "$(stats_spark 0 0 0)" = "▁▁▁" ]'

# ---- off keeps the files, clear empties them
out=$(stats_off)
check "off: setting, timer disabled, files kept"  '[ "$(cfg_get STATS)" = 0 ] && grep -q "disable --now zenithboard-stats.timer" "$t/systemctl.log" && [ -f "$STATS_FILE" ] && [ ! -e "$t/sysd/zenithboard-stats.timer" ]'
stats_clear >/dev/null
check "clear: header only, no day files"          '[ "$(cat "$STATS_FILE")" = "$STATS_HEADER" ] && [ -z "$(ls "$STATS_DIR"/seen-* 2>/dev/null)" ]'
rm -f "$STATS_FILE"
out=$(stats_show); r=$?
check "show without any file: says how to turn it on" '[ $r -ne 0 ] && printf "%s" "$out" | grep -q "stats on"'

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
