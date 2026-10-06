# SPDX-License-Identifier: GPL-3.0-or-later
# shellcheck shell=bash
# Shared helpers for install.sh and the `zenithboard` command. Source this file; do not execute it.

ZB_ETC="${ZENITHBOARD_ETC:-/etc/zenithboard}"   # override only for testing
ZB_CONFIG="$ZB_ETC/config.env"
ZB_HOME="/opt/zenithboard"; export ZB_HOME
ZB_DATA="/var/lib/zenithboard"; export ZB_DATA
ZB_USER="zenithboard"; export ZB_USER
RADIUS_PRESETS="1 2 5 10 15 30 50"

# shellcheck source=lib/versions.sh
. "$(dirname "${BASH_SOURCE[0]}")/versions.sh"

# ------------------------------------------------------------------ output
if [ -t 1 ]; then C_B=$'\e[1m'; C_G=$'\e[32m'; C_Y=$'\e[33m'; C_R=$'\e[31m'; C_0=$'\e[0m'; else C_B=""; C_G=""; C_Y=""; C_R=""; C_0=""; fi
export C_B
log()  { printf '%s==>%s %s\n' "$C_G" "$C_0" "$*"; }
warn() { printf '%s!!%s  %s\n' "$C_Y" "$C_0" "$*" >&2; }
err()  { printf '%sERROR:%s %s\n' "$C_R" "$C_0" "$*" >&2; }
die()  { err "$*"; exit 1; }

need_root() { [ "$(id -u)" -eq 0 ] || die "Please run as root:  sudo $0 $*"; }

# ------------------------------------------------------------------ config file (KEY=value, sourced by bash AND parsed by python)
cfg_get() {  # cfg_get KEY [default]
  local v=""
  if [ -f "$ZB_CONFIG" ]; then
    v=$(grep -E "^$1=" "$ZB_CONFIG" | tail -n1 | cut -d= -f2-)
    v=${v#\"}; v=${v%\"}
  fi
  printf '%s' "${v:-${2:-}}"
}

cfg_set() {  # cfg_set KEY VALUE
  local key="$1" val="$2" tmp
  mkdir -p "$ZB_ETC"; touch "$ZB_CONFIG"
  case "$val" in *[[:space:]]*) val="\"$val\"" ;; esac
  tmp=$(mktemp)
  grep -v -E "^$key=" "$ZB_CONFIG" > "$tmp" || true
  printf '%s=%s\n' "$key" "$val" >> "$tmp"
  install -m 644 "$tmp" "$ZB_CONFIG"; rm -f "$tmp"
}

cfg_defaults() {  # write any missing keys with defaults (never overwrites)
  local k v
  while IFS='=' read -r k v; do
    [ -n "$k" ] || continue
    [ -n "$(grep -E "^$k=" "$ZB_CONFIG" 2>/dev/null)" ] || cfg_set "$k" "$v"
  done <<'DEF'
UNITS=metric
THEME=amber
RADIUS=10
CYCLE_SECONDS=6
SHOW_PHOTOS=1
SHOW_ROUTES=1
AUTO_DATA_REFRESH=1
REGION=world
UAT978=0
UAT_SDR=
PORT=8080
DECODER=readsb
ADSB_SDR=
ACARS_SDR=
ACARS_FREQS=131.525 131.725 131.825
ACARS_RETENTION_DAYS=7
ACARS_IGNORE_EMPTY=1
ACARS_IGNORE_LABELS=_d,Q0,SQ
ACARS_UDP_PORT=5555
ACARS_DB=/var/lib/zenithboard/acars.db
DEF
}

# ------------------------------------------------------------------ validation
is_number() { [[ "$1" =~ ^-?[0-9]+([.][0-9]+)?$ ]]; }
valid_lat() { is_number "$1" && awk -v v="$1" 'BEGIN{exit !(v>=-90 && v<=90)}'; }
valid_lon() { is_number "$1" && awk -v v="$1" 'BEGIN{exit !(v>=-180 && v<=180)}'; }
valid_radius() { local r; for r in $RADIUS_PRESETS; do [ "$r" = "$1" ] && return 0; done; return 1; }
valid_theme() { case "$1" in amber|green|red|white) return 0 ;; *) return 1 ;; esac; }
valid_units() { [ "$1" = metric ] || [ "$1" = imperial ]; }

# ------------------------------------------------------------------ system state
unit_exists()  { systemctl list-unit-files "$1.service" 2>/dev/null | grep -q "^$1.service"; }
unit_active()  { systemctl is-active --quiet "$1"; }
pkg_installed() { dpkg -s "$1" >/dev/null 2>&1; }
arch() { dpkg --print-architecture; }

