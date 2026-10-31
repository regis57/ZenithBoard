# SPDX-License-Identifier: GPL-3.0-or-later
# shellcheck shell=bash
# Shared helpers for install.sh and the `zenithboard` command. Source this file; do not execute it.

ZB_ETC="${ZENITHBOARD_ETC:-/etc/zenithboard}"   # override only for testing
ZB_CONFIG="$ZB_ETC/config.env"
ZB_HOME="${ZENITHBOARD_HOME:-/opt/zenithboard}"; export ZB_HOME     # override only for testing (tests/test_install.sh)
ZB_BIN_DIR="${ZENITHBOARD_BIN_DIR:-/usr/local/bin}"; export ZB_BIN_DIR   # where the zenithboard command is linked
ZB_DATA="/var/lib/zenithboard"; export ZB_DATA
# where the units are installed; a test points it at a folder of its own (the audit of 22-23 October 2026: run as root,
# the tests wrote the real /etc/systemd/system)
ZB_UNIT_DIR="${ZB_SYSTEMD_DIR:-/etc/systemd/system}"; export ZB_UNIT_DIR
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

# The audit of 22-23 October 2026: config.env was rewritten in place from a copy in /tmp, so a power cut in the middle
# could leave it cut short, and two writers at once could lose one's setting. Now the new file is written beside it,
# put on the card, and renamed over it in one step, one writer at a time.
cfg_write() {  # cfg_write KEY [VALUE]: the file without KEY, then KEY=VALUE when a value is given
  local key="$1" tmp
  mkdir -p "$ZB_ETC"; touch "$ZB_CONFIG"
  {
    command -v flock >/dev/null && flock -w 10 9
    tmp=$(mktemp "${ZB_CONFIG%/*}/.config.env.XXXXXX") || return 1
    # the review of 0.99.8: the key is compared as text, never read as a pattern (config-set '.*' x emptied the file)
    ZB_CFG_KEY="$key" awk 'index($0, ENVIRON["ZB_CFG_KEY"] "=") != 1' "$ZB_CONFIG" > "$tmp" || true
    [ $# -lt 2 ] || printf '%s=%s\n' "$key" "$2" >> "$tmp"
    chmod 644 "$tmp"; sync "$tmp" 2>/dev/null || true
    mv -f "$tmp" "$ZB_CONFIG"
  } 9>>"${ZB_CONFIG%/*}/.config.lock"
}
cfg_set() {  # cfg_set KEY VALUE
  local val="$2"
  case "$val" in *[[:space:]]*) val="\"$val\"" ;; esac
  cfg_write "$1" "$val"
}

cfg_del() {  # cfg_del KEY: the key gone from the file
  [ -f "$ZB_CONFIG" ] || return 0
  cfg_write "$1"
}

cfg_defaults() {  # write any missing keys with defaults (never overwrites)
  local k v
  while IFS='=' read -r k v; do
    [ -n "$k" ] || continue
    [ -n "$(grep -E "^$k=" "$ZB_CONFIG" 2>/dev/null)" ] || cfg_set "$k" "$v"
  done <<'DEF'
UNITS=metric
THEME=amber
DISPLAY_MODE=dots
RADIUS=10
CYCLE_SECONDS=14
FLAGS=1
SHOW_PHOTOS=1
SHOW_ROUTES=1
AUTO_DATA_REFRESH=1
GAINLOG=0
PATCHES=0
STATS=0
GRAPHS_LOOK=zenithboard
CONSOLE=0
CONSOLE_PHONE_SIGNIN=0
UPDATE_VERIFY=1
REGION=world
UAT978=0
UAT_SDR=
WIFI=
WIFI_COUNTRY=
PORT=8080
BIND_ADDRESS=0.0.0.0
ALLOW_FROM=private
DECODER=readsb
ADSB_SDR=
DEF
}

