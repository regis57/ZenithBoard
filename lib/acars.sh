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

# ------------------------------------------------------------------ the Grafana admin password
# Grafana ships with admin / admin, and until somebody logs in and changes it, that is what anyone on the network
# can log in with. So ZenithBoard sets one itself: generated, stored root-only in $ZB_ETC/grafana.pass, shown by
# `zenithboard acars password`. Nothing is sent anywhere; the file is the only copy. `password set` lets you choose
# your own, `password new` draws another. Checked at install, at every update, and by `zenithboard security`.
GRAFANA_PASS_FILE="${ZB_ETC:-/etc/zenithboard}/grafana.pass"
GRAFANA_URL="${ZB_GRAFANA_URL:-http://127.0.0.1:3000}"

grafana_default_password_works() {   # 0 when admin/admin still logs in (the hole), 1 when it does not or Grafana is not up
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 -u admin:admin "$GRAFANA_URL/api/org" 2>/dev/null) || return 1
  [ "$code" = 200 ]
}
grafana_new_password() { tr -dc 'A-HJ-NP-Za-kmnp-z2-9' < /dev/urandom 2>/dev/null | head -c 20; }   # no 0/O/1/l: it will be typed from a screen
grafana_apply_password() {   # grafana_apply_password PASSWORD -> sets it in Grafana and keeps it root-only
  local pw="$1" old
  [ ${#pw} -ge 8 ] || { echo "The Grafana password must be at least 8 characters."; return 1; }
  # grafana-cli writes Grafana's own sqlite database: the server is stopped around it, and it runs as the grafana
  # user so nothing under /var/lib/grafana ends up owned by root
  systemctl stop grafana-server 2>/dev/null || true
  if ! runuser -u grafana -- grafana-cli admin reset-admin-password "$pw" >/dev/null 2>&1; then
    systemctl start grafana-server 2>/dev/null || true; echo "grafana-cli could not set the password."; return 1
  fi
  old=$(umask); umask 077
  install -d -m 755 "$(dirname "$GRAFANA_PASS_FILE")"
  printf '%s\n' "$pw" > "$GRAFANA_PASS_FILE.new" && mv -f "$GRAFANA_PASS_FILE.new" "$GRAFANA_PASS_FILE"
  umask "$old"; chmod 600 "$GRAFANA_PASS_FILE"
  systemctl start grafana-server 2>/dev/null || true
}
grafana_secure_password() {   # called at install and update: closes admin/admin if it is still open, says what it did
  is_grafana || return 0
  if grafana_default_password_works; then
    local pw; pw=$(grafana_new_password)
    if grafana_apply_password "$pw"; then
      echo "Grafana still accepted admin / admin, so a password was set. See it with: sudo zenithboard acars password"
    else
      echo "Grafana still accepts admin / admin and the password could not be changed: change it in Grafana itself (http://$(local_ip):3000/)."; return 1
    fi
  fi
}
grafana_password_cmd() {   # zenithboard acars password [new|set]
  is_grafana || { echo "Grafana is not installed (ACARS is optional)."; return 1; }
  case "${1:-show}" in
    show)
      if [ -f "$GRAFANA_PASS_FILE" ]; then echo "Grafana login: admin / $(cat "$GRAFANA_PASS_FILE")   at http://$(local_ip):3000/"
      elif grafana_default_password_works; then echo "Grafana still uses admin / admin. Close that with: sudo zenithboard acars password new"; return 1
      else echo "Grafana's password was changed in Grafana itself; ZenithBoard does not know it. To set one it knows: sudo zenithboard acars password new"; return 1; fi ;;
    new)
      local pw; pw=$(grafana_new_password); grafana_apply_password "$pw" || return 1
      echo "Grafana login: admin / $pw   (kept in $GRAFANA_PASS_FILE, root only)" ;;
    set)
      local pw; read -rsp "New Grafana admin password (8 characters or more): " pw; echo
      grafana_apply_password "$pw" || return 1
      echo "Grafana password set and kept in $GRAFANA_PASS_FILE (root only)." ;;
    *) echo "Usage: zenithboard acars password [new|set]"; return 1 ;;
  esac
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
  build_acarsdec || return 1                          # ensure_zb_user already made $ZB_DATA with the right mode
  usermod -aG plugdev "$ZB_USER" 2>/dev/null || true
  install -m 644 "$ZB_HOME"/systemd/zenithboard-acars-ingest.service "$ZB_HOME"/systemd/zenithboard-acarsdec.service /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable zenithboard-acars-ingest zenithboard-acarsdec
  systemctl restart zenithboard-acars-ingest; sleep 1; systemctl restart zenithboard-acarsdec
  install_grafana || return 1
  systemctl restart zenithboard-acars-ingest   # pick up group membership changes cleanly
  sleep 3; grafana_secure_password || true
  echo "    ACARS dashboard:  http://$(local_ip):3000/   login: admin, password: sudo zenithboard acars password"
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
  if ! is_acars && { is_low_mem || is_old_pi; }; then
    wt_yesno "ACARS + Grafana need roughly 900 MB of RAM on top of ADS-B.\n\nThis board: $(pi_model)\nMemory: $(mem_total_mb) MB total.\n\nIt may run slowly or crash. A Pi 4 with 2 GB or more is recommended.\n\nContinue anyway?" 16 || return 0
  fi
  while true; do
    if is_acars; then
      choice=$(wt_menu "ACARS is INSTALLED.\nDashboard: http://$(local_ip):3000/\nDongle: '$(cfg_get ACARS_SDR)'  Frequencies: $(cfg_get ACARS_FREQS)\nRetention: $(cfg_get ACARS_RETENTION_DAYS) days" \
        freqs "Change dongle / frequencies" anon "Grafana: allow anonymous viewing on the LAN" update "Update / reinstall" remove "Remove ACARS" back "Return to the previous menu") || return 0
    else
      choice=$(wt_menu "ACARS is not installed.\nOptional: collects ACARS aircraft messages (131 MHz) into Grafana, filtered and\nrolled every 7 days. REQUIRES a 2nd SDR dongle." \
        install "Install ACARS + Grafana" back "Return to the previous menu") || return 0
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
