# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Updating: ZenithBoard itself (git pull) and every component installed through it.
# Safe to run any time and as often as you like; your settings in /etc/zenithboard are never touched.

# Bring the download folder in line with GitHub. A normal update is a fast-forward; if the history was rewritten
# upstream (e.g. the author re-signed the commits) the folder is simply reset to GitHub's version, as long as you
# have not edited any tracked file in it.
zb_sync_source() {  # zb_sync_source DIR
  local dir="$1" owner rc=0
  owner=$(stat -c '%u:%g' "$dir" 2>/dev/null)
  _zb_sync_source "$dir" || rc=$?
  # git ran as root: give the folder back to its owner, otherwise the owner's own `git fetch` fails with "Permission denied"
  [ -z "$owner" ] || chown -R "$owner" "$dir" 2>/dev/null || true
  return "$rc"
}

_zb_sync_source() {
  local dir="$1" branch
  local -a g=(git -c "safe.directory=$dir" -C "$dir")
  branch=$("${g[@]}" rev-parse --abbrev-ref HEAD 2>/dev/null) || return 1
  "${g[@]}" fetch -q origin "$branch" || { warn "Could not reach GitHub."; return 1; }
  "${g[@]}" merge --ff-only -q "origin/$branch" >/dev/null 2>&1 && return 0
  if [ -n "$("${g[@]}" status --porcelain --untracked-files=no)" ]; then
    warn "You changed files in $dir, so it was not updated. Undo with: git -C $dir checkout . (then update again)"
    return 1
  fi
  log "GitHub's history was rewritten (for example commits were re-signed): resynchronising $dir"
  "${g[@]}" reset -q --hard "origin/$branch"
}

# Components that can be updated one by one (the name is what `zenithboard update only NAME...` and the menu use).
ZB_COMPONENTS="zenithboard readsb dump1090 adsbx piaware fr24 planefinder flightinfo acars"
zb_component_label() {
  case "$1" in
    zenithboard) echo "ZenithBoard itself (installer, menu, wall code)" ;;
    readsb) echo "readsb decoder" ;;
    dump1090) echo "dump1090-fa decoder" ;;
    adsbx) echo "ADSB Exchange feeder + MLAT" ;;
    piaware) echo "FlightAware (piaware)" ;;
    fr24) echo "Flightradar24 (fr24feed)" ;;
    planefinder) echo "Plane Finder" ;;
    flightinfo) echo "FlightInfo wall + aircraft data" ;;
    acars) echo "ACARS (acarsdec) + Grafana" ;;
  esac
}
zb_component_installed() {
  case "$1" in
    zenithboard) return 0 ;;
    readsb) is_readsb ;; dump1090) is_dump1090 ;; adsbx) is_adsbx ;; piaware) is_piaware ;;
    fr24) is_fr24 ;; planefinder) is_planefinder ;; flightinfo) is_flightinfo ;; acars) is_acars ;;
    *) return 1 ;;
  esac
}
zb_component_version() {   # a short version when it is cheap to know, else nothing
  local v=""
  case "$1" in
    zenithboard) v="$ZB_VERSION" ;;
    readsb) v=$(readsb --version 2>&1 | head -1 | grep -oE '[0-9][0-9A-Za-z.+~-]*' | head -1) ;;
    dump1090) v=$(dpkg-query -W -f='${Version}' dump1090-fa 2>/dev/null) ;;
    piaware) v=$(dpkg-query -W -f='${Version}' piaware 2>/dev/null) ;;
    fr24) v=$(dpkg-query -W -f='${Version}' fr24feed 2>/dev/null) ;;
  esac
  printf '%s' "$v"
}
zb_update_list() {   # what is installed, and what `update only` accepts
  local c v
  for c in $ZB_COMPONENTS; do
    zb_component_installed "$c" || continue
    v=$(zb_component_version "$c")
    printf '  %-12s %s%s\n' "$c" "$(zb_component_label "$c")" "${v:+  ($v)}"
  done
}

# zb_update [--no-pull] [--only NAME...]
#   no arguments : everything installed (ZenithBoard code, then every component)
#   --only NAMES : just those (name "zenithboard" = the ZenithBoard code itself; without it the code is not pulled)
zb_update() {
  local src="" old="$ZB_VERSION" pull=1 only=0 c names=()
  while [ $# -gt 0 ]; do
    case "$1" in
      --no-pull) pull=0 ;;
      --only) only=1; pull=0 ;;
      "") ;;
      *) names+=("$1") ;;
    esac; shift
  done
  if [ "$only" = 1 ]; then
    for c in "${names[@]}"; do
      case " $ZB_COMPONENTS " in *" $c "*) ;; *) err "Unknown component: $c. Choose from: $ZB_COMPONENTS"; return 1 ;; esac
      zb_component_installed "$c" || { err "$c is not installed (see: zenithboard update list)"; return 1; }
      [ "$c" != zenithboard ] || pull=1
    done
  fi
  [ -f "$ZB_HOME/.source" ] && src=$(cat "$ZB_HOME/.source")
  if [ "$pull" = 1 ] && [ -n "$src" ] && [ -d "$src/.git" ]; then
    log "Updating ZenithBoard from GitHub ($src), current version $old"
    zb_sync_source "$src" || warn "The ZenithBoard code was NOT updated: staying on version $old."
    bash "$src/install.sh" --deploy                      # copy the new files to /opt/zenithboard
  elif [ "$pull" = 1 ]; then
    warn "Original download folder not found: skipping the ZenithBoard code update (git clone it again to get the newest version)."
  fi
  if [ "$only" = 1 ]; then
    local rest=(); for c in "${names[@]}"; do [ "$c" = zenithboard ] || rest+=("$c"); done
    exec "$ZB_HOME/bin/zenithboard" update-components --only "${rest[@]}"
  fi
  exec "$ZB_HOME/bin/zenithboard" update-components      # run the freshly deployed code
}