# ------------------------------------------------------------------ validation
is_number() { [[ "$1" =~ ^-?[0-9]+([.][0-9]+)?$ ]]; }
# seconds each aircraft stays on the wall: whole seconds, 2 to 60, as the presets and the console have it (the audit of
# 22-23 October 2026: the menu and the command took 0, -3 and 600)
valid_cycle() { [[ ${1:-} =~ ^[0-9]{1,2}$ ]] && [ "$((10#$1))" -ge 2 ] && [ "$((10#$1))" -le 60 ]; }
# the review of 0.99.8: what goes into the decoders' and feeders' own files (by sed or as an option) holds no character
# a shell or sed gives a meaning to
valid_alt() { [[ ${1:-} =~ ^-?[0-9]{1,4}$ ]]; }                 # metres, whole
valid_sdr() { [[ ${1:-} =~ ^[A-Za-z0-9_-]{1,32}$ ]]; }          # a dongle's serial or index
valid_plain_value() { case "${1:-}" in *[\"\\\|\&\;\<\>\$\`]*|*$'\n'*|*$'\r'*) return 1 ;; *) return 0 ;; esac; }
valid_lat() { is_number "$1" && awk -v v="$1" 'BEGIN{exit !(v>=-90 && v<=90)}'; }
valid_lon() { is_number "$1" && awk -v v="$1" 'BEGIN{exit !(v>=-180 && v<=180)}'; }
valid_radius() { local r; for r in $RADIUS_PRESETS; do [ "$r" = "$1" ] && return 0; done; return 1; }
valid_theme() { case "$1" in amber|green|red|white|turquoise) return 0 ;; *) return 1 ;; esac; }   # blue: gone in 0.23.0
# The wall's colour as it shows: one taken out (the dark blue, 0.23.0) shows as amber until another is chosen, and the
# menus and messages say amber, not the word left in config.env
wall_theme() { local t; t=$(cfg_get THEME amber); if valid_theme "$t"; then printf '%s' "$t"; else printf amber; fi; }
# 0.55.0: aviation, the way pilots and controllers count: distances in nautical miles, speeds in knots, heights in feet
valid_units() { [ "$1" = metric ] || [ "$1" = imperial ] || [ "$1" = aviation ]; }
units_distance() { case "$1" in imperial) echo mi ;; aviation) echo NM ;; *) echo km ;; esac; }   # the radius's unit

# ------------------------------------------------------------------ system state
unit_exists()  { systemctl list-unit-files "$1.service" 2>/dev/null | grep -q "^$1.service"; }
unit_active()  { systemctl is-active --quiet "$1"; }
pkg_installed() { dpkg -s "$1" >/dev/null 2>&1; }
arch() { dpkg --print-architecture; }

is_readsb()      { [ -x /usr/bin/readsb ] || [ -x /usr/local/bin/readsb ]; }
is_dump1090()    { pkg_installed dump1090-fa; }
is_adsbx()       { unit_exists adsbexchange-feed; }
is_radarbox()    { pkg_installed rbfeeder; }       # 0.99.6: AirNav Radar
is_piaware()     { pkg_installed piaware; }
is_fr24()        { pkg_installed fr24feed; }
is_planefinder() { pkg_installed pfclient; }
is_flightinfo()  { unit_exists zenithboard-flightinfo; }

# The wall's own user, made by menu 2 until 0.43.0; now by whatever needs it first. On a fresh card the console
# (whose folders belong to it) was switched on before the wall: "chown: invalid user: zenithboard" (the owner,
# 21 October 2026, a new card on a Pi 4). Root only: tests and plain users never make users.
ensure_zb_user() {
  [ "$(id -u)" -eq 0 ] && [ "${ZB_SKIP_SERVICES:-}" != 1 ] || return 0
  id "$ZB_USER" >/dev/null 2>&1 || useradd --system --home-dir "$ZB_DATA" --shell /usr/sbin/nologin "$ZB_USER"
  # 2751: anyone may walk through to data/ (so `zenithboard status` works without sudo) but only the service
  # may list the folder, which keeps the statistics and the social state out of sight.
  install -d -o "$ZB_USER" -g "$ZB_USER" -m 2751 "$ZB_DATA"
  # the downloaded aircraft-type list is read by the wall server (user zenithboard): world-readable, root-writable
  install -d -m 755 "$ZB_DATA/data"
}



