# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# The menu, by what you want to do (0.44.0). The owner, 21 October 2026, after a new card: too many menus, some of
# ten entries, and nothing said that the console needs ADS-B and the wall first ("obvious to you, not to everyone").
# So: one entry to start with, which does the first installation in its order and ends in the web console; then one
# menu per subject, seven entries at most, each with a single way out. The commands behind them are the ones
# `zenithboard` runs, so the console, the menu and the terminal stay one and the same.
# Sourced by install.sh after every other lib (it calls their functions).

menu_pause() { echo; read -rp "Press Enter to go back to the menu..." _; }
menu_onoff() { [ "$1" = on ] && echo ON || echo OFF; }

# what the main menu says at the top: what this Pi already does, so the next step is plain
menu_status_line() {
  local d feeds="" url
  d=$(installed_decoder); [ -n "$d" ] || d="none yet"
  is_adsbx && feeds+=", ADSB Exchange"; is_piaware && feeds+=", FlightAware"; is_fr24 && feeds+=", Flightradar24"; is_planefinder && feeds+=", Plane Finder"; is_radarbox && feeds+=", AirNav Radar"
  feeds=${feeds#, }; [ -n "$feeds" ] || feeds="nobody yet"
  url="http://$(local_ip):$(cfg_get PORT 8080)"
  printf 'Decoder: %s    Feeding: %s\\nThe wall: %s    Console: %s' "$d" "$feeds" \
    "$(is_flightinfo && echo "$url/" || echo "not installed")" \
    "$( [ "$(console_state)" = on ] && echo "$url/console" || echo off)"
}
setup_done() { [ -n "$(installed_decoder)" ] && is_adsbx && is_flightinfo && [ "$(console_state)" = on ]; }

main_menu() {
  local c start
  while true; do
    if setup_done; then start="   Start here   - all done: check it again"
    else start="   Start here   - the first installation, step by step"; fi
    c=$(wt_menu "ZenithBoard $ZB_VERSION\n$(menu_status_line)\n\nNew here? Start here. Then the web console does most of this." \
      start "$start" \
      1 "1  ADS-B        - decoder, networks, antenna, gain" \
      2 "2  The wall     - install it, what it shows, its look" \
      3 "3  Connectivity - Wi-Fi, address, reaching it from outside" \
      4 "4  Troubleshoot - health, logs, watchdogs" \
      5 "5  Updates      - ZenithBoard, the feeders, security fixes" \
      6 "6  Backup       - keep it, move to a new card, uninstall" \
      7 "7  Options      - statistics, graphs, Bluesky, Telegram, web console" \
      0 "0  Exit") || exit 0
    case "$c" in
      start) start_here ;;
      1) adsb_section_menu ;;
      2) wall_menu ;;
      3) connectivity_menu ;;
      4) troubleshoot_menu ;;
      5) update_menu ;;
      6) backup_section_menu ;;
      7) options_menu ;;
      *) exit 0 ;;
    esac
  done
}

