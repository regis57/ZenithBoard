# SPDX-License-Identifier: GPL-3.0-or-later
# shellcheck shell=bash
# Menu 3 - ACARS (optional): acarsdec -> UDP JSON -> SQLite (filtered, 7-day rolling) -> Grafana.
# Needs a SECOND SDR dongle tuned around 131 MHz (the ADS-B dongle is busy at 1090 MHz).

build_acarsdec() {
  command -v acarsdec >/dev/null && { log "acarsdec already installed"; return 0; }
  log "Building acarsdec from source (a few minutes on a Pi)"
  apt_install build-essential cmake git pkg-config rtl-sdr librtlsdr-dev libusb-1.0-0-dev libcjson-dev libsndfile1-dev || return 1
  local d; d=$(mktemp -d)
  git clone --depth 1 --branch "$ACARSDEC_REF" "$ACARSDEC_REPO" "$d/acarsdec" || return 1
  ( cd "$d/acarsdec" && mkdir build && cd build && cmake .. -Drtl=ON -DCMAKE_BUILD_TYPE=Release && make -j"$(nproc)" && make install ) || return 1
  rm -rf "$d"
}

install_grafana() {
  if ! is_grafana; then
    log "Installing Grafana"
    apt_install apt-transport-https gnupg curl || return 1
    install -d -m 755 /etc/apt/keyrings
    curl -fsSL https://apt.grafana.com/gpg.key | gpg --dearmor --yes -o /etc/apt/keyrings/grafana.gpg || return 1
    echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" > /etc/apt/sources.list.d/grafana.list
    apt-get update && apt_install grafana || return 1
  fi
  grafana-cli plugins install frser-sqlite-datasource || warn "SQLite plugin install failed; ACARS panels will be empty."
  usermod -aG "$ZB_USER" grafana
  install -d -m 755 /etc/grafana/provisioning/datasources /etc/grafana/provisioning/dashboards /var/lib/grafana/zenithboard-dashboards
  install -m 644 "$ZB_HOME/acars/grafana-datasource.yaml" /etc/grafana/provisioning/datasources/zenithboard.yaml
  install -m 644 "$ZB_HOME/acars/grafana-dashboards.yaml" /etc/grafana/provisioning/dashboards/zenithboard.yaml
  install -m 644 "$ZB_HOME/acars/grafana-dashboard.json" /var/lib/grafana/zenithboard-dashboards/acars.json
  # Make the ACARS dashboard the home page; keep Grafana's own login unless the user opts in below.
  touch /etc/default/grafana-server
  grep -q '^GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=' /etc/default/grafana-server || \
    echo 'GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/var/lib/grafana/zenithboard-dashboards/acars.json' >> /etc/default/grafana-server
  systemctl daemon-reload; systemctl enable grafana-server; systemctl restart grafana-server
}

set_grafana_anonymous() {  # set_grafana_anonymous yes|no
  sed -i '/^GF_AUTH_ANONYMOUS_/d' /etc/default/grafana-server
  if [ "$1" = yes ]; then
    printf 'GF_AUTH_ANONYMOUS_ENABLED=true\nGF_AUTH_ANONYMOUS_ORG_ROLE=Viewer\n' >> /etc/default/grafana-server
  fi
  systemctl restart grafana-server
}

install_acars() {
  log "Installing the ACARS stack"
  ensure_zb_user; deploy_files
  build_acarsdec || return 1
  install -d -o "$ZB_USER" -g "$ZB_USER" -m 2750 "$ZB_DATA"
  usermod -aG plugdev "$ZB_USER" 2>/dev/null || true
  install -m 644 "$ZB_HOME"/systemd/zenithboard-acars-ingest.service "$ZB_HOME"/systemd/zenithboard-acarsdec.service /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable zenithboard-acars-ingest zenithboard-acarsdec
  systemctl restart zenithboard-acars-ingest; sleep 1; systemctl restart zenithboard-acarsdec
  install_grafana || return 1
  systemctl restart zenithboard-acars-ingest   # pick up group membership changes cleanly
  echo "    ACARS dashboard:  http://$(local_ip):3000/   (first login admin / admin - you will be asked to change it)"
}

