#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_gain.sh   Dongle gain: reading, rounding to real steps, editing the decoder options, the verdict from stats.json.
# shellcheck disable=SC2034  # variables are used inside the eval-ed check strings
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC" "$t/default" "$t/run/readsb" "$t/run/dump1090-fa"; touch "$ZENITHBOARD_ETC/config.env"
export ZB_SKIP_SERVICES=1 ZB_DEFAULT_DIR="$t/default" ZB_STATS_DIR="$t/run"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/gain.sh
. lib/gain.sh
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
r="$t/default/readsb"; dd="$t/default/dump1090-fa"

# ---- real steps
check "30 -> 29.7"                '[ "$(gain_nearest 30)" = 29.7 ]'
check "max -> 49.6"               '[ "$(gain_nearest max)" = 49.6 ]'
check "100 -> 49.6"               '[ "$(gain_nearest 100)" = 49.6 ]'
check "0 -> 0.0"                  '[ "$(gain_nearest 0)" = 0.0 ]'
check "letters refused"           '! gain_nearest abc >/dev/null'
check "negative refused"          '! gain_nearest -10 >/dev/null'
check "one step down from 49.6"   '[ "$(gain_step_move 49.6 down)" = 48.0 ]'
check "one step up from 40.2"     '[ "$(gain_step_move 40.2 up)" = 42.1 ]'
check "up from the maximum stays" '[ "$(gain_step_move 49.6 up)" = 49.6 ]'
check "down from 0 stays"         '[ "$(gain_step_move 0.0 down)" = 0.0 ]'
check "down from automatic = from the max" '[ "$(gain_step_move auto down)" = 48.0 ]'

# ---- reading the current gain
printf 'ENABLED=yes\nRECEIVER_OPTIONS="--device 0 --device-type rtlsdr --gain 40.2 --ppm 0"\nDECODER_OPTIONS="--lat 1 --lon 2"\n' > "$r"
check "reads 40.2"                '[ "$(gain_current readsb)" = 40.2 ]'
printf 'RECEIVER_OPTIONS="--device-index 0 --gain -10"\n' > "$dd"
check "-10 is the dongle AGC, not the maximum" '[ "$(gain_current dump1090-fa)" = agc ]'
printf 'RECEIVER_OPTIONS="--gain=auto-verbose --device 0"\n' > "$r"
check "readsb auto recognised"    '[ "$(gain_current readsb)" = auto ]'
printf 'RECEIVER_OPTIONS="--device 0"\n' > "$r"
check "no gain = default"         '[ "$(gain_current readsb)" = default ]'
check "missing file = default"    '[ "$(gain_current nothing)" = default ]'

# ---- writing
printf 'ENABLED=yes\nRECEIVER_OPTIONS="--device serial00000978 --device-type rtlsdr --gain=auto,0,25"\nDECODER_OPTIONS="--lat 1 --lon 2 --gain 7"\nJSON_DIR=/run/readsb\n' > "$r"
cp "$r" "$t/before"
gain_set 49.6 >/dev/null 2>&1 || true
export ZB_X=1; cfg_set DECODER readsb
gain_set 49.6 > "$t/out" 2>&1
check "49.6 in RECEIVER_OPTIONS"  'grep -q "^RECEIVER_OPTIONS=\"--gain 49.6 --device serial00000978 --device-type rtlsdr\"" "$r"'
check "old --gain=auto,... removed" '[ "$(grep -o -e "--gain" "$r" | wc -l)" = 1 ] || grep -c -e "--gain" "$r" | grep -q "^2$"'
check "serial and other lines kept" 'grep -q "serial00000978" "$r" && grep -q "^JSON_DIR=/run/readsb" "$r" && grep -q "^ENABLED=yes" "$r"'
check "no trailing space before the quote" '! grep -q " \"$" "$r"'
gain_set 30 >/dev/null 2>&1
check "30 became 29.7 and replaced the old one" 'grep -q -e "--gain 29.7 --device" "$r" && ! grep -q -e "--gain 49.6" "$r"'
check "explains the rounding"     'gain_set 30 2>&1 | grep -q "became 29.7"'
gain_set default >/dev/null 2>&1
check "default removes the gain from RECEIVER_OPTIONS" '! grep -q "^RECEIVER_OPTIONS=.*--gain" "$r" && grep -q "serial00000978" "$r"'
check "bad value refused, file unchanged" 'cp "$r" "$t/x"; ! gain_set loud >/dev/null 2>&1; cmp -s "$r" "$t/x"'
printf 'ENABLED=yes\n' > "$r"
gain_set 40.2 >/dev/null 2>&1
check "line added when the file has none" 'grep -qx "RECEIVER_OPTIONS=\"--gain 40.2\"" "$r"'
cfg_set DECODER dump1090-fa
printf 'RECEIVER_OPTIONS="--device-index 0 --gain -10 --ppm 0"\nDECODER_OPTIONS="--lat 1 --lon 2"\n' > "$dd"
gain_set max >/dev/null 2>&1
check "dump1090-fa: -10 replaced by 49.6, rest kept" 'grep -qx "RECEIVER_OPTIONS=\"--gain 49.6 --device-index 0 --ppm 0\"" "$dd" && grep -q "^DECODER_OPTIONS=\"--lat 1 --lon 2\"" "$dd"'

# ---- the verdict
stats() {  # stats DECODER ACCEPTED STRONG MAXDIST_M
  printf '{"now":1,"last15min":{"local":{"accepted":[%s,0],"strong_signals":%s,"signal":-20.1,"peak_signal":-3.2},"max_distance":%s}}\n' "$2" "$3" "$4" > "$t/run/$1/stats.json"
}
cfg_set DECODER readsb; printf 'RECEIVER_OPTIONS="--gain 40.2"\n' > "$r"
stats readsb 10000 800 250000
out=$(gain_check 2>&1)
check "8% strong -> too high, says the step"  'echo "$out" | grep -q "TOO HIGH" && echo "$out" | grep -q "38.6 dB"'
check "shows messages, range"                 'echo "$out" | grep -q "10000 messages" && echo "$out" | grep -q "250 km"'
stats readsb 10000 30 250000
check "0.3% strong, not at max -> judge at a busy hour, then one step up" 'gain_check 2>&1 | grep -q "LOW SHARE.*BUSY hour.*42.1 dB"'
stats readsb 10000 300 250000
check "3% -> good, leave it"                  'gain_check 2>&1 | grep -q "^GOOD"'
printf 'RECEIVER_OPTIONS="--gain 49.6"\n' > "$r"; stats readsb 10000 30 250000
check "under 1% at the maximum -> nothing to do" 'gain_check 2>&1 | grep -q "already at its maximum"'
stats readsb 100 5 1000
check "few messages -> no verdict"            'gain_check 2>&1 | grep -q "Not enough messages"'
rm "$t/run/readsb/stats.json"
check "no stats file -> says so"              'gain_check 2>&1 | grep -q "No statistics yet"'
printf '{"last15min":{"local":{"accepted":[9000,1000],"strong_signals":300}}}\n' > "$t/run/readsb/stats.json"
check "accepted list is summed (10000)"       'gain_check 2>&1 | grep -q "10000 messages"'
printf 'RECEIVER_OPTIONS="--gain=auto"\n' > "$r"; stats readsb 10000 300 1000
check "automatic gain: tells nothing to lower by hand" 'gain_check 2>&1 | grep -q "automatic, so there is nothing"'

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
