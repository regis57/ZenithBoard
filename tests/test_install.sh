#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_install.sh   The installer itself, run as a newcomer runs it (bash install.sh), against a
# whiptail that answers from a script and records every screen, and stubs for everything that touches the system.
# What it proves: the flags, the first-run wizard from a blank settings file to the main menu, the questions asked
# again on a bad answer, the hardware notice shown once, a clear stop when whiptail cannot be installed, no error
# on a machine that is not a Pi, and the menu texts the README promises. Written for the fresh-install check of
# 0.21.1; it does not install anything and needs no root (the `id` on PATH says root).
# shellcheck disable=SC2034  # out and rc are read inside the eval-ed check strings
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap '[ -n "${KEEP:-}" ] || rm -rf "$t"' EXIT; [ -z "${KEEP:-}" ] || echo "kept: $t"
mkdir -p "$t/bin" "$t/etc" "$t/opt" "$t/link"
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }

# ---- the scripted whiptail: one answer per screen from $WT_ANSWERS, every screen written to $WT_LOG, Cancel when
#      the answers run out (so a run always ends). It writes the answer where whiptail does: on stderr.
cat > "$t/bin/whiptail" <<'EOF'
#!/bin/bash
args=("$@"); type=""; text=""; i=0
while [ $i -lt ${#args[@]} ]; do a=${args[$i]}
  case "$a" in
    --title|--cancel-button) i=$((i+2)); continue ;;
    --msgbox|--yesno|--inputbox|--passwordbox|--menu|--radiolist|--checklist) type=${a#--}; text=${args[$((i+1))]}; i=$((i+2)); break ;;
    *) i=$((i+1)) ;;
  esac
done
rest=("${args[@]:$i}"); tags=""
case "$type" in
  menu) for ((j=3; j<${#rest[@]}; j+=2)); do tags+="${rest[$j]} "; done ;;
  radiolist|checklist) for ((j=3; j<${#rest[@]}; j+=3)); do tags+="${rest[$j]} "; done ;;
esac
ans=""; have=0
if [ -s "$WT_ANSWERS" ]; then ans=$(head -n1 "$WT_ANSWERS"); sed -i '1d' "$WT_ANSWERS"; have=1; fi
printf '%s\t%s\t[%s]\t<- %s\n' "$type" "$(printf '%s' "$text" | tr '\n' ' ')" "$tags" "$ans" >> "$WT_LOG"
case "$type" in
  msgbox) exit 0 ;;
  yesno) [ "$ans" = yes ] ;;
  inputbox|passwordbox) [ "$have" = 1 ] || exit 1; [ "$ans" = CANCEL ] && exit 1; [ "$ans" = EMPTY ] && ans=""; printf '%s' "$ans" >&2 ;;
  menu|radiolist) [ "$have" = 1 ] || exit 1; [ "$ans" = CANCEL ] && exit 1
    case " $tags" in *" $ans "*) printf '%s' "$ans" >&2 ;; *) echo "BAD TAG $ans" >> "$WT_LOG"; exit 2 ;; esac ;;
  checklist) [ "$have" = 1 ] || exit 1; [ "$ans" = CANCEL ] && exit 1; out=""; for x in $ans; do out+="\"$x\" "; done; printf '%s' "${out% }" >&2 ;;