# 0.47.0: the web pages' languages. English always; the others when this copy of ZenithBoard carries their catalogue
# (flightinfo/static/i18n/<code>/console.json), so a language is offered only once it is translated. The same codes
# as flightinfo/static/i18n.js and flightinfo/console_actions.py (tests/test_i18n.sh holds the three together).
ZB_LANG_CODES="en fr de nl it es pt-BR pl fi et lv lt id sw hi ru uk ar ja ko zh-Hans zh-Hant"
zb_langs() {
  local c out=en
  for c in $ZB_LANG_CODES; do
    [ "$c" != en ] && [ -f "$ZB_HOME/flightinfo/static/i18n/$c/console.json" ] && [ ! -e "$ZB_HOME/flightinfo/static/i18n/$c/draft.txt" ] && out="$out $c"
  done
  echo "$out"
}

installed_decoder() { if is_readsb; then echo readsb; elif is_dump1090; then echo dump1090-fa; fi; }
decoder_json()   { echo "/run/$(cfg_get DECODER readsb)/aircraft.json"; }

apt_install() { DEBIAN_FRONTEND=noninteractive apt-get install -y "$@"; }
apt_remove()  { DEBIAN_FRONTEND=noninteractive apt-get purge -y "$@"; }

# A download that is about to be run as root never lands on a name somebody could have created first.
# zb_tmp NAME gives a path inside a private folder (mode 700, random name), made once per run.
#
# zb_tmp_init MUST be called from the main shell (bin/zenithboard, install.sh). It is almost always used as
# f=$(zb_tmp x), which runs in a SUBSHELL: a folder made there would be removed by that subshell's own EXIT
# trap before the caller could write to it. Hence the split, and hence no trap inside zb_tmp itself.
zb_tmp_init() {
  [ -n "${ZB_TMPDIR:-}" ] && return 0
  ZB_TMPDIR=$(mktemp -d "${TMPDIR:-/tmp}/zenithboard.XXXXXXXX") || { err "Could not make a temporary folder"; return 1; }
  chmod 700 "$ZB_TMPDIR"
  trap 'zb_tmp_clean' EXIT
}
zb_tmp() {
  if [ -z "${ZB_TMPDIR:-}" ]; then
    # no init (a library used on its own): make one that nobody will remove under our feet
    ZB_TMPDIR=$(mktemp -d "${TMPDIR:-/tmp}/zenithboard.XXXXXXXX") || { err "Could not make a temporary folder"; return 1; }
    chmod 700 "$ZB_TMPDIR"
  fi
  printf '%s/%s' "$ZB_TMPDIR" "$1"
}
zb_tmp_clean() { [ -z "${ZB_TMPDIR:-}" ] || rm -rf "$ZB_TMPDIR"; ZB_TMPDIR=""; }

# 0.52.0: a station's identity (ADSB Exchange's UUID, FlightAware's feeder ID) hidden in output that is often pasted
zb_mask_ids() { sed -E 's/\{?[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}?/(id hidden)/g'; }

# 0.52.0: the installers whose added packages are noted for `off` (graphs1090, ADSB Exchange's stats) run one at a time,
# so one never counts the other's packages as its own (the console running one while the terminal runs the other)
ZB_PKG_LOCK="${ZB_PKG_LOCK:-/run/lock/zenithboard-packages.lock}"
zb_pkg_locked() {  # zb_pkg_locked COMMAND...   runs it holding the lock; waits up to 30 minutes for the other
  ( flock -w "${ZB_PKG_LOCK_WAIT:-1800}" 9 || { err "Another installation is still running (graphs1090 or ADSB Exchange's stats): try again when it ends."; exit 1; }
    "$@" ) 9>>"$ZB_PKG_LOCK"
}

fetch() {  # fetch URL DEST   (fails loudly)
  # https only, and a redirection cannot drop to plain http on the way
  curl -fsSL --proto '=https' --proto-redir '=https' --tlsv1.2 --retry 3 --connect-timeout 15 --max-time 900 \
       -o "$2" "$1" || { err "Download failed: $1   (no internet on the Pi, or the address moved: see lib/versions.sh)"; return 1; }
}