# ---------------------------------------------------------------- Start here: the first installation, in its order
# 1 a backup from another card, if any; 2 the antenna (asked by first_run_wizard); 3 ADS-B: the decoder and ADSB
# Exchange, other networks if wanted; 4 the wall; 5 what is worth switching on, ticked, the list shown; 6 Bluesky, if
# wanted (0.54.18); 7 the web console, with its password, and its address to finish in a browser. Each step is skipped
# when it is done already.
start_here() {
  wt_msg "The first installation, step by step:\n\n  1. A backup from another card, if you have one\n  2. ADS-B: the decoder, ADSB Exchange, and the other networks you want\n  3. The wall, for the tablet\n  4. What is worth switching on: a list, all ticked, untick at will\n  5. Bluesky, if you want the posts (optional)\n  6. The web console: you finish in your browser\n\nA step already done is skipped. Each one can be done again later from its own menu." 19 || return 0
  # 1 · a backup
  if [ -z "$(installed_decoder)" ] && wt_yesno "Are you moving from another card, with a ZenithBoard backup file?\n\n(Made on the old card with: menu 6 Backup, or  sudo zenithboard backup make. The console's copy leaves the networks' identities out: it is not the one to move with.)" 12; then
    # 0.54.5: a backup step left (Esc, a wrong path) used to end Start here, four screens back; the rest goes on without it
    start_restore || wt_msg "Going on without a backup. Start here again later puts one back, if the card is still bare." 8
  fi
  # 2 · ADS-B
  if [ -z "$(installed_decoder)" ] || ! is_adsbx; then
    wt_msg "ADS-B first: the decoder that reads the dongle, and ADSB Exchange (always fed: it runs the one MLAT client; MLAT locates aircraft that send no position, by comparing when several receivers heard them). On the next screens tick the other networks you want: FlightAware, Flightradar24, Plane Finder, AirNav Radar. Their installers are theirs and ask their own questions in the terminal (a station name, an e-mail, a key): the screen tells you what to answer.\n\nA backup restored a moment ago gave each network its identity back: they find it by themselves." 16 || return 0
    adsb_menu
    if [ -z "$(installed_decoder)" ]; then
      if [ -n "${ADSB_CANCELLED:-}" ]; then wt_msg "You left the ADS-B step before the end, so no decoder is installed and the rest waits: the wall and the console need one.\n\nChoose Start here again to do it." 11
      else wt_msg "No decoder is installed, so the rest waits: the wall and the console need one.\n\nCome back to Start here when the line above it says why (usually no internet)." 11; fi
      return 0
    fi
  fi
  # 3 · the wall
  if ! is_flightinfo; then
    wt_yesno "Now the wall: the page an old tablet shows, the aircraft above you as a dot-matrix or a split-flap board. The web console is one of its pages, so it comes first.\n\nInstall it?" 12 && { clear; install_flightinfo; menu_pause; }
    is_flightinfo || { wt_msg "Without the wall there is no web console either. Install it from menu 2 when you want it." 9; return 0; }
  fi
  # 4 · what is worth switching on
  start_recommended
  # 5 · Bluesky, optional (0.54.18)
  start_bluesky
  # 6 · the web console
  start_console
}

# 0.54.18 (the owner's fresh card, 25 October 2026): the account is set up only here, in the terminal, since it asks
# for an app password the console never handles; the console's first steps then showed the summaries' switches for an
# account that did not exist. Start here now offers it, before the console, and says where it is when declined.
start_bluesky() {
  [ -z "$(social_account)" ] || return 0
  if wt_yesno "Bluesky (optional): ZenithBoard can post the aircraft worth it, and the summaries of the day and the week, to a Bluesky account of yours. Nothing is posted until you switch it on.\n\nIt needs the account and an APP password for it, made at bsky.app: Settings -> Privacy and Security -> App Passwords.\n\nSet it up now?\n\n(Later: menu 7 Options -> 3 Bluesky -> 2 The account, or  sudo zenithboard social setup)" 18; then
    # the handle and password are kept even when Bluesky refused them, so Start here would not ask again: the way back
    # is the account's own entry (the review, 0.54.18)
    social_setup || wt_msg "The Bluesky account is not finished. When you have the right app password: menu 7 Options -> 3 Bluesky -> 2 The account, or  sudo zenithboard social setup" 10
  fi
  return 0
}

start_restore() {
  local f home
  home=$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)
  f=$(ls -t "$home"/zenithboard-backup-*.tar.gz 2>/dev/null | head -1)
  wt_msg "The backup file must be on this Pi, in your home folder ($home).\n\nFrom a Windows computer, the simplest is WinSCP (winscp.net, free): connect to this Pi (SFTP, its address $(local_ip), your user and password) and drag the file into the folder it opens on. From a Mac or Linux:  scp FILE ${SUDO_USER:-pi}@$(local_ip):\n\n$( [ -n "$f" ] && echo "Found: $f" || echo "No backup there yet: copy it now, then press OK.")" 17 || return 1
  f=$(wt_input "The backup file to put back (its full path):" "$(ls -t "$home"/zenithboard-backup-*.tar.gz 2>/dev/null | head -1)") || return 1
  [ -f "$f" ] || { wt_msg "No such file: $f\n\nNothing was changed. Copy it in your home folder and come back to Start here, or go on without it." 10; return 1; }
  clear; backup_restore "$f"; menu_pause
  return 0
}

