# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Optional log housekeeping. Every ZenithBoard service writes to the systemd journal, which is shared with the whole
# system and already has a built-in ceiling; this lets you see how much it uses, lower the ceiling (useful on a small
# SD card) and clean it now. Nothing here runs unless you ask for it.

JOURNALD_DIR="${ZB_JOURNALD_DIR:-/etc/systemd/journald.conf.d}"
JOURNALD_CONF="$JOURNALD_DIR/zenithboard.conf"
LOG_LIMIT_MIN_MB=10
LOG_LIMIT_MAX_MB=2000

logs_limit_mb() {   # the ceiling set through ZenithBoard (empty = system default)
  sed -n -E 's/^SystemMaxUse=([0-9]+)M$/\1/p' "$JOURNALD_CONF" 2>/dev/null | head -1
}

logs_restart_journald() { [ "${ZB_SKIP_SERVICES:-}" = 1 ] || systemctl restart systemd-journald; }

logs_set_limit() {  # logs_set_limit MB | default
  local mb="${1:-}"
  if [ "$mb" = default ]; then
    rm -f "$JOURNALD_CONF"; logs_restart_journald
    echo "Log size limit removed: the system default applies again (up to 10% of the disk, at most 4 GB)."
    return 0
  fi
  if ! [[ "$mb" =~ ^[0-9]+$ ]] || [ "$mb" -lt "$LOG_LIMIT_MIN_MB" ] || [ "$mb" -gt "$LOG_LIMIT_MAX_MB" ]; then
    err "The limit must be a whole number of MB between $LOG_LIMIT_MIN_MB and $LOG_LIMIT_MAX_MB."; return 1
  fi
  mkdir -p "$JOURNALD_DIR"
  printf '# Written by ZenithBoard (zenithboard logs limit). Remove with: zenithboard logs limit default\n[Journal]\nSystemMaxUse=%sM\nRuntimeMaxUse=%sM\n' "$mb" "$mb" > "$JOURNALD_CONF"
  logs_restart_journald
  echo "Logs are now limited to ${mb} MB (older entries are dropped automatically)."
}

logs_clean() {  # logs_clean [all]   deletes EVERY system log message now (nothing is kept)
  case "${1:-all}" in
    all) journalctl --rotate >/dev/null 2>&1 || true; journalctl --vacuum-time=1s 2>&1 | tail -1 ;;
    *) err "Usage: zenithboard logs clean      (deletes all logs; for a rolling 7-day clean-up use: zenithboard logs auto on)"; return 1 ;;
  esac
  journalctl --disk-usage
}

# Automatic cleaning (opt-in): once a day a systemd timer removes log messages older than 7 days, so the last 7 days are
# always there for troubleshooting and the rest never piles up. Off until you turn it on.
LOGS_UNIT=zenithboard-logs-clean
logs_auto_run() { journalctl --vacuum-time=7d >/dev/null 2>&1; }
logs_auto_on() {
  cfg_set LOG_AUTOCLEAN 1
  [ -f "$ZB_HOME/systemd/$LOGS_UNIT.service" ] || return 0
  install -m 644 "$ZB_HOME/systemd/$LOGS_UNIT.service" "$ZB_HOME/systemd/$LOGS_UNIT.timer" /etc/systemd/system/
  systemctl daemon-reload; systemctl enable --now "$LOGS_UNIT.timer" >/dev/null 2>&1 || true
}
logs_auto_off() {
  cfg_set LOG_AUTOCLEAN 0
  systemctl disable --now "$LOGS_UNIT.timer" >/dev/null 2>&1 || true
  rm -f "/etc/systemd/system/$LOGS_UNIT.service" "/etc/systemd/system/$LOGS_UNIT.timer"; systemctl daemon-reload 2>/dev/null || true
}
logs_auto_state() { [ "$(cfg_get LOG_AUTOCLEAN 0)" = 1 ] && echo "ON (every day, keeps the last 7 days)" || echo "OFF"; }

logs_usage() {
  journalctl --disk-usage
  local mb; mb=$(logs_limit_mb)
  echo "Size limit set by ZenithBoard: ${mb:+${mb} MB}${mb:-none (system default: up to 10% of the disk, at most 4 GB)}"
  echo "Automatic cleaning: $(logs_auto_state)"
}

logs_review() {     # what a user wants to look at: size, limit, and recent warnings of our services
  logs_usage
  echo; echo "Recent warnings and errors (ZenithBoard wall, decoder, feeders):"
  local units=(-u zenithboard-flightinfo -u readsb -u dump1090-fa -u dump978-fa -u adsbexchange-feed -u piaware -u fr24feed)
  journalctl -p warning -n 25 --no-pager "${units[@]}" 2>/dev/null || true
}

logs_menu() {
  local c mb v
  while true; do
    mb=$(logs_limit_mb)
    c=$(wt_menu "Logs (optional housekeeping)\n\n$(journalctl --disk-usage 2>/dev/null)\nSize limit: ${mb:+${mb} MB}${mb:-none (system default)}\nAutomatic cleaning: $(logs_auto_state)" \
      review "Review: size, limit, recent warnings" \
      auto "Automatic cleaning every day, keeps 7 days: $(logs_auto_state | cut -d' ' -f1)" \
      limit "Size: set a maximum (MB)" \
      default "Size: back to the system default" \
      cleanall "Delete ALL logs now" \
      back "Back") || return 0
    case "$c" in
      review) clear; logs_review; read -rp "Press Enter to continue..." _ ;;
      auto)
        if [ "$(cfg_get LOG_AUTOCLEAN 0)" = 1 ]; then
          wt_yesno "Automatic cleaning is ON: every day, log messages older than 7 days are removed.\n\nTurn it OFF?" 10 && logs_auto_off
        else
          wt_yesno "Turn on automatic cleaning?\n\nOnce a day, log messages older than 7 days are removed. The last 7 days always stay available for troubleshooting. Nothing stops working." 12 && logs_auto_on
        fi ;;
      limit)
        v=$(wt_input "Maximum size of ALL system logs in MB ($LOG_LIMIT_MIN_MB-$LOG_LIMIT_MAX_MB).\nOlder entries are dropped automatically. 50 is plenty on a small SD card." "${mb:-50}") || continue
        clear; logs_set_limit "$v" || true; read -rp "Press Enter to continue..." _ ;;
      default) clear; logs_set_limit default; read -rp "Press Enter to continue..." _ ;;
      cleanall) wt_yesno "Delete ALL system logs now, including the last 7 days?\n\nThis only removes old messages; nothing stops working." 10 && { clear; logs_clean all; read -rp "Press Enter to continue..." _; } ;;
      *) return 0 ;;
    esac
  done
}
