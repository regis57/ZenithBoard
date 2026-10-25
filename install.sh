#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# ZenithBoard installer and menu (0.44.0: by what you want to do, the owner's review of 21 October 2026).
#   Start here   the first installation, step by step: the antenna, ADS-B, the wall, what is worth switching on, the
#                web console to finish in a browser (or a backup from another card first)
#   1 ADS-B      decoder (readsb or dump1090-fa) + the networks, ADSB Exchange mandatory, single MLAT; antenna; gain
#   2 The wall   install it, what it shows, its look, photos and routes, presets
#   3 Connectivity  Wi-Fi, fixed address, domain name, reaching it from outside safely
#   4 Troubleshoot  health, what is running, memory, logs, security, watchdogs, log housekeeping
#   5 Updates    6 Backup (and moving, uninstall)    7 Options (statistics, graphs1090, Bluesky, web console)
# Every menu has seven entries at most, and one way out. Re-run it any time: it detects what is installed.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$ROOT/lib/common.sh"
. "$ROOT/lib/adsb.sh"
# shellcheck source=lib/adsbxstats.sh
. "$ROOT/lib/adsbxstats.sh"
. "$ROOT/lib/flightinfo.sh"
. "$ROOT/lib/legacy.sh"
. "$ROOT/lib/logs.sh"
. "$ROOT/lib/gain.sh"
. "$ROOT/lib/reliability.sh"
# shellcheck source=lib/patches.sh
. "$ROOT/lib/patches.sh"
# shellcheck source=lib/security.sh
. "$ROOT/lib/security.sh"
# shellcheck source=lib/stats.sh
. "$ROOT/lib/stats.sh"
# shellcheck source=lib/graphs.sh
. "$ROOT/lib/graphs.sh"
# shellcheck source=lib/social.sh
. "$ROOT/lib/social.sh"
. "$ROOT/lib/uat.sh"
. "$ROOT/lib/wifi.sh"
. "$ROOT/lib/network.sh"
. "$ROOT/lib/ddns.sh"
# shellcheck source=lib/settings.sh
. "$ROOT/lib/settings.sh"
# shellcheck source=lib/console.sh
. "$ROOT/lib/console.sh"
. "$ROOT/lib/update.sh"
# shellcheck source=lib/backup.sh
. "$ROOT/lib/backup.sh"
# shellcheck source=lib/tailscale.sh
. "$ROOT/lib/tailscale.sh"
# shellcheck source=lib/menus.sh
. "$ROOT/lib/menus.sh"

zb_tmp_init   # the private folder for downloads, made here in the main shell (see zb_tmp in lib/common.sh)

usage() { echo "Usage: sudo ./install.sh [--deploy] [--uninstall-all] [--version] [--help]      (to upgrade: sudo zenithboard update)"; }

preflight() {
  need_root "$@"
  command -v apt-get >/dev/null || die "This installer needs Raspberry Pi OS / Debian (apt)."
  case "$(arch)" in arm64|armhf) ;; *) warn "Architecture $(arch) is not a Raspberry Pi; continuing anyway." ;; esac
  # gpg too (the audit of 22-23 October 2026): without it the update's signature check said "the commit is not signed"
  if ! command -v whiptail >/dev/null || ! command -v curl >/dev/null || ! command -v gpg >/dev/null; then
    log "Installing whiptail, curl and gpg"; apt-get update -qq && apt_install whiptail curl ca-certificates gnupg
    # Without whiptail every screen fails and the menu quietly exits with nothing said (fresh-install check, 0.21.1)
    command -v whiptail >/dev/null && command -v curl >/dev/null \
      || die "whiptail and curl could not be installed (no internet, or apt failed above). Install them by hand:  sudo apt install whiptail curl   then run this again."
  fi
  mkdir -p "$ZB_ETC"; touch "$ZB_CONFIG"; cfg_defaults
  hardware_notice
}

hardware_notice() {
  local msg=""
  # Since 0.20.1 from what was measured: the project's reference Pi is a 3B with 1 GB (wiki: Hardware)
  if is_old_pi && pi_model | grep -q 'Raspberry Pi 3'; then
    msg+="A Raspberry Pi 3 ($(pi_model)): the board ZenithBoard is measured on.\nADS-B, the feeders, the wall and social sharing run comfortably on it. Ethernet or a strong Wi-Fi signal, and the official power supply.\n\n"
  elif is_old_pi; then
    msg+="This looks like an older Raspberry Pi ($(pi_model)).\nADS-B + the FlightInfo wall run on it. Use Ethernet if you can, and a good power supply.\n\n"
  fi
  if is_low_mem && [ "$(mem_total_mb)" -lt 700 ]; then
    msg+="Memory: only $(mem_total_mb) MB.\nRecommended here: ADS-B + the wall, no extra feeders.\n"
  elif is_low_mem; then
    msg+="Memory: $(mem_total_mb) MB.\nMeasured on a 1 GB Pi 3B: ADS-B Exchange, FlightAware, Flightradar24, the wall and social sharing still leave about 650 MB free.\n"
  fi
  [ -n "$msg" ] && [ "$(cfg_get HW_NOTICE_SEEN)" != 1 ] && { wt_msg "$msg" 20; cfg_set HW_NOTICE_SEEN 1; }
  return 0
}

