# SPDX-License-Identifier: GPL-3.0-or-later
# shellcheck shell=bash
# Menu 2 - FlightInfo: the dot-matrix wall for an old tablet.

ensure_zb_user() {
  id "$ZB_USER" >/dev/null 2>&1 || useradd --system --home-dir "$ZB_DATA" --shell /usr/sbin/nologin "$ZB_USER"
  # 2751: anyone may walk through to data/ (so `zenithboard status` works without sudo) but only the service
  # may list the folder, which keeps the ACARS database out of sight.
  install -d -o "$ZB_USER" -g "$ZB_USER" -m 2751 "$ZB_DATA"
  # the downloaded aircraft-type list is read by the wall server (user zenithboard): world-readable, root-writable
  install -d -m 755 "$ZB_DATA/data"
}

# Monthly aircraft-type data refresh (model names for the silhouettes). The timer follows AUTO_DATA_REFRESH.
data_refresh_apply() {
  if [ "$(cfg_get AUTO_DATA_REFRESH 1)" = 1 ]; then
    install -m 644 "$ZB_HOME/systemd/zenithboard-data-refresh.service" "$ZB_HOME/systemd/zenithboard-data-refresh.timer" /etc/systemd/system/
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
    rm -rf "${ZB_HOME:?}/flightinfo" "${ZB_HOME:?}/acars" "${ZB_HOME:?}/lib" "${ZB_HOME:?}/bin" "${ZB_HOME:?}/systemd" "${ZB_HOME:?}/tools"
    cp -r "$src/flightinfo" "$src/acars" "$src/lib" "$src/bin" "$src/systemd" "$src/tools" "$src/install.sh" "$src/LICENSE" "$ZB_HOME/"
    printf '%s\n' "$src" > "$ZB_HOME/.source"      # where to `git pull` from when updating
  fi
  chmod +x "$ZB_HOME/install.sh" "$ZB_HOME"/bin/*
  ln -sf "$ZB_HOME/bin/zenithboard" /usr/local/bin/zenithboard
}

install_flightinfo() {
  log "Installing FlightInfo"
  apt_install python3 || return 1
  ensure_zb_user; deploy_files
  install -m 644 "$ZB_HOME/systemd/zenithboard-flightinfo.service" /etc/systemd/system/
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
  rm -f /etc/systemd/system/zenithboard-flightinfo.service /etc/systemd/system/zenithboard-data-refresh.service /etc/systemd/system/zenithboard-data-refresh.timer
  systemctl daemon-reload
}

flightinfo_menu() {
  local choice units radius
  while true; do
    units=$(cfg_get UNITS metric); radius=$(cfg_get RADIUS 10)
    if is_flightinfo; then
      choice=$(wt_menu "FlightInfo is INSTALLED.\nWall address:  http://$(local_ip):$(cfg_get PORT 8080)/\nRadius: $radius ($units)" \
        radius "Change the detection radius" update "Update / reinstall files" remove "Remove FlightInfo" back "Return to the previous menu") || return 0
    else
      choice=$(wt_menu "FlightInfo is not installed.\nIt turns an old tablet into a dot-matrix wall showing the aircraft above you." \
        install "Install FlightInfo" back "Return to the previous menu") || return 0
    fi
    case "$choice" in
      install|update) clear; install_flightinfo; read -rp "Press Enter to continue..." _ ;;
      radius) change_radius ;;
      remove) wt_yesno "Remove FlightInfo?" 8 && { clear; remove_flightinfo; } ;;
      *) return 0 ;;
    esac
  done
}

change_radius() {
  local r; r=$(pick_radius) || return 0
  [ -n "$r" ] && cfg_set RADIUS "$r" && restart_flightinfo
}
