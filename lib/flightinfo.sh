# SPDX-License-Identifier: GPL-3.0-or-later
# shellcheck shell=bash
# Menu 2 - FlightInfo: the dot-matrix wall for an old tablet.

# Monthly aircraft-type data refresh (model names for the silhouettes). The timer follows AUTO_DATA_REFRESH.
data_refresh_apply() {
  if [ "$(cfg_get AUTO_DATA_REFRESH 1)" = 1 ]; then
    install -m 644 "$ZB_HOME/systemd/zenithboard-data-refresh.service" "$ZB_HOME/systemd/zenithboard-data-refresh.timer" "${ZB_UNIT_DIR}"/
    systemctl daemon-reload; systemctl enable --now zenithboard-data-refresh.timer >/dev/null 2>&1 || warn "could not enable the monthly refresh timer"
  else
    systemctl disable --now zenithboard-data-refresh.timer >/dev/null 2>&1 || true
  fi
}

data_refresh_now() {
  install -d -m 755 "$ZB_DATA/data"
  python3 "$ZB_HOME/tools/update_types.py" --out "$ZB_DATA/data/types.json"
}

# Copy the project (this clone) to /opt/zenithboard so the services do not depend on where it was cloned.
deploy_files() {
  local src; src="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  if [ "$src" != "$ZB_HOME" ]; then
    install -d -m 755 "$ZB_HOME"
    # ACARS left ZenithBoard in 0.30.0 and its files are no longer shipped. A Pi still running it keeps the
    # ingester (acars/) and acarsdec's launcher (bin/run-acarsdec) its services start, until `acars remove`:
    # an update never stops a service its owner kept (0.30.1)
    local keep=""
    if [ -f "${ZB_UNIT_DIR}"/zenithboard-acars-ingest.service ] || [ -f "${ZB_UNIT_DIR}"/zenithboard-acarsdec.service ]; then
      keep=$(mktemp -d)
      [ -d "$ZB_HOME/acars" ] && cp -a "$ZB_HOME/acars" "$keep/"
      [ -f "$ZB_HOME/bin/run-acarsdec" ] && cp -a "$ZB_HOME/bin/run-acarsdec" "$keep/"
    fi
    rm -rf "${ZB_HOME:?}/flightinfo" "${ZB_HOME:?}/acars" "${ZB_HOME:?}/lib" "${ZB_HOME:?}/bin" "${ZB_HOME:?}/systemd" "${ZB_HOME:?}/tools"
    # the audit of 22-23 October 2026: an interrupted copy (a full card) left /opt/zenithboard without its files and
    # nothing said so
    cp -r "$src/flightinfo" "$src/lib" "$src/bin" "$src/systemd" "$src/tools" "$src/install.sh" "$src/LICENSE" "$ZB_HOME/" || {
      err "Copying ZenithBoard's files from $src to $ZB_HOME failed (a full card? zenithboard health says): ZenithBoard is incomplete there."
      err "Once the cause is fixed:  sudo bash $src/install.sh --deploy"
      return 1; }
    if [ -n "$keep" ]; then
      [ -d "$keep/acars" ] && cp -a "$keep/acars" "$ZB_HOME/"
      [ -f "$keep/run-acarsdec" ] && cp -a "$keep/run-acarsdec" "$ZB_HOME/bin/"
      rm -rf "$keep"
    fi
    printf '%s\n' "$src" > "$ZB_HOME/.source"      # where to `git pull` from when updating
  fi
  chmod +x "$ZB_HOME/install.sh" "$ZB_HOME"/bin/*
  ln -sf "$ZB_HOME/bin/zenithboard" "$ZB_BIN_DIR/zenithboard"
  # 0.99.11 (review B3): every install and update puts the data folder's owners right (root's, the service's own
  # subfolders), the wall installed or not: a Pi that feeds only can have stats/ and the trust folder too
  [ ! -d "$ZB_DATA" ] || ensure_zb_user
}

install_flightinfo() {
  log "Installing FlightInfo"
  apt_install python3 || return 1
  ensure_zb_user; deploy_files
  install -m 644 "$ZB_HOME/systemd/zenithboard-flightinfo.service" "${ZB_UNIT_DIR}"/
  systemctl daemon-reload
  systemctl enable zenithboard-flightinfo; systemctl restart zenithboard-flightinfo
  data_refresh_apply
  [ -f "$ZB_DATA/data/types.json" ] || [ "$(cfg_get AUTO_DATA_REFRESH 1)" != 1 ] || data_refresh_now || warn "Aircraft model list not downloaded (no internet?). The wall works without it; retry: sudo zenithboard data update"
  echo "    Open on your tablet:  http://$(local_ip):$(cfg_get PORT 8080)/"
}

remove_flightinfo() {
  log "Removing FlightInfo"
  systemctl disable --now zenithboard-flightinfo 2>/dev/null || true
  systemctl disable --now zenithboard-data-refresh.timer 2>/dev/null || true
  rm -f "${ZB_UNIT_DIR}"/zenithboard-flightinfo.service "${ZB_UNIT_DIR}"/zenithboard-data-refresh.service "${ZB_UNIT_DIR}"/zenithboard-data-refresh.timer
  systemctl daemon-reload
}

change_radius() {
  local r; r=$(pick_radius) || return 0
  [ -n "$r" ] && cfg_set RADIUS "$r" && restart_flightinfo
}
