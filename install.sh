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
. "$ROOT/lib/logs.sh"
. "$ROOT/lib/uat.sh"
. "$ROOT/lib/wifi.sh"
. "$ROOT/lib/network.sh"
. "$ROOT/lib/ddns.sh"
. "$ROOT/lib/update.sh"

usage() { echo "Usage: sudo ./install.sh [--deploy] [--uninstall-all] [--version]      (to upgrade: sudo zenithboard update)"; }

preflight() {
  need_root "$@"
  command -v apt-get >/dev/null || die "This installer needs Raspberry Pi OS / Debian (apt)."
  case "$(arch)" in arm64|armhf) ;; *) warn "Architecture $(arch) is not a Raspberry Pi; continuing anyway." ;; esac
  if ! command -v whiptail >/dev/null || ! command -v curl >/dev/null; then
    log "Installing whiptail and curl"; apt-get update -qq && apt_install whiptail curl ca-certificates
  fi
  mkdir -p "$ZB_ETC"; touch "$ZB_CONFIG"; cfg_defaults
  hardware_notice
}

hardware_notice() {
  local msg=""
  if is_old_pi; then
    msg+="This looks like an older Raspberry Pi ($(pi_model)).\nADS-B + the FlightInfo wall run fine on it. Use Ethernet if you can, and a good power supply.\nACARS + Grafana are NOT recommended on it.\n\n"
  fi
  if is_low_mem; then
    msg+="Memory: only $(mem_total_mb) MB.\nRecommended here: ADS-B + FlightInfo + at most one or two extra feeders.\nACARS + Grafana need about 900 MB more: use a Pi with 2 GB or more.\n"
  fi
  [ -n "$msg" ] && [ "$(cfg_get HW_NOTICE_SEEN)" != 1 ] && { wt_msg "$msg" 16; cfg_set HW_NOTICE_SEEN 1; }
  return 0
}

first_run_wizard() {
  grep -q '^LAT=.' "$ZB_CONFIG" && grep -q '^LON=.' "$ZB_CONFIG" && return 0
  wt_msg "Welcome to ZenithBoard - ADSB Flight Info.\n\nA few questions first:\n  1. Your region (decides whether 978 MHz UAT is offered)\n  2. Units (metric or imperial)\n  3. Where your antenna is\n  4. The default detection radius\n\nYou can change all of them later:  sudo zenithboard config   (or Settings in this menu)." 18 || exit 0
  settings_region || exit 0
  [ "$(cfg_get REGION world)" != us ] || cfg_set UNITS imperial     # a sensible start for the US; the next screen lets you change it
  settings_units || exit 0
  settings_location || exit 0
  local r; r=$(pick_radius) && cfg_set RADIUS "$r"
}

settings_region() {
  local cur w u c; cur=$(cfg_get REGION world); w=OFF; u=OFF; [ "$cur" = us ] && u=ON || w=ON
  c=$(wt_radio "Where will the antenna be?\n\nIn the United States (and its territories) a lot of small aircraft transmit on 978 MHz (UAT) instead of 1090 MHz. Choosing the US adds an optional 978 MHz step; it needs a second SDR dongle.\nEverywhere else only 1090 MHz is used." \
      world "Everywhere else (1090 MHz only)" "$w" us "United States and territories (1090 MHz + optional 978 MHz UAT)" "$u") || return 1
  cfg_set REGION "$c"
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
    lat=$(wt_input "Antenna LATITUDE in decimal degrees (e.g. 49.1193, south is negative)." "$(cfg_get LAT)") || return 1
    valid_lat "$lat" && break; wt_msg "Not a valid latitude (-90..90)." 8
  done
  while true; do
    lon=$(wt_input "Antenna LONGITUDE in decimal degrees (e.g. 6.1757, west is negative)." "$(cfg_get LON)") || return 1
    valid_lon "$lon" && break; wt_msg "Not a valid longitude (-180..180)." 8
  done
  alt=$(wt_input "Antenna altitude above sea level in METRES (approximate is fine)." "$(cfg_get ALT_M 0)") || return 1
  is_number "$alt" || alt=0
  cfg_set LAT "$lat"; cfg_set LON "$lon"; cfg_set ALT_M "$alt"
}