# 0.54.5: Esc at one of the first questions ended the installer with nothing said
wizard_stop() { echo "Stopped before the first questions were all answered. The ones you answered are kept, and the questions come again at the next start:  sudo ./install.sh  (later: sudo zenithboard menu)"; exit 0; }

first_run_wizard() {
  grep -q '^LAT=.' "$ZB_CONFIG" && grep -q '^LON=.' "$ZB_CONFIG" && return 0
  wt_msg "Welcome to ZenithBoard - ADSB Flight Info.\n\nA few questions first:\n  1. Your region (decides whether 978 MHz UAT is offered)\n  2. Units (metric, imperial or aviation)\n  3. Where your antenna is\n  4. The default detection radius\n\nThen the menu: 'Start here' takes you through the rest, step by step. Moving from another card with a backup? Answer these anyway: the backup puts its own back." 18 || wizard_stop
  settings_region || wizard_stop
  [ "$(cfg_get REGION world)" != us ] || cfg_set UNITS imperial     # a sensible start for the US; the next screen lets you change it
  settings_units || wizard_stop
  settings_location || wizard_stop
  local r; r=$(pick_radius) && cfg_set RADIUS "$r"
}

settings_region() {
  local cur w u c; cur=$(cfg_get REGION world); w=OFF; u=OFF; [ "$cur" = us ] && u=ON || w=ON
  c=$(wt_radio "Where will the antenna be?\n\nIn the United States (and its territories) a lot of small aircraft transmit on 978 MHz (UAT) instead of 1090 MHz. Choosing the US adds an optional 978 MHz step; it needs a second SDR dongle.\nEverywhere else only 1090 MHz is used." \
      world "Everywhere else (1090 MHz only)" "$w" us "United States and territories (1090 MHz + optional 978 MHz UAT)" "$u") || return 1
  cfg_set REGION "$c"
}

settings_units() {
  local cur u m i a; cur=$(cfg_get UNITS metric); m=OFF; i=OFF; a=OFF
  case "$cur" in imperial) i=ON ;; aviation) a=ON ;; *) m=ON ;; esac
  # 0.55.0: aviation, as on a pilot's or a controller's screen (the owner, 25 October 2026)
  u=$(wt_radio "Units for the wall, the radius and the posts.\n\nmetric   : distance km, speed km/h, altitude m\nimperial : distance miles, speed knots, altitude ft\naviation : distance nautical miles (NM), speed knots (kt), altitude feet (ft): the way pilots and air traffic control count" \
      metric "Metric (km, km/h, m)" "$m" imperial "Imperial (miles, knots, feet)" "$i" aviation "Aviation (NM, kt, ft)" "$a") || return 1
  cfg_set UNITS "$u"
}

# 0.54.18: where to find the three numbers (the owner, 25 October 2026). The site was checked that day: a map, a search
# box, and for the spot clicked the latitude, longitude and elevation in metres, no account.
POSITION_HELP_URL="https://www.mapcoordinates.net/en"

settings_location() {
  local lat lon alt
  while true; do
    lat=$(wt_input "Antenna LATITUDE in decimal degrees (e.g. 49.1193, south is negative).\n\nNot sure? On a phone or a computer open  $POSITION_HELP_URL  and click the antenna's spot on the map: it shows the latitude, the longitude and the elevation (m) to type here." "$(cfg_get LAT)") || return 1
    valid_lat "$lat" && break; wt_msg "Not a valid latitude (-90..90)." 8
  done
  while true; do
    lon=$(wt_input "Antenna LONGITUDE in decimal degrees (e.g. 6.1757, west is negative)." "$(cfg_get LON)") || return 1
    valid_lon "$lon" && break; wt_msg "Not a valid longitude (-180..180)." 8
  done
  # a typo used to become 0 without a word (fresh-install check, 0.21.1): ask again instead, like the latitude
  while true; do
    alt=$(wt_input "Antenna altitude above sea level in METRES (approximate is fine).\n\n$POSITION_HELP_URL gives the ground's elevation; add the antenna's height above the ground (a roof: about 6 to 10 m)." "$(cfg_get ALT_M 0)") || return 1
    is_number "$alt" && break; wt_msg "Not a number: the altitude in metres, e.g. 180 (0 if you do not know it)." 8
  done
  cfg_set LAT "$lat"; cfg_set LON "$lon"; cfg_set ALT_M "$alt"
}