# The list is the owner's: what a ZenithBoard should have on, each said in a line, ticked; only what is off is listed.
start_recommended() {
  local items=() sel x
  [ "$(stats_state)" = on ] || items+=(stats "Statistics: the /stats page and the Bluesky summaries" ON)
  if ! is_graphs && graphs_has_lighttpd; then items+=(graphs "graphs1090: years of graphs, in ZenithBoard's look (minutes)" ON); fi
  [ "$(keeplogs_state)" = on ] || items+=(keeplogs "Logs kept after a restart, to find why it stopped (50 MB)" ON)
  [ "$(watchdog_state)" = on ] || { [ -e "${ZB_WATCHDOG_DEV:-/dev/watchdog}" ] && items+=(watchdog "Hardware watchdog: a frozen Pi restarts by itself" ON); }
  [ "$(netwatch_state)" = on ] || items+=(netwatch "Network watchdog: the network, then the Pi, restarted if lost" ON)
  [ "$(patches_state)" = on ] || items+=(patches "Debian's security fixes, daily (the feeders left alone)" ON)
  [ "$(cfg_get LOG_AUTOCLEAN 0)" = 1 ] || items+=(logclean "Daily log clean-up, the last 7 days kept" ON)
  if [ "$(wifi_harden_state)" != on ] && [ -n "$(wifi_iface 2>/dev/null)" ] && [ -n "$(wifi_active_ssid 2>/dev/null)" ]; then
    items+=(wifiharden "Wi-Fi hardening: reconnects without end, no power saving" ON); fi
  [ "${#items[@]}" -gt 0 ] || return 0
  sel=$(wt_check "Worth switching on (Space unticks, Enter goes on). Each one can be switched off again, in the menu, the console or with its command." "${items[@]}") || return 0
  clear
  for x in $sel; do
    x=${x//\"/}
    case "$x" in
      stats) stats_on ;; graphs) graphs_on ;; keeplogs) keeplogs_on ;; watchdog) watchdog_on ;; netwatch) netwatch_on ;;
      patches) patches_on ;; logclean) logs_auto_on; echo "Daily log clean-up is ON (the last 7 days kept)." ;; wifiharden) wifi_harden_on ;;
    esac
  done
  [ -z "$sel" ] || menu_pause
}

start_console() {
  if [ "$(console_state)" != on ]; then
    wt_yesno "Last step: the web console, the same settings from a browser or a phone on your home network. You finish there: its first steps check what is left, it pairs your phone, and it shows every service.\n\nIt has its own password, chosen now (10 characters at least, asked twice).\n\nSwitch it on?" 15 || return 0
    clear
    # 0.54.5: a mistyped confirmation ended Start here at the main menu with the console off and no address shown
    until console_has_password; do
      console_password && break
      wt_yesno "The password was not saved (the two did not match, or it was too short).\n\nTry again?" 9 || { menu_pause; return 0; }
      clear
    done
    console_on; menu_pause
  fi
  wt_msg "Done. Open the web console on your computer or phone:\n\n    http://$(local_ip):$(cfg_get PORT 8080)/console\n\nSign in with the console password. Then:\n  - its first steps (they open by themselves) check what is left\n  - System → Signed in → Pair a phone\n  - Bluesky, if you post: menu 7 Options here (it asks for an app password)\n\nThe tablet: http://$(local_ip):$(cfg_get PORT 8080)/" 19
}

# ---------------------------------------------------------------- 1 ADS-B
adsb_section_menu() {
  local c
  while true; do
    c=$(wt_menu "ADS-B: what the dongle hears and who gets it\n\nDecoder: $(d=$(installed_decoder); echo "${d:-none yet}")    Region: $(cfg_get REGION world)\nAntenna: $(cfg_get LAT), $(cfg_get LON), $(cfg_get ALT_M 0) m" \
      networks "1  Decoder and networks: install, add, remove" \
      antenna "2  The antenna: position, altitude, region" \
      gain "3  Gain: check it, tune the dongle" \
      status "4  What is running, and the MLAT check" \
      back "Return to the previous menu") || return 0
    case "$c" in
      networks) adsb_menu ;;
      antenna)
        settings_location || continue
        settings_region
        clear; zb_apply_location "$(cfg_get LAT)" "$(cfg_get LON)" "$(cfg_get ALT_M 0)"
        echo; echo "Lines marked MANUAL can only be changed on the provider's website."; menu_pause ;;
      gain) gain_menu ;;
      status) clear; "$ZB_HOME/bin/zenithboard" status; menu_pause ;;
      *) return 0 ;;
    esac
  done
}

