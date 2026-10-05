#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# ZenithBoard installer / uninstaller menu.
#   1 ADSB        decoder (readsb or dump1090-fa) + feeders, ADSB Exchange mandatory, single MLAT
#   2 FlightInfo  dot-matrix wall for an old tablet
#   3 ACARS       optional ACARS -> Grafana (needs a 2nd SDR dongle)
# Re-run it any time: it detects what is installed and lets you add or remove components.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$ROOT/lib/common.sh"
. "$ROOT/lib/adsb.sh"
. "$ROOT/lib/flightinfo.sh"
. "$ROOT/lib/acars.sh"

usage() { echo "Usage: sudo ./install.sh [--uninstall-all] [--version]"; }

preflight() {
  need_root "$@"
  command -v apt-get >/dev/null || die "This installer needs Raspberry Pi OS / Debian (apt)."
  case "$(arch)" in arm64|armhf) ;; *) warn "Architecture $(arch) is not a Raspberry Pi; continuing anyway." ;; esac
  if ! command -v whiptail >/dev/null || ! command -v curl >/dev/null; then
    log "Installing whiptail and curl"; apt-get update -qq && apt_install whiptail curl ca-certificates
  fi
  mkdir -p "$ZB_ETC"; touch "$ZB_CONFIG"; cfg_defaults
}

first_run_wizard() {
  grep -q '^LAT=.' "$ZB_CONFIG" && grep -q '^LON=.' "$ZB_CONFIG" && return 0
  wt_msg "Welcome to ZenithBoard - ADSB Flight Info.\n\nA few questions first:\n  1. Units (metric or imperial)\n  2. Where your antenna is\n  3. The default detection radius\n\nYou can change all of them later:  sudo zenithboard config   (or Settings in this menu)." 16 || exit 0
  settings_units || exit 0
  settings_location || exit 0
  local r; r=$(pick_radius) && cfg_set RADIUS "$r"
}

settings_units() {
  local cur u m i; cur=$(cfg_get UNITS metric); m=OFF; i=OFF; [ "$cur" = imperial ] && i=ON || m=ON
  u=$(wt_radio "Units for the wall and the radius.\n\nmetric   : distance km, speed km/h, altitude m, climb m/s\nimperial : distance miles, speed knots, altitude ft, climb ft/min" \
      metric "Metric (km, km/h, m)" "$m" imperial "Imperial (miles, knots, feet)" "$i") || return 1
  cfg_set UNITS "$u"
}

settings_location() {
  local lat lon alt
  while true; do
    lat=$(wt_input "Antenna LATITUDE in decimal degrees (e.g. 49.246, south is negative)." "$(cfg_get LAT)") || return 1
    valid_lat "$lat" && break; wt_msg "Not a valid latitude (-90..90)." 8
  done
  while true; do
    lon=$(wt_input "Antenna LONGITUDE in decimal degrees (e.g. 6.223, west is negative)." "$(cfg_get LON)") || return 1
    valid_lon "$lon" && break; wt_msg "Not a valid longitude (-180..180)." 8
  done
  alt=$(wt_input "Antenna altitude above sea level in METRES (approximate is fine)." "$(cfg_get ALT_M 0)") || return 1
  is_number "$alt" || alt=0
  cfg_set LAT "$lat"; cfg_set LON "$lon"; cfg_set ALT_M "$alt"
}

settings_menu() {
  local c
  while true; do
    c=$(wt_menu "Settings (applied immediately)\n\nUnits: $(cfg_get UNITS)   Radius: $(cfg_get RADIUS)   Position: $(cfg_get LAT), $(cfg_get LON)\nSeconds per aircraft: $(cfg_get CYCLE_SECONDS)   Photos: $(cfg_get SHOW_PHOTOS)" \
      units "Units: metric / imperial" radius "Detection radius" location "Antenna position" cycle "Seconds per aircraft" photos "Aircraft photos on/off" back "Back") || return 0
    case "$c" in
      units) settings_units && restart_flightinfo ;;
      radius) change_radius ;;
      location)
        if settings_location; then
          apply_location_to_decoder "$(cfg_get LAT)" "$(cfg_get LON)" 2>/dev/null || true
          restart_flightinfo
          wt_msg "Position saved for the decoder and the wall.\n\nADSB Exchange / FlightAware / Flightradar24 keep their own copy: update it there if you moved the antenna permanently." 12
        fi ;;
      cycle) local s; s=$(wt_input "Seconds each aircraft stays on the wall (2-60)." "$(cfg_get CYCLE_SECONDS 6)") && is_number "$s" && cfg_set CYCLE_SECONDS "$s" && restart_flightinfo ;;
      photos) if wt_yesno "Show aircraft photos (Planespotters) on the wall? Needs internet on the Pi." 8; then cfg_set SHOW_PHOTOS 1; else cfg_set SHOW_PHOTOS 0; fi ;;
      *) return 0 ;;
    esac
  done
}

uninstall_all() {
  wt_yesno "UNINSTALL EVERYTHING?\n\nThis removes FlightInfo, ACARS, all feeders and the decoder installed through this menu." 12 || return 0
  clear
  is_acars && remove_acars
  is_flightinfo && remove_flightinfo
  is_planefinder && remove_planefinder
  is_fr24 && remove_fr24
  is_piaware && remove_piaware
  is_adsbx && remove_adsbx
  [ -n "$(installed_decoder)" ] && remove_decoder
  if wt_yesno "Also delete your ZenithBoard settings ($ZB_ETC) and program files ($ZB_HOME)?" 8; then
    rm -rf "$ZB_ETC" "$ZB_HOME" /usr/local/bin/zenithboard
    id "$ZB_USER" >/dev/null 2>&1 && userdel "$ZB_USER" 2>/dev/null
  fi
  log "Everything removed."; exit 0
}

main_menu() {
  local c
  while true; do
    c=$(wt_menu "ZenithBoard $ZB_VERSION   (units: $(cfg_get UNITS), radius: $(cfg_get RADIUS))\n\nPick a step. You can come back any time to add or remove things." \
      1 "ADSB        - decoder + share to ADSB Exchange, FlightAware, FR24..." \
      2 "FlightInfo  - dot-matrix wall for an old tablet" \
      3 "ACARS       - optional ACARS messages in Grafana (2nd dongle)" \
      4 "Settings    - units, radius, antenna position" \
      5 "Status      - what is running" \
      6 "Uninstall everything" \
      0 "Exit") || exit 0
    case "$c" in
      1) adsb_menu ;;
      2) flightinfo_menu ;;
      3) acars_menu ;;
      4) settings_menu ;;
      5) clear; "$ROOT/bin/zenithboard" status; read -rp "Press Enter..." _ ;;
      6) uninstall_all ;;
      *) exit 0 ;;
    esac
  done
}

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
  --version) echo "ZenithBoard $ZB_VERSION"; exit 0 ;;
  --uninstall-all) preflight "$@"; uninstall_all; exit 0 ;;
  "") ;;
  *) usage; exit 1 ;;
esac
preflight "$@"
# the CLI needs the files in place even if only menu 1 is used
deploy_files
first_run_wizard
main_menu
