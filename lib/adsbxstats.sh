# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# ADSB Exchange's stats package (0.52.0, optional, off by default). It is what fills "Feed Details" on
# https://www.adsbexchange.com/myip/. Without it, that panel says "Feed UID Not Found / No Stats" while the feed and
# MLAT are fine (the owner's screenshot, 22 October 2026). With it, ADSB Exchange shows ADS-B Exchange Anywhere (a map
# of only the aircraft this antenna hears, viewable from anywhere) and the receiver's statistics. Their site also
# needs it to claim the receiver under an ADSB Exchange account; ZenithBoard never creates that account.
#
# It is installed by ADSB Exchange's own script, as the feed is. https://adsbexchange.com/stats.sh clones
# github.com/adsbexchange/adsbexchange-stats and runs its install.sh. What that does, read on 22 October 2026
# (commit 11647f2, February 2023):
#   - installs curl, jq, gzip, bind9-host, perl and bash-builtins with apt when one is missing, and git to fetch itself;
#   - copies itself to /usr/local/share/adsbexchange-stats, and adds the adsbexchange-stats unit (user adsbexchange,
#     nice 19) and /usr/local/bin/adsbexchange-showurl;
#   - adds the adsbexchange user to the video group, for vcgencmd;
#   - keeps the feed's UUID (/usr/local/share/adsbexchange/adsbx-uuid).
# Every 5 seconds the service sends adsbexchange.com/api/receive/ the UUID and the feed's aircraft list
# (/run/adsbexchange-feed/aircraft.json, the aircraft the feed already sends them). It adds three signal figures and
# the Pi's power warnings (vcgencmd get_throttled).
#
# `off` puts back what `on` found: their own uninstaller (the unit, its folder, adsbexchange-showurl), the video group
# when the user was not in it, and the packages that were not there before `on`. apt is asked first what it would
# take with them. The UUID stays: it is the feed's, and the backup keeps it. ADSB Exchange's uninstaller of the feed
# leaves this service running, failing every two minutes, so removing ADSB Exchange removes it first (remove_adsbx).

AXS_ROOT="${ZB_AXS_ROOT:-}"                                     # tests run against a folder standing in for /
AXS_HOME="$AXS_ROOT/usr/local/share/adsbexchange-stats"
AXS_UNIT="$AXS_ROOT/etc/systemd/system/adsbexchange-stats.service"
AXS_SHOWURL="$AXS_ROOT/usr/local/bin/adsbexchange-showurl"
AXS_UUID="$AXS_ROOT/usr/local/share/adsbexchange/adsbx-uuid"
AXS_CLONE="${ZB_AXS_CLONE:-/tmp/adsbexchange-stats-git}"        # where their stats.sh clones itself
AXS_STATE="${ZENITHBOARD_ETC:-/etc/zenithboard}/adsbx-stats.state"
# what their adsbexchange-showurl prints, the UUID after it (read in its code, 22 October 2026)
AXS_MAP="https://www.adsbexchange.com/api/feeders/?feed="

is_adsbx_stats() { [ -f "$AXS_UNIT" ]; }
adsbx_stats_state() { is_adsbx_stats && echo on || echo off; }

adsbx_stats_uuid() {
  local u; u=$(tr -d ' \r\n{}' < "$AXS_UUID" 2>/dev/null)
  [[ $u =~ ^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$ ]] && printf '%s\n' "$u"
}
adsbx_stats_url() { local u; u=$(adsbx_stats_uuid) && printf '%s%s\n' "$AXS_MAP" "$u"; }

axs_state_get() { sed -n "s/^$1=\"\{0,1\}\([^\"]*\)\"\{0,1\}\$/\1/p" "$AXS_STATE" 2>/dev/null | tail -1; }
axs_state_set() {
  install -d -m 755 "$(dirname "$AXS_STATE")"
  touch "$AXS_STATE"; chmod 644 "$AXS_STATE"
  sed -i "/^$1=/d" "$AXS_STATE"
  printf '%s="%s"\n' "$1" "$2" >> "$AXS_STATE"
}
# installed packages only: one removed with its settings left ("rc") is not counted as there
axs_packages() { dpkg-query -W -f='${db:Status-Status} ${binary:Package}\n' 2>/dev/null | awk '$1 == "installed" {sub(/:.*/, "", $2); print $2}' | sort -u; }
axs_in_video() { id -nG adsbexchange 2>/dev/null | tr ' ' '\n' | grep -qx video; }