settings_style() {
  local cur d f c; cur=$(cfg_get DISPLAY_MODE dots); d=OFF; f=OFF; [ "$cur" = flap ] && f=ON || d=ON
  c=$(wt_radio "Look of the wall.\n\nDot matrix : glowing dots, wipes from one aircraft to the next (the default).\nSplit-flap  : an old airport departure board; every letter flips through the alphabet, row after row, when the aircraft changes.\n\nOne tablet can also choose by itself with the address  http://PI:8080/?mode=flap  (or ?mode=dots). To go back: choose Dot matrix here." \
      dots "Dot matrix" "$d" flap "Split-flap airport board" "$f") || return 1
  cfg_set DISPLAY_MODE "$c"
}

settings_color() {
  # the same five as `zenithboard color` and the tablet's gear (turquoise was missing here until 0.21.1; the dark
  # blue went in 0.23.0). A Pi still set to blue sees amber ticked: what the wall shows now
  local cur c items=() col on; cur=$(wall_theme)
  for col in amber green red white turquoise; do
    on=OFF; [ "$col" = "$cur" ] && on=ON; items+=("$col" "${col^}" "$on")
  done
  c=$(wt_radio "Dot colour of the wall (amber is the default)." "${items[@]}") || return 1
  cfg_set THEME "$c"
}

presets_menu() {
  local c n v out pairs
  while true; do
    c=$(wt_menu "Presets: a second screen opens  http://PI:8080/?p=NAME  and gets these choices, with no long address to type.\nKeys: $PRESET_KEYS   (mode dots|flap, units metric|imperial|aviation, flags 0|1)\n\n$(preset_list | head -8)" \
      add "Add or change a preset" \
      del "Forget a preset" \
      back "Return to the previous menu") || return 0
    case "$c" in
      add)
        n=$(wt_input "Preset name (letters and digits, 16 at most): kitchen, tv2, bedroom" "") || continue
        v=$(wt_input "What it sets, as key=value separated by spaces.\nExample:  theme=green mode=flap radius=5 cycle=8" "$(cfg_get "$(preset_key_of "$n")" "")") || continue
        read -r -a pairs <<<"$v"
        if out=$(preset_add "$n" "${pairs[@]}" 2>&1); then wt_msg "$out" 10; else wt_msg "$out" 9; fi ;;
      del) n=$(wt_input "Preset to forget" "") || continue; out=$(preset_del "$n" 2>&1); wt_msg "$out" 8 ;;
      *) return 0 ;;
    esac
  done
}

# The one step that cannot be undone asks for the word, not a key: a Yes one Enter too many (seen as a risk in
# the menu review of 0.21.0) must not take a working receiver down. A backup is pointed to first.
uninstall_all() {
  local word
  # the audit of 22-23 October 2026: "First, keep a backup?" under a Yes/No read as two questions; Yes is now "go on"
  wt_yesno "UNINSTALL EVERYTHING?\n\nThis removes FlightInfo, all feeders, graphs1090 and the decoder installed through this menu (and ACARS / Grafana if an older ZenithBoard installed them).\n\nNo backup yet? Choose No, then 6 Backup -> 1 Make a backup now (or: sudo zenithboard backup make).\n\nYes goes on to the typed word." 16 || return 0
  word=$(wt_input "To go on, type the word  uninstall  (anything else cancels)." "") || return 0
  [ "$word" = uninstall ] || { wt_msg "Not uninstalled: nothing was changed." 7; return 0; }
  clear
  wifi_remove_unit
  ddns_remove_units
  logs_auto_off
  netwatch_remove_units
  gain_log_remove_units
  stats_remove_units
  console_remove_units
  # 0.54.0: the Bluesky service was left running (and enabled) by "uninstall everything". Off, not removed: the account
  # goes with the settings if they are deleted below, and stays with them if they are kept
  [ "$(social_state)" != on ] || social_off >/dev/null
  [ -z "$(acars_leftovers)" ] || acars_remove --yes
  if is_graphs || [ -f "$GRAPHS_STATE" ]; then graphs_off; fi
  is_flightinfo && remove_flightinfo
  is_planefinder && remove_planefinder
  is_fr24 && remove_fr24
  is_piaware && remove_piaware
  # 0.52.0: ADSB Exchange's stats, also when their feed was removed by hand first (its uninstaller leaves them running)
  if is_adsbx_stats || [ -f "$AXS_STATE" ]; then adsbx_stats_off; fi
  is_adsbx && remove_adsbx
  [ -n "$(installed_decoder)" ] && remove_decoder
  if wt_yesno "Also delete your ZenithBoard settings ($ZB_ETC, with the Bluesky app password in social.env and the console's password) and program files ($ZB_HOME)?\n\nThe statistics and the posts' history in $ZB_DATA stay either way (to delete them too: sudo rm -rf $ZB_DATA)." 12; then
    rm -rf "$ZB_ETC" "$ZB_HOME" "$ZB_BIN_DIR/zenithboard"
    id "$ZB_USER" >/dev/null 2>&1 && userdel "$ZB_USER" 2>/dev/null
  fi
  log "Everything removed."; exit 0
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
