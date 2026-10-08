# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Reliability: what to do when a Pi freezes or loses its network in the night, and how to find out why afterwards.
# Everything here is opt-in and off until you turn it on:
#   hardware watchdog  the Pi's own chip reboots it when it freezes completely
#   network watchdog   every 2 minutes the Pi checks it can reach its router; restarts the network, then reboots
#   keep logs          the system log survives a restart (capped at 50 MB), so the cause can be read afterwards
#   health check       one screen: power, temperature, memory, disk, how the previous boot ended, problems in the logs
# Paths can be redirected for tests: ZB_SYSTEMD_CONF_DIR, ZB_JOURNALD_DIR, ZB_RUN_DIR, ZB_VAR_DIR, ZB_JOURNAL_DIR,
# ZB_WATCHDOG_DEV, ZB_UPTIME_FILE.

RELI_SYSTEMD_DIR="${ZB_SYSTEMD_CONF_DIR:-/etc/systemd/system.conf.d}"
RELI_WATCHDOG_CONF="$RELI_SYSTEMD_DIR/watchdog.conf"
RELI_JOURNAL_CONF="${ZB_JOURNALD_DIR:-/etc/systemd/journald.conf.d}/50-persistent.conf"
RELI_JOURNAL_DIR="${ZB_JOURNAL_DIR:-/var/log/journal}"
RELI_WATCHDOG_DEV="${ZB_WATCHDOG_DEV:-/dev/watchdog}"
NETWATCH_UNIT=zenithboard-netwatch
NETWATCH_FAILS="${ZB_RUN_DIR:-/run}/zenithboard-netwatch.fails"            # in memory: nothing is written to the SD card every 2 minutes
NETWATCH_REBOOTED="${ZB_VAR_DIR:-/var/lib/zenithboard}/netwatch-reboot"    # when the network watchdog last rebooted the Pi (a time, not a log)
NETWATCH_UPTIME_FILE="${ZB_UPTIME_FILE:-/proc/uptime}"
NETWATCH_GRACE_S=600           # not judged during the first 10 minutes after a start (the router may still be starting too)
NETWATCH_RESTART_AT=3          # 3 checks in a row failed (about 6 minutes): restart the network
NETWATCH_REBOOT_AT=6           # 6 in a row (about 12 minutes): reboot
NETWATCH_REBOOT_GAP_S=10800    # but never more than one reboot every 3 hours (no reboot loop when the router is simply off)

# ------------------------------------------------------------------ hardware watchdog
watchdog_state() { [ -f "$RELI_WATCHDOG_CONF" ] && grep -q '^RuntimeWatchdogSec=' "$RELI_WATCHDOG_CONF" && echo on || echo off; }
watchdog_on() {
  if [ ! -e "$RELI_WATCHDOG_DEV" ]; then err "This Pi has no hardware watchdog ($RELI_WATCHDOG_DEV is missing): nothing was changed."; return 1; fi
  mkdir -p "$RELI_SYSTEMD_DIR"
  printf '[Manager]\nRuntimeWatchdogSec=10\nRebootWatchdogSec=2min\n' > "$RELI_WATCHDOG_CONF"
  [ "${ZB_SKIP_SERVICES:-}" = 1 ] || systemctl daemon-reexec
  echo "Hardware watchdog is ON: if the Pi freezes completely, it restarts itself after about 10 seconds."
}
watchdog_off() {
  rm -f "$RELI_WATCHDOG_CONF"
  [ "${ZB_SKIP_SERVICES:-}" = 1 ] || systemctl daemon-reexec
  echo "Hardware watchdog is OFF."
}

# ------------------------------------------------------------------ logs that survive a restart
keeplogs_state() { [ -f "$RELI_JOURNAL_CONF" ] && grep -q '^Storage=persistent' "$RELI_JOURNAL_CONF" && echo on || echo off; }
keeplogs_on() {
  mkdir -p "$RELI_JOURNAL_DIR" "$(dirname "$RELI_JOURNAL_CONF")"
  printf '# Written by ZenithBoard (zenithboard keeplogs). Remove with: zenithboard keeplogs off\n[Journal]\nStorage=persistent\nSystemMaxUse=50M\n' > "$RELI_JOURNAL_CONF"
  if [ "${ZB_SKIP_SERVICES:-}" != 1 ]; then systemctl restart systemd-journald; journalctl --flush 2>/dev/null || true; fi
  echo "Logs are now kept after a restart (at most 50 MB; a size limit set in the Logs menu still applies). After the next restart, 'journalctl --list-boots' shows the earlier boots."
}
keeplogs_off() {
  rm -f "$RELI_JOURNAL_CONF"
  [ "${ZB_SKIP_SERVICES:-}" = 1 ] || systemctl restart systemd-journald
  echo "Logs are kept in memory only again (older saved logs stay on the card until you delete them: zenithboard logs clean)."
}