# ---------------------------------------------------------------- 2 The wall
wall_menu() {
  local c inst
  while true; do
    if is_flightinfo; then inst="Reinstall its files (the same version)"; else inst="Install the wall"; fi
    c=$(wt_menu "The wall: the page an old tablet shows ($(is_flightinfo && echo "http://$(local_ip):$(cfg_get PORT 8080)/" || echo "not installed"))\n\nRadius $(cfg_get RADIUS) $(units_distance "$(cfg_get UNITS)")    Look: $(cfg_get DISPLAY_MODE dots), $(wall_theme)    $(cfg_get CYCLE_SECONDS 14) s per aircraft\nPhotos $(menu_onoff "$( [ "$(cfg_get SHOW_PHOTOS 1)" = 1 ] && echo on)")    Routes $(menu_onoff "$( [ "$(cfg_get SHOW_ROUTES 1)" = 1 ] && echo on)")" \
      install "1  $inst" \
      show "2  What it shows: radius, units, seconds" \
      look "3  Its look: dots or split-flap, and colour" \
      data "4  Photos, routes, aircraft names" \
      presets "5  Presets: a tablet's own choices (?p=NAME)" \
      remove "6  Remove the wall (asks for a typed word)" \
      back "Return to the previous menu") || return 0
    case "$c" in
      install) clear; install_flightinfo; menu_pause ;;
      show) wall_show_menu ;;
      look)
        # the audit of 22-23 October 2026: Esc on the colour after a new look left the look written, on the wall at
        # its next reload, with no restart and no word; the look is kept and said, the colour as it was
        if settings_style; then
          settings_color; c=$?
          restart_flightinfo; graphs_look_keep
          wt_msg "Saved: $(cfg_get DISPLAY_MODE dots), $(wall_theme)$( [ "$c" = 0 ] || echo " (colour unchanged)").\n\nThe default for every screen. A tablet that chose its own (its gear icon, or ?mode=) keeps it until Reset in its gear panel." 11
        fi ;;
      data) wall_data_menu ;;
      presets) presets_menu ;;
      remove)
        is_flightinfo || { wt_msg "The wall is not installed." 7; continue; }
        wt_yesno "Remove the wall?\n\nThe feeders keep running; your settings stay in $ZB_CONFIG and the wall comes back with 'Install'. The web console goes with it (it is one of its pages)." 11 && [ "$(wt_input "To remove the wall, type the word  remove  (anything else cancels)." "")" = remove ] && { clear; remove_flightinfo; menu_pause; } ;;
      *) return 0 ;;
    esac
  done
}

wall_show_menu() {
  local c s
  while true; do
    c=$(wt_menu "What the wall shows\n\nRadius: $(cfg_get RADIUS)    Units: $(cfg_get UNITS)    Seconds per aircraft: $(cfg_get CYCLE_SECONDS 14)" \
      radius "1  Detection radius" \
      units "2  Units: metric, imperial or aviation (everywhere)" \
      cycle "3  Seconds each aircraft stays" \
      back "Return to the previous menu") || return 0
    case "$c" in
      radius) change_radius ;;
      units) settings_units && restart_flightinfo ;;
      cycle)
        while s=$(wt_input "Seconds each aircraft stays on the wall: whole seconds, 2 to 60." "$(cfg_get CYCLE_SECONDS 14)"); do
          if valid_cycle "$s"; then cfg_set CYCLE_SECONDS "$((10#$s))"; restart_flightinfo; break; fi
          wt_msg "Seconds per aircraft: whole seconds, 2 to 60. Nothing was changed." 8
        done ;;
      *) return 0 ;;
    esac
  done
}

