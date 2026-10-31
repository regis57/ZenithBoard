#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_settings.sh   Settings as a file (export never carries a secret, import takes only settings
# and keeps a way back), the per-tablet presets (names, keys, what the wall serves), Wi-Fi hardening (what it sets,
# what "off" puts back), the counters behind "stats gaps", and the typed word before the destructive menu steps.
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC" "$t/bin"; touch "$ZENITHBOARD_ETC/config.env"
export ZB_SKIP_SERVICES=1
printf '#!/bin/bash\necho "nmcli $*" >> %s/nmcli.log\ncase "$*" in\n  *"-g connection.autoconnect-retries"*) echo -1 ;;\n  *"-g 802-11-wireless.powersave"*) echo 0 ;;\n  *"-f UUID,TYPE connection show --active"*) echo "u-wifi-1:802-11-wireless" ;;\nesac\n' "$t" > "$t/bin/nmcli"
printf '#!/bin/bash\necho "systemctl $*" >> "%s/systemctl.log"\n' "$t" > "$t/bin/systemctl"
chmod +x "$t"/bin/*; export PATH="$t/bin:$PATH"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/settings.sh
. lib/settings.sh
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }

# ---- export: config.env without the secrets and the one-off flags
cfg_set UNITS metric; cfg_set RADIUS 10; cfg_set SOCIAL_AREA "near Metz"; cfg_set ADSBX_KEY "secret-key-1"; cfg_set HW_NOTICE_SEEN 1; cfg_set GRAFANA_PASSWORD "pw"
f=$(settings_export "$t/out.env")
check "export: writes the file it names"            '[ "$f" = "$t/out.env" ] && [ -f "$t/out.env" ]'
check "export: settings in, quoted value kept"      'grep -q "^UNITS=metric$" "$t/out.env" && grep -q "^SOCIAL_AREA=\"near Metz\"$" "$t/out.env"'
check "export: no secret, no one-off flag"          '! grep -q "secret-key-1\|GRAFANA_PASSWORD\|HW_NOTICE_SEEN" "$t/out.env"'
check "export: to stdout with -"                    'settings_export - | grep -q "^RADIUS=10$"'

# ---- import: only KEY=VALUE, never a secret, never shell; the file from before kept
cat > "$t/in.env" <<'EOF'
# a settings file
RADIUS=30
THEME=green
ADSBX_KEY=stolen
EVIL=$(touch /tmp/pwned)
rm -rf /
lower=case
EOF
out=$(settings_import "$t/in.env")
check "import: the settings taken"                  '[ "$(cfg_get RADIUS)" = 30 ] && [ "$(cfg_get THEME)" = green ]'
check "import: a secret and shell lines skipped"    '[ "$(cfg_get ADSBX_KEY)" = secret-key-1 ] && [ -z "$(cfg_get EVIL "")" ] && echo "$out" | grep -q "Skipped 4"'
check "import: the file from before is kept"        'ls "$ZENITHBOARD_ETC"/config.env.bak-* >/dev/null 2>&1 && grep -q "^RADIUS=10$" "$ZENITHBOARD_ETC"/config.env.bak-*'
check "import: a file with no setting is refused"   'echo "hello" > "$t/no.env" && ! settings_import "$t/no.env" >/dev/null 2>&1'
check "import: a missing file is refused"           '! settings_import "$t/none.env" >/dev/null 2>&1'

# ---- the review of 0.99.8 (B1): a value is checked by its key; nothing imported or typed reaches a shell or sed
mkdir -p "$t/default"; printf 'LATITUDE=1\nLONGITUDE=2\nALTITUDE=10m\nUSER=x\n' > "$t/default/adsbexchange"
cfg_set LAT 49.1; cfg_set LON 6.1; cfg_set ALT_M 180; cfg_set ADSB_SDR 00001090
printf 'ALT_M=0"; touch %s/X; #|e;#\nADSB_SDR=1"; touch %s/Y; #\nSOCIAL_AREA=a|b\nLAT=91\nRADIUS=10\nUNITS=aviation\n' "$t" "$t" > "$t/evil.env"
out=$(settings_import "$t/evil.env")
apply_here() {   # the position applied as a restore applies it, into the stub ADSB Exchange file
  ( # shellcheck source=lib/adsb.sh
    . lib/adsb.sh
    is_readsb() { return 1; }; is_dump1090() { return 1; }; is_adsbx() { return 0; }; is_piaware() { return 1; }
    is_fr24() { return 1; }; is_radarbox() { return 1; }; is_planefinder() { return 1; }; restart_flightinfo() { :; }
    ZB_DEFAULT_DIR="$t/default" zb_apply_location "$@" ) >/dev/null 2>&1
}
apply_here "$(cfg_get LAT)" "$(cfg_get LON)" "$(cfg_get ALT_M 0)"
check "import (B1): an altitude carrying a command is skipped, nothing runs" '[ ! -e "$t/X" ] && [ "$(cfg_get ALT_M)" = 180 ] && echo "$out" | grep -q "Skipped 4 " && echo "$out" | grep -q "refused.*ALT_M"'
check "import (B1): ADSB Exchange gets the altitude kept, never the payload" 'grep -qx "ALTITUDE=\"180m\"" "$t/default/adsbexchange" && grep -qx "USER=x" "$t/default/adsbexchange"'
check "import (B1): a dongle serial with a quote or ; is refused" '[ "$(cfg_get ADSB_SDR)" = 00001090 ] && echo "$out" | grep -q "refused.*ADSB_SDR" && [ ! -e "$t/Y" ]'
check "import (B1): a | in a free setting, a latitude out of range refused; the good ones taken" '[ "$(cfg_get SOCIAL_AREA)" = "near Metz" ] && [ "$(cfg_get LAT)" = 49.1 ] && [ "$(cfg_get UNITS)" = aviation ] && echo "$out" | grep -q "Imported 2 "'
apply_here 49.1 6.1 '0"; touch '"$t"'/Z; #|e;#'
check "position (B1): an altitude that is not whole metres counts as 0" '[ ! -e "$t/Z" ] && grep -qx "ALTITUDE=\"0m\"" "$t/default/adsbexchange"'
check "position (B1): a position that is not one changes nothing" '! apply_here "1;id" 6 0 && grep -qx "LATITUDE=\"49.1\"" "$t/default/adsbexchange"'
check "values (B1): what each key takes" 'settings_value_ok ALT_M -12 && ! settings_value_ok ALT_M 12345 && ! settings_value_ok CYCLE_SECONDS 2.5 && settings_value_ok STATS 1 && ! settings_value_ok STATS on && settings_value_ok SOCIAL_AREA "L'"'"'Hôpital, Moselle" && ! settings_value_ok SOCIAL_AREA "a\$b" && settings_value_ok UAT_SDR ""'

# ini_set: the value written as it is, whatever it holds
printf 'A="1"\nKEY="old"\nB="2"\n' > "$t/ini"; chmod 640 "$t/ini"
ini_set "$t/ini" KEY 'a/b&c\d"e'"'"'f|g'
check "ini_set (B1): / & \\ and quotes written literally, the rest kept, the mode kept" '[ "$(sed -n 2p "$t/ini")" = "KEY=\"a/b&c\\d\"e'"'"'f|g\"" ] && [ "$(sed -n 1p "$t/ini")" = "A=\"1\"" ] && [ "$(sed -n 3p "$t/ini")" = "B=\"2\"" ] && [ "$(stat -c %a "$t/ini")" = 640 ]'
ini_set "$t/ini" NEW 'x\ny'
check "ini_set (B1): a new key added at the end, its backslash kept" '[ "$(tail -n1 "$t/ini")" = "NEW=\"x\\ny\"" ] && [ "$(wc -l < "$t/ini")" = 4 ]'

# config-set: a key is a name, never a pattern
cp "$ZB_CONFIG" "$t/before.env"
out=$(bash bin/zenithboard config-set '.*' x 2>&1); rc=$?
check "config-set (B1): a key that is not a name refused, config.env unchanged" '[ "$rc" != 0 ] && echo "$out" | grep -q "capital letters" && cmp -s "$ZB_CONFIG" "$t/before.env"'
out=$(bash bin/zenithboard config-set PORT "$(printf '1\nEVIL=1')" 2>&1); rc=$?
check "config-set (B1): a value of two lines refused" '[ "$rc" != 0 ] && echo "$out" | grep -q "one line" && cmp -s "$ZB_CONFIG" "$t/before.env"'
cfg_set '.*' x
check "cfg_set (B1): the key compared as text, the other settings kept" '[ "$(grep -c . "$ZB_CONFIG")" = "$(( $(grep -c . "$t/before.env") + 1 ))" ] && grep -qx ".\*=x" "$ZB_CONFIG"'
cfg_del '.*'
check "cfg_del (B1): only that key gone" 'cmp -s "$ZB_CONFIG" "$t/before.env"'

# ---- presets
check "preset: name rules"                          'preset_valid_name kitchen && preset_valid_name tv2 && ! preset_valid_name Kitchen && ! preset_valid_name 2tv && ! preset_valid_name "a b" && ! preset_valid_name abcdefghijklmnopq'
check "preset: add writes PRESET_NAME"              'preset_add kitchen theme=green mode=flap radius=5 >/dev/null && [ "$(cfg_get PRESET_KITCHEN)" = "theme=green mode=flap radius=5" ]'
check "preset: only the tablet keys, sane values"   '! preset_add tv PORT=1 >/dev/null 2>&1 && ! preset_add tv mode=huge >/dev/null 2>&1 && ! preset_add tv radius=0 >/dev/null 2>&1 && ! preset_add tv cycle=999 >/dev/null 2>&1 && [ -z "$(cfg_get PRESET_TV "")" ]'
check "units (0.55.0): metric, imperial and aviation; the radius in km, mi or NM" 'valid_units aviation && valid_units metric && ! valid_units nautical && preset_valid_pair units=aviation && [ "$(units_distance aviation)" = NM ] && [ "$(units_distance imperial)" = mi ] && [ "$(units_distance metric)" = km ]'
check "preset (B1): seconds per aircraft are whole seconds" '! preset_add tv cycle=2.5 >/dev/null 2>&1 && [ -z "$(cfg_get PRESET_TV "")" ] && preset_add tv cycle=14 >/dev/null && [ "$(cfg_get PRESET_TV)" = cycle=14 ] && preset_del tv >/dev/null'
check "preset: only the wall's colours (blue gone in 0.23.0)" '! preset_add tv theme=blue >/dev/null 2>&1 && ! preset_add tv theme=pink >/dev/null 2>&1 && preset_add tv theme=turquoise >/dev/null && preset_del tv >/dev/null'
check "preset: list and del"                        'preset_list | grep -q "^kitchen .*theme=green" && preset_del kitchen >/dev/null && [ -z "$(cfg_get PRESET_KITCHEN "")" ] && ! preset_del kitchen >/dev/null 2>&1'
check "preset: the wall serves them"                'cfg_set PRESET_TV2 "theme=red cycle=8 PORT=1"; ZENITHBOARD_CONFIG="$ZENITHBOARD_ETC/config.env" python3 -c "
import sys; sys.path.insert(0, \"flightinfo\"); import server
p = server.presets_of(server.load_config()); assert p == {\"tv2\": {\"theme\": \"red\", \"cycle\": \"8\"}}, p"'
check "preset: the page applies ?p= after /api/config" 'grep -q "prefs.preset = String(q.get(\"p\"))" flightinfo/static/app.js && grep -q "applyPreset(); }" flightinfo/static/app.js'

# ---- Wi-Fi hardening: what is set, what off puts back
check "harden: off by default"                      '[ "$(wifi_harden_state)" = off ]'
wifi_harden_on >/dev/null
check "harden: on sets retries 0 and powersave 2"   'grep -q "modify uuid u-wifi-1 connection.autoconnect-retries 0 802-11-wireless.powersave 2" "$t/nmcli.log" && [ "$(wifi_harden_state)" = on ]'
check "harden: the values from before are noted"    '[ "$(cfg_get WIFI_HARDEN_PREV)" = "-1,0,u-wifi-1" ]'
wifi_harden_off >/dev/null
check "harden: off puts them back"                  'grep -q "modify uuid u-wifi-1 connection.autoconnect-retries -1 802-11-wireless.powersave 0" "$t/nmcli.log" && [ "$(wifi_harden_state)" = off ] && [ -z "$(cfg_get WIFI_HARDEN_PREV "")" ]'

# ---- the counters behind "stats gaps": a wall stub on the loopback
# shellcheck source=lib/stats.sh
. lib/stats.sh
STATS_DIR="$t/stats"; STATS_FILE="$STATS_DIR/stats.csv"; mkdir -p "$STATS_DIR"
port=$((20000 + RANDOM % 20000)); cfg_set PORT "$port"
python3 - "$port" "$t/gaps-asked" <<'PY' &
import http.server, json, sys
planes = [{"hex": "aaa001", "flight": "BGA113J", "airline": None, "shape": "wide", "type": "A337"},
          {"hex": "aaa002", "flight": "EZY12", "airline": "easyJet", "shape": "generic", "type": "A21N"},
          {"hex": "aaa003", "flight": "BGA2", "airline": None, "shape": "generic", "type": "A21N"},
          {"hex": "aaa004", "flight": "", "airline": None, "shape": "generic", "type": ""}]
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        open(sys.argv[2], "a").write(self.path + "\n")
        b = json.dumps({"planes": planes}).encode(); self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
PY
srv=$!; for _ in $(seq 50); do (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null && break; sleep 0.1; done   # 0.54.13: until it listens, 5 s at most, not a fixed sleep
# the review of 0.99.8: a fixed date was pruned as older than 30 days from 18 November 2026, failing every CI run
gd=$(date -d "2 days ago" +%F)
cfg_set UNITS imperial; cfg_set RADIUS 10       # 10 miles: sent as radius_km=10 before 0.99.13, 10 km sampled
stats_gaps_sample "$gd"; stats_gaps_sample "$gd"
kill $srv 2>/dev/null
check "gaps: the wall is asked without radius_km, so it applies RADIUS in its own units (0.99.13, review B5)" '[ "$(sort -u "$t/gaps-asked")" = "/api/planes" ]'
check "gaps: each aircraft once, by prefix and by type" '[ "$(sort "$STATS_DIR/gaps-$gd" | tr "\t" " ")" = "$(printf "airline BGA aaa001\nairline BGA aaa003\nshape A21N aaa002\nshape A21N aaa003")" ]'
check "gaps: the report counts aircraft"           'stats_gaps | grep -q "BGA    2 aircraft" && stats_gaps | grep -q "A21N   2 aircraft"'
check "gaps: pruned with the rest"                  'touch "$STATS_DIR/gaps-2020-01-01" "$STATS_DIR/seen-2020-01-01"; echo "$STATS_HEADER" > "$STATS_FILE"; stats_prune >/dev/null 2>&1; [ ! -f "$STATS_DIR/gaps-2020-01-01" ] && [ -f "$STATS_DIR/gaps-$gd" ]'
check "gaps: the stats unit may reach the loopback only" 'grep -q "^RestrictAddressFamilies=AF_UNIX AF_INET$" systemd/zenithboard-stats.service && grep -q "^IPAddressAllow=localhost$" systemd/zenithboard-stats.service && grep -q "^IPAddressDeny=any$" systemd/zenithboard-stats.service'

# ---- the destructive steps ask for a typed word, and the main menu keeps them out of the numbered flow
check "menu: uninstall asks for the word"           'grep -q "\[ \"\$word\" = uninstall \]" install.sh'
check "menu: removing the wall and all logs too"    'grep -q "= remove \]" lib/menus.sh && grep -q "= delete \]" lib/logs.sh'
check "menu: Backup holds the backup, the settings file, uninstall (not last)" 'grep -q "6 \"6  Backup" lib/menus.sh && grep -q "uninstall \"4  Uninstall everything" lib/menus.sh && grep -q "import \"6  Settings only" lib/menus.sh'
# 0.54.10 (the audit of 22-23 October 2026): the menu and the command took 0, -3 and 600 seconds per aircraft
check "cycle: whole seconds, 2 to 60"               'valid_cycle 2 && valid_cycle 14 && valid_cycle 60 && ! valid_cycle 0 && ! valid_cycle -3 && ! valid_cycle 600 && ! valid_cycle 10s && ! valid_cycle 1.5 && ! valid_cycle ""'
check "cycle: the command and the menu use it"      'grep -q "valid_cycle \"\${2:-x}\"" bin/zenithboard && grep -q "if valid_cycle \"\$s\"" lib/menus.sh'
cfg_set SHOW_PHOTOS 1
( wt_yesno() { return 255; }; . lib/menus.sh; menu_yesno_set SHOW_PHOTOS "q" 8 ); rc=$?
check "Esc on a yes/no leaves the setting as it was" '[ '"$rc"' = 2 ] && [ "$(cfg_get SHOW_PHOTOS)" = 1 ]'
( wt_yesno() { return 1; }; . lib/menus.sh; menu_yesno_set SHOW_PHOTOS "q" 8 )
check "No on a yes/no switches it off"              '[ "$(cfg_get SHOW_PHOTOS)" = 0 ]'
# 0.99.22 (review of 0.99.8): the menu's photos and routes switches wrote the setting and did not restart the wall,
# so an open tablet kept the old one; `photos on|off` and `routes on|off` restart it. Both now take the same path.
mkdir -p "$t/wb"; printf '#!/bin/bash\necho "systemctl $*" >> "%s/wall.log"\n[ "$1" = list-unit-files ] && echo "$2 enabled"\nexit 0\n' "$t" > "$t/wb/systemctl"; chmod +x "$t/wb/systemctl"
menu_switch() {   # menu_switch ENTRY yes|no|esc: the wall's Photos, routes menu, that entry, that answer, then Back
  ( PATH="$t/wb:$PATH"; . lib/flightinfo.sh; . lib/menus.sh
    rm -f "$t/menu.n"   # the menu is read in $(...), a subshell of its own: its count is kept in a file
    wt_menu() { [ -e "$t/menu.n" ] && { echo back; return 0; }; : > "$t/menu.n"; echo "$ENTRY"; }
    wt_yesno() { case "$ANSWER" in yes) return 0 ;; no) return 1 ;; *) return 255 ;; esac; }
    wt_msg() { echo "MSG $1" >> "$t/wall.log"; }
    ENTRY=$1 ANSWER=$2; wall_data_menu )
}
for e in photos:SHOW_PHOTOS routes:SHOW_ROUTES; do
  key=${e#*:}; cfg_set "$key" 1; : > "$t/wall.log"
  menu_switch "${e%%:*}" no
  check "menu ${e%%:*} No: off and the wall restarted, so the tablets reload" '[ "$(cfg_get "$key")" = 0 ] && grep -q "^systemctl restart zenithboard-flightinfo$" "$t/wall.log" && grep -q "^MSG .* OFF" "$t/wall.log"'
  : > "$t/wall.log"; menu_switch "${e%%:*}" yes
  check "menu ${e%%:*} Yes: on and the wall restarted"                       '[ "$(cfg_get "$key")" = 1 ] && grep -q "^systemctl restart zenithboard-flightinfo$" "$t/wall.log" && grep -q "^MSG .* ON" "$t/wall.log"'
  : > "$t/wall.log"; menu_switch "${e%%:*}" esc
  check "menu ${e%%:*} Esc: nothing changed, nothing restarted"               '[ "$(cfg_get "$key")" = 1 ] && ! grep -q "restart" "$t/wall.log"'
done
check "the command and the menu share the switch's function" 'grep -q "on)  root_or_die; wall_photos_set 1 ;;" bin/zenithboard && grep -q "on)  wall_routes_set 1 ;;" bin/zenithboard && grep -q "menu_yesno_apply wall_photos_set" lib/menus.sh && grep -q "menu_yesno_apply wall_routes_set" lib/menus.sh'
check "backup sub-menu: no Make or Restore twice, delete not last" '! sed -n "/^backup_menu() {/,/^}/p" lib/backup.sh | grep -q "make \"\|restore \"" && sed -n "/^backup_menu() {/,/^}/p" lib/backup.sh | grep -A1 "clean \"" | grep -q "show \""'
check "uninstall: Yes goes on, the secrets and the data named" 'grep -q "Yes goes on to the typed word" install.sh && grep -q "Bluesky app password in social.env" install.sh && grep -q "sudo rm -rf \$ZB_DATA" install.sh'
check "menu: the look is said even when the colour is left" 'grep -q "colour unchanged" lib/menus.sh'
# 0.54.12 (the audit of 22-23 October 2026): config.env renamed over in one step, one writer at a time
for i in 1 2 3 4 5 6 7 8; do cfg_set "PAR_$i" "v $i" & done; wait
check "config: eight writers at once lose nothing"  '( for i in 1 2 3 4 5 6 7 8; do [ "$(cfg_get "PAR_$i")" = "v $i" ] || exit 1; done )'
for i in 1 2 3 4 5 6 7 8; do cfg_del "PAR_$i"; done
check "config: no copy left beside it, 644"         '! ls -A "$ZENITHBOARD_ETC" | grep -q "^\.config\.env\." && [ "$(stat -c %a "$ZENITHBOARD_ETC/config.env")" = 644 ] && [ -z "$(cfg_get PAR_1 "")" ]'
check "deploy: a failed copy says so and how to repair" 'grep -q "install.sh --deploy" lib/flightinfo.sh && grep -q "is incomplete there" lib/flightinfo.sh'
check "install: gpg comes with whiptail and curl"   'grep -q "apt_install whiptail curl ca-certificates gnupg" install.sh && grep -q "gpg is not installed on this Pi" lib/update.sh'
check "stats on: the /stats page offered only with the wall" 'grep -q "the /stats page comes with the wall" lib/stats.sh'
check "wifi: a join that failed offers to type the password again (0.54.16)" 'grep -q "Type its password again?" lib/wifi.sh'
check "menu: update offers quick first"             'grep -q "quick \"1  ZenithBoard and the wall only" lib/update.sh'

[ "$fail" = 0 ] && echo "ALL OK"; exit "$fail"
