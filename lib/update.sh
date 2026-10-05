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

zb_update() {  # zb_update [--no-pull]
  local src="" old="$ZB_VERSION"
  [ -f "$ZB_HOME/.source" ] && src=$(cat "$ZB_HOME/.source")
  if [ "${1:-}" != "--no-pull" ] && [ -n "$src" ] && [ -d "$src/.git" ]; then
    log "Updating ZenithBoard from GitHub ($src), current version $old"
    zb_sync_source "$src" || warn "The ZenithBoard code was NOT updated: staying on version $old."
    bash "$src/install.sh" --deploy                      # copy the new files to /opt/zenithboard
  elif [ "${1:-}" != "--no-pull" ]; then
    warn "Original download folder not found: skipping the ZenithBoard code update (git clone it again to get the newest version)."
  fi
  exec "$ZB_HOME/bin/zenithboard" update-components      # run the freshly deployed code
}

zb_update_components() {
  log "ZenithBoard $ZB_VERSION: updating installed components"
  apt-get update -qq
  if is_readsb; then
    log "readsb"; fetch "$READSB_INSTALL_URL" /tmp/readsb-install.sh && bash /tmp/readsb-install.sh || warn "readsb update failed"
  fi
  is_dump1090 && { log "dump1090-fa"; apt_install --only-upgrade dump1090-fa || warn "dump1090-fa update failed"; }
  if is_adsbx; then
    log "ADSB Exchange"; fetch "$ADSBX_UPDATE_URL" /tmp/axupdate.sh && bash /tmp/axupdate.sh || warn "ADSB Exchange update failed"
  fi
  is_piaware && { log "piaware"; apt_install --only-upgrade piaware || warn "piaware update failed"; }
  is_fr24 && { log "fr24feed"; apt_install --only-upgrade fr24feed || warn "fr24feed update failed"; }
  if is_planefinder; then
    log "Plane Finder"; install_planefinder || warn "Plane Finder update failed (check lib/versions.sh)"
  fi
  if is_flightinfo; then
    log "FlightInfo"; ensure_zb_user          # also repairs the folder modes of older installs
    systemctl daemon-reload; install -m 644 "$ZB_HOME/systemd/zenithboard-flightinfo.service" /etc/systemd/system/; systemctl daemon-reload; restart_flightinfo
    data_refresh_apply
    [ "$(cfg_get AUTO_DATA_REFRESH 1)" != 1 ] || data_refresh_now || warn "aircraft data refresh failed (kept the previous data)"
  fi
  if is_acars; then
    log "ACARS (rebuilding acarsdec)"
    rm -f /usr/local/bin/acarsdec; build_acarsdec || warn "acarsdec rebuild failed"
    install -m 644 "$ZB_HOME"/systemd/zenithboard-acars-ingest.service "$ZB_HOME"/systemd/zenithboard-acarsdec.service /etc/systemd/system/
    systemctl daemon-reload; systemctl restart zenithboard-acars-ingest zenithboard-acarsdec
    is_grafana && { apt_install --only-upgrade grafana || warn "grafana update failed"; install -m 644 "$ZB_HOME/acars/grafana-dashboard.json" /var/lib/grafana/zenithboard-dashboards/acars.json; systemctl restart grafana-server; }
  fi
  zb_mlat_guard
  log "Update finished. Check:  zenithboard status"
}
