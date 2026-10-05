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
exit $fail
