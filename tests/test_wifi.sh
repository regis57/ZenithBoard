#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_wifi.sh   Wi-Fi: scan parsing, validation, profile files, country and persistence, on throw-away files.
# shellcheck disable=SC2034  # variables are used inside the eval-ed check strings
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC"; touch "$ZENITHBOARD_ETC/config.env"
export ZB_SKIP_SERVICES=1 ZB_NM_DIR="$t/nm" ZB_MODPROBE_DIR="$t/modprobe"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/wifi.sh
. lib/wifi.sh
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

# ---- scan parsing (nmcli -t escapes ':' and '\' with a backslash); strongest first, one line per name, hidden skipped
out=$(printf '%s\n' 'Livebox-1A2B:62:WPA2' 'Livebox-1A2B:81:WPA2' 'Caf\:e\\Net:40:WPA1 WPA2' ':55:WPA2' 'GuestOpen:30:' 'Home5G:90:WPA3' | wifi_parse_scan)
check "scan: strongest first"                '[ "$(printf "%s\n" "$out" | head -1 | cut -f1)" = Home5G ]'
check "scan: duplicate names keep the best signal" '[ "$(printf "%s\n" "$out" | grep -c "^Livebox-1A2B")" = 1 ] && printf "%s\n" "$out" | grep -q "^Livebox-1A2B	81	WPA2$"'
check "scan: escaped colon and backslash decoded" 'printf "%s\n" "$out" | cut -f1 | grep -qxF "Caf:e\\Net"'
check "scan: hidden (empty) names skipped"    '[ "$(printf "%s\n" "$out" | wc -l)" = 4 ]'
check "scan: open network shown as --"        'printf "%s\n" "$out" | grep -q "^GuestOpen	30	--$"'

# ---- signal bars and key management
check "bars strong"  '[ "$(wifi_bars 90)" = "[####]" ]'
check "bars medium"  '[ "$(wifi_bars 55)" = "[### ]" ]'
check "bars weak"    '[ "$(wifi_bars 10)" = "[#   ]" ]'
check "WPA3 only -> sae"        '[ "$(wifi_keymgmt WPA3)" = sae ]'
check "WPA2+WPA3 -> wpa-psk"    '[ "$(wifi_keymgmt "WPA2 WPA3")" = wpa-psk ]'
check "WPA2 -> wpa-psk"         '[ "$(wifi_keymgmt WPA2)" = wpa-psk ]'

# ---- validation
check "country FR ok"            'valid_country FR'
for b in fr FRA F 1A "" "F R"; do check "country '$b' refused" '! valid_country "$b"'; done
check "psk 8 chars ok"           'valid_wifi_psk 12345678'
check "psk 63 chars ok"          'valid_wifi_psk "$(printf "a%.0s" $(seq 63))"'
check "psk 64 hex ok"            'valid_wifi_psk "$(printf "ab%.0s" $(seq 32))"'
check "psk 7 chars refused"      '! valid_wifi_psk 1234567'
check "psk 64 non-hex refused"   '! valid_wifi_psk "$(printf "g%.0s" $(seq 64))"'
check "psk 65 chars refused"     '! valid_wifi_psk "$(printf "a%.0s" $(seq 65))"'
check "ssid 32 ok / 33 refused"  'valid_ssid "$(printf "s%.0s" $(seq 32))" && ! valid_ssid "$(printf "s%.0s" $(seq 33))"'
check "empty ssid refused"       '! valid_ssid ""'