# Their script (on, and the update), noting the packages it added: those, and only those, go with `off`.
axs_run_installer() {
  local before after script added
  before=$(zb_tmp axstats-before) && after=$(zb_tmp axstats-after) && script=$(zb_tmp axstats.sh) || return 1
  axs_packages > "$before"
  fetch "$ADSBX_STATS_URL" "$script" || { err "Could not download ADSB Exchange's stats script."; return 1; }
  ( cd / && bash "$script" ) || err "ADSB Exchange's stats script reported an error (above)."
  axs_packages > "$after"
  added=$(comm -13 "$before" "$after" | tr '\n' ' ' | sed 's/ *$//')
  if [ -n "$added" ]; then
    axs_state_set ADDED "$(printf '%s %s' "$(axs_state_get ADDED)" "$added" | tr ' ' '\n' | sed '/^$/d' | sort -u | tr '\n' ' ' | sed 's/ *$//')"
  fi
  # their stats.sh leaves its clone in /tmp; a link there is somebody else's, never followed
  if [ -d "$AXS_CLONE" ] && [ ! -L "$AXS_CLONE" ]; then rm -rf "$AXS_CLONE"; fi
  is_adsbx_stats
}

adsbx_stats_where() {
  local url
  url=$(adsbx_stats_url) || { warn "The feed's UUID ($AXS_UUID) is missing or unreadable: run the ADSB Exchange setup again (menu 1)."; return 0; }
  echo "  Your map, only the aircraft this antenna hears, from anywhere (a minute or two after the start):"
  echo "    $url"
  echo "  The same link is at the bottom of https://www.adsbexchange.com/myip/ opened from your home network."
  echo "  Keep it to yourself: the aircraft on it show roughly where the antenna is."
}

adsbx_stats_on() {
  if is_adsbx_stats; then echo "ADSB Exchange stats are already on."; adsbx_stats_where; return 0; fi
  is_adsbx || { err "ADSB Exchange's stats read what its feed receives: install ADSB Exchange first (menu 1 ADSB). Nothing was changed."; return 1; }
  # what `off` puts back: whether the adsbexchange user was in the video group; the packages are noted as they come
  [ -f "$AXS_STATE" ] || { axs_state_set VIDEO "$(axs_in_video && echo 1 || echo 0)"; axs_state_set ADDED ""; }
  log "Installing ADSB Exchange's stats package (their script: a minute or two)"
  axs_run_installer || { err "ADSB Exchange's stats are not installed. To put back what was changed: sudo zenithboard adsbx-stats off"; return 1; }
  echo "ADSB Exchange stats are ON. Every 5 seconds the Pi sends them the aircraft it hears (the list their feed already"
  echo "gets), with its power warnings."
  adsbx_stats_where
  echo "  Off again: sudo zenithboard adsbx-stats off"
}

adsbx_stats_off() {
  local added extra out
  if ! is_adsbx_stats && [ ! -f "$AXS_STATE" ]; then echo "ADSB Exchange stats are already off."; return 0; fi
  log "Removing ADSB Exchange's stats package"
  if [ -f "$AXS_HOME/uninstall.sh" ]; then
    out=$(zb_tmp axstats-uninstall.out) || out=/dev/null
    bash "$AXS_HOME/uninstall.sh" > "$out" 2>&1 || { cat "$out" 2>/dev/null; warn "Their uninstaller reported an error (above); going on."; }
  fi
  # what their uninstaller removes, for a copy that came without one (their README: early versions)
  systemctl disable --now adsbexchange-stats >/dev/null 2>&1 || true
  rm -f "$AXS_UNIT" "$AXS_SHOWURL"; rm -rf "$AXS_HOME"
  systemctl daemon-reload >/dev/null 2>&1 || true
  if [ "$(axs_state_get VIDEO)" = 0 ] && axs_in_video; then gpasswd -d adsbexchange video >/dev/null 2>&1 || true; fi
  added=$(axs_state_get ADDED)
  if [ -n "$added" ]; then
    # shellcheck disable=SC2086
    extra=$(apt-get -s remove $added 2>/dev/null | awk '/^Remv /{print $2}' | sort -u | comm -23 - <(tr ' ' '\n' <<<"$added" | sort -u) | tr '\n' ' ')
    if [ -n "${extra// /}" ]; then
      warn "Removing the packages ADSB Exchange's stats brought ($added) would also remove: $extra. They are left installed."
    else
      # shellcheck disable=SC2086
      DEBIAN_FRONTEND=noninteractive apt-get remove -y $added >/dev/null || warn "Some packages were not removed: $added"
    fi
  fi
  rm -f "$AXS_STATE"
  echo "ADSB Exchange stats are OFF: nothing more is sent besides the feed. The feed's UUID is kept, so 'on' again"
  echo "gives the same map."
}

adsbx_stats_status() {
  if is_adsbx_stats; then
    echo "ADSB Exchange stats: ON, $(systemctl is-active adsbexchange-stats 2>/dev/null || true)"
    adsbx_stats_where
  elif is_adsbx; then
    echo "ADSB Exchange stats: OFF. Their map of only your aircraft, and Feed Details on their page: sudo zenithboard adsbx-stats on"
  else
    echo "ADSB Exchange stats: OFF (they need ADSB Exchange's feed first: menu 1 ADSB)"
  fi
}

# zenithboard update: their script again, the way their README updates it (it starts the service again)
adsbx_stats_update() {
  is_adsbx_stats || return 0
  axs_run_installer || warn "ADSB Exchange stats update failed (above)"
}