# The review of 0.99.8: the value went into a sed expression, so a | or a quote in it was a command. Now it reaches awk
# through the environment (awk -v would turn its backslashes into escapes) and is written as it is, into a file beside
# the original that takes its place in one step, with its owner and mode.
ini_set() {  # ini_set FILE KEY VALUE  -> KEY="VALUE" (replace or append)
  local f="$1" tmp
  touch "$f" || return 1
  tmp=$(mktemp "$f.XXXXXX") || return 1
  if ZB_INI_K="$2" ZB_INI_V="$3" awk 'BEGIN { k = ENVIRON["ZB_INI_K"]; line = k "=\"" ENVIRON["ZB_INI_V"] "\"" }
      index($0, k "=") == 1 { if (!done) print line; done = 1; next }
      { print }
      END { if (!done) print line }' "$f" > "$tmp"; then
    chmod --reference="$f" "$tmp" 2>/dev/null || true; chown --reference="$f" "$tmp" 2>/dev/null || true
    mv -f "$tmp" "$f"
  else
    rm -f "$tmp"; return 1
  fi
}

# 0.99.6: an ini file with [sections] and plain key=value lines (AirNav Radar's rbfeeder.ini)
ini_sec_get() {   # ini_sec_get FILE SECTION KEY
  awk -v sec="$2" -v k="$3" '
    /^[ \t]*\[.*\][ \t]*$/ { s = $0; gsub(/[][ \t]/, "", s); insec = (s == sec); next }
    insec { line = $0; sub(/^[ \t]+/, "", line); if (index(line, k "=") == 1 || line ~ ("^" k "[ \t]+=")) { sub(/^[^=]*=[ \t]*/, "", line); sub(/[ \t\r]+$/, "", line); print line; exit } }' "$1" 2>/dev/null
}
ini_sec_set() {   # ini_sec_set FILE SECTION KEY VALUE: replaced inside its section, added at its end, or a new section
  local f="$1" tmp
  [ -f "$f" ] || : > "$f"
  tmp=$(mktemp "$f.XXXXXX") || return 1
  # blank lines are held back, so a line added to a section goes before the blank lines that end it
  awk -v sec="$2" -v k="$3" -v v="$4" '
    function blanks() { while (nb > 0) { print ""; nb-- } }
    function flush() { if (insec && !done) { print k "=" v; done = 1 } }
    /^[ \t]*$/ { nb++; next }
    /^[ \t]*\[.*\][ \t]*$/ { flush(); blanks(); s = $0; gsub(/[][ \t]/, "", s); insec = (s == sec); if (insec) seen = 1; print; next }
    insec { line = $0; sub(/^[ \t]+/, "", line); if (index(line, k "=") == 1 || line ~ ("^" k "[ \t]+=")) { blanks(); if (!done) print k "=" v; done = 1; next } }
    { blanks(); print }
    END { flush(); blanks(); if (!seen) { print ""; print "[" sec "]"; print k "=" v } }' "$f" > "$tmp" && cat "$tmp" > "$f"
  local rc=$?; rm -f "$tmp"; return "$rc"
}

