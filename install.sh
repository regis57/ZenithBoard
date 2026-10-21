#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# ZenithBoard installer / uninstaller menu.
#   1 ADSB        decoder (readsb or dump1090-fa) + feeders, ADSB Exchange mandatory, single MLAT
#   2 FlightInfo  dot-matrix wall for an old tablet
# Re-run it any time: it detects what is installed and lets you add or remove components.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
. "$ROOT/lib/common.sh"
. "$ROOT/lib/adsb.sh"
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

zb_tmp_init   # the private folder for downloads, made here in the main shell (see zb_tmp in lib/common.sh)

usage() { echo "Usage: sudo ./install.sh [--deploy] [--uninstall-all] [--version] [--help]      (to upgrade: sudo zenithboard update)"; }

preflight() {
  need_root "$@"
  command -v apt-get >/dev/null || die "This installer needs Raspberry Pi OS / Debian (apt)."
  case "$(arch)" in arm64|armhf) ;; *) warn "Architecture $(arch) is not a Raspberry Pi; continuing anyway." ;; esac
  if ! command -v whiptail >/dev/null || ! command -v curl >/dev/null; then
    log "Installing whiptail and curl"; apt-get update -qq && apt_install whiptail curl ca-certificates
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

first_run_wizard() {
  grep -q '^LAT=.' "$ZB_CONFIG" && grep -q '^LON=.' "$ZB_CONFIG" && return 0
  wt_msg "Welcome to ZenithBoard - ADSB Flight Info.\n\nA few questions first:\n  1. Your region (decides whether 978 MHz UAT is offered)\n  2. Units (metric or imperial)\n  3. Where your antenna is\n  4. The default detection radius\n\nYou can change all of them later: menu 4 Settings (sudo zenithboard menu), or the commands\n  sudo zenithboard region|units|location|radius ..." 18 || exit 0
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
  # a typo used to become 0 without a word (fresh-install check, 0.21.1): ask again instead, like the latitude
  while true; do
    alt=$(wt_input "Antenna altitude above sea level in METRES (approximate is fine)." "$(cfg_get ALT_M 0)") || return 1
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
      gain "4  Gain: check it and tune the dongle's sensitivity" \
      stats "5  Statistics: messages per hour, farthest aircraft, aircraft per day ($(stats_state))" \
      graphs "6  graphs1090: years of the decoder's graphs, on port 8542 ($(graphs_state))" \
      back "Return to the previous menu") || return 0
    case "$c" in
      region) settings_region && wt_msg "Region saved: $(cfg_get REGION world).\n\nIn menu 1 ADSB the 978 MHz UAT option appears for the United States." 10 ;;
      units) settings_units && restart_flightinfo ;;
      gain) gain_menu ;;
      stats)
        if [ "$(stats_state)" = on ]; then
          if wt_yesno "Statistics are ON: a sample every 15 minutes, 30 days kept, readable at http://$(local_ip):$(cfg_get PORT 8080)/stats and with 'zenithboard stats'.\n\nTurn them OFF? (the files are kept)" 12; then clear; stats_off; read -rp "Press Enter to continue..." _; fi
        else
          if wt_yesno "Collect statistics?\n\nEvery 15 minutes: messages, the farthest aircraft, how many aircraft had a position, and which aircraft were seen. Since 0.31.0 also the airlines, types and altitudes seen. About 30 KB a day on the card, 30 days kept. Read them at http://$(local_ip):$(cfg_get PORT 8080)/stats or with 'zenithboard stats'. Off again at any time." 14; then clear; stats_on; read -rp "Press Enter to continue..." _; fi
        fi ;;
      graphs)
        if is_graphs; then
          if wt_yesno "graphs1090 is ON: http://$(local_ip):$GRAPHS_PORT/\n\nTurn it OFF? Its packages that were not there before go; its history stays on the card for a later 'on'." 12; then clear; graphs_off; read -rp "Press Enter to continue..." _; fi
        else
          if wt_yesno "Install graphs1090?\n\nwiedehopf's graphs of the receiver: messages, range, signal, aircraft, CPU and temperature, kept for years, on port $GRAPHS_PORT (and /graphs1090 on the map's port 80). Installed by its author's script: collectd and rrdtool from apt, its files from GitHub. Needs the receiver map's lighttpd.\n\nIts graphs live in memory and go to the card once a day and at shutdown. Off again at any time." 17; then clear; graphs_on; read -rp "Press Enter to continue..." _; fi
        fi ;;
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
    c=$(wt_menu "ZenithBoard wall settings (defaults for every screen; a tablet can override them with its gear icon)\n\nRadius: $(cfg_get RADIUS)    Look: $(cfg_get DISPLAY_MODE dots)    Colour: $(wall_theme)    Seconds per aircraft: $(cfg_get CYCLE_SECONDS)\nPhotos: $(cfg_get SHOW_PHOTOS)    Routes: $(cfg_get SHOW_ROUTES 1)    Monthly data refresh: $( [ "$(cfg_get AUTO_DATA_REFRESH 1)" = 1 ] && echo ON || echo OFF )    Offline database: $( [ "$(cfg_get LOCAL_DB 0)" = 1 ] && echo ON || echo OFF )" \
      radius "1  Detection radius" \
      style "2  Look: dot matrix / split-flap airport board" \
      color "3  Colour: amber, green, red, white, turquoise" \
      cycle "4  Seconds per aircraft" \
      photos "5  Aircraft photos on/off" \
      routes "6  Flight origin/destination on/off" \
      data "7  Monthly aircraft-data refresh on/off" \
      presets "8  Presets: a name for a tablet's own choices (?p=NAME in its address)" \
      localdb "9  Registrations from the receiver map's database (offline) on/off" \
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
      presets) presets_menu ;;
      localdb)
        if wt_yesno "Read registrations and models from tar1090's aircraft database on this Pi?\n\nThe receiver map (tar1090) keeps this database on the card and updates it itself. It knows aircraft that adsbdb and hexdb do not (9H-EWG, a Eurowings A320, for one). Nothing is downloaded and nothing is sent to the internet.\n\nNow: $( [ "$(cfg_get LOCAL_DB 0)" = 1 ] && echo ON || echo OFF )" 15; then
          [ -d "$(cfg_get LOCAL_DB_DIR /usr/local/share/tar1090/git-db/db)" ] && cfg_set LOCAL_DB 1 || wt_msg "No tar1090 database at $(cfg_get LOCAL_DB_DIR /usr/local/share/tar1090/git-db/db).\n\nIt comes with the receiver map (tar1090)." 10
        else cfg_set LOCAL_DB 0; fi
        restart_flightinfo ;;
      *) return 0 ;;
    esac
  done
}

