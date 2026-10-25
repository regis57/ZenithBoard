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

# ---- presets
check "preset: name rules"                          'preset_valid_name kitchen && preset_valid_name tv2 && ! preset_valid_name Kitchen && ! preset_valid_name 2tv && ! preset_valid_name "a b" && ! preset_valid_name abcdefghijklmnopq'
check "preset: add writes PRESET_NAME"              'preset_add kitchen theme=green mode=flap radius=5 >/dev/null && [ "$(cfg_get PRESET_KITCHEN)" = "theme=green mode=flap radius=5" ]'
check "preset: only the tablet keys, sane values"   '! preset_add tv PORT=1 >/dev/null 2>&1 && ! preset_add tv mode=huge >/dev/null 2>&1 && ! preset_add tv radius=0 >/dev/null 2>&1 && ! preset_add tv cycle=999 >/dev/null 2>&1 && [ -z "$(cfg_get PRESET_TV "")" ]'
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
python3 - "$port" <<'PY' &
import http.server, json, sys
planes = [{"hex": "aaa001", "flight": "BGA113J", "airline": None, "shape": "wide", "type": "A337"},
          {"hex": "aaa002", "flight": "EZY12", "airline": "easyJet", "shape": "generic", "type": "A21N"},
          {"hex": "aaa003", "flight": "BGA2", "airline": None, "shape": "generic", "type": "A21N"},
          {"hex": "aaa004", "flight": "", "airline": None, "shape": "generic", "type": ""}]
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b = json.dumps({"planes": planes}).encode(); self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
http.server.HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
PY
srv=$!; sleep 1
stats_gaps_sample 2026-10-18; stats_gaps_sample 2026-10-18
kill $srv 2>/dev/null
check "gaps: each aircraft once, by prefix and by type" '[ "$(sort "$STATS_DIR/gaps-2026-10-18" | tr "\t" " ")" = "$(printf "airline BGA aaa001\nairline BGA aaa003\nshape A21N aaa002\nshape A21N aaa003")" ]'
check "gaps: the report counts aircraft"           'stats_gaps | grep -q "BGA    2 aircraft" && stats_gaps | grep -q "A21N   2 aircraft"'
check "gaps: pruned with the rest"                  'touch "$STATS_DIR/gaps-2020-01-01" "$STATS_DIR/seen-2020-01-01"; echo "$STATS_HEADER" > "$STATS_FILE"; stats_prune >/dev/null 2>&1; [ ! -f "$STATS_DIR/gaps-2020-01-01" ] && [ -f "$STATS_DIR/gaps-2026-10-18" ]'
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
check "backup sub-menu: no Make or Restore twice, delete not last" '! sed -n "/^backup_menu() {/,/^}/p" lib/backup.sh | grep -q "make \"\|restore \"" && sed -n "/^backup_menu() {/,/^}/p" lib/backup.sh | grep -A1 "clean \"" | grep -q "show \""'
check "uninstall: Yes goes on, the secrets and the data named" 'grep -q "Yes goes on to the typed word" install.sh && grep -q "Bluesky app password in social.env" install.sh && grep -q "sudo rm -rf \$ZB_DATA" install.sh'
check "menu: the look is said even when the colour is left" 'grep -q "colour unchanged" lib/menus.sh'
check "menu: update offers quick first"             'grep -q "quick \"1  ZenithBoard and the wall only" lib/update.sh'

[ "$fail" = 0 ] && echo "ALL OK"; exit "$fail"