# ------------------------------------------------------------------ network watchdog
netwatch_state() { [ "$(cfg_get NETWATCH 0)" = 1 ] && echo on || echo off; }
netwatch_install_units() {
  [ -f "$ZB_HOME/systemd/$NETWATCH_UNIT.service" ] || return 0
  install -m 644 "$ZB_HOME/systemd/$NETWATCH_UNIT.service" "$ZB_HOME/systemd/$NETWATCH_UNIT.timer" /etc/systemd/system/
  systemctl daemon-reload; systemctl enable --now "$NETWATCH_UNIT.timer" >/dev/null 2>&1 || true
}
netwatch_remove_units() {
  systemctl disable --now "$NETWATCH_UNIT.timer" >/dev/null 2>&1 || true
  rm -f "/etc/systemd/system/$NETWATCH_UNIT.service" "/etc/systemd/system/$NETWATCH_UNIT.timer"; systemctl daemon-reload 2>/dev/null || true
}
netwatch_on()  { cfg_set NETWATCH 1; netwatch_install_units; echo "Network watchdog is ON: every 2 minutes the Pi checks it can reach your router. After about 6 minutes of failure it restarts the network; after about 12 it restarts the Pi (never more than once every 3 hours)."; }
netwatch_off() { cfg_set NETWATCH 0; netwatch_remove_units; rm -f "$NETWATCH_FAILS"; echo "Network watchdog is OFF."; }

netwatch_gateway() { ip -4 route show default 2>/dev/null | awk '{for(i=1;i<NF;i++) if($i=="via"){print $(i+1); exit}}'; }
netwatch_log()     { logger -t zenithboard-netwatch "$*" 2>/dev/null || true; }

# One check, called by the timer. Never blocks for more than a few seconds and never fails the unit.
netwatch_run() {
  local up gw n now last
  up=$(cut -d. -f1 "$NETWATCH_UPTIME_FILE" 2>/dev/null); up=${up:-0}
  if [ "$up" -lt "$NETWATCH_GRACE_S" ]; then rm -f "$NETWATCH_FAILS"; return 0; fi
  gw=$(netwatch_gateway)
  if [ -n "$gw" ] && ping -c 2 -W 2 -q "$gw" >/dev/null 2>&1; then
    n=$(cat "$NETWATCH_FAILS" 2>/dev/null || echo 0)
    [ "${n:-0}" -gt 0 ] && netwatch_log "router $gw reachable again after $n failed checks"
    rm -f "$NETWATCH_FAILS"; return 0
  fi
  n=$(cat "$NETWATCH_FAILS" 2>/dev/null || echo 0); [[ "$n" =~ ^[0-9]+$ ]] || n=0
  n=$((n + 1)); mkdir -p "$(dirname "$NETWATCH_FAILS")"; echo "$n" > "$NETWATCH_FAILS"
  netwatch_log "router ${gw:-(no default route)} not reachable, failed check $n"
  if [ "$n" -eq "$NETWATCH_RESTART_AT" ]; then
    netwatch_log "restarting the network"
    if systemctl is-active --quiet NetworkManager 2>/dev/null; then systemctl restart NetworkManager || true
    else systemctl restart dhcpcd 2>/dev/null || systemctl restart networking 2>/dev/null || true; fi
  elif [ "$n" -ge "$NETWATCH_REBOOT_AT" ]; then
    now=$(date +%s); last=$(cat "$NETWATCH_REBOOTED" 2>/dev/null || echo 0); [[ "$last" =~ ^[0-9]+$ ]] || last=0
    if [ $((now - last)) -lt "$NETWATCH_REBOOT_GAP_S" ]; then
      netwatch_log "still no network, but the Pi was already restarted by this watchdog less than 3 hours ago: not restarting again"
    else
      mkdir -p "$(dirname "$NETWATCH_REBOOTED")"; echo "$now" > "$NETWATCH_REBOOTED"
      netwatch_log "no network for about $((n * 2)) minutes: restarting the Pi"
      systemctl reboot || true
    fi
  fi
  return 0
}

