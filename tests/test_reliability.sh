#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_reliability.sh   Watchdogs, saved logs, the health screen. Stub programs stand in for ping, ip, systemctl,
# vcgencmd, journalctl and logger; nothing touches the real system.
# shellcheck disable=SC2034  # variables are used inside the eval-ed check strings
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/run" "$t/var" "$t/sysd" "$t/jd" "$t/jdir"; touch "$ZENITHBOARD_ETC/config.env"
export ZB_SKIP_SERVICES=1 ZB_RUN_DIR="$t/run" ZB_VAR_DIR="$t/var" ZB_SYSTEMD_CONF_DIR="$t/sysd" ZB_JOURNALD_DIR="$t/jd" ZB_JOURNAL_DIR="$t/jdir"
export ZB_UPTIME_FILE="$t/uptime" ZB_WATCHDOG_DEV="$t/watchdog" ZB_PI_MODEL_FILE="$t/model"
echo "Raspberry Pi 3 Model B Rev 1.2" > "$t/model"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/reliability.sh
. lib/reliability.sh
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

# ---- stubs: they log every call in $t/calls
: > "$t/calls"
mk() { printf '#!/bin/bash\n%s\n' "$2" > "$t/bin/$1"; chmod +x "$t/bin/$1"; }
mk ping 'echo "ping $*" >> '"$t"'/calls; [ -f '"$t"'/router_up ]'
mk ip 'echo "default via 192.168.1.1 dev eth0"'
mk systemctl 'echo "systemctl $*" >> '"$t"'/calls; [ "$1" != is-active ] || exit 0'
mk logger 'echo "logger $*" >> '"$t"'/calls'
mk vcgencmd 'case "$1" in get_throttled) echo "throttled=$(cat '"$t"'/throttled)";; measure_temp) echo "temp=$(cat '"$t"'/temp)'"'"'C";; esac'
mk journalctl 'echo "journalctl $*" >> '"$t"'/calls; case "$*" in *list-boots*) cat '"$t"'/boots;; *"-b -1 -n 40"*) cat '"$t"'/prevtail;; *"-b -1 -n 8"*) cat '"$t"'/prevtail;; *"-k -b 0"*) cat '"$t"'/kern0;; *"-k -b -1"*) cat '"$t"'/kern1;; esac'
PATH="$t/bin:$PATH"
touch "$t/watchdog"

# ---- hardware watchdog
check "off at first"               '[ "$(watchdog_state)" = off ]'
watchdog_on >/dev/null
check "on writes RuntimeWatchdogSec=10 and RebootWatchdogSec" 'grep -qx "RuntimeWatchdogSec=10" "$RELI_WATCHDOG_CONF" && grep -qx "RebootWatchdogSec=2min" "$RELI_WATCHDOG_CONF"'
check "state is on"                '[ "$(watchdog_state)" = on ]'
watchdog_off >/dev/null
check "off removes the file"       '[ ! -e "$RELI_WATCHDOG_CONF" ] && [ "$(watchdog_state)" = off ]'
rm "$t/watchdog"
check "no watchdog device: refused, nothing written" '! watchdog_on >/dev/null 2>&1 && [ ! -e "$RELI_WATCHDOG_CONF" ]'
touch "$t/watchdog"

# ---- saved logs
keeplogs_on >/dev/null
check "keeplogs on: persistent, capped at 50M" 'grep -qx "Storage=persistent" "$RELI_JOURNAL_CONF" && grep -qx "SystemMaxUse=50M" "$RELI_JOURNAL_CONF" && [ -d "$RELI_JOURNAL_DIR" ] && [ "$(keeplogs_state)" = on ]'
keeplogs_off >/dev/null
check "keeplogs off removes the setting, keeps the old logs" '[ ! -e "$RELI_JOURNAL_CONF" ] && [ -d "$RELI_JOURNAL_DIR" ] && [ "$(keeplogs_state)" = off ]'