settings_style() {
  local cur d f c; cur=$(cfg_get DISPLAY_MODE dots); d=OFF; f=OFF; [ "$cur" = flap ] && f=ON || d=ON
  c=$(wt_radio "Look of the wall.\n\nDot matrix : glowing dots, wipes from one aircraft to the next (the default).\nSplit-flap  : an old airport departure board; every letter flips through the alphabet, row after row, when the aircraft changes.\n\nOne tablet can also choose by itself with the address  http://PI:8080/?mode=flap  (or ?mode=dots). To go back: choose Dot matrix here." \
      dots "Dot matrix" "$d" flap "Split-flap airport board" "$f") || return 1
  cfg_set DISPLAY_MODE "$c"
}

settings_color() {
  local cur c a g r w; cur=$(cfg_get THEME amber); a=OFF; g=OFF; r=OFF; w=OFF
  case "$cur" in green) g=ON ;; red) r=ON ;; white) w=ON ;; *) a=ON ;; esac
  c=$(wt_radio "Dot colour of the wall (amber is the default)." amber "Amber" "$a" green "Green" "$g" red "Red" "$r" white "White" "$w") || return 1
  cfg_set THEME "$c"
}

network_menu() {
  local c u
  while true; do
    c=$(wt_menu "Network - in the order you usually need it\n\nWi-Fi: $(wifi_summary)\nAddress: $(net_has_nm && { u=$(net_default_profile) && net_profile_summary "$u"; } || echo 'not managed by NetworkManager')\nDomain name: $(ddns_summary)\n\nEthernet stays the preferred connection; nothing here changes that." \
      wifi "1  Wi-Fi: on/off, country, networks, password" \
      ip "2  Fixed IP address, mask, gateway, DNS" \
      name "3  Domain name (DuckDNS, No-IP, FreeDNS)" \
      status "Status of all of the above" \
      back "Return to the previous menu") || return 0
    case "$c" in
      wifi) wifi_menu ;;
      ip) net_static_menu ;;
      name) ddns_menu ;;
      status) clear; net_status; echo; wifi_has_nm && [ -n "$(wifi_iface)" ] && { wifi_status; echo; }; ddns_status; echo; read -rp "Press Enter to continue..." _ ;;
      *) return 0 ;;
    esac
  done
}

settings_receiver_menu() {
  local c
  while true; do
    c=$(wt_menu "Receiver settings (what the RTL-SDR dongle and its antenna are used for)\n\nRegion: $(cfg_get REGION world)    Units: $(cfg_get UNITS)\nAntenna position: $(cfg_get LAT), $(cfg_get LON), $(cfg_get ALT_M 0) m" \
      region "1  Region: world / United States (978 MHz UAT)" \
      units "2  Units: metric / imperial" \
      location "3  Antenna position (updates it everywhere)" \
      back "Return to the previous menu") || return 0
    case "$c" in
      region) settings_region && wt_msg "Region saved: $(cfg_get REGION world).\n\nIn menu 1 ADSB the 978 MHz UAT option appears for the United States." 10 ;;
      units) settings_units && restart_flightinfo ;;
      location)
        if settings_location; then
          clear; zb_apply_location "$(cfg_get LAT)" "$(cfg_get LON)" "$(cfg_get ALT_M 0)"
          echo; echo "Lines marked MANUAL can only be changed on the provider's website."
          read -rp "Press Enter to continue..." _
        fi ;;
      *) return 0 ;;
    esac
  done
}

settings_wall_menu() {
  local c
  while true; do
    c=$(wt_menu "ZenithBoard wall settings (defaults for every screen; a tablet can override them with its gear icon)\n\nRadius: $(cfg_get RADIUS)    Look: $(cfg_get DISPLAY_MODE dots)    Colour: $(cfg_get THEME amber)    Seconds per aircraft: $(cfg_get CYCLE_SECONDS)\nPhotos: $(cfg_get SHOW_PHOTOS)    Routes: $(cfg_get SHOW_ROUTES 1)    Monthly data refresh: $( [ "$(cfg_get AUTO_DATA_REFRESH 1)" = 1 ] && echo ON || echo OFF )" \
      radius "1  Detection radius" \
      style "2  Look: dot matrix / split-flap airport board" \
      color "3  Colour: amber / green / red / white" \
      cycle "4  Seconds per aircraft" \
      photos "5  Aircraft photos on/off" \
      routes "6  Flight origin/destination on/off" \
      data "7  Monthly aircraft-data refresh on/off" \
      back "Return to the previous menu") || return 0
    case "$c" in
      style) settings_style && restart_flightinfo && wt_msg "Look saved: $(cfg_get DISPLAY_MODE dots).\n\nThis is the default for every screen. A tablet that chose its own look (?mode=... or the gear icon) keeps it until you press Reset in its gear panel." 11 ;;
      color) settings_color && restart_flightinfo ;;
      radius) change_radius ;;
      cycle) local s; s=$(wt_input "Seconds each aircraft stays on the wall (2-60)." "$(cfg_get CYCLE_SECONDS 6)") && is_number "$s" && cfg_set CYCLE_SECONDS "$s" && restart_flightinfo ;;
      photos) if wt_yesno "Show aircraft photos (Planespotters) on the wall? Needs internet on the Pi." 8; then cfg_set SHOW_PHOTOS 1; else cfg_set SHOW_PHOTOS 0; fi ;;
      routes) if wt_yesno "Show where each flight comes from and goes to?\n\nThe callsign (for example DLH4YK) is looked up on the free adsbdb.com database. When your decoder does not know an aircraft, its address is also used to find the model name. Needs internet on the Pi." 13; then cfg_set SHOW_ROUTES 1; else cfg_set SHOW_ROUTES 0; fi ;;
      data)
        if wt_yesno "Refresh the aircraft model list automatically once a month?\n\n(Downloads a free list of aircraft names from GitHub. Needs internet on the Pi; the wall works without it.)" 12; then cfg_set AUTO_DATA_REFRESH 1; else cfg_set AUTO_DATA_REFRESH 0; fi
        data_refresh_apply ;;
      *) return 0 ;;
    esac
  done
}