netwatch_status() {
  echo "Network watchdog: $(netwatch_state)"
  [ "$(netwatch_state)" = on ] || return 0
  local gw n last; gw=$(netwatch_gateway); n=$(cat "$NETWATCH_FAILS" 2>/dev/null || echo 0)
  echo "  Router checked: ${gw:-no default route}    Failed checks in a row: ${n:-0}"
  last=$(cat "$NETWATCH_REBOOTED" 2>/dev/null || true)
  [[ "${last:-}" =~ ^[0-9]+$ ]] && echo "  Last restart done by the watchdog: $(date -d "@$last" '+%Y-%m-%d %H:%M' 2>/dev/null)"
  return 0
}

# ------------------------------------------------------------------ health check
# decode vcgencmd get_throttled (bit 0 under-voltage now, 1 frequency capped, 2 throttled, 3 soft temperature limit;
# bits 16-19 the same "has happened since the start")
health_power() {
  local v hex now ever
  v=$(vcgencmd get_throttled 2>/dev/null | sed -n 's/^throttled=//p')
  [[ "$v" =~ ^0x[0-9a-fA-F]+$ ]] || { echo "Power:        not available on this system"; return 0; }
  hex=$((v)); now=$((hex & 0xF)); ever=$(((hex >> 16) & 0xF))
  if [ "$hex" -eq 0 ]; then echo "Power:        OK (no under-voltage or throttling since the start)"; return 0; fi
  [ $((now & 1)) -ne 0 ] && echo "Power:        UNDER-VOLTAGE RIGHT NOW: use a better power supply and a shorter, thicker cable"
  [ $((ever & 1)) -ne 0 ] && echo "Power:        under-voltage happened since the start ($v): the power supply or cable is too weak"
  [ $(((now | ever) & 6)) -ne 0 ] && echo "Power:        the Pi slowed itself down (frequency capped or throttled): power or heat ($v)"
  [ $(((now | ever) & 8)) -ne 0 ] && echo "Power:        the Pi reached its temperature limit: add airflow or a heat sink ($v)"
  return 0
}

health_check() {
  local t mem swap used boots prev lines
  echo "Model:        $(pi_model 2>/dev/null)"
  echo "Running since: $(uptime -s 2>/dev/null || echo unknown)"
  health_power
  t=$(vcgencmd measure_temp 2>/dev/null | sed -n "s/^temp=\\([0-9]*\\).*/\\1/p")
  if [ -n "$t" ]; then
    if [ "$t" -ge 80 ]; then echo "Temperature:  ${t} C: TOO HOT, the Pi will slow down"; elif [ "$t" -ge 70 ]; then echo "Temperature:  ${t} C: warm"; else echo "Temperature:  ${t} C: OK"; fi
  fi
  mem=$(awk '/^MemAvailable:/{printf "%d", $2/1024}' /proc/meminfo 2>/dev/null)
  swap=$(awk '/^SwapTotal:/{t=$2} /^SwapFree:/{f=$2} END{printf "%d", (t-f)/1024}' /proc/meminfo 2>/dev/null)
  if [ -n "$mem" ]; then
    if [ "$mem" -lt 100 ]; then echo "Memory:       only ${mem} MB free: very low (swap used ${swap:-0} MB)"; else echo "Memory:       ${mem} MB free (swap used ${swap:-0} MB)"; fi
  fi
  used=$(df --output=pcent / 2>/dev/null | tail -1 | tr -dc '0-9')
  if [ -n "$used" ]; then
    if [ "$used" -ge 90 ]; then echo "Card:         ${used}% full: free some space"; else echo "Card:         ${used}% full"; fi
  fi
  echo "Watchdogs:    hardware $(watchdog_state), network $(netwatch_state)"
  echo "Saved logs:   $(keeplogs_state) $( [ "$(keeplogs_state)" = on ] || echo '(logs are lost at every restart: turn it on to find the cause of the next freeze)')"
  boots=$(journalctl --list-boots 2>/dev/null | grep -c . || true)
  if [ "${boots:-0}" -ge 2 ]; then
    prev=$(journalctl -b -1 -n 40 --no-pager 2>/dev/null)
    if grep -qiE 'Reached target.*(Shutdown|Reboot|Power-Off)|systemd-shutdown|Powering off|Rebooting|Journal stopped' <<<"$prev"; then
      echo "Previous boot: ended normally (a clean shutdown or restart)"
    else
      echo "Previous boot: ended ABRUPTLY (a freeze, a crash or a power cut). Its last lines:"
      journalctl -b -1 -n 8 --no-pager 2>/dev/null | sed 's/^/    /'
    fi
  else
    echo "Previous boot: no earlier boot in the logs"
  fi
  echo
  echo "Problems seen in the system logs (this boot and the previous one):"
  lines=$( { journalctl -k -b 0 --no-pager 2>/dev/null; journalctl -k -b -1 --no-pager 2>/dev/null; } | grep -iE 'under-voltage|mmc[0-9: ].*(error|timeout)|ext4.*error|i/o error|out of memory|oom-kill|usb [0-9.-]+: (usb disconnect|reset)|smsc95xx.*(fail|error)|lan78xx.*(fail|error)|nmi watchdog|soft lockup' | tail -8 || true)
  if [ -n "$lines" ]; then sed 's/^/    /' <<<"$lines"; else echo "    nothing alarming"; fi
  return 0
}

