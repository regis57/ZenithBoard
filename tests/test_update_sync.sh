#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# zb_sync_source: normal update, rewritten upstream history, and locally edited files.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ZENITHBOARD_ETC="$(mktemp -d)"; export ZENITHBOARD_ETC
# shellcheck source=lib/common.sh
. "$HERE/lib/common.sh"
# shellcheck source=lib/update.sh
. "$HERE/lib/update.sh"
T="$(mktemp -d)"; trap 'rm -rf "$T" "$ZENITHBOARD_ETC"' EXIT
# this file tests the syncing itself; the signature check before it has tests of its own (test_update_verify.sh)
cfg_set UPDATE_VERIFY 0
fail=0; check() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: got '$2' expected '$3'"; fail=1; fi; }
G() { git -c user.name=t -c user.email=t@example.com "$@"; }

G init -q --bare -b main "$T/origin.git"
G clone -q "$T/origin.git" "$T/work" 2>/dev/null
( cd "$T/work" && echo v1 > f && G add f && G commit -qm one && echo v2 > f && G commit -qam two && G push -q origin main )
G clone -q "$T/origin.git" "$T/pi"

# 1. plain fast-forward
( cd "$T/work" && echo v3 > f && G commit -qam three && G push -q origin main )
zb_sync_source "$T/pi" >/dev/null 2>&1; check "fast-forward" "$(cat "$T/pi/f")" v3

# 2. upstream rewrote history (same content, new hashes - like re-signing)
( cd "$T/work" && G rebase -q --root --exec "git -c user.name=t -c user.email=t@example.com commit -q --amend --no-edit --reset-author" && echo v4 > f && G commit -qam four && G push -q -f origin main )
zb_sync_source "$T/pi" >/dev/null 2>&1; check "rewritten history" "$(cat "$T/pi/f")" v4
check "same commit as GitHub" "$(G -C "$T/pi" rev-parse HEAD)" "$(G -C "$T/origin.git" rev-parse main)"

# 3. rewritten again but the user edited a tracked file: must not be destroyed
( cd "$T/work" && G commit -q --amend -m "four (reworded)" && G push -q -f origin main )
echo mine > "$T/pi/f"
zb_sync_source "$T/pi" >/dev/null 2>&1; rc=$?
check "local edit kept" "$(cat "$T/pi/f")" mine
check "reports failure" "$rc" 1
# 4. git runs as root during an update: the folder must stay owned by its user (needs root; skipped otherwise)
if [ "$(id -u)" -eq 0 ]; then
  ( cd "$T/work" && echo v5 > f && G commit -qam five && G push -q -f origin main )
  git -C "$T/pi" checkout -q . && chown -R 1234:1234 "$T/pi"
  zb_sync_source "$T/pi" >/dev/null 2>&1
  check "folder ownership kept" "$(stat -c '%u:%g' "$T/pi" "$T/pi/.git/FETCH_HEAD" "$T/pi/f" | sort -u)" "1234:1234"
else
  echo "skip ownership test (not root)"
fi

# 5. updating components one by one: names are checked before anything is downloaded or changed
res=$(zb_update --only nonsense 2>&1); rc=$?
check "unknown component refused" "$rc:$(printf '%s' "$res" | grep -c 'Unknown component')" "1:1"
is_flightinfo() { return 1; }
res=$(zb_update --only flightinfo 2>&1); rc=$?
check "not-installed component refused" "$rc:$(printf '%s' "$res" | grep -c 'not installed')" "1:1"
check "list always offers ZenithBoard itself" "$(zb_update_list | grep -c '^  zenithboard ')" "1"
check "every component has a label" "$(for c in $ZB_COMPONENTS; do zb_component_label "$c"; done | grep -c .)" "$(echo $ZB_COMPONENTS | wc -w)"
# ---- every unit file the Pi has is refreshed from the repository, whatever component is being updated;
#      one it does not have is not installed, and one already identical is left alone
ud="$T/units"; mkdir -p "$ud"
printf '[Service]\nExecStart=/old\n' > "$ud/zenithboard-data-refresh.service"      # the unit from before the sandboxes
cp systemd/zenithboard-flightinfo.service "$ud/"                                    # already current
old_mtime=$(stat -c %Y "$ud/zenithboard-flightinfo.service"); sleep 1
mkdir -p "$T/bin"; printf '#!/bin/bash\necho "$*" >> "%s/systemctl.log"\n' "$T" > "$T/bin/systemctl"; chmod +x "$T/bin/systemctl"
PATH="$T/bin:$PATH" ZB_SYSTEMD_DIR="$ud" ZB_HOME="$PWD" zb_refresh_units
check "refresh: the old unit is replaced by the repository's" "$(cmp -s systemd/zenithboard-data-refresh.service "$ud/zenithboard-data-refresh.service" && echo same)" "same"
check "refresh: a unit the Pi does not have is not installed" "$([ -e "$ud/zenithboard-netwatch.service" ] && echo yes || echo no)" "no"
check "refresh: an identical unit is not rewritten" "$(stat -c %Y "$ud/zenithboard-flightinfo.service")" "$old_mtime"
check "refresh: systemd is told once" "$(grep -c daemon-reload "$T/systemctl.log")" "1"
# ---- 0.23.0: the dark blue is gone. A wall or a preset still set to it is not changed: the update names it, with
#      the command; nothing is said to a Pi that never chose it
cfg_set THEME blue; cfg_set PRESET_TV "theme=blue mode=flap"
out=$(zb_retired_colours 2>&1)
check "retired blue: the wall's colour named, with the command" "$(printf '%s' "$out" | grep -c 'taken out in 0.23.0.*zenithboard color turquoise')" "1"
check "retired blue: the preset named"            "$(printf '%s' "$out" | grep -c 'preset tv sets theme=blue')" "1"
check "retired blue: the settings themselves kept" "$(cfg_get THEME):$(cfg_get PRESET_TV)" "blue:theme=blue mode=flap"
# the command printed for the preset is run as given: it is accepted and keeps the preset's other settings
cmd=$(printf '%s\n' "$out" | sed -n -E 's/.*sudo zenithboard preset add (.*)$/\1/p')
# shellcheck disable=SC2086  # the words of the printed command, as a shell would split them
( . "$HERE/lib/settings.sh"; preset_add $cmd ) >/dev/null 2>&1
check "retired blue: the preset command works as printed" "$?:$(cfg_get PRESET_TV)" "0:theme=turquoise mode=flap"
cfg_set PRESET_TV "mode=flap theme=blue radius=5 theme=blue"       # written twice by a pre-0.23.0 preset add
check "retired blue: every theme=blue replaced, wherever it stands" "$(zb_retired_colours 2>&1 | sed -n -E 's/.*preset add (.*)$/\1/p')" "tv mode=flap theme=turquoise radius=5 theme=turquoise"
cfg_set THEME green; cfg_del PRESET_TV
check "retired blue: silent otherwise"            "$(zb_retired_colours 2>&1)" ""
# ---- the wall is asked what it is actually running, and restarted when it is not the installed version.
#      Seen on a real Pi: the menu said 0.17.2 while the gear panel said 0.17.1, because that update had deployed
#      the new files without passing through the FlightInfo step, which is what restarts the server process.
wall_stub() {            # $1 = the version the fake wall answers; empty = it does not answer at all
  { echo '#!/bin/bash'
    if [ -z "$1" ]; then echo 'exit 7'; else echo "printf '{\"version\":\"$1\"}'"; fi
  } > "$T/bin/curl"
  chmod +x "$T/bin/curl"
}
{ echo '#!/bin/bash'
  echo "echo \"\$*\" >> $T/restart.log"
  # restart_flightinfo asks first whether the unit exists, so the stub has to answer that like systemd does
  echo 'case "${1:-}" in list-unit-files) echo "$2 enabled";; esac'
  echo 'exit 0'
} > "$T/bin/systemctl"; chmod +x "$T/bin/systemctl"
is_flightinfo() { return 0; }                      # pretend the wall is installed

