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
  graphs_look_keep
  ! declare -F bk_pending_apply >/dev/null || bk_pending_apply graphs       # 0.42.0: the history from a backup
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
  cfg_set GRAPHS1090 0                             # GRAPHS_LOOK is kept: a later `on` puts the chosen look back
  echo "graphs1090 is OFF."
  if [ -d "$GRAPHS_ROOT/var/lib/collectd/rrd" ]; then
    echo "Its history is kept on the card ($(graphs_du "$GRAPHS_ROOT/var/lib/collectd/rrd"), /var/lib/collectd/rrd): 'graphs on' picks it up again."
    echo "To delete it:  sudo rm -r /var/lib/collectd/rrd"
  fi
}

# zenithboard update: graphs1090's installer again (it stops at once when its version has not changed)
graphs_update() {
  is_graphs || return 0
  graphs_run_installer || warn "graphs1090 update failed (above)"
  graphs_look_keep                                 # 0.43.0: its installer writes its page again: the look goes back on
}

# ---- 0.43.0: graphs1090 in ZenithBoard's look (the owner, 21 October 2026); since 0.44.0 the default whenever
# graphs1090 is on (the owner again: "as default, just a command to disable it"), `graphs look original` to opt out.
# Two things, both graphs1090's own ways: the graphs' colours are rrdtool's, set by variables graphs1090 reads from
# /etc/default/graphs1090 after its own colour schemes (graphs1090.sh sources that file again after them, commit
# 2f96314), so a block at its end wins; and the page gets a stylesheet and a script beside its own, linked from its
# index.html. `original` takes the block, the two links and the three files away; graphs1090's dark scheme is part
# of the block, so its own page switches back to light by itself (its boot.sh, at the restart).
GRAPHS_DEFAULTS="$GRAPHS_ROOT/etc/default/graphs1090"
GRAPHS_LOOK_BEGIN="# >>> ZenithBoard look"
GRAPHS_LOOK_END="# <<< ZenithBoard look"
GRAPHS_LOOK_FILES="zenithboard.css zenithboard.js font5x7.js"
graphs_look_state() { grep -qF "$GRAPHS_LOOK_BEGIN" "$GRAPHS_DEFAULTS" 2>/dev/null && echo zenithboard || echo original; }
graphs_theme_hex() {
  case "$(wall_theme)" in green) echo 39ff6a ;; red) echo ff3b30 ;; white) echo e8e8e8 ;; turquoise) echo 00d6d7 ;; *) echo ffb000 ;; esac
}
# The palette: the wall's colour for the main series (messages, aircraft), its shades for the others, the wall's
# turquoise, green and red where graphs1090 needs more series told apart; a black canvas, light grey text. Read
# against each graph of the reference Pi's own history (21 October 2026), every line still told apart.
graphs_look_block() {
  local on; on=$(graphs_theme_hex)
  local light dim dark
  light=$(graphs_mix "$on" ffffff 40); dim=$(graphs_mix "$on" 000000 30); dark=$(graphs_mix "$on" 000000 55)
  cat <<EOT
$GRAPHS_LOOK_BEGIN (sudo zenithboard graphs look zenithboard). Taken away by: sudo zenithboard graphs look original
colorscheme=dark
CANVAS=0a0a0a
colors="-c CANVAS#0a0a0a -c BACK#000000 -c FONT#e8e8e8 -c AXIS#8c8c8c -c ARROW#8c8c8c -c FRAME#333333 -c GRID#262626 -c MGRID#3a3a3a -c SHADEA#000000 -c SHADEB#000000"
LBLUE=$light
BLUE=$on
ABLUE=$dim
DBLUE=$dark
LGREEN=7dffa3
GREEN=1f6b37
DGREEN=39d468
CYAN=00d6d7
LCYAN=7aeaea
RED=ff3b30
DRED=c4281f
LRED=ff8a80
LIGHTYELLOW=2b2b2b
AYELLOW=$on
AGRAY=1c1c1c
$GRAPHS_LOOK_END
EOT
}
graphs_mix() {   # graphs_mix RRGGBB RRGGBB PERCENT_OF_THE_SECOND -> RRGGBB
  local a=$1 b=$2 p=$3 i out=""
  for i in 0 2 4; do out="$out$(printf '%02x' $(( (16#${a:$i:2} * (100 - p) + 16#${b:$i:2} * p) / 100 )))"; done
  printf '%s' "$out"
}
graphs_look_strip() {
  [ -f "$GRAPHS_DEFAULTS" ] && sed -i "/^$GRAPHS_LOOK_BEGIN/,/^$GRAPHS_LOOK_END/d" "$GRAPHS_DEFAULTS"
  local html="$GRAPHS_HOME/html/index.html" f
  [ -f "$html" ] && sed -i -e '/zenithboard\.css/d' -e '/zenithboard\.js/d' -e '/font5x7\.js/d' "$html"
  for f in $GRAPHS_LOOK_FILES; do rm -f "$GRAPHS_HOME/html/$f"; done
  return 0
}
graphs_look_apply() {
  local html="$GRAPHS_HOME/html/index.html" src="$ZB_HOME/tools/graphs1090-look"
  graphs_look_strip
  graphs_look_block >> "$GRAPHS_DEFAULTS"
  install -m 644 "$src/zenithboard.js" "$ZB_HOME/flightinfo/static/font5x7.js" "$GRAPHS_HOME/html/"
  sed "s|--on: #ffb000; /\* ZB_THEME_HEX \*/|--on: #$(graphs_theme_hex);|" "$src/zenithboard.css" > "$GRAPHS_HOME/html/zenithboard.css"
  chmod 644 "$GRAPHS_HOME/html/zenithboard.css"
  sed -i -e 's|\(<link rel="stylesheet" href="portal.css">\)|\1\n\t\t<link rel="stylesheet" href="zenithboard.css">|' \
         -e 's|\(<script src="graphs.js"></script>\)|\1\n\t\t<script src="font5x7.js"></script>\n\t\t<script src="zenithboard.js"></script>|' "$html"
  grep -q 'zenithboard.css' "$html" && grep -q 'zenithboard.js' "$html"
}
graphs_look() {   # graphs_look zenithboard|original|status
  case "${1:-status}" in
    status) echo "graphs1090's look: $(graphs_look_state)"; return 0 ;;
    zenithboard|zb|on)
      is_graphs || { err "graphs1090 is not installed: sudo zenithboard graphs on, then this again."; return 1; }
      graphs_look_apply || { graphs_look_strip; err "graphs1090's page is not the one this was written for (its links were not found): nothing was changed."; return 1; }
      cfg_set GRAPHS_LOOK zenithboard ;;
    original|off)
      graphs_look_strip; cfg_set GRAPHS_LOOK original ;;
    *) err "Usage: zenithboard graphs look zenithboard|original|status"; return 1 ;;
  esac
  [ "${ZB_SKIP_SERVICES:-}" = 1 ] || systemctl restart graphs1090 >/dev/null 2>&1 || true
  echo "graphs1090's look: $(graphs_look_state). The graphs are drawn again in the next minute (the longer periods within the hour); reload the page."
}
# after graphs1090's installer, or a new wall colour: the look again, if it was chosen
graphs_look_keep() {
  [ "$(cfg_get GRAPHS_LOOK zenithboard)" != original ] && is_graphs || return 0
  graphs_look_apply >/dev/null 2>&1 || return 0
  [ "${ZB_SKIP_SERVICES:-}" = 1 ] || systemctl restart graphs1090 >/dev/null 2>&1 || true
}

graphs_status() {
  echo "graphs1090: $(graphs_state)$(is_graphs && printf ' (version %s), look: %s' "$(graphs_version)" "$(graphs_look_state)")"
  is_graphs || { echo "    Turn it on: sudo zenithboard graphs on   (menu 7 Options -> 2 graphs1090)"; return 0; }
  graphs_urls
  echo "    collectd: $(systemctl is-active collectd 2>/dev/null)   graph drawing: $(systemctl is-active graphs1090 2>/dev/null)"
  echo "    In memory (/run/collectd): $(graphs_du "$GRAPHS_ROOT/run/collectd" || echo '?')   on the card (/var/lib/collectd): $(graphs_du "$GRAPHS_ROOT/var/lib/collectd" || echo '?')   /run free: $(graphs_run_free_mb) MB"
  local m; m=$(systemctl show -p MemoryCurrent --value collectd 2>/dev/null)
  case "$m" in ''|*[!0-9]*) ;; *) echo "    collectd's memory: $((m / 1048576)) MB" ;; esac
}