esac
EOF
# ---- the system, as a fresh Pi 3B (1 GB) answers it; nothing here reaches the real one
stub() { printf '#!/bin/bash\necho "%s $*" >> "$STUB_LOG"\n%s\n' "$1" "$2" > "$t/bin/$1"; chmod +x "$t/bin/$1"; }
stub id 'case "$1" in -u) echo 0 ;; -un) echo root ;; *) exit 1 ;; esac'
stub dpkg 'case "$1" in --print-architecture) echo arm64 ;; *) exit 1 ;; esac'
stub apt-get 'exit 0'
stub systemctl 'case "$1" in is-active) shift; [ "${1:-}" = --quiet ] && shift; [ "${1:-}" = NetworkManager ] && exit 0; exit 3 ;; esac; exit 0'
stub nmcli 'case "$*" in "radio wifi") echo enabled ;; *"-f DEVICE,TYPE device"*) echo "eth0:ethernet"; echo "wlan0:wifi" ;; *"-f DEVICE,TYPE,STATE device"*) echo "eth0:ethernet:connected" ;; esac; exit 0'
stub hostname 'case "$1" in -I) echo "192.168.1.23 " ;; *) echo zenithboard ;; esac'
stub journalctl 'exit 0'
stub curl 'exit 7'
chmod +x "$t"/bin/*
printf 'MemTotal:         948000 kB\nMemAvailable:     700000 kB\n' > "$t/meminfo"
printf 'Raspberry Pi 3 Model B Rev 1.2\0' > "$t/model"
export PATH="$t/bin:$PATH" STUB_LOG="$t/stub.log" WT_LOG="$t/screens" WT_ANSWERS="$t/answers"
export ZENITHBOARD_ETC="$t/etc" ZENITHBOARD_HOME="$t/opt" ZENITHBOARD_BIN_DIR="$t/link" ZB_MEMINFO="$t/meminfo" ZB_PI_MODEL_FILE="$t/model" ZB_SKIP_SERVICES=1
run() {   # run NAME answers... -> stdout+stderr in $t/NAME.out, the screens in $t/NAME.screens, exit code in $rc
  local name="$1"; shift
  printf '%s\n' "$@" > "$WT_ANSWERS"; : > "$WT_LOG"; : > "$STUB_LOG"
  timeout 60 bash install.sh "${INSTALL_ARGS[@]}" < /dev/null > "$t/$name.out" 2>&1; rc=$?
  cp "$WT_LOG" "$t/$name.screens"
}
INSTALL_ARGS=()

# ---- the flags
check "uninstall everything stops the Bluesky service too (0.54.0: it was left running)" 'sed -n "/^uninstall_all()/,/^}/p" install.sh | grep -q "social_off"'
check "--help prints the usage and names --help"   'out=$(bash install.sh --help) && echo "$out" | grep -q -- "--help" && echo "$out" | grep -q -- "--uninstall-all"'
check "--version prints the version"               '[ "$(bash install.sh --version)" = "ZenithBoard $(. lib/versions.sh; echo "$ZB_VERSION")" ]'
check "an unknown flag is refused with the usage"  '! bash install.sh --bogus >/dev/null 2>&1 && bash install.sh --bogus 2>&1 | grep -q Usage'
if [ "$(/usr/bin/id -u)" -ne 0 ]; then
  check "without root it says to use sudo"         'PATH=/usr/bin:/bin bash install.sh --deploy 2>&1 | grep -q "run as root"'
else
  echo "skip the root check (this run is root)"
fi

# ---- a fresh Pi: the hardware notice, the welcome, the four questions, then the main menu; a typo is asked again
run fresh ok ok world metric abc ok 49.1193 6.1757 xyz ok 180 10 0
check "fresh: ends normally at the main menu"       '[ "$rc" = 0 ] && grep -q "^menu	ZenithBoard" "$t/fresh.screens"'
check "fresh: the Pi 3 notice comes first, once"    'head -1 "$t/fresh.screens" | grep -q "Raspberry Pi 3" && [ "$(cfg=$t/etc/config.env; grep -c "^HW_NOTICE_SEEN=1$" "$cfg")" = 1 ]'
check "fresh: the welcome points at the menu, not at the read-only config command" 'grep "^msgbox	Welcome" "$t/fresh.screens" | grep -q "Start here" && ! grep "^msgbox	Welcome" "$t/fresh.screens" | grep -q "sudo zenithboard config "'
check "fresh: a bad latitude is asked again"        '[ "$(grep -c "^inputbox	Antenna LATITUDE" "$t/fresh.screens")" = 2 ] && grep -q "Not a valid latitude" "$t/fresh.screens"'
check "fresh: a bad altitude is asked again, not written as 0" '[ "$(grep -c "^inputbox	Antenna altitude" "$t/fresh.screens")" = 2 ] && grep -q "^msgbox	Not a number" "$t/fresh.screens"'
check "fresh: the answers are in config.env"        'grep -q "^REGION=world$" "$t/etc/config.env" && grep -q "^UNITS=metric$" "$t/etc/config.env" && grep -q "^LAT=49.1193$" "$t/etc/config.env" && grep -q "^LON=6.1757$" "$t/etc/config.env" && grep -q "^ALT_M=180$" "$t/etc/config.env" && grep -q "^RADIUS=10$" "$t/etc/config.env"'
check "fresh: the defaults are written too"         'grep -q "^THEME=amber$" "$t/etc/config.env" && grep -q "^PORT=8080$" "$t/etc/config.env" && grep -q "^DECODER=readsb$" "$t/etc/config.env"'
check "fresh: the files are deployed and the command linked" '[ -x "$t/opt/install.sh" ] && [ -f "$t/opt/lib/common.sh" ] && [ -L "$t/link/zenithboard" ] && [ "$(cat "$t/opt/.source")" = "$PWD" ]'
check "fresh: nothing was installed with apt"       '! grep -q "apt-get install" "$t/stub.log"'

# ---- the second run skips the wizard and the notice
run again 0
check "again: straight to the main menu"            '[ "$rc" = 0 ] && [ "$(head -1 "$t/again.screens" | cut -f1)" = menu ] && [ "$(wc -l < "$t/again.screens")" = 1 ]'

# ---- the wizard interrupted: nothing half-written is taken as done
rm -f "$t/etc/config.env"
run cancelled ok CANCEL
check "cancel in the wizard: exit 0, no position saved, asked again next time" '[ "$rc" = 0 ] && ! grep -q "^LAT=." "$t/etc/config.env" && ! grep -q "^menu" "$t/cancelled.screens"'
run resumed ok world metric 49.1 6.1 0 10 0
check "the wizard runs again after a cancel"        '[ "$rc" = 0 ] && grep -q "^LAT=49.1$" "$t/etc/config.env" && grep -q "^menu	ZenithBoard" "$t/resumed.screens"'

# ---- the menu texts the README promises
run colours 2 look dots CANCEL back 0
check "wall colour offers the five colours of the wall" 'grep "^radiolist	Dot colour" "$t/colours.screens" | grep -q "\[amber green red white turquoise \]"'
check "the wall menu says look and colour together"  'grep "^menu	The wall" "$t/colours.screens" | grep -q "\[install show look data presets remove back \]"'
# 0.44.0: the menu by what you want to do (the owner's review): Start here, then seven subjects, seven entries at most
run settings 3 back 0
check "main menu: Start here, then seven subjects"   'grep "^menu	ZenithBoard" "$t/settings.screens" | head -1 | grep -q "\[start 1 2 3 4 5 6 7 0 \]" && grep -q "Start here" README.md'
check "connectivity: Wi-Fi on with no network reads \"not connected\", not \"ON, \"" 'grep "^menu	Connectivity" "$t/settings.screens" | grep -q "Wi-Fi: ON, not connected"'
check "no menu has more than seven entries and its way out" '! grep -h "^menu" "$t"/*.screens | grep -o "\[[^]]*\]" | awk "{ if (NF > 9) exit 1 }" && [ "$(grep -c "^      [a-z0-9]* \"[0-9]  " lib/menus.sh)" -gt 20 ]'
# ---- 0.44.0: Start here, in its order: a backup first if any (WinSCP said), then ADS-B; nothing goes on without a decoder
run startbackup start ok yes ok CANCEL 0
check "start: a backup first, WinSCP named, cancel changes nothing" '[ "$rc" = 0 ] && grep -q "^yesno	Are you moving from another card" "$t/startbackup.screens" && grep -q "WinSCP" "$t/startbackup.screens" && [ "$(grep -c "^menu	ZenithBoard" "$t/startbackup.screens")" = 2 ]'
run startadsb start ok no ok CANCEL 0
check "start: ADS-B next, and without a decoder the rest waits" '[ "$rc" = 0 ] && grep -q "^msgbox	ADS-B first" "$t/startadsb.screens" && grep -q "^radiolist	ADS-B decoder" "$t/startadsb.screens" && grep -q "the rest waits" "$t/startadsb.screens" && ! grep -q "web console, the same settings" "$t/startadsb.screens"'
check "start: the console comes after the wall, the list before it" 'awk "/^start_here\(\)/,/^}/" lib/menus.sh | grep -n "is_flightinfo\|start_recommended\|start_console" | tr "\n" " " | grep -q "is_flightinfo.*start_recommended.*start_console"'
check "outside: the safe way first, the dangers named, port 22 never" 'grep -q "Only the first is safe" lib/menus.sh && grep -q "NEVER forward port 22" lib/menus.sh && grep -q "tailscale_menu" lib/menus.sh && grep -q "100.64.0.0/10" lib/tailscale.sh'
check "README: the wall address comes from menu 2"   'grep -q "menu \*2 The wall\* printed" README.md && ! grep -q "address from step 2" README.md'

# ---- a machine that is not a Pi: a warning, no error from a missing model file
ZB_PI_MODEL_FILE="$t/no-such-model" run notapi 0
check "no model file: no 'No such file' error"      '! grep -q "No such file" "$t/notapi.out" && [ "$rc" = 0 ]'

# ---- whiptail missing and apt unable to install it: a clear stop, not a silent exit. A PATH made of the stubs
#      and links to the tools the installer needs, so that the real whiptail of this machine cannot be found.
mkdir -p "$t/path"
for c in bash sh dirname basename mktemp chmod grep sed awk cut tail head tr install cp rm mkdir touch ln cat printf date wc sort ls readlink env timeout; do
  p=$(command -v "$c") && ln -sf "$p" "$t/path/$c"
done
mv "$t/bin/whiptail" "$t/whiptail.keep"
out=$(PATH="$t/bin:$t/path" timeout 60 bash install.sh < /dev/null 2>&1); rc=$?
mv "$t/whiptail.keep" "$t/bin/whiptail"
check "no whiptail: stops with a message naming it" '[ "$rc" != 0 ] && echo "$out" | grep -q "whiptail and curl could not be installed"'
check "no whiptail: apt was asked first"             'grep -q "apt-get install -y whiptail curl" "$t/stub.log"'

# ---- the decoder failure in menu 1 says the feeders were skipped
check "ADSB: a decoder failure says nothing else was installed" 'grep -q "nothing else was installed" lib/adsb.sh'

[ "$fail" = 0 ] && echo "ALL OK"; exit "$fail"