# zb_update_components [--only NAME...]   (no arguments = every installed component)
zb_update_components() {
  local only=0; [ "${1:-}" = "--only" ] && { only=1; shift; }
  local sel=("$@")
  want_c() { if [ "$only" = 0 ]; then return 0; fi; local x; for x in "${sel[@]}"; do [ "$x" = "$1" ] && return 0; done; return 1; }
  log "ZenithBoard $ZB_VERSION: updating installed components"
  ! want_c fr24 || [ -z "$(fr24_source_file)" ] || fr24_repair_key || warn "Flightradar24 signing key not refreshed (see above)."
  apt-get update -qq
  if want_c readsb && is_readsb; then
    log "readsb"; fetch "$READSB_INSTALL_URL" /tmp/readsb-install.sh && bash /tmp/readsb-install.sh || warn "readsb update failed"
  fi
  want_c dump1090 && is_dump1090 && { log "dump1090-fa"; apt_install --only-upgrade dump1090-fa || warn "dump1090-fa update failed"; }
  if want_c adsbx && is_adsbx; then
    log "ADSB Exchange"; fetch "$ADSBX_UPDATE_URL" /tmp/axupdate.sh && bash /tmp/axupdate.sh || warn "ADSB Exchange update failed"
  fi
  want_c piaware && is_piaware && { log "piaware"; apt_install --only-upgrade piaware || warn "piaware update failed"; }
  want_c fr24 && is_fr24 && { log "fr24feed"; apt_install --only-upgrade fr24feed || warn "fr24feed update failed"; }
  if want_c planefinder && is_planefinder; then
    log "Plane Finder"; install_planefinder || warn "Plane Finder update failed (check lib/versions.sh)"
  fi
  if want_c flightinfo && is_flightinfo; then
    log "FlightInfo"; ensure_zb_user          # also repairs the folder modes of older installs
    systemctl daemon-reload; install -m 644 "$ZB_HOME/systemd/zenithboard-flightinfo.service" /etc/systemd/system/; systemctl daemon-reload; restart_flightinfo
    data_refresh_apply
    [ "$(cfg_get AUTO_DATA_REFRESH 1)" != 1 ] || data_refresh_now || warn "aircraft data refresh failed (kept the previous data)"
  fi
  if want_c acars && is_acars; then
    log "ACARS (rebuilding acarsdec)"
    rm -f /usr/local/bin/acarsdec; build_acarsdec || warn "acarsdec rebuild failed"
    install -m 644 "$ZB_HOME"/systemd/zenithboard-acars-ingest.service "$ZB_HOME"/systemd/zenithboard-acarsdec.service /etc/systemd/system/
    systemctl daemon-reload; systemctl restart zenithboard-acars-ingest zenithboard-acarsdec
    is_grafana && { apt_install --only-upgrade grafana || warn "grafana update failed"; install -m 644 "$ZB_HOME/acars/grafana-dashboard.json" /var/lib/grafana/zenithboard-dashboards/acars.json; systemctl restart grafana-server; }
  fi
  if [ -f /etc/systemd/system/zenithboard-wifi.service ]; then wifi_install_unit; fi
  if [ "$(cfg_get DDNS_PROVIDER none)" != none ]; then ddns_install_units; fi
  if [ "$(cfg_get LOG_AUTOCLEAN 0)" = 1 ]; then logs_auto_on; fi
  zb_mlat_guard
  log "Update finished. Check:  zenithboard status"
}

# This menu is a running script: after an update it still holds the OLD code in memory. Start it again so the very next
# screen is the new version (the same menu, freshly loaded). Starting again is only possible from the real installer.
update_menu_reload() {
  read -rp "Press Enter to reopen the menu on the new version..." _
  local me="${ROOT:-$ZB_HOME}/install.sh"
  [ -x "$me" ] && exec "$me"
  return 0
}

# Menu 6: update everything, or pick components from a list (space = tick).
update_menu() {
  local c items=() sel x names=()
  while true; do
    c=$(wt_menu "Update\n\nZenithBoard $ZB_VERSION. Your settings are never touched." \
      all "Update everything (ZenithBoard + every installed component)" \
      pick "Choose what to update (tick the ones you want)" \
      list "What is installed" \
      back "Return to the previous menu") || return 0
    case "$c" in
      all) clear; "$ZB_HOME/bin/zenithboard" update; update_menu_reload ;;
      list) clear; zb_update_list; echo; read -rp "Press Enter..." _ ;;
      pick)
        items=(); for x in $ZB_COMPONENTS; do
          zb_component_installed "$x" || continue
          items+=("$x" "$(zb_component_label "$x")$( v=$(zb_component_version "$x"); [ -n "$v" ] && printf '  (%s)' "$v")" OFF)
        done
        sel=$(whiptail --title "$WT_TITLE" --checklist "Tick what to update (Space = tick, Enter = go).\nNothing ticked = nothing happens." 20 76 10 "${items[@]}" 3>&1 1>&2 2>&3) || continue
        eval "names=($sel)"
        [ "${#names[@]}" -gt 0 ] || { wt_msg "Nothing ticked, nothing updated." 7; continue; }
        clear; "$ZB_HOME/bin/zenithboard" update only "${names[@]}"; update_menu_reload ;;
      *) return 0 ;;
    esac
  done
}
