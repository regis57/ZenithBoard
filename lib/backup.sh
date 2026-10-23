# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Backup and restore (0.42.0): one file that carries a ZenithBoard to a new card and carries on where the old one
# stopped. Asked for by the owner on 21 October 2026, writing a new card: the settings alone (`settings export`) left
# the statistics, the graphs, the kept logs and the networks' identities behind, and a feature that was on came back
# "on" in config.env with nothing behind it (no timer, no watchdog file).
#
# What a backup holds, under zb/ in a .tar.gz:
#   MANIFEST            format, version, host, date, architecture, machine id
#   settings.env        config.env without its secrets (the same as `settings export`)
#   features.env        each feature on or off (some live outside config.env: the watchdog, the kept logs)
#   stats/              /var/lib/zenithboard/stats, the 30 days behind /stats and the summaries
#   social/state.json   what was posted and when the last summaries went out (no double post after a move)
#   social/templates.txt  the owner's own post templates (0.51.0), his words
#   graphs-xml.tar.gz   graphs1090's history, dumped to XML by its own rrd-dump.sh: readable on another architecture
#   journal/ID/         the logs kept after a restart, when they are kept
#   feeders.env         the networks' identities: ADSB Exchange's UUID, FlightAware's feeder ID, the FR24 sharing key
#   pfclient-config.json  Plane Finder's settings, its share code with them
# Never: the Bluesky app password, the console password, the domain-name token. They are made again in a minute.
# The console's backup (`--console`) leaves the networks' identities out too: it goes through a browser.
#
# Restore runs at any time; best right after the installer's first questions, before menu 1 (Fresh install, step 13).
# What cannot be applied yet (a network not installed, graphs1090 waiting for the receiver map) waits in
# restore-pending/ and is applied by that network's or graphs1090's own installation.

BK_FORMAT=1
BK_DATA="${ZB_BACKUP_DATA:-$ZB_DATA}"
BK_PENDING="$BK_DATA/restore-pending"
BK_JOURNAL_DIR="${ZB_JOURNAL_DIR:-/var/log/journal}"
BK_MACHINE_ID="${ZB_MACHINE_ID_FILE:-/etc/machine-id}"
BK_RRD="${ZB_GRAPHS_ROOT:-}/var/lib/collectd/rrd/localhost"
BK_GRAPHS_TOOLS="${ZB_GRAPHS_ROOT:-}/usr/share/graphs1090"
BK_ADSBX_UUID="${ZB_ADSBX_UUID:-/usr/local/share/adsbexchange/adsbx-uuid}"
BK_PF_CONFIG="${ZB_PF_CONFIG:-/etc/pfclient-config.json}"
BK_PIAWARE_CACHE="${ZB_PIAWARE_ID_CACHE:-/var/cache/piaware/feeder_id}"
BK_CMD="${ZB_BACKUP_CMD:-$ZB_HOME/bin/zenithboard}"
BK_CONSOLE_OUT="${ZB_CONSOLE_DIR:-/var/lib/zenithboard/console}/out/backup.tar.gz"
BK_FEATURES="stats graphs watchdog netwatch keeplogs patches wifi_harden logs_auto gain_log social console phone_signin adsbx_stats"
BK_MAX_MB=2048

bk_svc() { [ "${ZB_SKIP_SERVICES:-}" = 1 ] || systemctl "$@" >/dev/null 2>&1 || true; }
bk_id_ok() { [[ ${1:-} =~ ^\{?[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}?$ ]]; }
bk_key_ok() { [[ ${1:-} =~ ^[A-Za-z0-9]{8,64}$ ]]; }
bk_get() { sed -n "s/^$1=//p" "$2" 2>/dev/null | head -1; }      # a value read, never sourced

bk_feature_state() {
  case "$1" in
    stats) stats_state ;; graphs) graphs_state ;; watchdog) watchdog_state ;; netwatch) netwatch_state ;;
    keeplogs) keeplogs_state ;; patches) patches_state ;; wifi_harden) wifi_harden_state ;; gain_log) gain_log_state ;;
    logs_auto) [ "$(cfg_get LOG_AUTOCLEAN 0)" = 1 ] && echo on || echo off ;;
    social) social_state ;; console) console_state ;;
    phone_signin) [ "$(cfg_get CONSOLE_PHONE_SIGNIN 0)" = 1 ] && echo on || echo off ;;
    adsbx_stats) declare -F adsbx_stats_state >/dev/null && adsbx_stats_state || echo off ;;
    *) echo off ;;
  esac
}
bk_feature_cmd() {
  case "$1" in
    wifi_harden) echo "wifi harden on" ;; logs_auto) echo "logs auto on" ;; gain_log) echo "gain log on" ;;
    phone_signin) echo "console phone-signin on" ;; adsbx_stats) echo "adsbx-stats on" ;; *) echo "$1 on" ;;
  esac
}
bk_feature_label() {
  case "$1" in
    stats) echo "Statistics" ;; graphs) echo "graphs1090" ;; watchdog) echo "Hardware watchdog" ;; netwatch) echo "Network watchdog" ;;
    keeplogs) echo "Logs kept after a restart" ;; patches) echo "Daily security fixes" ;; wifi_harden) echo "Wi-Fi hardening" ;;
    logs_auto) echo "Daily log clean-up" ;; gain_log) echo "Gain log" ;; social) echo "Bluesky posts" ;; console) echo "Web console" ;;
    phone_signin) echo "Computers signed in by a phone" ;; adsbx_stats) echo "ADSB Exchange stats" ;; *) echo "$1" ;;
  esac
}

