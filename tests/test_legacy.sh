#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_legacy.sh   0.30.0: ACARS and Grafana left ZenithBoard. What an older install left behind is
# found, said by status and update, never removed by an update, and removed by `acars remove` after the typed word.
# The menus and the command no longer offer ACARS. Stubs: systemctl, dpkg, apt-get; the Pi's folders under a temp dir.
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc" T="$t"; mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/data"; touch "$ZENITHBOARD_ETC/config.env"
printf '#!/bin/bash\necho "systemctl $*" >> "$T/log"\n' > "$t/bin/systemctl"
printf '#!/bin/bash\n[ "$2" = grafana ] && [ -f "$T/grafana" ] && exit 0; exit 1\n' > "$t/bin/dpkg"
printf '#!/bin/bash\necho "apt-get $*" >> "$T/log"; rm -f "$T/grafana"\n' > "$t/bin/apt-get"
chmod +x "$t"/bin/*; export PATH="$t/bin:$PATH"
# shellcheck source=lib/common.sh
. lib/common.sh
ZB_DATA="$t/data"
# shellcheck source=lib/legacy.sh
. lib/legacy.sh
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }

check "a clean Pi: nothing left, no notice"          '[ -z "$(acars_leftovers)" ] && [ -z "$(acars_notice)" ]'
check "a clean Pi: remove says so"                   'acars_remove | grep -q "Nothing of ACARS"'
touch "$t/grafana" "$t/data/acars.db" "$GRAFANA_PASS_FILE"; cfg_set ACARS_SDR 00000131; cfg_set ACARS_FREQS "131.525"
check "leftovers listed: package, messages, password" 'acars_leftovers | grep -q "package grafana" && acars_leftovers | grep -q "messages" && acars_leftovers | grep -q "password"'
check "the notice gives the command"                 'acars_notice | grep -q "sudo zenithboard acars remove"'
check "a wrong word removes nothing"                 '! echo nope | acars_remove >/dev/null && [ -f "$t/data/acars.db" ] && [ -f "$t/grafana" ]'
echo remove | acars_remove >/dev/null
check "the word removes it all"                      '[ ! -f "$t/data/acars.db" ] && [ ! -f "$GRAFANA_PASS_FILE" ] && grep -q "apt-get purge -y grafana" "$t/log" && [ -z "$(acars_leftovers)" ]'
check "and the ACARS settings"                       '[ -z "$(cfg_get ACARS_SDR "")" ] && [ -z "$(cfg_get ACARS_FREQS "")" ]'
check "the services stopped"                         'grep -q "disable --now zenithboard-acarsdec" "$t/log" && grep -q "disable --now grafana-server" "$t/log"'

# an update never removes it: it only says so
check "update says, never removes"                   'grep -q "acars_notice" lib/update.sh && ! grep -q "acars_remove" lib/update.sh'
# nothing offers ACARS any more
check "main menu: no ACARS, Settings is 3, Maintenance is 6" '! grep -q "ACARS       -" install.sh && grep -q "3 \"Settings" install.sh && grep -q "6 \"Maintenance" install.sh'
check "no ACARS install code left"                   '[ ! -e lib/acars.sh ] && [ ! -e acars ] && [ ! -e bin/run-acarsdec ] && ! ls systemd | grep -q acars'
check "command: acars remove only"                   'grep -q "remove) root_or_die; acars_remove" bin/zenithboard && ! grep -q "grafana_password_cmd" bin/zenithboard'
check "update list: no acars component"              '! grep -q "ZB_COMPONENTS=.*acars" lib/update.sh'
check "uninstall everything takes the leftovers too" 'grep -q "acars_remove --yes" install.sh'

# 0.30.1: an update on a Pi still running ACARS keeps the files its services start; a clean Pi loses the old ones
src=$(pwd); export ZB_HOME="$t/opt"; mkdir -p "$ZB_HOME/acars" "$ZB_HOME/bin"
echo ingest > "$ZB_HOME/acars/acars_ingest.py"; echo run > "$ZB_HOME/bin/run-acarsdec"
# shellcheck source=lib/flightinfo.sh
. lib/flightinfo.sh
ZB_BIN_DIR="$t/usrbin"; mkdir -p "$ZB_BIN_DIR"
deploy_on() { ( BASH_SOURCE_DIR="$src"; cd "$src" && deploy_files ) >/dev/null 2>&1; }
units_dir_has() { [ -f /etc/systemd/system/zenithboard-acars-ingest.service ]; }
if units_dir_has; then echo "skip keep-files: this machine has an ACARS unit"; else
  deploy_on
  check "a clean Pi: the old ACARS files go with an update" '[ ! -e "$ZB_HOME/acars" ] && [ ! -e "$ZB_HOME/bin/run-acarsdec" ] && [ -x "$ZB_HOME/bin/zenithboard" ]'
fi
check "deploy keeps them while a unit is installed"  'grep -q "zenithboard-acars-ingest.service" lib/flightinfo.sh && grep -q "cp -a \"\$keep/run-acarsdec\"" lib/flightinfo.sh'
check "acars remove takes the kept files"            'grep -q "rm -rf \"\${ZB_HOME:?}/acars\"" lib/legacy.sh && grep -q "bin/run-acarsdec" lib/legacy.sh'
[ "$fail" = 0 ] && echo "ALL OK"; exit "$fail"