presets_menu() {
  local c n v out pairs
  while true; do
    c=$(wt_menu "Presets: a second screen opens  http://PI:8080/?p=NAME  and gets these choices, with no long address to type.\nKeys: $PRESET_KEYS   (mode dots|flap, units metric|imperial, flags 0|1)\n\n$(preset_list | head -8)" \
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

settings_menu() {
  local c
  while true; do
    c=$(wt_menu "Settings (applied immediately), in the order of a first setup\n\nNetwork: Wi-Fi $(wifi_summary)\nReceiver: $(cfg_get REGION world), $(cfg_get UNITS), $(cfg_get LAT), $(cfg_get LON)\nWall: radius $(cfg_get RADIUS), $(cfg_get DISPLAY_MODE dots), $(wall_theme)\nLogs: automatic cleaning $(logs_auto_state | cut -d' ' -f1)\nReliability: watchdog $(watchdog_state), network watchdog $(netwatch_state), saved logs $(keeplogs_state)" \
      network "1  Network: Wi-Fi, fixed IP, domain name" \
      receiver "2  Receiver: region, units, antenna position" \
      wall "3  ZenithBoard wall: radius, look, colour, photos, routes..." \
      logs "4  Logs: size limit, review, automatic cleaning" \
      reliability "5  Reliability: watchdogs, saved logs, health check" \
      social "6  Social sharing: post the aircraft overhead to Bluesky ($(social_state))" \
      console "7  Web console: these settings from a browser or a phone ($(console_state))" \
      back "Return to the previous menu") || return 0
    case "$c" in
      network) network_menu ;;
      social) social_menu ;;
      console) console_menu ;;
      receiver) settings_receiver_menu ;;
      wall) settings_wall_menu ;;
      logs) logs_menu ;;
      reliability) reliability_menu ;;
      *) return 0 ;;
    esac
  done
}