# ------------------------------------------------------------------ whiptail helpers (all return non-zero on Cancel)
WT_TITLE="ZenithBoard - ADSB Flight Info"
wt_msg()   { whiptail --title "$WT_TITLE" --msgbox "$1" "${2:-16}" 76; }
wt_yesno() { whiptail --title "$WT_TITLE" --yesno "$1" "${2:-12}" 76; }
# 0.54.18: tall enough for a question of several lines (the position's, with where to find it)
wt_input() {
  local nl h; nl=$(grep -o '\\n' <<<"$1" | wc -l); h=$(( ${#1} / 68 + nl + 8 )); [ "$h" -ge 10 ] || h=10; [ "$h" -le 22 ] || h=22
  whiptail --title "$WT_TITLE" --inputbox "$1" "$h" 76 "${2:-}" 3>&1 1>&2 2>&3
}
# wt_menu "text" tag item tag item ...
# ONE way out in every menu: a list entry tagged "back" (or "0" for the main menu) is selectable with the arrow keys, and then
# there is no Cancel button next to it (that made two). A menu without such an entry (a plain picker) keeps its button, named
# Back. Esc always works too.
wt_menu() {
  local t="$1" i cancel=(--cancel-button Back); shift
  for ((i = 1; i <= $#; i += 2)); do
    case "${!i}" in back|0) cancel=(--nocancel) ;; esac
  done
  # 0.44.0: the box fits its text and its list (a fixed 22 x 12 hid the lines above a long list); the terminal's height
  # is the limit, 24 rows on PuTTY by default
  local n=$(( $# / 2 )) lines=0 seg rows max
  while IFS= read -r seg; do lines=$(( lines + 1 + ${#seg} / 72 )); done < <(printf '%b\n' "$t")
  max=$(tput lines 2>/dev/null); [[ $max =~ ^[0-9]+$ ]] && [ "$max" -ge 20 ] || max=24
  [ "$n" -le 14 ] || n=14
  rows=$(( lines + n + 7 )); [ "$rows" -le "$max" ] || rows=$max
  # --notags: the entries are read by their words (each with its number); the tag is only what comes back
  whiptail --title "$WT_TITLE" "${cancel[@]}" --notags --menu "$t" "$rows" 76 "$n" "$@" 3>&1 1>&2 2>&3
}
# wt_radio "text" tag item ON|OFF ...
wt_radio() { local t="$1"; shift; whiptail --title "$WT_TITLE" --radiolist "$t" 20 76 8 "$@" 3>&1 1>&2 2>&3; }
# wt_check "text" tag item ON|OFF ...
wt_check() { local t="$1"; shift; whiptail --title "$WT_TITLE" --checklist "$t" 22 76 10 "$@" 3>&1 1>&2 2>&3; }

radius_radio_items() {  # radius_radio_items CURRENT UNITS -> args for wt_radio
  local r unit; unit=$(units_distance "$2")
  for r in $RADIUS_PRESETS; do
    if [ "$r" = "$1" ]; then printf '%s\n%s\n%s\n' "$r" "$r $unit" ON; else printf '%s\n%s\n%s\n' "$r" "$r $unit" OFF; fi
  done
}

pick_radius() {  # prints the chosen preset on stdout
  local units items; units=$(cfg_get UNITS metric)
  mapfile -t items < <(radius_radio_items "$(cfg_get RADIUS 10)" "$units")
  wt_radio "Detection radius in $(case "$units" in imperial) echo miles ;; aviation) echo nautical miles ;; *) echo kilometres ;; esac).\nAircraft inside it are cycled on the wall." "${items[@]}"
}

restart_flightinfo() { unit_exists zenithboard-flightinfo && systemctl restart zenithboard-flightinfo || true; }

# ------------------------------------------------------------------ hardware: memory and Pi model
LOW_MEM_MB=1500          # boards below this (a "1 GB" Pi reports ~900 MB) are treated as low-memory
mem_total_mb() { awk '/^MemTotal:/ {printf "%d", $2/1024}' "${ZB_MEMINFO:-/proc/meminfo}"; }
mem_avail_mb() { awk '/^MemAvailable:/ {printf "%d", $2/1024}' "${ZB_MEMINFO:-/proc/meminfo}"; }
is_low_mem()   { [ "$(mem_total_mb)" -lt "$LOW_MEM_MB" ]; }
# On a machine that is not a Pi the file does not exist, and bash reports a missing input file before 2>/dev/null
# applies (seen in the fresh-install check, 0.21.1): test for it first, so a non-Pi gets an empty model, not an error.
pi_model()     { local f="${ZB_PI_MODEL_FILE:-/proc/device-tree/model}"; [ -r "$f" ] && tr -d '\0' < "$f"; }
is_old_pi()    { pi_model | grep -qE 'Raspberry Pi (Zero|[0-3]|Model)'; }   # Zero, 1, 2, 3 (any variant)

local_ip() { hostname -I 2>/dev/null | awk '{print $1}'; }
