# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# graphs1090 (0.32.0, optional, off by default): wiedehopf's graphs of the receiver, years of history: messages,
# range, signal, aircraft, CPU, temperature. The owner chose it with the removal of Grafana (0.30.0): the wall's
# /stats page keeps thirty days of what ZenithBoard measures; graphs1090 is the long view of the decoder itself.
#
# It is installed by its author's own script (https://github.com/wiedehopf/graphs1090), the way readsb and tar1090
# are: packages from apt (signed, never bypassed), its files from GitHub. What the script does, read on 20 October
# 2026 (commit 2f96314): it installs collectd-core, rrdtool, git, wget, unzip and bash-builtins; copies itself to
# /usr/share/graphs1090; replaces /etc/collectd/collectd.conf (the old one kept as collectd.conf.graphs1090); keeps
# the graphs' data in memory (/run/collectd) and writes it to the card once a day at 23:42 and at shutdown;
# adds two lighttpd files, /graphs1090 on port 80 and its own port 8542. So it needs lighttpd, which the receiver
# map (tar1090, and FlightAware's SkyAware) brings.
#
# `off` puts back what `on` found: graphs1090's own uninstaller, then the files it leaves behind (the lighttpd
# files, its unit, its settings, its cron line), then the packages that were not there before `on`, with
# `apt-get remove`: Debian's purge of collectd-core deletes /var/lib/collectd, the history, by default. The history
# stays on the card for a later `on`, and the command to delete it is said.

GRAPHS_ROOT="${ZB_GRAPHS_ROOT:-}"                      # tests run against a folder standing in for /
GRAPHS_HOME="$GRAPHS_ROOT/usr/share/graphs1090"
GRAPHS_PORT=8542
GRAPHS_STATE="${ZENITHBOARD_ETC:-/etc/zenithboard}/graphs1090.state"
GRAPHS_RUN_MIN_MB=64                                   # the graphs live in /run: what they take, plus room to spare
GRAPHS_LIGHTTPD_FILES="88-graphs1090.conf 95-graphs1090-otherport.conf"

graphs_has_lighttpd() { command -v lighttpd >/dev/null 2>&1 || [ -x /usr/sbin/lighttpd ]; }
is_graphs() { [ -f "$GRAPHS_HOME/html/index.html" ]; }
graphs_state() { is_graphs && echo on || echo off; }
graphs_version() { head -1 "$GRAPHS_HOME/version" 2>/dev/null; }
graphs_packages() { dpkg-query -W -f='${binary:Package}\n' 2>/dev/null | sed 's/:.*//' | sort -u; }
graphs_run_free_mb() { df -Pm "$GRAPHS_ROOT/run" 2>/dev/null | awk 'NR==2 {print $4}'; }
graphs_du() { [ -e "$1" ] && du -sh "$1" 2>/dev/null | cut -f1; }

graphs_urls() {
  local ip; ip=$(local_ip)
  echo "    http://$ip:$GRAPHS_PORT/   (or http://$ip/graphs1090/)"
}

# Run graphs1090's installer (on, and the update), noting the packages it added: those, and only those, go with `off`.
graphs_run_installer() {
  local before after script added
  before=$(zb_tmp graphs-before) && after=$(zb_tmp graphs-after) && script=$(zb_tmp graphs1090-install.sh) || return 1
  graphs_packages > "$before"
  fetch "$GRAPHS1090_INSTALL_URL" "$script" || { err "Could not download graphs1090's installer."; return 1; }
  bash "$script" || { err "graphs1090's installer failed (above). Run again: sudo zenithboard graphs on"; }
  graphs_packages > "$after"
  added=$(comm -13 "$before" "$after" | tr '\n' ' ' | sed 's/ *$//')
  if [ -n "$added" ]; then
    local old; old=$(graphs_state_get ADDED)
    graphs_state_set ADDED "$(printf '%s %s' "$old" "$added" | tr ' ' '\n' | sed '/^$/d' | sort -u | tr '\n' ' ' | sed 's/ *$//')"
  fi
  is_graphs
}

graphs_state_get() { sed -n "s/^$1=\"\{0,1\}\([^\"]*\)\"\{0,1\}\$/\1/p" "$GRAPHS_STATE" 2>/dev/null | tail -1; }
graphs_state_set() {
  install -d -m 755 "$(dirname "$GRAPHS_STATE")"
  touch "$GRAPHS_STATE"; chmod 644 "$GRAPHS_STATE"
  sed -i "/^$1=/d" "$GRAPHS_STATE"
  printf '%s="%s"\n' "$1" "$2" >> "$GRAPHS_STATE"
}

graphs_on() {
  local free
  if is_graphs; then
    echo "graphs1090 is already on (version $(graphs_version)):"; graphs_urls; return 0
  fi
  [ -n "$(installed_decoder)" ] || { err "graphs1090 draws the decoder's statistics: install a decoder first (menu 1 ADSB)."; return 1; }
  graphs_has_lighttpd || {
    err "graphs1090's pages are served by lighttpd, which comes with the receiver map (tar1090, installed with readsb, or FlightAware's SkyAware). lighttpd is not installed: nothing was changed."
    return 1; }
  free=$(graphs_run_free_mb)
  if [ -n "$free" ] && [ "$free" -lt "$GRAPHS_RUN_MIN_MB" ]; then
    err "graphs1090 keeps its graphs in memory (/run), and only ${free} MB are free there (${GRAPHS_RUN_MIN_MB} MB needed): the decoder writes its aircraft there too. Nothing was changed."
    return 1
  fi
  # what is put back by `off`: whether collectd's settings folder and lighttpd's mod_alias file were already there
  [ -f "$GRAPHS_STATE" ] || {
    graphs_state_set COLLECTD_ETC "$([ -d "$GRAPHS_ROOT/etc/collectd" ] && echo 1 || echo 0)"
    graphs_state_set MOD_ALIAS "$([ -e "$GRAPHS_ROOT/etc/lighttpd/conf-enabled/07-mod_alias.conf" ] && echo 1 || echo 0)"
    graphs_state_set ADDED ""
  }
  log "Installing graphs1090 (wiedehopf's installer: a minute or two)"
  graphs_run_installer || { err "graphs1090 is not installed. To put back what was changed: sudo zenithboard graphs off"; return 1; }
  cfg_set GRAPHS1090 1
  echo "graphs1090 is ON (version $(graphs_version)). The first points appear within ten minutes:"
  graphs_urls
  echo "    Its graphs are kept in memory and written to the card once a day (23:42) and at shutdown: unplugging"
  echo "    the Pi without 'sudo shutdown now' loses up to a day of them. Off again: sudo zenithboard graphs off"
}