# The networks' identities found on this Pi, as KEY=VALUE lines.
bk_read_ids() {
  local v=""
  v=$(tr -d ' \r\n' < "$BK_ADSBX_UUID" 2>/dev/null); bk_id_ok "$v" && echo "ADSBX_UUID=$v"
  v=""
  command -v piaware-config >/dev/null 2>&1 && v=$(piaware-config -show feeder-id 2>/dev/null | tr -d ' \r\n')
  bk_id_ok "$v" || v=$(tr -d ' \r\n' < "$BK_PIAWARE_CACHE" 2>/dev/null)
  bk_id_ok "$v" && echo "PIAWARE_FEEDER_ID=$v"
  v=$(sed -n -E 's/^fr24key="?([A-Za-z0-9]+)"?.*/\1/p' "${FR24_INI:-/etc/fr24feed.ini}" 2>/dev/null | head -1)
  bk_key_ok "$v" && echo "FR24_KEY=$v"
  return 0
}

bk_size() { du -sh "$1" 2>/dev/null | cut -f1; }

# backup_make [--console] [FILE]
backup_make() {
  local console=0 out="" st b mid f n owner
  while [ $# -gt 0 ]; do case "$1" in --console) console=1 ;; *) out="$1" ;; esac; shift; done
  [ "$console" = 0 ] || out="$BK_CONSOLE_OUT"
  [ -n "$out" ] || out="$PWD/zenithboard-backup-$(hostname)-$(date +%Y%m%d-%H%M).tar.gz"
  st=$(mktemp -d) || return 1
  chmod 700 "$st"; b="$st/zb"; mkdir -p "$b"
  mid=$(tr -d ' \n' < "$BK_MACHINE_ID" 2>/dev/null)
  printf 'FORMAT=%s\nVERSION=%s\nHOST=%s\nMADE=%s\nARCH=%s\nMACHINE_ID=%s\nKIND=%s\n' "$BK_FORMAT" "$ZB_VERSION" "$(hostname)" \
    "$(date '+%Y-%m-%d %H:%M')" "$(uname -m)" "$mid" "$([ "$console" = 1 ] && echo console || echo full)" > "$b/MANIFEST"
  if [ -f "$ZB_CONFIG" ]; then settings_export "$b/settings.env" >/dev/null || { rm -rf "$st"; return 1; }; fi
  for f in $BK_FEATURES; do printf '%s=%s\n' "$f" "$(bk_feature_state "$f")"; done > "$b/features.env"
  [ -d "$STATS_DIR" ] && cp -a "$STATS_DIR" "$b/stats"
  if [ -f "$SOCIAL_DIR/state.json" ]; then mkdir -p "$b/social"; cp -p "$SOCIAL_DIR/state.json" "$b/social/"; fi
  if [ -s "$SOCIAL_TEMPLATES" ]; then mkdir -p "$b/social"; cp -p "$SOCIAL_TEMPLATES" "$b/social/templates.txt"; fi
  # graphs1090's own way, from its README: collectd stopped so the day kept in memory is written to the card first
  if [ -d "$BK_RRD" ] && [ -x "$BK_GRAPHS_TOOLS/rrd-dump.sh" ]; then
    bk_svc stop collectd
    "$BK_GRAPHS_TOOLS/rrd-dump.sh" "$BK_RRD" "$b/graphs-xml.tar.gz" >/dev/null 2>&1 || { rm -f "$b/graphs-xml.tar.gz"; warn "graphs1090's history could not be dumped: left out."; }
    bk_svc start collectd
  fi
  if [ -n "$mid" ] && [ -d "$BK_JOURNAL_DIR/$mid" ]; then
    [ "${ZB_SKIP_SERVICES:-}" = 1 ] || journalctl --sync 2>/dev/null || true
    mkdir -p "$b/journal/$mid"; cp -p "$BK_JOURNAL_DIR/$mid"/* "$b/journal/$mid/" 2>/dev/null || true
  fi
  if [ "$console" = 0 ]; then
    bk_read_ids > "$b/feeders.env"
    [ -s "$b/feeders.env" ] || rm -f "$b/feeders.env"
    grep -q '"sharecode"' "$BK_PF_CONFIG" 2>/dev/null && cp "$BK_PF_CONFIG" "$b/pfclient-config.json"
  fi
  install -d "$(dirname "$out")" 2>/dev/null
  ( umask 077; tar -C "$st" -czf "$out.tmp" zb ) || { rm -rf "$st" "$out.tmp"; err "Could not write $out"; return 1; }
  mv -f "$out.tmp" "$out"
  gzip -t "$out" 2>/dev/null || { err "The backup just written does not read back: $out (a full card?)"; rm -rf "$st"; return 1; }
  if [ "$console" = 1 ]; then
    chgrp "$ZB_USER" "$out" 2>/dev/null; chmod 640 "$out"
  else
    owner="${SUDO_USER:-}"; [ -z "$owner" ] || [ "$owner" = root ] || chown "$owner:" "$out" 2>/dev/null
    chmod 600 "$out"
  fi
  n=$(find "$b/stats" -name 'seen-*' 2>/dev/null | wc -l)
  rm -rf "$st"
  echo "Backup written: $out ($(bk_size "$out"))"
  echo "  settings, the features that are on, $n day(s) of statistics$( [ -f "$SOCIAL_DIR/state.json" ] && echo ", what was posted")$( [ -d "$BK_RRD" ] && [ -x "$BK_GRAPHS_TOOLS/rrd-dump.sh" ] && echo ", graphs1090's history")$( [ -n "$mid" ] && [ -d "$BK_JOURNAL_DIR/$mid" ] && echo ", the kept logs")."
  if [ "$console" = 0 ]; then
    echo "  It holds your networks' identities (FR24's sharing key among them): keep it to yourself, never in an issue."
    echo "  Copy it to your computer:  scp $(id -un 2>/dev/null | sed "s/^root$/${SUDO_USER:-USER}/")@$(hostname).local:$out ."
    echo "  On the new card:           sudo zenithboard backup restore $(basename "$out")"
  fi
}

# bk_unpack FILE DIR: only the names a backup holds, only files and folders, no path outside, 2 GB at most.
bk_unpack() {
  python3 - "$1" "$2" "$BK_MAX_MB" <<'PY'
import sys, tarfile
src, dest, max_mb = sys.argv[1], sys.argv[2], int(sys.argv[3])
TOP = {"MANIFEST", "settings.env", "features.env", "feeders.env", "pfclient-config.json", "graphs-xml.tar.gz",
       "stats", "social", "journal"}
try:
    t = tarfile.open(src, "r:gz")
except (OSError, tarfile.TarError) as e:
    sys.exit("Not a ZenithBoard backup (%s)." % e)
with t:
    members, total = t.getmembers(), 0
    for m in members:
        parts = m.name.split("/")
        if m.name.startswith("/") or ".." in parts or parts[0] != "zb" or (len(parts) > 1 and parts[1] not in TOP):
            sys.exit("Refused: %s is not something a backup holds." % m.name)
        if not (m.isfile() or m.isdir()):
            sys.exit("Refused: %s is a link or a device." % m.name)
        total += m.size
    if total > max_mb * 1024 * 1024:
        sys.exit("Refused: more than %d MB unpacked." % max_mb)
    if hasattr(tarfile, "data_filter"):
        t.extractall(dest, members=members, filter="data")
    else:
        t.extractall(dest, members=members)   # the checks above already refused every unsafe name and kind
PY
}

bk_describe() {   # bk_describe DIR(zb)
  local b="$1" f on="" n
  echo "Backup of $(bk_get HOST "$b/MANIFEST"), made $(bk_get MADE "$b/MANIFEST") by ZenithBoard $(bk_get VERSION "$b/MANIFEST") ($(bk_get ARCH "$b/MANIFEST"))."
  [ -f "$b/settings.env" ] && echo "  Settings: $(grep -c -E '^[A-Z]' "$b/settings.env") value(s)"
  for f in $BK_FEATURES; do [ "$(bk_get "$f" "$b/features.env")" = on ] && on="$on, $(bk_feature_label "$f")"; done
  echo "  On: ${on#, }"
  [ -z "$on" ] && echo "  On: nothing beyond the wall"
  n=$(find "$b/stats" -name 'seen-*' 2>/dev/null | wc -l); [ -d "$b/stats" ] && echo "  Statistics: $n day(s), $(bk_size "$b/stats")"
  [ -f "$b/social/state.json" ] && echo "  What was posted to Bluesky, and when the summaries went out"
  [ -f "$b/graphs-xml.tar.gz" ] && echo "  graphs1090's history: $(bk_size "$b/graphs-xml.tar.gz")"
  [ -d "$b/journal" ] && echo "  Kept logs: $(bk_size "$b/journal")"
  if [ -f "$b/feeders.env" ] || [ -f "$b/pfclient-config.json" ]; then
    printf '  Network identities:'
    [ -n "$(bk_get ADSBX_UUID "$b/feeders.env")" ] && printf ' ADSB Exchange UUID;'
    [ -n "$(bk_get PIAWARE_FEEDER_ID "$b/feeders.env")" ] && printf ' FlightAware feeder ID;'
    [ -n "$(bk_get FR24_KEY "$b/feeders.env")" ] && printf ' Flightradar24 sharing key;'
    [ -f "$b/pfclient-config.json" ] && printf ' Plane Finder share code;'
    echo
  else
    echo "  Network identities: none (a backup made from the console never holds them)"
  fi
  bk_check "$b"
}

# bk_check DIR(zb): each part read back, as a restore would read it (0.42.1, the owner's "check the dump"). Prints the
# span each part covers and a verdict; returns 1 when a part would not come back.
bk_check() {
  local b="$1" bad="" first last n x lu made
  echo "Checked:"
  made=$(bk_get MADE "$b/MANIFEST")
  [ -f "$b/settings.env" ] && grep -q -E '^[A-Z][A-Z0-9_]*=' "$b/settings.env" || bad="$bad settings"
  [ -f "$b/features.env" ] || bad="$bad features"
  if [ -f "$b/stats/stats.csv" ]; then
    if [ "$(head -1 "$b/stats/stats.csv")" = "$STATS_HEADER" ]; then
      n=$(tail -n +2 "$b/stats/stats.csv" | grep -c .); first=$(sed -n 2p "$b/stats/stats.csv" | cut -d, -f1); last=$(tail -1 "$b/stats/stats.csv" | cut -d, -f1)
      echo "  statistics: $n samples, $first to $last"
      first=$(find "$b/stats" -name 'seen-*' -printf '%f\n' | sort | head -1); last=$(find "$b/stats" -name 'seen-*' -printf '%f\n' | sort | tail -1)
      [ -z "$first" ] || echo "  aircraft lists: ${first#seen-} to ${last#seen-}"
    else bad="$bad statistics"; echo "  statistics: the file does not start with the expected header"; fi
  fi
  if [ -f "$b/social/state.json" ]; then
    if x=$(python3 -c 'import json, sys; d = json.load(open(sys.argv[1])); print(len(d.get("posted") or {}))' "$b/social/state.json" 2>/dev/null)
    then echo "  posting history: readable, $x aircraft posted"; else bad="$bad posting-history"; echo "  posting history: not readable"; fi
  fi
  if [ -f "$b/graphs-xml.tar.gz" ]; then
    if gzip -t "$b/graphs-xml.tar.gz" 2>/dev/null; then
      n=$(tar -tzf "$b/graphs-xml.tar.gz" | grep -c '\.xml$')
      x=$(tar -tzf "$b/graphs-xml.tar.gz" | grep -m1 'messages\|\.xml$')
      lu=$(tar -xzOf "$b/graphs-xml.tar.gz" "$x" 2>/dev/null | grep -m1 -o '<lastupdate>[0-9]*' | tr -dc 0-9)
      echo "  graphs1090: $n databases$( [ -n "$lu" ] && echo ", last point $(date -d "@$lu" '+%Y-%m-%d %H:%M')")"
      [ "$n" -gt 0 ] || bad="$bad graphs1090"
    else bad="$bad graphs1090"; echo "  graphs1090: the archive is damaged"; fi
  fi
  if [ -d "$b/journal" ]; then
    for x in "$b/journal"/*; do
      if command -v journalctl >/dev/null 2>&1 && n=$(journalctl -D "$x" --list-boots --no-pager 2>/dev/null | grep -c .) && [ "$n" -gt 0 ]; then
        first=$(journalctl -D "$x" --no-pager -o short-iso 2>/dev/null | head -1 | cut -c1-16)
        last=$(journalctl -D "$x" --no-pager -o short-iso -n 1 2>/dev/null | tail -1 | cut -c1-16)
        echo "  kept logs: $n boot(s), $first to $last"
      else echo "  kept logs: $(bk_size "$x") (not read here: no journalctl)"; fi
    done
  fi
  if [ -n "$bad" ]; then echo "  NOT COMPLETE:$bad would not come back."; return 1; fi
  echo "  Everything in it reads back; made $made."
}

backup_show() {   # backup_show FILE
  local st
  [ -f "${1:-}" ] || { err "No such file: ${1:-}"; return 1; }
  st=$(mktemp -d) || return 1
  if ! bk_unpack "$1" "$st" || [ "$(bk_get FORMAT "$st/zb/MANIFEST")" != "$BK_FORMAT" ]; then rm -rf "$st"; err "$1 is not a ZenithBoard backup."; return 1; fi
  local rc=0; bk_describe "$st/zb" || rc=1; rm -rf "$st"; return "$rc"
}

# ---- identities: now when the network is installed, else kept for its installation
bk_pending_put() { install -d -m 700 "$BK_PENDING"; ( umask 077; printf '%s\n' "$2" > "$BK_PENDING/$1" ); }

bk_apply_ids() {   # bk_apply_ids DIR(zb) BEFORE_DIR
  local b="$1" before="$2" v cur
  v=$(bk_get ADSBX_UUID "$b/feeders.env")
  if bk_id_ok "$v"; then
    cur=$(tr -d ' \r\n' < "$BK_ADSBX_UUID" 2>/dev/null)
    if [ "$cur" != "$v" ]; then
      [ -z "$cur" ] || cp -p "$BK_ADSBX_UUID" "$before/adsbx-uuid"
      install -d "$(dirname "$BK_ADSBX_UUID")"; printf '%s\n' "$v" > "$BK_ADSBX_UUID"; chmod 644 "$BK_ADSBX_UUID"
      bk_svc try-restart adsbexchange-feed adsbexchange-mlat
    fi
    echo "  ADSB Exchange: your station's UUID is back (its installer keeps a UUID it finds)."
  fi
  v=$(bk_get PIAWARE_FEEDER_ID "$b/feeders.env")
  if bk_id_ok "$v"; then
    if command -v piaware-config >/dev/null 2>&1; then
      piaware-config feeder-id "$v" >/dev/null 2>&1; bk_svc restart piaware
      echo "  FlightAware: your feeder ID is back; nothing to claim."
    else bk_pending_put piaware-feeder-id "$v"; echo "  FlightAware: your feeder ID waits for menu 1 (FlightAware ticked)."; fi
  fi
  v=$(bk_get FR24_KEY "$b/feeders.env")
  if bk_key_ok "$v"; then
    if [ -f "${FR24_INI:-/etc/fr24feed.ini}" ]; then
      cp -p "$FR24_INI" "$before/fr24feed.ini"; ini_set "$FR24_INI" fr24key "$v"; bk_svc restart fr24feed
      echo "  Flightradar24: your sharing key is back."
    else bk_pending_put fr24key "$v"; echo "  Flightradar24: your sharing key waits for menu 1 (Flightradar24 ticked)."; fi
  fi
  if [ -f "$b/pfclient-config.json" ]; then
    if [ -f "$BK_PF_CONFIG" ] || command -v pfclient >/dev/null 2>&1; then
      [ ! -f "$BK_PF_CONFIG" ] || cp -p "$BK_PF_CONFIG" "$before/pfclient-config.json"
      install -m 644 "$b/pfclient-config.json" "$BK_PF_CONFIG"; bk_svc restart pfclient
      echo "  Plane Finder: your share code is back."
    else install -d -m 700 "$BK_PENDING"; install -m 600 "$b/pfclient-config.json" "$BK_PENDING/pfclient-config.json"
      echo "  Plane Finder: your share code waits for menu 1 (Plane Finder ticked)."; fi
  fi
  return 0
}

# Called by the installers (lib/adsb.sh, lib/graphs.sh) once their part is in place.
bk_pending_apply() {   # bk_pending_apply piaware|fr24|planefinder|graphs
  local v
  case "$1" in
    piaware)
      v=$(cat "$BK_PENDING/piaware-feeder-id" 2>/dev/null); bk_id_ok "$v" || return 0
      piaware-config feeder-id "$v" >/dev/null 2>&1 && bk_svc restart piaware && rm -f "$BK_PENDING/piaware-feeder-id" \
        && echo "    FlightAware: the feeder ID from your backup is set; nothing to claim." ;;
    fr24)
      v=$(cat "$BK_PENDING/fr24key" 2>/dev/null); bk_key_ok "$v" || return 0
      ini_set "${FR24_INI:-/etc/fr24feed.ini}" fr24key "$v" && rm -f "$BK_PENDING/fr24key" \
        && echo "    Flightradar24: the sharing key from your backup is set." ;;
    planefinder)
      [ -f "$BK_PENDING/pfclient-config.json" ] || return 1
      install -m 644 "$BK_PENDING/pfclient-config.json" "$BK_PF_CONFIG" && rm -f "$BK_PENDING/pfclient-config.json" && bk_svc restart pfclient \
        && echo "    Plane Finder: the share code from your backup is set; nothing to do on its page." ;;
    graphs)
      [ -f "$BK_PENDING/graphs-xml.tar.gz" ] || return 0
      bk_graphs_restore "$BK_PENDING/graphs-xml.tar.gz" && rm -f "$BK_PENDING/graphs-xml.tar.gz" ;;
  esac
  rmdir "$BK_PENDING" 2>/dev/null || true
  return 0
}
bk_pending_fr24_key() { cat "$BK_PENDING/fr24key" 2>/dev/null; }

bk_graphs_restore() {   # bk_graphs_restore XML_TAR_GZ   (graphs1090's rrd-restore.sh, as its README says)
  [ -x "$BK_GRAPHS_TOOLS/rrd-restore.sh" ] || return 1
  bk_svc stop collectd
  install -d "$BK_RRD"
  "$BK_GRAPHS_TOOLS/rrd-restore.sh" "$1" "$BK_RRD" >/dev/null 2>&1 || { bk_svc start collectd; warn "graphs1090's history could not be restored."; return 1; }
  bk_svc restart collectd graphs1090
  echo "    graphs1090: the history from your backup is back."
}

# backup_restore FILE [--yes]
backup_restore() {
  local f="" yes=0 st b before w mid old feat v failed="" later="" n
  while [ $# -gt 0 ]; do case "$1" in --yes) yes=1 ;; *) f="$1" ;; esac; shift; done
  [ -f "$f" ] || { err "No such file: $f"; return 1; }
  st=$(mktemp -d) || return 1
  if ! bk_unpack "$f" "$st" || [ "$(bk_get FORMAT "$st/zb/MANIFEST")" != "$BK_FORMAT" ]; then rm -rf "$st"; err "$f is not a ZenithBoard backup."; return 1; fi
  b="$st/zb"
  bk_describe "$b"
  echo
  # 0.53.8: the console's copy leaves the networks' identities out. Restored on a card with no network yet, every network
  # starts as a new station, and nothing said so before the typed word (the audit of 22-23 October 2026)
  if [ "$(bk_get KIND "$b/MANIFEST")" = console ] && ! { declare -F is_adsbx >/dev/null && is_adsbx; } && ! { declare -F is_piaware >/dev/null && is_piaware; } \
     && ! { declare -F is_fr24 >/dev/null && is_fr24; } && ! { declare -F is_planefinder >/dev/null && is_planefinder; }; then
    echo
    echo "!! This is the console's copy: it holds no network identity, so ADSB Exchange, FlightAware, Flightradar24 and"
    echo "   Plane Finder would each start as a NEW station here. Moving to a new card? Make the full backup on the old one first:"
    echo "   sudo zenithboard backup make"
  fi
  echo "Restoring replaces this Pi's settings, statistics and posting history with the backup's (what is here now is"
  echo "kept first, see below), switches on again what was on, and gives the networks their identities back."
  echo "Switch the old card OFF first: two receivers with the same identities is one too many (Plane Finder blocks it)."
  if [ "$yes" != 1 ]; then
    read -r -p "Type RESTORE to go on: " w || w=""
    [ "$w" = RESTORE ] || { echo "Nothing was changed."; rm -rf "$st"; return 1; }
  fi
  ensure_zb_user                                    # 0.43.0: restored before menu 2, the files still go to the wall's user
  before="$BK_DATA/before-restore-$(date +%Y%m%d-%H%M%S)"; install -d -m 700 "$before"
  [ ! -f "$ZB_CONFIG" ] || cp -p "$ZB_CONFIG" "$before/config.env"
  [ ! -d "$STATS_DIR" ] || cp -a "$STATS_DIR" "$before/stats"
  [ ! -f "$SOCIAL_DIR/state.json" ] || cp -p "$SOCIAL_DIR/state.json" "$before/social-state.json"
  [ ! -f "$SOCIAL_TEMPLATES" ] || cp -p "$SOCIAL_TEMPLATES" "$before/social-templates.txt"

  echo "1. Settings"
  [ ! -f "$b/settings.env" ] || settings_import "$b/settings.env" | sed 's/^/  /'
  # 0.44.0: imported is not applied (the owner: the position, the altitude and the units "did not follow"): the
  # position goes everywhere it is stored (the decoder, the feeders that take it), the wall and the posts restart
  local lat lon; lat=$(cfg_get LAT ""); lon=$(cfg_get LON "")
  if valid_lat "$lat" && valid_lon "$lon" && [ "$lat$lon" != 00 ] && declare -F zb_apply_location >/dev/null; then
    echo "  The antenna position, applied everywhere it is stored:"
    zb_apply_location "$lat" "$lon" "$(cfg_get ALT_M 0)" 2>&1 | sed 's/^/  /'
  fi
  ! declare -F settings_apply >/dev/null || settings_apply
  echo "2. Statistics and posting history"
  if [ -d "$b/stats" ]; then
    install -d -m 755 "$STATS_DIR"
    if [ -f "$STATS_DIR/stats.csv" ] && [ -f "$b/stats/stats.csv" ]; then   # the samples of both cards, once each, in order
      { echo "$STATS_HEADER"; tail -n +2 -q "$b/stats/stats.csv" "$STATS_DIR/stats.csv" | sort -u; } > "$b/stats/stats.csv.new"
      mv -f "$b/stats/stats.csv.new" "$b/stats/stats.csv"
    fi
    cp -a "$b/stats/." "$STATS_DIR/"
    chown -R "$ZB_USER:$ZB_USER" "$STATS_DIR" 2>/dev/null || true
    echo "  $(find "$b/stats" -name 'seen-*' | wc -l) day(s) of statistics back in $STATS_DIR"
  fi
  if [ -f "$b/social/state.json" ]; then
    install -d -m 750 "$SOCIAL_DIR"; cp -p "$b/social/state.json" "$SOCIAL_DIR/state.json"
    chown -R "$ZB_USER:$ZB_USER" "$SOCIAL_DIR" 2>/dev/null || true
    bk_svc try-restart zenithboard-social
    echo "  What was posted, and when the summaries went out: back (nothing is posted twice)"
  fi
  if [ -f "$b/social/templates.txt" ]; then
    install -d -m 755 "$(dirname "$SOCIAL_TEMPLATES")"; install -m 644 "$b/social/templates.txt" "$SOCIAL_TEMPLATES"
    echo "  Your own post templates: $(grep -c . "$SOCIAL_TEMPLATES" || true), back"
  fi
  echo "3. Logs"
  mid=$(tr -d ' \n' < "$BK_MACHINE_ID" 2>/dev/null)
  if [ -d "$b/journal" ]; then
    for old in "$b/journal"/*; do
      old=$(basename "$old")
      if [ "$old" = "$mid" ]; then echo "  The kept logs are this card's own: left as they are."; continue; fi
      install -d "$BK_JOURNAL_DIR/$old"; cp -p "$b/journal/$old"/* "$BK_JOURNAL_DIR/$old/" 2>/dev/null
      chgrp -R systemd-journal "$BK_JOURNAL_DIR/$old" 2>/dev/null || true
      echo "  The old card's logs are in $BK_JOURNAL_DIR/$old: read them with  journalctl -m  (both cards) or"
      echo "  journalctl -D $BK_JOURNAL_DIR/$old  (the old one alone). Delete them: sudo rm -r $BK_JOURNAL_DIR/$old"
    done
  else echo "  None in the backup (they were not kept after a restart)."; fi
  echo "4. The networks"
  if [ -f "$b/feeders.env" ] || [ -f "$b/pfclient-config.json" ]; then bk_apply_ids "$b" "$before"
  else echo "  No identities in the backup: each network starts as a new station (or set them by hand: Fresh install)."; fi
  echo "5. What was on"
  for feat in $BK_FEATURES; do
    [ "$(bk_get "$feat" "$b/features.env")" = on ] || continue
    case "$feat" in
      console)
        if console_has_password; then :; else cfg_set CONSOLE 0; later="$later\n  sudo zenithboard console password && sudo zenithboard console on"; continue; fi ;;
      phone_signin) console_has_password || continue ;;
      social)
        if [ ! -s "$SOCIAL_SECRETS" ]; then cfg_set SOCIAL 0; later="$later\n  sudo zenithboard social setup        (a new app password: bsky.app > Settings > Privacy and security > App passwords)"; continue; fi ;;
      wifi_harden) [ -n "$(wifi_iface 2>/dev/null)" ] || continue ;;
      # 0.52.0: they need ADSB Exchange's feed, which a fresh card gets from menu 1; the UUID came back with step 4
      adsbx_stats) is_adsbx || { later="$later\n  sudo zenithboard adsbx-stats on      (after ADSB Exchange: menu 1 ADS-B → 1 Decoder and networks)"; continue; } ;;
      graphs) [ ! -f "$b/graphs-xml.tar.gz" ] || { install -d -m 700 "$BK_PENDING"; install -m 600 "$b/graphs-xml.tar.gz" "$BK_PENDING/graphs-xml.tar.gz"; } ;;
    esac
    # shellcheck disable=SC2046
    if "$BK_CMD" $(bk_feature_cmd "$feat") > "$st/out" 2>&1; then echo "  $(bk_feature_label "$feat"): on"
    else failed="$failed\n  sudo zenithboard $(bk_feature_cmd "$feat")      # $(tail -1 "$st/out")"; fi
  done
  # 0.54.3: the settings come back with TAILSCALE=1, the program and its sign-in do not
  if [ "$(cfg_get TAILSCALE 0)" = 1 ] && declare -F ts_installed >/dev/null && ! ts_installed; then
    later="$later\n  sudo zenithboard tailscale on        (Tailscale is not on this card: it installs and signs in to your own account again)"
  fi
  ! declare -F graphs_look_keep >/dev/null || graphs_look_keep         # the look and the wall's colour of the backup
  if [ -f "$BK_PENDING/graphs-xml.tar.gz" ]; then
    if is_graphs; then bk_pending_apply graphs | sed 's/^ *//; s/^/  /'
    else later="$later\n  graphs1090's history waits for graphs1090: it comes back by itself with  sudo zenithboard graphs on  (after ADS-B: menu 1 ADS-B → 1 Decoder and networks, then tick graphs1090)"; fi
  fi
  rm -rf "$st"
  echo
  echo "Restored. What was here before is in $before"
  n=$(printf '%b' "$failed$later" | grep -c .)
  if [ "$n" -gt 0 ]; then echo "Still to do:"; printf '%b\n' "$failed$later" | grep .; fi
  return 0
}

# Where backups are: the folder given, else the sudo user's home and the current folder; the console's one apart.
bk_home() { getent passwd "${SUDO_USER:-$(id -un)}" 2>/dev/null | cut -d: -f6; }
bk_files() {   # bk_files DIR...  -> the backups, newest first (their names carry the date, YYYYMMDD-HHMM)
  local d
  for d in "$@"; do [ -d "$d" ] && find "$d" -maxdepth 1 -type f -name 'zenithboard-backup-*.tar.gz'; done | sort -u |
    while IFS= read -r f; do printf '%s\t%s\n' "$(stat -c %Y "$f")" "$f"; done | sort -rn | cut -f2
}

backup_list() {   # backup_list [DIR]
  local f n=0 dirs
  if [ -n "${1:-}" ]; then dirs=("$1"); else dirs=("$(bk_home)" "$PWD"); fi
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    n=$((n + 1)); printf '  %s  %6s  %s\n' "$(date -r "$f" '+%Y-%m-%d %H:%M')" "$(bk_size "$f")" "$f"
  done < <(bk_files "${dirs[@]}")
  [ "$n" -gt 0 ] || echo "  No backup in ${dirs[*]}."
  [ ! -f "$BK_CONSOLE_OUT" ] || printf '  %s  %6s  %s  (the console'"'"'s, replaced by each new one)\n' "$(date -r "$BK_CONSOLE_OUT" '+%Y-%m-%d %H:%M')" "$(bk_size "$BK_CONSOLE_OUT")" "$BK_CONSOLE_OUT"
  return 0
}

backup_clean() {   # backup_clean [--keep N] [--yes] [DIR]  -> the older backups deleted, the N newest kept (3)
  local keep=3 yes=0 dir="" f old=() w
  while [ $# -gt 0 ]; do case "$1" in --keep) keep="${2:-}"; shift ;; --yes) yes=1 ;; *) dir="$1" ;; esac; shift; done
  [[ $keep =~ ^[0-9]+$ ]] && [ "$keep" -ge 1 ] || { err "--keep takes a number, 1 or more."; return 1; }
  [ -n "$dir" ] || dir=$(bk_home)
  while IFS= read -r f; do [ -n "$f" ] && old+=("$f"); done < <(bk_files "$dir" | tail -n +"$((keep + 1))")
  if [ "${#old[@]}" -eq 0 ]; then echo "Nothing to delete: $keep backup(s) or fewer in $dir."; return 0; fi
  echo "Kept: the $keep newest. Deleted:"; printf '  %s\n' "${old[@]}"
  if [ "$yes" != 1 ]; then
    read -r -p "Type delete to go on: " w || w=""
    [ "$w" = delete ] || { echo "Nothing was deleted."; return 1; }
  fi
  rm -f -- "${old[@]}" && echo "Deleted ${#old[@]} backup(s)."
}

backup_delete_console() {
  if [ -f "$BK_CONSOLE_OUT" ]; then rm -f "$BK_CONSOLE_OUT"; echo "The console's backup is deleted ($BK_CONSOLE_OUT)."
  else echo "The console holds no backup."; fi
}

backup_menu() {
  local c f out
  while true; do
    c=$(wt_menu "Backup and restore\n\nOne file with the settings, the features that are on, the statistics, graphs1090's history, the kept logs and the networks' identities: to keep, or to move to a new card." \
      make "1  Make a backup now (in your home folder)" \
      show "2  Show what a backup holds, and check it reads back" \
      list "3  List the backups, newest first" \
      clean "4  Delete the older ones, keep the 3 newest (asks you to type delete)" \
      restore "5  Restore a backup (asks you to type RESTORE)" \
      back "Return to the previous menu") || return 0
    case "$c" in
      make) out=$(backup_make "$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)/zenithboard-backup-$(hostname)-$(date +%Y%m%d-%H%M).tar.gz" 2>&1); wt_msg "$out" 20 ;;
      show) f=$(wt_input "The backup file (its full path):" "$(ls -t "$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)"/zenithboard-backup-*.tar.gz 2>/dev/null | head -1)") || continue
            wt_msg "$(backup_show "$f" 2>&1)" 20 ;;
      list) wt_msg "Backups, newest first (their names carry the date, so they sort the same way):\n\n$(backup_list "" 2>&1)" 20 ;;
      clean) clear; backup_clean "$(bk_home)"; read -r -p "Press Enter to go back to the menu. " _ ;;
      restore) f=$(wt_input "The backup file to restore (its full path; copy it here first with scp):" "$(ls -t "$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)"/zenithboard-backup-*.tar.gz 2>/dev/null | head -1)") || continue
            clear; backup_restore "$f"; read -r -p "Press Enter to go back to the menu. " _ ;;
      *) return 0 ;;
    esac
  done
}