is_readsb()      { [ -x /usr/bin/readsb ] || [ -x /usr/local/bin/readsb ]; }
is_dump1090()    { pkg_installed dump1090-fa; }
is_adsbx()       { unit_exists adsbexchange-feed; }
is_piaware()     { pkg_installed piaware; }
is_fr24()        { pkg_installed fr24feed; }
is_planefinder() { pkg_installed pfclient; }
is_flightinfo()  { unit_exists zenithboard-flightinfo; }
is_acars()       { unit_exists zenithboard-acarsdec; }
is_grafana()     { pkg_installed grafana; }

installed_decoder() { if is_readsb; then echo readsb; elif is_dump1090; then echo dump1090-fa; fi; }
decoder_json()   { echo "/run/$(cfg_get DECODER readsb)/aircraft.json"; }

apt_install() { DEBIAN_FRONTEND=noninteractive apt-get install -y "$@"; }
apt_remove()  { DEBIAN_FRONTEND=noninteractive apt-get purge -y "$@"; }

fetch() {  # fetch URL DEST   (fails loudly)
  curl -fsSL --retry 3 --connect-timeout 15 -o "$2" "$1" || { err "Download failed: $1"; return 1; }
}

ini_set() {  # ini_set FILE KEY VALUE  -> KEY="VALUE" (replace or append)
  local f="$1" k="$2" v="$3"
  touch "$f"
  if grep -qE "^$k=" "$f"; then sed -i -E "s|^$k=.*|$k=\"$v\"|" "$f"; else printf '%s="%s"\n' "$k" "$v" >> "$f"; fi
}

# ------------------------------------------------------------------ whiptail helpers (all return non-zero on Cancel)
WT_TITLE="ZenithBoard - ADSB Flight Info"
wt_msg()   { whiptail --title "$WT_TITLE" --msgbox "$1" "${2:-16}" 76; }
wt_yesno() { whiptail --title "$WT_TITLE" --yesno "$1" "${2:-12}" 76; }
wt_input() { whiptail --title "$WT_TITLE" --inputbox "$1" 10 76 "${2:-}" 3>&1 1>&2 2>&3; }
# wt_menu "text" tag item tag item ...
wt_menu()  { local t="$1"; shift; whiptail --title "$WT_TITLE" --menu "$t" 22 76 12 "$@" 3>&1 1>&2 2>&3; }
# wt_radio "text" tag item ON|OFF ...
wt_radio() { local t="$1"; shift; whiptail --title "$WT_TITLE" --radiolist "$t" 20 76 8 "$@" 3>&1 1>&2 2>&3; }
# wt_check "text" tag item ON|OFF ...
wt_check() { local t="$1"; shift; whiptail --title "$WT_TITLE" --checklist "$t" 22 76 10 "$@" 3>&1 1>&2 2>&3; }

radius_radio_items() {  # radius_radio_items CURRENT UNITS -> args for wt_radio
  local r unit="km"; [ "$2" = imperial ] && unit="mi"
  for r in $RADIUS_PRESETS; do
    if [ "$r" = "$1" ]; then printf '%s\n%s\n%s\n' "$r" "$r $unit" ON; else printf '%s\n%s\n%s\n' "$r" "$r $unit" OFF; fi
  done
}

pick_radius() {  # prints the chosen preset on stdout
  local units items; units=$(cfg_get UNITS metric)
  mapfile -t items < <(radius_radio_items "$(cfg_get RADIUS 10)" "$units")
  wt_radio "Detection radius in $( [ "$units" = imperial ] && echo miles || echo kilometres ).\nAircraft inside it are cycled on the wall." "${items[@]}"
}

restart_flightinfo() { unit_exists zenithboard-flightinfo && systemctl restart zenithboard-flightinfo || true; }

# ------------------------------------------------------------------ hardware: memory and Pi model
LOW_MEM_MB=1500          # boards below this (a "1 GB" Pi reports ~900 MB) are treated as low-memory
mem_total_mb() { awk '/^MemTotal:/ {printf "%d", $2/1024}' "${ZB_MEMINFO:-/proc/meminfo}"; }
mem_avail_mb() { awk '/^MemAvailable:/ {printf "%d", $2/1024}' "${ZB_MEMINFO:-/proc/meminfo}"; }
is_low_mem()   { [ "$(mem_total_mb)" -lt "$LOW_MEM_MB" ]; }
pi_model()     { tr -d '\0' < "${ZB_PI_MODEL_FILE:-/proc/device-tree/model}" 2>/dev/null; }
is_old_pi()    { pi_model | grep -qE 'Raspberry Pi (Zero|[0-3]|Model)'; }   # Zero, 1, 2, 3 (any variant)

local_ip() { hostname -I 2>/dev/null | awk '{print $1}'; }
