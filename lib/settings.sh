#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Settings as a file (export / import), the per-tablet presets, and the two Wi-Fi hardening settings (0.21.0).
# Sourced by bin/zenithboard and install.sh after lib/common.sh.

# ---- export / import: config.env alone. Never the secrets (the Bluesky app password lives in its own file,
# root-only), never the feeders' keys files: a settings file is something people paste into an issue.
SETTINGS_SECRET_KEYS='^(ADSBX_KEY|FR24_KEY|PIAWARE_FEEDER_ID|PLANEFINDER_KEY|GRAFANA_PASSWORD|.*PASSWORD.*|.*TOKEN.*|.*SECRET.*)='

settings_export() {   # settings_export [FILE]  -> the file written (stdout when FILE is -)
  local out="${1:-}" tmp
  [ -f "$ZB_CONFIG" ] || { echo "No settings yet ($ZB_CONFIG)." >&2; return 1; }
  [ -n "$out" ] || out="zenithboard-settings-$(hostname)-$(date +%Y%m%d).env"
  tmp=$(mktemp)
  {
    printf '# ZenithBoard settings, exported %s from %s, version %s\n' "$(date '+%Y-%m-%d %H:%M')" "$(hostname)" "$ZB_VERSION"
    printf '# Import on another Pi:  sudo zenithboard settings import FILE\n# Keys that look like secrets were left out.\n'
    grep -E '^[A-Z][A-Z0-9_]*=' "$ZB_CONFIG" | grep -v -E "$SETTINGS_SECRET_KEYS" | grep -v -E '^HW_NOTICE_SEEN='
  } > "$tmp"
  if [ "$out" = - ]; then cat "$tmp"; rm -f "$tmp"; return 0; fi
  install -m 644 "$tmp" "$out" && rm -f "$tmp" && echo "$out"
}

# Import: only well-formed KEY=VALUE lines, only keys that are not secrets, no shell at all (the file is read,
# never sourced). The current file is kept as config.env.bak-DATE first, so an import is one copy away from undone.
settings_import() {   # settings_import FILE
  local f="$1" n=0 bad=0 line k v bak
  [ -f "$f" ] || { echo "No such file: $f" >&2; return 1; }
  grep -q -E '^[A-Z][A-Z0-9_]*=' "$f" || { echo "$f holds no KEY=VALUE line: not a settings file." >&2; return 1; }
  bak="$ZB_CONFIG.bak-$(date +%Y%m%d-%H%M%S)"
  [ -f "$ZB_CONFIG" ] && install -m 644 "$ZB_CONFIG" "$bak"
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue ;; esac
    if [[ ! $line =~ ^([A-Z][A-Z0-9_]*)=(.*)$ ]]; then bad=$((bad + 1)); continue; fi
    k=${BASH_REMATCH[1]}; v=${BASH_REMATCH[2]}
    v=${v#\"}; v=${v%\"}
    case "$k=" in HW_NOTICE_SEEN=) continue ;; esac
    if printf '%s=' "$k" | grep -q -E "$SETTINGS_SECRET_KEYS"; then bad=$((bad + 1)); continue; fi
    case "$v" in *$'\n'*|*'`'*|*'$('*) bad=$((bad + 1)); continue ;; esac
    cfg_set "$k" "$v"; n=$((n + 1))
  done < "$f"
  echo "Imported $n setting(s) from $f.$( [ "$bad" -gt 0 ] && printf ' Skipped %s line(s): not a setting, or a secret.' "$bad" )"
  [ -z "$bak" ] || [ ! -f "$bak" ] || echo "The settings from before are in $bak  (put them back: sudo zenithboard settings import $bak)"
  return 0
}

# What an import must restart so that it is taken: the wall reads config.env at every request (nothing to do);
# the services that read it once at start are restarted when they are installed.
settings_apply() {
  is_flightinfo 2>/dev/null && restart_flightinfo >/dev/null 2>&1
  [ "$(cfg_get SOCIAL 0)" = 1 ] && systemctl try-restart zenithboard-social.service 2>/dev/null
  return 0
}

# ---- presets: a name for a set of the tablet's own choices, kept in config.env as PRESET_<NAME>, so that a
# second screen opens  http://PI:8080/?p=kitchen  instead of a long address. The wall serves them in /api/config.
PRESET_KEYS="units radius cycle theme mode flags"

preset_valid_name() { [[ $1 =~ ^[a-z][a-z0-9]{0,15}$ ]]; }
preset_key_of() { printf 'PRESET_%s' "$(printf '%s' "$1" | tr '[:lower:]' '[:upper:]')"; }

preset_valid_pair() {   # preset_valid_pair key=value -> 0 when it is one of the tablet's settings with a sane value
  local k=${1%%=*} v=${1#*=}
  case "$k" in
    units) [ "$v" = metric ] || [ "$v" = imperial ] ;;
    radius) is_number "$v" && awk -v r="$v" 'BEGIN { exit !(r > 0 && r <= 500) }' ;;
    cycle) is_number "$v" && awk -v c="$v" 'BEGIN { exit !(c >= 2 && c <= 60) }' ;;
    theme) [[ $v =~ ^[a-z]+$ ]] ;;
    mode) [ "$v" = dots ] || [ "$v" = flap ] ;;
    flags) [ "$v" = 0 ] || [ "$v" = 1 ] ;;
    *) return 1 ;;
  esac
}