graphs_off() {
  local added f extra
  if ! is_graphs && [ ! -f "$GRAPHS_STATE" ]; then echo "graphs1090 is already off."; cfg_set GRAPHS1090 0; return 0; fi
  log "Removing graphs1090"
  # its own uninstaller first: it stops collectd, which writes the graphs from memory to the card
  if [ -f "$GRAPHS_HOME/uninstall.sh" ]; then bash "$GRAPHS_HOME/uninstall.sh" || warn "graphs1090's uninstaller reported an error (above); going on."; fi
  # what that uninstaller leaves behind (read in its code): the lighttpd files, the unit, the settings, the cron line
  for f in $GRAPHS_LIGHTTPD_FILES; do rm -f "$GRAPHS_ROOT/etc/lighttpd/conf-enabled/$f" "$GRAPHS_ROOT/etc/lighttpd/conf-available/$f"; done
  if [ "$(graphs_state_get MOD_ALIAS)" = 0 ]; then
    rm -f "$GRAPHS_ROOT/etc/lighttpd/conf-enabled/07-mod_alias.conf" "$GRAPHS_ROOT/etc/lighttpd/conf-available/07-mod_alias.conf"
  fi
  systemctl disable --now graphs1090 >/dev/null 2>&1 || true
  rm -f "$GRAPHS_ROOT/lib/systemd/system/graphs1090.service" "$GRAPHS_ROOT/etc/default/graphs1090" "$GRAPHS_ROOT/etc/cron.d/collectd_to_disk" \
        "$GRAPHS_ROOT/etc/systemd/system/collectd.service.d/malarky.conf"
  rm -rf "$GRAPHS_HOME" "$GRAPHS_ROOT/var/lib/graphs1090" "$GRAPHS_ROOT/run/graphs1090"
  systemctl daemon-reload >/dev/null 2>&1 || true
  graphs_has_lighttpd && { systemctl restart lighttpd >/dev/null 2>&1 || warn "lighttpd did not restart: sudo systemctl status lighttpd"; }
  # the packages `on` added, and nothing else: apt is asked first what it would remove, and a package that something
  # installed since depends on is left in place rather than taken with it
  added=$(graphs_state_get ADDED)
  if [ -n "$added" ]; then
    # shellcheck disable=SC2086
    extra=$(apt-get -s remove $added 2>/dev/null | awk '/^Remv /{print $2}' | sort -u | comm -23 - <(tr ' ' '\n' <<<"$added" | sort -u) | tr '\n' ' ')
    if [ -n "${extra// /}" ]; then
      warn "Removing the packages graphs1090 brought ($added) would also remove: $extra. They are left installed."
    else
      systemctl stop collectd >/dev/null 2>&1 || true
      # shellcheck disable=SC2086
      DEBIAN_FRONTEND=noninteractive apt-get remove -y $added || warn "Some packages were not removed: $added"
      [ "$(graphs_state_get COLLECTD_ETC)" = 1 ] || rm -rf "$GRAPHS_ROOT/etc/collectd"
    fi
  fi
  rm -f "$GRAPHS_STATE"
  cfg_set GRAPHS1090 0
  echo "graphs1090 is OFF."
  if [ -d "$GRAPHS_ROOT/var/lib/collectd/rrd" ]; then
    echo "Its history is kept on the card ($(graphs_du "$GRAPHS_ROOT/var/lib/collectd/rrd"), /var/lib/collectd/rrd): 'graphs on' picks it up again."
    echo "To delete it:  sudo rm -r /var/lib/collectd/rrd"
  fi
}

# zenithboard update: graphs1090's installer again (it stops at once when its version has not changed)
graphs_update() { is_graphs || return 0; graphs_run_installer || warn "graphs1090 update failed (above)"; }

graphs_status() {
  echo "graphs1090: $(graphs_state)$(is_graphs && printf ' (version %s)' "$(graphs_version)")"
  is_graphs || { echo "    Turn it on: sudo zenithboard graphs on   (menu 3 Settings -> 2 Receiver -> 6)"; return 0; }
  graphs_urls
  echo "    collectd: $(systemctl is-active collectd 2>/dev/null)   graph drawing: $(systemctl is-active graphs1090 2>/dev/null)"
  echo "    In memory (/run/collectd): $(graphs_du "$GRAPHS_ROOT/run/collectd" || echo '?')   on the card (/var/lib/collectd): $(graphs_du "$GRAPHS_ROOT/var/lib/collectd" || echo '?')   /run free: $(graphs_run_free_mb) MB"
  local m; m=$(systemctl show -p MemoryCurrent --value collectd 2>/dev/null)
  case "$m" in ''|*[!0-9]*) ;; *) echo "    collectd's memory: $((m / 1048576)) MB" ;; esac
}
