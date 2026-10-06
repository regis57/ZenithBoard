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

logs_clean() {  # logs_clean [DAYS|all]   default: keep the last 7 days
  local what="${1:-7}"
  if [ "$what" = all ]; then
    journalctl --rotate >/dev/null 2>&1 || true
    journalctl --vacuum-time=1s 2>&1 | tail -1
  elif [[ "$what" =~ ^[0-9]+$ ]] && [ "$what" -ge 1 ]; then
    journalctl --vacuum-time="${what}d" 2>&1 | tail -1
  else
    err "Usage: zenithboard logs clean [DAYS|all]"; return 1
  fi
  journalctl --disk-usage
}

logs_usage() {
  journalctl --disk-usage
  local mb; mb=$(logs_limit_mb)
  echo "Size limit set by ZenithBoard: ${mb:+${mb} MB}${mb:-none (system default: up to 10% of the disk, at most 4 GB)}"
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
    c=$(wt_menu "Logs (optional housekeeping)\n\n$(journalctl --disk-usage 2>/dev/null)\nSize limit set here: ${mb:+${mb} MB}${mb:-none (system default)}" \
      review "Review: size, limit, recent warnings" limit "Size: set a maximum (MB)" clean7 "Clean: keep the last 7 days" cleanall "Clean: delete everything" default "Size: back to the system default" back "Back") || return 0
    case "$c" in
      review) clear; logs_review; read -rp "Press Enter to continue..." _ ;;
      limit)
        v=$(wt_input "Maximum size of ALL system logs in MB ($LOG_LIMIT_MIN_MB-$LOG_LIMIT_MAX_MB).\nOlder entries are dropped automatically. 50 is plenty on a small SD card." "${mb:-50}") || continue
        clear; logs_set_limit "$v" || true; read -rp "Press Enter to continue..." _ ;;
      clean7) clear; logs_clean 7; read -rp "Press Enter to continue..." _ ;;
      cleanall) wt_yesno "Delete ALL system logs now?\n\nThis only removes old messages; nothing stops working." 10 && { clear; logs_clean all; read -rp "Press Enter to continue..." _; } ;;
      default) clear; logs_set_limit default; read -rp "Press Enter to continue..." _ ;;
      *) return 0 ;;
    esac
  done
}