preset_add() {   # preset_add NAME key=value...
  local name="$1" p pairs=(); shift
  preset_valid_name "$name" || { echo "A preset name is 1 to 16 lower-case letters or digits, starting with a letter (kitchen, tv2)." >&2; return 1; }
  [ $# -gt 0 ] || { echo "Give what the preset sets: one or more of  $PRESET_KEYS  as key=value." >&2; return 1; }
  for p in "$@"; do
    preset_valid_pair "$p" || { echo "Not a tablet setting, or a bad value: $p   (keys: $PRESET_KEYS; mode dots|flap; units metric|imperial; flags 0|1)" >&2; return 1; }
    pairs+=("$p")
  done
  cfg_set "$(preset_key_of "$name")" "${pairs[*]}"
  echo "Preset $name: ${pairs[*]}"
  echo "Open on that tablet:  http://$(hostname -I 2>/dev/null | awk '{print $1}'):$(cfg_get PORT 8080)/?p=$name"
}

preset_del() {
  preset_valid_name "$1" || { echo "No such preset: $1" >&2; return 1; }
  [ -n "$(cfg_get "$(preset_key_of "$1")" "")" ] || { echo "No preset called $1 (see: zenithboard preset list)" >&2; return 1; }
  cfg_del "$(preset_key_of "$1")"; echo "Preset $1 forgotten. A tablet that still opens ?p=$1 shows the wall's defaults."
}

preset_list() {
  local line n v found=0
  while IFS= read -r line; do
    n=${line%%=*}; n=${n#PRESET_}; n=$(printf '%s' "$n" | tr '[:upper:]' '[:lower:]')
    v=${line#*=}; v=${v#\"}; v=${v%\"}
    printf '%-16s %s\n' "$n" "$v"; found=1
  done < <(grep -E '^PRESET_[A-Z0-9]+=' "$ZB_CONFIG" 2>/dev/null)
  [ "$found" = 1 ] || echo "No preset yet. Make one:  sudo zenithboard preset add kitchen theme=green mode=flap radius=5"
}

# ---- Wi-Fi hardening (0.21.0): two settings of the Wi-Fi profile that cost nothing.
#   connection.autoconnect-retries 0  : NetworkManager keeps trying to join after a loss, instead of giving up
#                                       after four tries and waiting for a kick
#   802-11-wireless.powersave 2       : the radio's power saving off, a known cause of short losses on a Pi
# Off by default. "on" notes the profile's values first, so "off" puts back exactly what was there.
wifi_harden_profile() {   # the active Wi-Fi profile's UUID, or the first saved one
  local u
  u=$(nmcli -t -f UUID,TYPE connection show --active 2>/dev/null | awk -F: '$2=="802-11-wireless" {print $1; exit}')
  [ -n "$u" ] || u=$(nmcli -t -f UUID,TYPE connection show 2>/dev/null | awk -F: '$2=="802-11-wireless" {print $1; exit}')
  printf '%s' "$u"
}
wifi_harden_state() { [ "$(cfg_get WIFI_HARDEN 0)" = 1 ] && echo on || echo off; }
wifi_harden_on() {
  local u retries ps
  u=$(wifi_harden_profile); [ -n "$u" ] || { echo "No saved Wi-Fi network to harden (see: zenithboard wifi list)." >&2; return 1; }
  if [ "$(cfg_get WIFI_HARDEN 0)" != 1 ]; then
    retries=$(nmcli -g connection.autoconnect-retries connection show uuid "$u" 2>/dev/null)
    ps=$(nmcli -g 802-11-wireless.powersave connection show uuid "$u" 2>/dev/null)
    cfg_set WIFI_HARDEN_PREV "${retries:--1},${ps:-0},$u"
  fi
  nmcli connection modify uuid "$u" connection.autoconnect-retries 0 802-11-wireless.powersave 2 || return 1
  cfg_set WIFI_HARDEN 1
  echo "Wi-Fi hardening is ON for the saved network: it is retried without end after a loss, and the radio's power saving is off."
  echo "Taken at the next connection (now: sudo nmcli connection up uuid $u, which cuts a Wi-Fi session for a few seconds). Off again: sudo zenithboard wifi harden off"
}
wifi_harden_off() {
  local prev retries ps u
  prev=$(cfg_get WIFI_HARDEN_PREV ""); u=${prev##*,}
  [ -n "$u" ] || u=$(wifi_harden_profile)
  retries=${prev%%,*}; ps=${prev#*,}; ps=${ps%%,*}
  [ -n "$u" ] && nmcli connection modify uuid "$u" connection.autoconnect-retries "${retries:--1}" 802-11-wireless.powersave "${ps:-0}" 2>/dev/null
  cfg_set WIFI_HARDEN 0; cfg_del WIFI_HARDEN_PREV
  echo "Wi-Fi hardening is OFF: the profile's two settings are back to what they were (retries ${retries:--1}, power saving ${ps:-0})."
}
wifi_harden_status() {
  local u
  echo "Wi-Fi hardening: $(wifi_harden_state)   (sudo zenithboard wifi harden on|off)"
  u=$(wifi_harden_profile); [ -n "$u" ] || return 0
  echo "Profile now: autoconnect-retries $(nmcli -g connection.autoconnect-retries connection show uuid "$u" 2>/dev/null) (0 = without end, -1 = NetworkManager's default of 4), powersave $(nmcli -g 802-11-wireless.powersave connection show uuid "$u" 2>/dev/null) (2 = off, 3 = on, 0 = the driver's default)"
}
