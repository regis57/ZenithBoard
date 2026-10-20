# SPDX-License-Identifier: GPL-3.0-or-later
# shellcheck shell=bash
# What an older ZenithBoard may have left on a Pi, and how to take it away (0.30.0).
#
# ACARS (acarsdec on a second dongle, its ingester and SQLite database) and Grafana were part of ZenithBoard until
# 0.29.0. The owner took them out in 0.30.0: on the reference Pi 3B they were never installed, they needed about 900 MB
# more than a 1 GB board has, and the statistics they could have shown are on the wall's own /stats page. A Pi that
# installed them keeps them until its owner says otherwise: an update says what is left and gives the command, as it
# does for a setting it will not change. `sudo zenithboard acars remove` takes it all away, after a typed word.

GRAFANA_PASS_FILE="${ZB_ETC:-/etc/zenithboard}/grafana.pass"
LEGACY_UNITS="zenithboard-acarsdec zenithboard-acars-ingest"

acars_leftovers() {   # prints what is left, one item per line; nothing when the Pi is clean
  local u
  for u in $LEGACY_UNITS; do [ -f "/etc/systemd/system/$u.service" ] && echo "service $u"; done
  [ -x /usr/local/bin/acarsdec ] && echo "program /usr/local/bin/acarsdec"
  ls "$ZB_DATA"/acars.db* >/dev/null 2>&1 && echo "messages $ZB_DATA/acars.db"
  pkg_installed grafana && echo "package grafana"
  [ -f /etc/apt/sources.list.d/grafana.list ] && echo "apt source /etc/apt/sources.list.d/grafana.list"
  [ -f "$GRAFANA_PASS_FILE" ] && echo "password $GRAFANA_PASS_FILE"
  return 0
}

acars_notice() {      # one line for update and status, or nothing
  [ -n "$(acars_leftovers)" ] || return 0
  echo "ACARS / Grafana from an older ZenithBoard are still on this Pi (no longer part of ZenithBoard). Remove them: sudo zenithboard acars remove"
}

acars_remove() {      # acars_remove [--yes]: everything acars_leftovers lists, and the config keys
  local left word
  left=$(acars_leftovers)
  [ -n "$left" ] || { echo "Nothing of ACARS or Grafana is left on this Pi."; return 0; }
  echo "This removes, for good:"; printf '  %s\n' "$left"
  if [ "${1:-}" != --yes ]; then
    read -rp "Type the word  remove  to go on (anything else stops): " word
    [ "$word" = remove ] || { echo "Nothing was removed."; return 1; }
  fi
  local u
  for u in $LEGACY_UNITS; do systemctl disable --now "$u" 2>/dev/null || true; rm -f "/etc/systemd/system/$u.service"; done
  systemctl daemon-reload 2>/dev/null || true
  rm -f /usr/local/bin/acarsdec "$ZB_DATA"/acars.db* "$GRAFANA_PASS_FILE" "$ZB_HOME/bin/run-acarsdec"
  rm -rf "${ZB_HOME:?}/acars"
  if pkg_installed grafana; then
    systemctl disable --now grafana-server 2>/dev/null || true
    apt_remove grafana || warn "Grafana could not be removed: sudo apt-get purge grafana"
  fi
  rm -rf /etc/grafana/provisioning/datasources/zenithboard.yaml /etc/grafana/provisioning/dashboards/zenithboard.yaml /var/lib/grafana/zenithboard-dashboards
  rm -f /etc/apt/sources.list.d/grafana.list /etc/apt/keyrings/grafana.gpg
  for u in ACARS_SDR ACARS_FREQS ACARS_RETENTION_DAYS ACARS_IGNORE_EMPTY ACARS_IGNORE_LABELS ACARS_UDP_PORT ACARS_DB GRAFANA_PASSWORD; do
    cfg_del "$u" 2>/dev/null || true
  done
  echo "ACARS and Grafana are gone. The build tools acarsdec needed (cmake, libcjson-dev...) are left: other software may use them."
}