remove_acars() {
  log "Removing the ACARS stack"
  systemctl disable --now zenithboard-acarsdec zenithboard-acars-ingest 2>/dev/null || true
  rm -f /etc/systemd/system/zenithboard-acarsdec.service /etc/systemd/system/zenithboard-acars-ingest.service
  systemctl daemon-reload
  rm -f /usr/local/bin/acarsdec
  rm -f /etc/grafana/provisioning/datasources/zenithboard.yaml /etc/grafana/provisioning/dashboards/zenithboard.yaml
  rm -rf /var/lib/grafana/zenithboard-dashboards
  if wt_yesno "Also delete the stored ACARS messages ($ZB_DATA/acars.db)?" 8; then rm -f "$ZB_DATA"/acars.db*; fi
  if is_grafana && wt_yesno "Also uninstall Grafana completely (dashboards, users, settings)?" 8; then
    systemctl disable --now grafana-server 2>/dev/null || true; apt_remove grafana
  else
    is_grafana && systemctl restart grafana-server
  fi
}

acars_menu() {
  local choice
  while true; do
    if is_acars; then
      choice=$(wt_menu "ACARS is INSTALLED.\nDashboard: http://$(local_ip):3000/\nDongle: '$(cfg_get ACARS_SDR)'  Frequencies: $(cfg_get ACARS_FREQS)\nRetention: $(cfg_get ACARS_RETENTION_DAYS) days" \
        freqs "Change dongle / frequencies" anon "Grafana: allow anonymous viewing on the LAN" update "Update / reinstall" remove "Remove ACARS" back "Back") || return 0
    else
      choice=$(wt_menu "ACARS is not installed.\nOptional: collects ACARS aircraft messages (131 MHz) into Grafana, filtered and\nrolled every 7 days. REQUIRES a 2nd SDR dongle." \
        install "Install ACARS + Grafana" back "Back") || return 0
    fi
    case "$choice" in
      install|update)
        ask_acars_settings || continue
        clear; install_acars; read -rp "Press Enter to continue..." _ ;;
      freqs) ask_acars_settings && { systemctl restart zenithboard-acarsdec; wt_msg "Applied." 8; } ;;
      anon)
        if wt_yesno "Let anyone on your home network VIEW the dashboard without logging in?\n(They can not change anything. Do not expose port 3000 to the internet.)" 10
        then set_grafana_anonymous yes; else set_grafana_anonymous no; fi ;;
      remove) wt_yesno "Remove ACARS?" 8 && { clear; remove_acars; } ;;
      *) return 0 ;;
    esac
  done
}

ask_acars_settings() {
  local dongles dev f
  dongles=$(lsusb 2>/dev/null | grep -ci -E '0bda:(2832|2838)|rtl28|rtl-sdr') || true
  wt_msg "ACARS needs its own dongle: the ADS-B dongle can not listen at 131 MHz.\n\nRTL-SDR dongles detected: ${dongles:-0}\n\nGive each dongle a unique serial number first (see docs/HARDWARE.md), e.g.:\n  rtl_eeprom -d 0 -s 00000131\nThen enter the ACARS dongle's serial (or its index, e.g. 1) on the next screen." 18 || return 1
  dev=$(wt_input "ACARS dongle serial number (or index)." "$(cfg_get ACARS_SDR)") || return 1
  [ -n "$dev" ] || { wt_msg "A dongle serial or index is required." 8; return 1; }
  if [ "$dev" = "$(cfg_get ADSB_SDR)" ]; then wt_msg "That is the ADS-B dongle. Pick a different one." 8; return 1; fi
  f=$(wt_input "ACARS frequencies in MHz (space separated, max 8).\nEurope default: 131.525 131.725 131.825\nUSA: 131.550 130.025 129.125" "$(cfg_get ACARS_FREQS)") || return 1
  cfg_set ACARS_SDR "$dev"; cfg_set ACARS_FREQS "$f"
}