# menu_yesno_set KEY QUESTION HEIGHT: Yes sets KEY to 1, No to 0, Esc leaves it as it was (and returns 2)
menu_yesno_set() {
  wt_yesno "$2" "$3"
  case $? in 0) cfg_set "$1" 1 ;; 1) cfg_set "$1" 0 ;; *) return 2 ;; esac
}
# menu_yesno_apply FUNC QUESTION HEIGHT: Yes runs FUNC 1, No FUNC 0 (the command's own function, so the menu does
# what the command does: 0.99.22), and says what it printed; Esc changes nothing (and returns 2)
menu_yesno_apply() {
  local v
  wt_yesno "$2" "$3"
  case $? in 0) v=1 ;; 1) v=0 ;; *) return 2 ;; esac
  wt_msg "$("$1" "$v" 2>&1)" 9
}
wall_data_menu() {
  local c
  while true; do
    c=$(wt_menu "Photos, routes and aircraft names\n\nPhotos: $(cfg_get SHOW_PHOTOS 1)    Routes: $(cfg_get SHOW_ROUTES 1)    Monthly names refresh: $(cfg_get AUTO_DATA_REFRESH 1)    Offline database: $(cfg_get LOCAL_DB 0)   (1 = on)" \
      photos "1  Photos (Planespotters, internet)" \
      routes "2  Routes: where each flight comes from and goes" \
      data "3  Monthly refresh of the model names" \
      localdb "4  Offline registrations (the map's database)" \
      back "Return to the previous menu") || return 0
    case "$c" in
      # the audit of 22-23 October 2026: Esc (whiptail's 255) was taken for No and switched the feature off; now
      # only Yes and No change anything (menu_yesno_set). 0.99.22: photos and routes go through the commands'
      # functions, which restart the wall so that the tablets reload, as `photos on|off` and `routes on|off` do
      photos) menu_yesno_apply wall_photos_set "Show aircraft photos (Planespotters) on the wall? Needs internet on the Pi." 8 ;;
      routes) menu_yesno_apply wall_routes_set "Show where each flight comes from and goes to?\n\nThe callsign (for example DLH4YK) is looked up on the free adsbdb.com database. When your decoder does not know an aircraft, its address is also used to find the model name. Needs internet on the Pi." 13 ;;
      data)
        menu_yesno_set AUTO_DATA_REFRESH "Refresh the aircraft model list automatically once a month?\n\n(Downloads a free list of aircraft names from GitHub. Needs internet on the Pi; the wall works without it.)" 12 && data_refresh_apply ;;
      localdb)
        wt_yesno "Read registrations and models from tar1090's aircraft database on this Pi?\n\nThe receiver map (tar1090) keeps it on the card and updates it itself. Nothing is downloaded and nothing is sent to the internet." 12
        case $? in
          0) [ -d "$(cfg_get LOCAL_DB_DIR /usr/local/share/tar1090/git-db/db)" ] && cfg_set LOCAL_DB 1 || wt_msg "No tar1090 database at $(cfg_get LOCAL_DB_DIR /usr/local/share/tar1090/git-db/db).\n\nIt comes with the receiver map (tar1090)." 10 ;;
          1) cfg_set LOCAL_DB 0 ;;
          *) continue ;;
        esac
        restart_flightinfo ;;
      *) return 0 ;;
    esac
  done
}

# ---------------------------------------------------------------- 3 Connectivity
connectivity_menu() {
  local c u
  while true; do
    c=$(wt_menu "Connectivity\n\nWi-Fi: $(wifi_summary)\nAddress: $(net_has_nm && { u=$(net_default_profile) && net_profile_summary "$u"; } || echo 'not managed by NetworkManager')\nDomain name: $(ddns_summary)    The wall answers: $(cfg_get ALLOW_FROM private)" \
      wifi "1  Wi-Fi: on/off, country, networks" \
      ip "2  A fixed address for the Pi" \
      outside "3  From outside your home, safely (read first)" \
      tailscale "4  Tailscale: from anywhere, no port opened ($(ts_state))" \
      name "5  A domain name for your home (DuckDNS...)" \
      status "6  Status of all of the above" \
      back "Return to the previous menu") || return 0
    case "$c" in
      wifi) wifi_menu ;;
      ip) net_static_menu ;;
      outside) outside_help ;;
      tailscale) tailscale_menu ;;
      name) ddns_menu ;;
      status) clear; net_status; echo; wifi_has_nm && [ -n "$(wifi_iface)" ] && { wifi_status; echo; }; ddns_status; echo; ddns_reach_note; echo; tailscale_status; menu_pause ;;
      *) return 0 ;;
    esac
  done
}