settings_menu() {
  local c
  while true; do
    c=$(wt_menu "Settings (applied immediately), in the order of a first setup\n\nNetwork: Wi-Fi $(wifi_summary)\nReceiver: $(cfg_get REGION world), $(cfg_get UNITS), $(cfg_get LAT), $(cfg_get LON)\nWall: radius $(cfg_get RADIUS), $(cfg_get DISPLAY_MODE dots), $(cfg_get THEME amber)\nLogs: automatic cleaning $(logs_auto_state | cut -d' ' -f1)" \
      network "1  Network: Wi-Fi, fixed IP, domain name" \
      receiver "2  Receiver: region, units, antenna position" \
      wall "3  ZenithBoard wall: radius, look, colour, photos, routes..." \
      logs "4  Logs: size limit, review, automatic cleaning" \
      back "Return to the previous menu") || return 0
    case "$c" in
      network) network_menu ;;
      receiver) settings_receiver_menu ;;
      wall) settings_wall_menu ;;
      logs) logs_menu ;;
      *) return 0 ;;
    esac
  done
}

uninstall_all() {
  wt_yesno "UNINSTALL EVERYTHING?\n\nThis removes FlightInfo, ACARS, all feeders and the decoder installed through this menu." 12 || return 0
  clear
  wifi_remove_unit
  ddns_remove_units
  logs_auto_off
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

weak_hw_tag() { if is_low_mem || is_old_pi; then echo "  [NOT recommended on this Pi]"; fi; }

main_menu() {
  local c
  while true; do
    c=$(wt_menu "ZenithBoard $ZB_VERSION   (units: $(cfg_get UNITS), radius: $(cfg_get RADIUS))\n\nPick a step. You can come back any time to add or remove things." \
      1 "ADSB        - decoder + share to ADSB Exchange, FlightAware, FR24..." \
      2 "FlightInfo  - dot-matrix wall for an old tablet" \
      3 "ACARS       - optional ACARS messages in Grafana (2nd dongle)$(weak_hw_tag)" \
      4 "Settings    - network (Wi-Fi, IP, domain), receiver, wall, logs" \
      5 "Status      - what is running" \
      6 "Update      - everything at once, or pick components" \
      7 "Uninstall everything" \
      0 "Exit") || exit 0
    case "$c" in
      1) adsb_menu ;;
      2) flightinfo_menu ;;
      3) acars_menu ;;
      4) settings_menu ;;
      5) clear; "$ROOT/bin/zenithboard" status; read -rp "Press Enter..." _ ;;
      6) update_menu ;;
      7) uninstall_all ;;
      *) exit 0 ;;
    esac
  done
}

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
  --version) echo "ZenithBoard $ZB_VERSION"; exit 0 ;;
  --deploy) need_root "$@"; mkdir -p "$ZB_ETC"; touch "$ZB_CONFIG"; cfg_defaults; deploy_files; exit 0 ;;
  --uninstall-all) preflight "$@"; uninstall_all; exit 0 ;;
  "") ;;
  *) usage; exit 1 ;;
esac
preflight "$@"
# the CLI needs the files in place even if only menu 1 is used
deploy_files
first_run_wizard
main_menu