# The one step that cannot be undone asks for the word, not a key: a Yes one Enter too many (seen as a risk in
# the menu review of 0.21.0) must not take a working receiver down. Your settings are offered as a file first.
uninstall_all() {
  local word
  wt_yesno "UNINSTALL EVERYTHING?\n\nThis removes FlightInfo, all feeders, graphs1090 and the decoder installed through this menu (and ACARS / Grafana if an older ZenithBoard installed them).\n\nFirst, keep a backup? (Maintenance -> Back up everything, or: sudo zenithboard backup make)" 14 || return 0
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
  [ -z "$(acars_leftovers)" ] || acars_remove --yes
  if is_graphs || [ -f "$GRAPHS_STATE" ]; then graphs_off; fi
  is_flightinfo && remove_flightinfo
  is_planefinder && remove_planefinder
  is_fr24 && remove_fr24
  is_piaware && remove_piaware
  is_adsbx && remove_adsbx
  [ -n "$(installed_decoder)" ] && remove_decoder
  if wt_yesno "Also delete your ZenithBoard settings ($ZB_ETC) and program files ($ZB_HOME)?" 8; then
    rm -rf "$ZB_ETC" "$ZB_HOME" "$ZB_BIN_DIR/zenithboard"
    id "$ZB_USER" >/dev/null 2>&1 && userdel "$ZB_USER" 2>/dev/null
  fi
  log "Everything removed."; exit 0
}

maintenance_menu() {
  local c f out d
  while true; do
    c=$(wt_menu "Maintenance\n\nSettings file: $ZB_CONFIG   (secrets are in their own root-only files and never leave with it)" \
      save "Save my settings to a file (to keep, or to move to another Pi)" \
      restore "Restore settings from a file (the ones from before are kept as .bak)" \
      backup "Back up everything, or restore on a new card: statistics, graphs, logs, networks' identities" \
      uninstall "Uninstall everything (asks you to type the word)" \
      back "Return to the previous menu") || return 0
    case "$c" in
      save)
        d="/home/${SUDO_USER:-}"; [ -n "${SUDO_USER:-}" ] && [ -d "$d" ] || d="${HOME:-/root}"     # the user's own folder, or root's when there is no sudo user
        f=$(wt_input "Where to write the settings file." "$d/zenithboard-settings-$(hostname)-$(date +%Y%m%d).env") || continue
        if out=$(settings_export "$f" 2>&1); then
          [ -n "${SUDO_USER:-}" ] && chown "$SUDO_USER" "$f" 2>/dev/null
          wt_msg "Saved: $out\n\nCopy it off the Pi (scp, a USB stick). On another Pi:  sudo zenithboard settings import FILE" 12
        else wt_msg "$out" 8; fi ;;
      restore)
        f=$(wt_input "The settings file to restore." "") || continue
        [ -f "$f" ] || { wt_msg "No such file: $f" 7; continue; }
        wt_yesno "Restore the settings in $f?\n\nEvery setting in it replaces the current one. The current file is kept first as $ZB_CONFIG.bak-DATE, so this can be undone the same way." 12 || continue
        clear; settings_import "$f" && settings_apply; read -rp "Press Enter to continue..." _ ;;
      backup) backup_menu ;;
      uninstall) uninstall_all ;;
      *) return 0 ;;
    esac
  done
}


main_menu() {
  local c
  while true; do
    c=$(wt_menu "ZenithBoard $ZB_VERSION   (units: $(cfg_get UNITS), radius: $(cfg_get RADIUS))\n\nPick a step. You can come back any time to add or remove things." \
      1 "ADSB        - decoder + share to ADSB Exchange, FlightAware, FR24..." \
      2 "FlightInfo  - dot-matrix wall for an old tablet" \
      3 "Settings    - network (Wi-Fi, IP, domain), receiver, wall, logs" \
      4 "Status      - what is running" \
      5 "Update      - ZenithBoard and the wall in seconds, or everything" \
      6 "Maintenance - back up, save or restore your settings, uninstall" \
      0 "Exit") || exit 0
    case "$c" in
      1) adsb_menu ;;
      2) flightinfo_menu ;;
      3) settings_menu ;;
      4) clear; "$ROOT/bin/zenithboard" status; read -rp "Press Enter..." _ ;;
      5) update_menu ;;
      6) maintenance_menu ;;
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