# Plain words on what opening the Pi to the internet means, and the safe way. Checked against what the code does:
# the wall answers the networks in ALLOW_FROM (home networks by default, a forwarded port gets a 403); the console
# answers home networks only, whatever ALLOW_FROM says; the receiver map (lighttpd, port 80) has no such guard.
outside_help() {
  local ip; ip=$(local_ip)
  wt_scroll "REACHING ZENITHBOARD FROM OUTSIDE YOUR HOME\n\nAt home everything works with no change: the wall (http://$ip:$(cfg_get PORT 8080)/), the web console, the receiver map.\n\nFrom outside, there are two ways. Only the first is safe.\n\n1. A VPN: your phone or computer joins your home network from anywhere. Nothing is open to the internet.\n   - The best: the VPN your router has built in (WireGuard or OpenVPN, in many home routers and boxes; its menu often says 'VPN server'). Connected through it you are 'at home': the wall AND the console answer, nothing to change on the Pi. If your home address changes, a domain name (item 5) lets the VPN find it.\n   - Or Tailscale on the Pi: item 4 of this menu installs it, connects it and lets the wall answer it (sudo zenithboard tailscale on), and takes it all away again. Free account on tailscale.com, its app on your phone. Works even behind a shared address (CGNAT). The web console over it too only if you choose.\n\n2. Opening a port in your router ('port forwarding'): the wall becomes PUBLIC.\n   DANGERS: no password and no encryption; anyone who finds it sees the aircraft around your antenna, which tells roughly where you live; robots scan every address all day.\n   If you still want it: a fixed address for the Pi (item 2), a domain name (item 5), forward ONLY port $(cfg_get PORT 8080) to the Pi, then  sudo zenithboard config-set ALLOW_FROM any\n   NEVER forward port 22 (SSH: your Pi's login) or port 80 (the receiver map has no guard). The console never answers from the internet anyway.\n\nCheck what is open at any time: menu 4 Troubleshoot -> Security check.\nSome internet providers share one public address between many homes (CGNAT): no port can be opened then, a VPN like Tailscale still works."
}

# ---------------------------------------------------------------- 4 Troubleshoot
troubleshoot_menu() {
  local c l
  while true; do
    c=$(wt_menu "Troubleshoot\n\nWatchdogs: hardware $(watchdog_state), network $(netwatch_state)    Logs kept after a restart: $(keeplogs_state)" \
      health "1  Health: power, heat, memory, card, last start" \
      status "2  What is running, and the MLAT check" \
      memory "3  Memory, service by service" \
      logs "4  The last lines of a log" \
      security "5  Security: what is open, what to close" \
      reliability "6  Watchdogs, logs kept after a restart" \
      housekeeping "7  Log housekeeping: size, clean-up" \
      back "Return to the previous menu") || return 0
    case "$c" in
      health) clear; health_check; menu_pause ;;
      status) clear; "$ZB_HOME/bin/zenithboard" status; menu_pause ;;
      memory) clear; python3 "$ZB_HOME/tools/memory_report.py"; menu_pause ;;
      logs)
        l=$(wt_radio "Whose log? (the last 100 lines)" flightinfo "The wall" ON decoder "The decoder" OFF social "Bluesky posts" OFF telegram "Telegram messages" OFF radarbox "AirNav Radar" OFF uat "978 MHz UAT" OFF) || continue
        clear; "$ZB_HOME/bin/zenithboard" logs "$l"; menu_pause ;;
      security) clear; security_check; menu_pause ;;
      reliability) reliability_menu ;;
      housekeeping) logs_menu ;;
      *) return 0 ;;
    esac
  done
}

# ---------------------------------------------------------------- 6 Backup
backup_section_menu() {
  local c f out d home
  home=$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)
  while true; do
    c=$(wt_menu "Backup: everything in one file (settings, what is on, statistics, graphs, kept logs, the networks' identities), to keep or to move to a new card. Copy it off the Pi: WinSCP from Windows.\n\nIn $home: $(ls "$home"/zenithboard-backup-*.tar.gz 2>/dev/null | wc -l) backup(s)" \
      make "1  Make a backup now (in your home folder)" \
      restore "2  Put a backup back (asks you to type RESTORE)" \
      manage "3  Show, list, delete older backups" \
      uninstall "4  Uninstall everything (asks for a typed word)" \
      save "5  Settings only: save them to a file" \
      import "6  Settings only: put them back from a file" \
      back "Return to the previous menu") || return 0
    case "$c" in
      make) out=$(backup_make "$home/zenithboard-backup-$(hostname)-$(date +%Y%m%d-%H%M).tar.gz" 2>&1); wt_msg "$out\n\nTo copy it to your computer: WinSCP (Windows) or scp. Help: the wiki page 'Moving to a new card'." 20 ;;
      restore)
        f=$(wt_input "The backup file to put back (its full path; copy it here first, WinSCP from Windows):" "$(ls -t "$home"/zenithboard-backup-*.tar.gz 2>/dev/null | head -1)") || continue
        clear; backup_restore "$f"; menu_pause ;;
      manage) backup_menu ;;
      uninstall) uninstall_all ;;
      save)
        d="$home"; [ -d "$d" ] || d="${HOME:-/root}"
        f=$(wt_input "Where to write the settings file." "$d/zenithboard-settings-$(hostname)-$(date +%Y%m%d).env") || continue
        if out=$(settings_export "$f" 2>&1); then
          [ -n "${SUDO_USER:-}" ] && chown "$SUDO_USER" "$f" 2>/dev/null
          wt_msg "Saved: $out\n\nOn another Pi:  sudo zenithboard settings import FILE" 10
        else wt_msg "$out" 8; fi ;;
      import)
        f=$(wt_input "The settings file to put back." "") || continue
        [ -f "$f" ] || { wt_msg "No such file: $f" 7; continue; }
        wt_yesno "Put back the settings in $f?\n\nEvery setting in it replaces the current one. The current file is kept first as $ZB_CONFIG.bak-DATE, so this can be undone the same way." 12 || continue
        clear; settings_import "$f" && settings_apply; menu_pause ;;
      *) return 0 ;;
    esac
  done
}