# ---- network watchdog: one check at a time
runs() { local i; for ((i = 0; i < $1; i++)); do netwatch_run; done; }
echo 5000 > "$t/uptime"; rm -f "$t/router_up"
check "gateway is read from the default route" '[ "$(netwatch_gateway)" = 192.168.1.1 ]'
echo 100 > "$t/uptime"; netwatch_run
check "first 10 minutes after a start: not judged"  '[ ! -e "$NETWATCH_FAILS" ] && ! grep -q "^ping" "$t/calls"'
echo 5000 > "$t/uptime"; touch "$t/router_up"; netwatch_run
check "router answers: nothing happens"             '[ ! -e "$NETWATCH_FAILS" ] && ! grep -q "systemctl" "$t/calls"'
rm "$t/router_up"; : > "$t/calls"; runs 2
check "2 failures: only counted"                    '[ "$(cat "$NETWATCH_FAILS")" = 2 ] && ! grep -q "systemctl" "$t/calls"'
netwatch_run
check "3rd failure: network restarted, no reboot"   'grep -q "systemctl restart NetworkManager" "$t/calls" && ! grep -q "reboot" "$t/calls"'
: > "$t/calls"; runs 2
check "4th and 5th failure: nothing more"           '! grep -q "systemctl" "$t/calls"'
netwatch_run
check "6th failure: the Pi is restarted"            'grep -q "systemctl reboot" "$t/calls" && [ -s "$NETWATCH_REBOOTED" ]'
: > "$t/calls"; runs 3
check "never again within 3 hours (no reboot loop)" '! grep -q "systemctl reboot" "$t/calls" && grep -q "not restarting again" "$t/calls"'
echo $(( $(date +%s) - 20000 )) > "$NETWATCH_REBOOTED"; : > "$t/calls"; netwatch_run
check "after 3 hours it may restart again"          'grep -q "systemctl reboot" "$t/calls"'
touch "$t/router_up"; netwatch_run
check "router back: counter reset"                  '[ ! -e "$NETWATCH_FAILS" ]'
# no default route at all counts as a failure
mk ip 'exit 0'; rm -f "$NETWATCH_FAILS" "$t/router_up"; netwatch_run
check "no default route: a failure"                 '[ "$(cat "$NETWATCH_FAILS")" = 1 ] && ! grep -q "ping.*default" "$t/calls"'
mk ip 'echo "default via 192.168.1.1 dev eth0"'
echo "garbage" > "$NETWATCH_FAILS"; netwatch_run
check "a damaged counter file does not break it"    '[ "$(cat "$NETWATCH_FAILS")" = 1 ]'
check "the check always ends successfully"          'netwatch_run'
cfg_set NETWATCH 1
check "status shows on"                              'netwatch_status | grep -q "Network watchdog: on"'
netwatch_off >/dev/null
check "off: setting cleared, counter removed"       '[ "$(cfg_get NETWATCH 0)" = 0 ] && [ ! -e "$NETWATCH_FAILS" ]'

# ---- the units
check "service runs the check as a one-shot"  'grep -q "ExecStart=/opt/zenithboard/bin/zenithboard netwatch run" systemd/zenithboard-netwatch.service && grep -q "Type=oneshot" systemd/zenithboard-netwatch.service'
check "timer starts 2 min after being enabled and repeats (OnBootSec alone would never fire)" 'grep -q "OnActiveSec=2min" systemd/zenithboard-netwatch.timer && grep -q "OnUnitInactiveSec=2min" systemd/zenithboard-netwatch.timer'

# ---- health screen
echo 0x0 > "$t/throttled"; echo 41.2 > "$t/temp"
printf ' -1 aaa Wed 2026-10-07 10:00:00 CEST Thu 2026-10-08 03:10:00 CEST\n  0 bbb Thu 2026-10-08 08:43:00 CEST Thu 2026-10-08 09:00:00 CEST\n' > "$t/boots"
printf 'Oct 08 03:09:58 rp3 readsb[300]: something\nOct 08 03:10:00 rp3 piaware[400]: sent\n' > "$t/prevtail"
: > "$t/kern0"; : > "$t/kern1"
out=$(health_check 2>&1)
check "OK power"                       'grep -q "Power:        OK" <<<"$out"'
check "temperature shown"              'grep -q "Temperature:  41 C: OK" <<<"$out"'
check "previous boot without shutdown messages = abrupt" 'grep -q "ended ABRUPTLY" <<<"$out" && grep -q "piaware" <<<"$out"'
check "nothing alarming"               'grep -q "nothing alarming" <<<"$out"'
check "saved logs off is explained"    'grep -q "logs are lost at every restart" <<<"$out"'
printf 'Oct 08 03:09:58 rp3 systemd[1]: Reached target Shutdown.\nOct 08 03:10:00 rp3 systemd-journald[200]: Journal stopped\n' > "$t/prevtail"
check "previous boot with a clean shutdown" 'health_check 2>&1 | grep -q "ended normally"'
echo 0x50005 > "$t/throttled"; echo 83.0 > "$t/temp"
printf 'Oct 08 03:00 kernel: Under-voltage detected! (0x00050005)\nOct 08 03:01 kernel: usb 1-1.1: USB disconnect, device number 4\n' > "$t/kern1"
out=$(health_check 2>&1)
check "under-voltage now and earlier"  'grep -q "UNDER-VOLTAGE RIGHT NOW" <<<"$out" && grep -q "under-voltage happened since the start" <<<"$out"'
check "too hot"                        'grep -q "TOO HOT" <<<"$out"'
check "kernel lines about power and USB are listed" 'grep -q "Under-voltage detected" <<<"$out" && grep -q "USB disconnect" <<<"$out"'
echo 0x80000 > "$t/throttled"
check "soft temperature limit happened" 'health_check 2>&1 | grep -q "temperature limit"'
printf '  0 bbb Thu 2026-10-08 08:43:00 CEST Thu 2026-10-08 09:00:00 CEST\n' > "$t/boots"
check "only one boot in the logs"      'health_check 2>&1 | grep -q "no earlier boot"'
mk vcgencmd 'exit 1'
check "no vcgencmd: the screen still works" 'health_check >/dev/null 2>&1'

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