wall_stub "$ZB_VERSION"; : > "$T/restart.log"
PATH="$T/bin:$PATH" zb_wall_check > "$T/out.txt" 2>&1
check "wall: already on the installed version, nothing restarted" "$(grep -c restart "$T/restart.log")" "0"
check "wall: it says which version is running" "$(grep -c "Wall: running $ZB_VERSION" "$T/out.txt")" "1"

wall_stub "0.0.1"; : > "$T/restart.log"            # the process is older than the files on disk
PATH="$T/bin:$PATH" zb_wall_check > "$T/out.txt" 2>&1
check "wall: an older wall is restarted" "$(grep -c "restart zenithboard-flightinfo" "$T/restart.log")" "1"
check "wall: and the reason is printed" "$(grep -c "still running 0.0.1" "$T/out.txt")" "1"
check "wall: one that stays behind is reported, not hidden" "$(grep -c "systemctl restart zenithboard-flightinfo" "$T/out.txt")" "1"

wall_stub ""; : > "$T/restart.log"                 # the wall does not answer at all
PATH="$T/bin:$PATH" zb_wall_check > "$T/out.txt" 2>&1
check "wall: no answer is a warning, never a restart loop" "$(grep -c restart "$T/restart.log")" "0"
check "wall: the warning points at the logs" "$(grep -c "logs flightinfo" "$T/out.txt")" "1"

is_flightinfo() { return 1; }                      # no wall installed: the check stays out of the way
: > "$T/restart.log"
PATH="$T/bin:$PATH" zb_wall_check > "$T/out.txt" 2>&1
check "wall: none installed, nothing done" "$(cat "$T/restart.log")$(cat "$T/out.txt")" ""

# ---- 0.53.7: an update whose code pull failed does not end "Update finished" with exit 0
mkdir -p "$T/home/bin" "$T/badsrc"
G init -q -b main "$T/badsrc"; printf 'exit 0\n' > "$T/badsrc/install.sh"; echo "$T/badsrc" > "$T/home/.source"
printf '#!/bin/bash\necho "flag=${ZB_CODE_NOT_UPDATED:-none}"\n' > "$T/home/bin/zenithboard"; chmod +x "$T/home/bin/zenithboard"
res=$(ZB_HOME="$T/home" zb_update 2>&1)
check "a failed code pull is carried to the end of the update" "$(printf '%s' "$res" | grep -c "flag=$ZB_VERSION")" "1"
res=$(ZB_CODE_NOT_UPDATED=0.1.0 zb_update_verdict 2>&1); rc=$?
check "verdict: code not updated says so and exits 1" "$rc:$(printf '%s' "$res" | grep -c 'Update NOT complete.*still version 0.1.0'):$(printf '%s' "$res" | grep -c 'Update finished')" "1:1:0"
res=$(unset ZB_CODE_NOT_UPDATED; zb_update_verdict 2>&1); rc=$?
check "verdict: code updated says finished and exits 0" "$rc:$(printf '%s' "$res" | grep -c 'Update finished')" "0:1"

exit $fail
