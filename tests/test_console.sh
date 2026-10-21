#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_console.sh   0.39.0: `zenithboard console`, off by default. The password is read, never taken
# from the command line, kept as a scrypt hash in its own file (0640), and signs everyone out; `on` makes the folders
# and installs the helper's two units, `off` takes them away and keeps the password, `forget` deletes it; `pair`
# leaves a code's hash for the wall; `state` prints what the overview shows. Stubs: systemctl, hostname.
# shellcheck disable=SC2034
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/sysd"; touch "$ZENITHBOARD_ETC/config.env"
export ZB_SYSTEMD_DIR="$t/sysd" ZB_CONSOLE_DIR="$t/console"
printf '#!/bin/bash\necho "systemctl $*" >> "%s/systemctl.log"\n[ "$1" = is-active ] && echo active\nexit 0\n' "$t" > "$t/bin/systemctl"
printf '#!/bin/bash\necho 192.168.1.50\n' > "$t/bin/hostname"
chmod +x "$t"/bin/*; export PATH="$t/bin:$PATH"
# shellcheck source=lib/common.sh
. lib/common.sh
for f in reliability patches graphs social wifi ddns settings console; do
  # shellcheck disable=SC1090
  . "lib/$f.sh"
done
ZB_HOME="$PWD"
ZB_USER=$(id -un)      # root in a container (its group has its name), or the CI's user, who chowns nothing
want='CONSOLE_PASSWORD_HASH="scrypt$16384$8$1$'
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }

check "off at first"                                  '[ "$(console_state)" = off ] && ! console_has_password'
check "the default is written as off"                 'grep -qx "CONSOLE=0" lib/common.sh'

out=$(printf 'short\nshort\n' | console_password 2>&1)
check "a short password is refused, nothing written"  'printf "%s" "$out" | grep -q "Too short" && [ ! -f "$CONSOLE_ENV" ]'
out=$(printf 'a long password\nanother long one\n' | console_password 2>&1)
check "two different ones are refused"                'printf "%s" "$out" | grep -q "do not match" && [ ! -f "$CONSOLE_ENV" ]'
out=$(printf 'a long password\na long password\n' | console_password 2>&1)
check "saved as a scrypt hash, never in clear"        'grep -qF "$want" "$CONSOLE_ENV" && ! grep -q "a long password" "$CONSOLE_ENV"'
check "its file is 0640"                              '[ "$(stat -c %a "$CONSOLE_ENV")" = 640 ]'
check "and it signs everyone out (an epoch)"          'grep -q "^CONSOLE_EPOCH=\"[0-9]*\"" "$CONSOLE_ENV"'
check "never in config.env"                           '! grep -q "CONSOLE_PASSWORD" "$ZENITHBOARD_ETC/config.env"'
h=$(console_secret_get CONSOLE_PASSWORD_HASH)
check "the wall's side accepts it"                    'python3 -c "import sys; sys.path.insert(0, \"flightinfo\"); import console; sys.exit(0 if console.check_password(\"a long password\", sys.argv[1]) else 1)" "$h"'

out=$(console_on)
check "on: the setting, the address"                  '[ "$(cfg_get CONSOLE)" = 1 ] && printf "%s" "$out" | grep -q "http://192.168.1.50:8080/console"'
check "on: the wall restarted, so its sandbox opens the new folder" 'grep -q "try-restart zenithboard-flightinfo" "$t/systemctl.log"'
check "on: the folders, the spool private"            '[ -d "$t/console/out" ] && [ "$(stat -c %a "$t/console/state/spool")" = 700 ]'
check "on: the helper's two units, the path enabled"  '[ -f "$t/sysd/zenithboard-console.path" ] && [ -f "$t/sysd/zenithboard-console.service" ] && grep -q "enable --now zenithboard-console.path" "$t/systemctl.log"'
check "the path unit watches the spool"               'grep -q "^PathExistsGlob=/var/lib/zenithboard/console/state/spool/\*.job" systemd/zenithboard-console.path'
check "the wall may write its state folder only"      '[ "$(grep -c "^ReadWritePaths=" systemd/zenithboard-flightinfo.service)" = 1 ] && grep -q "^ReadWritePaths=-/var/lib/zenithboard/console/state$" systemd/zenithboard-flightinfo.service'

out=$(console_pair)
check "pair: a code's hash and its end for the wall"  'read -r hh until < "$t/console/out/pair" && [ ${#hh} = 64 ] && [ "$until" -gt "$(date +%s)" ]'
tok=$(printf "%s" "$out" | sed -n "s/.*#pair=\([A-Za-z0-9_-]*\).*/\1/p" | head -1)
check "pair: the link carries the code, its hash is the one kept" '[ -n "$tok" ] && [ "$(printf "%s" "$tok" | sha256sum | cut -d" " -f1)" = "$(cut -d" " -f1 "$t/console/out/pair")" ]'
check "pair: says how to see the QR code without qrencode" 'command -v qrencode >/dev/null || printf "%s" "$out" | grep -q "apt install qrencode"'

out=$(console_state_lines 2>/dev/null)
check "state: KEY=value lines for the overview"       'printf "%s\n" "$out" | grep -q "^version=$ZB_VERSION$" && printf "%s\n" "$out" | grep -q "^watchdog=\(on\|off\)$" && ! printf "%s\n" "$out" | grep -qv "^[a-z0-9_]*="'

out=$(console_off)
check "off: the units go, the password stays"         '[ "$(cfg_get CONSOLE)" = 0 ] && [ ! -f "$t/sysd/zenithboard-console.path" ] && [ -f "$CONSOLE_ENV" ]'
out=$(console_forget)
check "forget: the password and records go"           '[ ! -f "$CONSOLE_ENV" ] && [ ! -d "$t/console/state" ] && [ ! -d "$t/console/out" ]'
check "console status works off and without root"     'console_status | grep -q "Web console: off"'
[ "$fail" = 0 ] && echo "ALL OK" || exit 1
