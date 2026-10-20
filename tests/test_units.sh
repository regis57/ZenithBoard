#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_units.sh   Every systemd unit is sandboxed, and each one keeps exactly what its job needs.
# The exposure score comes from systemd-analyze itself (offline, on the unit file), so a directive quietly dropped
# from a unit shows up here as a number going up, before it shows up on a Pi.
set -u
cd "$(dirname "$0")/.." || exit 1
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
has() { grep -qE "^$2" "systemd/zenithboard-$1.service"; }
score() { systemd-analyze security --offline=true --no-pager "systemd/zenithboard-$1.service" 2>/dev/null | sed -n 's/.*Overall exposure level for .*: \([0-9.]*\).*/\1/p'; }

# ---- ceilings: what each unit may score, at most. The watchdog and the Wi-Fi unit talk to the network as root
# and keep ping, netlink and D-Bus, so they sit higher than the rest on purpose.
declare -A MAX=( [flightinfo]=1.5 [data-refresh]=4.5
                 [ddns]=2.0 [logs-clean]=1.6 [gain-log]=1.2 [stats]=1.2 [netwatch]=4.5 [wifi]=4.5 [social]=1.5 )
if command -v systemd-analyze >/dev/null 2>&1 && systemd-analyze security --offline=true --no-pager systemd/zenithboard-flightinfo.service >/dev/null 2>&1; then
  for u in "${!MAX[@]}"; do
    s=$(score "$u")
    check "$u: exposure $s <= ${MAX[$u]}" '[ -n "$s" ] && awk -v s="$s" -v m="${MAX[$u]}" "BEGIN{exit !(s<=m)}"'
  done
else
  echo "skip systemd-analyze security not available here: the exposure ceilings are not measured"
fi

# ---- every unit has the basics, whatever its score
for u in flightinfo data-refresh ddns logs-clean gain-log stats netwatch wifi social; do
  check "$u: ProtectSystem=strict"   'has $u "ProtectSystem=strict"'
  check "$u: ProtectHome"            'has $u "ProtectHome=true"'
  check "$u: PrivateTmp"             'has $u "PrivateTmp=true"'
  check "$u: no kernel modules"      'has $u "ProtectKernelModules=true"'
done

# ---- what each one keeps, because its job needs it
check "gain-log runs as the wall user, not root"      'has gain-log "User=zenithboard"'
check "gain-log has no capability at all"             'has gain-log "CapabilityBoundingSet=$"'
check "stats runs as the wall user with no capability"  'has stats "User=zenithboard" && has stats "CapabilityBoundingSet=$"'
check "social runs as the wall user, writes only its own folder, keeps the internet" \
  'has social "User=zenithboard" && has social "ReadWritePaths=/var/lib/zenithboard/social$" && has social "RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX" && has social "RuntimeDirectory=zenithboard/social"'
check "ddns keeps no capability (curl needs none)"    'has ddns "CapabilityBoundingSet=$"'
check "ddns keeps its status folder between runs"     'has ddns "RuntimeDirectoryPreserve=yes"'
check "logs-clean may write only the journal"         'has logs-clean "ReadWritePaths=-/var/log/journal"'
check "netwatch keeps raw sockets for ping"           'grep -q "CapabilityBoundingSet=.*CAP_NET_RAW" systemd/zenithboard-netwatch.service'
check "netwatch may write the wall users folder"      'has netwatch "ReadWritePaths=/var/lib/zenithboard"'
check "netwatch has no system-call filter"            '! has netwatch "SystemCallFilter"'   # a filter that killed ping would leave the Pi unwatched
check "wifi keeps CAP_NET_ADMIN for iw reg set"       'grep -q "CapabilityBoundingSet=.*CAP_NET_ADMIN" systemd/zenithboard-wifi.service'
check "wifi can reach /dev/rfkill"                    'has wifi "DeviceAllow=/dev/rfkill rw" && ! has wifi "PrivateDevices=true"'
check "wifi has no system-call filter"                '! has wifi "SystemCallFilter"'
check "no unit uses StateDirectory (it would chown /var/lib/zenithboard away from the wall user)" '! grep -q "^StateDirectory" systemd/*.service'

# ---- the run-time files now live where the units put them
check "ddns status under /run/zenithboard"            'grep -q "ZB_RUN_DIR:-/run/zenithboard}/zenithboard-ddns.status" lib/ddns.sh'
check "netwatch counter under /run/zenithboard"       'grep -q "ZB_RUN_DIR:-/run/zenithboard}/zenithboard-netwatch.fails" lib/reliability.sh'
check "the gain log timer hands an old root CSV to the wall user" 'grep -q "chown \"\$ZB_USER:\$ZB_USER\" \"\$GAIN_LOG_FILE\"" lib/gain.sh'

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