# ---- profile file: private, complete, wired stays preferred (Wi-Fi metric 600)
id=$(wifi_write_profile 'My "Home" Wi-Fi' 'pa$$w\ord;#1' 0 wpa-psk)
f="$WIFI_NM_DIR/$id.nmconnection"
check "profile file exists, named zenithboard-wifi-*" '[ -f "$f" ] && case "$id" in zenithboard-wifi-*) true ;; *) false ;; esac'
check "profile file is private (600)"       '[ "$(stat -c %a "$f")" = 600 ]'
check "profile: autoconnect on (survives reboot)" 'grep -qx "autoconnect=true" "$f"'
check "profile: ssid and psk written, backslash escaped" 'grep -qxF "ssid=My \"Home\" Wi-Fi" "$f" && grep -qxF "psk=pa\$\$w\\\\ord;#1" "$f"'
check "profile: Wi-Fi metric 600 (Ethernet stays preferred)" '[ "$(grep -c "^route-metric=600$" "$f")" = 2 ]'
check "profile: key-mgmt wpa-psk"           'grep -qx "key-mgmt=wpa-psk" "$f"'
check "profile: not hidden by default"      '! grep -q "^hidden=" "$f"'
u1=$(sed -n 's/^uuid=//p' "$f")
id2=$(wifi_write_profile 'My "Home" Wi-Fi' 'newpassword9' 1 sae)
check "same network again updates the same file, same uuid" '[ "$id" = "$id2" ] && [ "$(ls "$WIFI_NM_DIR" | wc -l)" = 1 ] && [ "$(sed -n "s/^uuid=//p" "$f")" = "$u1" ]'
check "update: new password, hidden, sae"   'grep -qx "psk=newpassword9" "$f" && grep -qx "hidden=true" "$f" && grep -qx "key-mgmt=sae" "$f"'
id3=$(wifi_write_profile 'Open Cafe' '' 0)
check "open network has no security section" '! grep -q "wifi-security" "$WIFI_NM_DIR/$id3.nmconnection"'
a=$(wifi_profile_id "a b"); b=$(wifi_profile_id "a_b")
check "SSIDs that look alike get different profile names" '[ "$a" != "$b" ]'
wifi_write_profile 'x' 'short' >/dev/null 2>&1; rc=$?
check "bad password refused, no file written" '[ "$rc" -ne 0 ] && [ "$(ls "$WIFI_NM_DIR" | wc -l)" = 2 ]'
check "no temporary file left behind"       '! ls -A "$WIFI_NM_DIR" | grep -q "^\.zb-wifi"'

# ---- country: persistent in the config and in modprobe.d
wifi_set_country FR
check "country saved in config.env"         '[ "$(cfg_get WIFI_COUNTRY)" = FR ]'
check "country kept across reboots (modprobe.d)" 'grep -qx "options cfg80211 ieee80211_regdom=FR" "$WIFI_MODPROBE"'
wifi_set_country be >/dev/null 2>&1; rc=$?
check "lowercase / bad country refused and unchanged" '[ "$rc" -ne 0 ] && [ "$(cfg_get WIFI_COUNTRY)" = FR ]'
wifi_set_country BE
check "a new country replaces the old"      '[ "$(grep -c regdom "$WIFI_MODPROBE")" = 1 ] && grep -q "regdom=BE" "$WIFI_MODPROBE" && [ "$(cfg_get WIFI_COUNTRY)" = BE ]'
check "country_now reads the config"        '[ "$(wifi_country_now)" = BE ]'

# ---- on/off choice is stored for the boot-time re-apply
wifi_set_radio off; check "off stored" '[ "$(cfg_get WIFI)" = 0 ]'
wifi_set_radio on;  check "on stored"  '[ "$(cfg_get WIFI)" = 1 ]'
wifi_set_radio maybe 2>/dev/null; rc=$?
check "bad on/off value refused"            '[ "$rc" -ne 0 ] && [ "$(cfg_get WIFI)" = 1 ]'
check "untouched Pi: WIFI empty by default" 'cfg_defaults; : > "$ZB_CONFIG"; cfg_defaults; [ -z "$(cfg_get WIFI)" ] && [ -z "$(cfg_get WIFI_COUNTRY)" ]'

# ---- the boot unit exists and calls the CLI
check "systemd unit present"                'grep -q "wifi apply" systemd/zenithboard-wifi.service && grep -q "After=NetworkManager.service" systemd/zenithboard-wifi.service'

[ "$fail" = 0 ] && echo "wifi tests OK" || { echo "wifi tests FAILED"; exit 1; }