# ---------------------------------------------------------------- 7 Options
options_menu() {
  local c
  while true; do
    c=$(wt_menu "Options, each off until you switch it on (graphs1090's look excepted)\n\nStatistics: $(stats_state)    graphs1090: $(graphs_state)    Bluesky: $(social_state)    Telegram: $(telegram_state)    Web console: $(console_state)" \
      stats "1  Statistics, the /stats page: $(stats_state)" \
      graphs "2  graphs1090, years of graphs: $(graphs_state)" \
      social "3  Bluesky posts and summaries: $(social_state)" \
      console "4  Web console, from a browser: $(console_state)" \
      telegram "5  Telegram messages to your own chat: $(telegram_state)" \
      back "Return to the previous menu") || return 0
    case "$c" in
      stats)
        if [ "$(stats_state)" = on ]; then
          wt_yesno "Statistics are ON: a sample every 15 minutes, 30 days kept, at http://$(local_ip):$(cfg_get PORT 8080)/stats\n\nTurn them OFF? (the files are kept; the Bluesky summaries need them)" 12 && { clear; stats_off; menu_pause; }
        else
          wt_yesno "Collect statistics?\n\nEvery 15 minutes: messages, the farthest aircraft, the aircraft seen, their airlines, models and altitudes. About 30 KB a day on the card, 30 days kept. Read them at http://$(local_ip):$(cfg_get PORT 8080)/stats" 13 && { clear; stats_on; menu_pause; }
        fi ;;
      graphs) graphs_menu ;;
      social) social_menu ;;
      telegram) telegram_menu ;;
      console) console_menu ;;
      *) return 0 ;;
    esac
  done
}

graphs_menu() {
  local c
  while true; do
    c=$(wt_menu "graphs1090: $(graphs_state)$(is_graphs && echo "  -  http://$(local_ip):$GRAPHS_PORT/")\nIts look: $(graphs_look_state)" \
      onoff "1  Switch graphs1090 $(is_graphs && echo OFF || echo ON)" \
      look "2  Its look: ZenithBoard's (default) or its own" \
      back "Return to the previous menu") || return 0
    case "$c" in
      onoff)
        if is_graphs; then
          wt_yesno "graphs1090 is ON.\n\nTurn it OFF? Its packages that were not there before go; its history stays on the card for a later 'on'." 11 && { clear; graphs_off; menu_pause; }
        else
          wt_yesno "Install graphs1090?\n\nwiedehopf's graphs of the receiver: messages, range, signal, aircraft, CPU and temperature, kept for years, on port $GRAPHS_PORT, in ZenithBoard's look. Installed by its author's script (collectd and rrdtool from apt). Needs the receiver map's web server.\n\nIts graphs live in memory and go to the card once a day and at shutdown." 15 && { clear; graphs_on; menu_pause; }
        fi ;;
      look)
        is_graphs || { wt_msg "graphs1090 is not installed: item 1 first." 8; continue; }
        if [ "$(graphs_look_state)" = zenithboard ]; then
          wt_yesno "graphs1090 is in ZenithBoard's look.\n\nBack to its own look (its light page and colours)?" 10 && { clear; graphs_look original; menu_pause; }
        else
          wt_yesno "Give graphs1090 ZenithBoard's look again?" 8 && { clear; graphs_look zenithboard; menu_pause; }
        fi ;;
      *) return 0 ;;
    esac
  done
}