# ------------------------------------------------------------------ menu
reliability_menu() {
  local c
  while true; do
    c=$(wt_menu "Reliability: what to do when the Pi freezes or loses its network\n\nHardware watchdog: $(watchdog_state)    Network watchdog: $(netwatch_state)    Saved logs: $(keeplogs_state)\n\nAll off until you turn them on; each can be turned off again." \
      health "Health check: power, temperature, memory, last boot" \
      keeplogs "Saved logs (read the cause after a freeze): $(keeplogs_state)" \
      watchdog "Hardware watchdog (restarts a frozen Pi): $(watchdog_state)" \
      netwatch "Network watchdog (restarts a Pi that lost its network): $(netwatch_state)" \
      back "Return to the previous menu") || return 0
    case "$c" in
      health) clear; health_check; echo; read -rp "Press Enter to continue..." _ ;;
      keeplogs)
        if [ "$(keeplogs_state)" = on ]; then wt_yesno "Saved logs are ON.\n\nTurn them OFF? (after a restart the logs would be lost again)" 10 && { clear; keeplogs_off; read -rp "Press Enter to continue..." _; }
        else wt_yesno "Keep the system logs after a restart?\n\nUp to 50 MB on the card. After a freeze you can read what happened just before it." 11 && { clear; keeplogs_on; read -rp "Press Enter to continue..." _; }; fi ;;
      watchdog)
        if [ "$(watchdog_state)" = on ]; then wt_yesno "The hardware watchdog is ON.\n\nTurn it OFF?" 8 && { clear; watchdog_off; read -rp "Press Enter to continue..." _; }
        else wt_yesno "Turn on the hardware watchdog?\n\nIf the Pi freezes completely, its own chip restarts it after about 10 seconds. It cannot help when the Pi is running but has lost its network (use the network watchdog for that)." 13 && { clear; watchdog_on; read -rp "Press Enter to continue..." _; }; fi ;;
      netwatch)
        if [ "$(netwatch_state)" = on ]; then wt_yesno "The network watchdog is ON.\n\nTurn it OFF?" 8 && { clear; netwatch_off; read -rp "Press Enter to continue..." _; }
        else wt_yesno "Turn on the network watchdog?\n\nEvery 2 minutes the Pi checks that it can reach your router. After about 6 minutes without it, the network is restarted; after about 12 minutes the Pi restarts (never more than once every 3 hours, and not during the first 10 minutes after a start).\n\nIt only looks at your router, so an internet outage alone does not restart anything." 17 && { clear; netwatch_on; read -rp "Press Enter to continue..." _; }; fi ;;
      *) return 0 ;;
    esac
  done
}
