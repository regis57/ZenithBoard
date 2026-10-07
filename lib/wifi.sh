# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Wi-Fi settings (menu 4 Settings -> Wi-Fi, and `zenithboard wifi ...`): on/off, country, scan with signal strength,
# connect with a password, saved networks. Built on NetworkManager (the default on Raspberry Pi OS Bookworm and newer).
#
# Persistence: every network is a NetworkManager profile file under /etc/NetworkManager/system-connections (root only,
# mode 600, available to the whole system, so it comes back after a crash, a power cut or a reboot, without any login).
# The on/off choice and the country are also saved in config.env and re-applied at boot by zenithboard-wifi.service.
# Wired Ethernet stays the preferred connection: it has the lower route metric (NetworkManager default: 100 wired,
# 600 Wi-Fi), and every profile written here sets the Wi-Fi metric to 600 explicitly.
# NOTE: written and unit-tested without a Pi in front of the author: see the README "Wi-Fi" section.

WIFI_NM_DIR="${ZB_NM_DIR:-/etc/NetworkManager/system-connections}"
WIFI_MODPROBE="${ZB_MODPROBE_DIR:-/etc/modprobe.d}/zenithboard-wifi.conf"
WIFI_PREFIX="zenithboard-wifi-"
WIFI_METRIC=600
WIFI_UNIT=zenithboard-wifi

wt_pass() { whiptail --title "$WT_TITLE" --passwordbox "$1" 10 76 3>&1 1>&2 2>&3; }

# ------------------------------------------------------------------ detection
wifi_has_nm()    { command -v nmcli >/dev/null 2>&1 && systemctl is-active --quiet NetworkManager 2>/dev/null; }
wifi_iface()     { nmcli -t -f DEVICE,TYPE device 2>/dev/null | awk -F: '$2=="wifi" {print $1; exit}'; }
wifi_radio_on()  { [ "$(nmcli radio wifi 2>/dev/null)" = enabled ]; }
wifi_eth_dev()   { nmcli -t -f DEVICE,TYPE,STATE device 2>/dev/null | awk -F: '$2=="ethernet" && $3=="connected" {print $1; exit}'; }
wifi_active_ssid() { nmcli -t -f ACTIVE,SSID device wifi list 2>/dev/null | awk -F: '$1=="yes" {sub(/^yes:/, ""); gsub(/\\:/, ":"); print; exit}'; }
wifi_active_signal() { nmcli -t -f ACTIVE,SIGNAL device wifi list 2>/dev/null | awk -F: '$1=="yes" {print $2; exit}'; }

# ------------------------------------------------------------------ validation and helpers
valid_country() { [[ "${1:-}" =~ ^[A-Z]{2}$ ]]; }
valid_ssid()    { local n; n=$(printf '%s' "${1:-}" | wc -c); [ "$n" -ge 1 ] && [ "$n" -le 32 ] && ! printf '%s' "$1" | grep -q '[[:cntrl:]]'; }
# WPA passphrase: 8-63 printable characters, or exactly 64 hexadecimal digits
valid_wifi_psk() {
  local p="${1:-}" n
  n=$(printf '%s' "$p" | wc -c)
  if [ "$n" -eq 64 ]; then [[ "$p" =~ ^[0-9A-Fa-f]{64}$ ]]; return; fi
  [ "$n" -ge 8 ] && [ "$n" -le 63 ] && ! printf '%s' "$p" | grep -q '[[:cntrl:]]'
}
wifi_bars() {   # wifi_bars SIGNAL(0-100)
  local s="${1:-0}"
  if   [ "$s" -ge 75 ]; then printf '[####]'
  elif [ "$s" -ge 50 ]; then printf '[### ]'
  elif [ "$s" -ge 25 ]; then printf '[##  ]'
  else printf '[#   ]'; fi
}
# WPA3-only networks need key-mgmt=sae; everything else (WPA2, WPA2/WPA3 mixed) uses wpa-psk
wifi_keymgmt() {   # wifi_keymgmt SECURITY-STRING
  case "$1" in *WPA3*) case "$1" in *WPA2*|*WPA1*) echo wpa-psk ;; *) echo sae ;; esac ;; *) echo wpa-psk ;; esac
}

# nmcli -t escapes ':' and '\' with a backslash. Reads that output on stdin, writes "SSID<TAB>SIGNAL<TAB>SECURITY",
# one line per network name (the strongest access point), strongest first. Hidden (empty) names are skipped.
wifi_parse_scan() {
  awk '
    { n = 0; cur = ""; esc = 0
      for (i = 1; i <= length($0); i++) {
        c = substr($0, i, 1)
        if (esc) { cur = cur c; esc = 0 }
        else if (c == "\\") esc = 1
        else if (c == ":") { f[++n] = cur; cur = "" }
        else cur = cur c
      }
      f[++n] = cur
      if (f[1] == "") next
      sig = f[2] + 0
      if (!(f[1] in best) || sig > best[f[1]]) { best[f[1]] = sig; sec[f[1]] = f[3] }
    }
    END { for (s in best) printf "%s\t%d\t%s\n", s, best[s], (sec[s] == "" ? "--" : sec[s]) }
  ' | sort -t "$(printf '\t')" -k2,2nr -k1,1
}
wifi_scan() { nmcli -t -f SSID,SIGNAL,SECURITY device wifi list --rescan yes 2>/dev/null | wifi_parse_scan; }

# ------------------------------------------------------------------ country and on/off (persistent)
wifi_country_now() {
  local c; c=$(cfg_get WIFI_COUNTRY)
  if [ -z "$c" ] && command -v iw >/dev/null 2>&1; then c=$(iw reg get 2>/dev/null | awk '/^country/ {sub(":", "", $2); print $2; exit}'); fi
  case "$c" in 00|"") echo "" ;; *) echo "$c" ;; esac
}

wifi_set_country() {   # wifi_set_country XX
  local cc="${1:-}"
  valid_country "$cc" || { err "The country is a 2-letter code in capitals, for example FR, BE, CH, DE, GB, US."; return 1; }
  mkdir -p "$(dirname "$WIFI_MODPROBE")"
  printf '# Written by ZenithBoard (zenithboard wifi country). Wi-Fi regulatory domain, kept across reboots.\noptions cfg80211 ieee80211_regdom=%s\n' "$cc" > "$WIFI_MODPROBE"
  cfg_set WIFI_COUNTRY "$cc"
  if [ "${ZB_SKIP_SERVICES:-}" != 1 ]; then
    command -v iw >/dev/null 2>&1 && iw reg set "$cc" 2>/dev/null || true
    command -v raspi-config >/dev/null 2>&1 && raspi-config nonint do_wifi_country "$cc" >/dev/null 2>&1 || true
    command -v rfkill >/dev/null 2>&1 && rfkill unblock wifi 2>/dev/null || true
  fi
}

wifi_set_radio() {   # wifi_set_radio on|off
  case "${1:-}" in
    on)  cfg_set WIFI 1 ;;
    off) cfg_set WIFI 0 ;;
    *) return 1 ;;
  esac
  [ "${ZB_SKIP_SERVICES:-}" = 1 ] && return 0
  wifi_install_unit
  if [ "$1" = on ]; then command -v rfkill >/dev/null 2>&1 && rfkill unblock wifi 2>/dev/null || true; fi
  nmcli radio wifi "$1" >/dev/null 2>&1 || return 1
}

# Re-apply what the user chose (run at every boot by zenithboard-wifi.service). Does nothing at all until the user has
# used the Wi-Fi settings once, so a Pi that was set up some other way is never touched.
wifi_apply() {
  local cc w; cc=$(cfg_get WIFI_COUNTRY); w=$(cfg_get WIFI)
  if [ -n "$cc" ] && command -v iw >/dev/null 2>&1; then iw reg set "$cc" 2>/dev/null || true; fi
  case "$w" in
    1) command -v rfkill >/dev/null 2>&1 && rfkill unblock wifi 2>/dev/null || true; nmcli radio wifi on >/dev/null 2>&1 || true ;;
    0) nmcli radio wifi off >/dev/null 2>&1 || true ;;
  esac
}

wifi_install_unit() {
  [ -f "$ZB_HOME/systemd/$WIFI_UNIT.service" ] || return 0
  install -m 644 "$ZB_HOME/systemd/$WIFI_UNIT.service" /etc/systemd/system/
  systemctl daemon-reload; systemctl enable "$WIFI_UNIT" >/dev/null 2>&1 || true
}
wifi_remove_unit() {   # the saved networks and the radio state are left alone on purpose
  systemctl disable "$WIFI_UNIT" >/dev/null 2>&1 || true
  rm -f "/etc/systemd/system/$WIFI_UNIT.service"; systemctl daemon-reload 2>/dev/null || true
}

# ------------------------------------------------------------------ saved networks (NetworkManager profile files)
wifi_kf_escape() { printf '%s' "$1" | sed -e 's/\\/\\\\/g'; }
wifi_profile_id() {   # a short, file-safe, collision-free name for an SSID
  local safe; safe=$(printf '%s' "$1" | tr -c 'A-Za-z0-9._-' '_' | cut -c1-24)
  printf '%s%s-%s' "$WIFI_PREFIX" "$safe" "$(printf '%s' "$1" | cksum | cut -d' ' -f1)"
}

# wifi_write_profile SSID PSK [hidden 0|1] [keymgmt wpa-psk|sae]   (empty PSK = open network)
# The password goes straight into a root-only file: it never appears on a command line.
wifi_write_profile() {
  local ssid="$1" psk="${2:-}" hidden="${3:-0}" km="${4:-wpa-psk}" id f tmp uuid
  valid_ssid "$ssid" || { err "A network name (SSID) is 1 to 32 characters."; return 1; }
  [ -z "$psk" ] || valid_wifi_psk "$psk" || { err "A Wi-Fi password is 8 to 63 characters (or 64 hexadecimal digits)."; return 1; }
  id=$(wifi_profile_id "$ssid"); f="$WIFI_NM_DIR/$id.nmconnection"
  mkdir -p "$WIFI_NM_DIR"
  uuid=$(cat /proc/sys/kernel/random/uuid 2>/dev/null || cksum <<<"$ssid$$" | cut -d' ' -f1)
  [ ! -f "$f" ] || uuid=$(sed -n 's/^uuid=//p' "$f" | head -1)      # same network again = same profile, updated in place
  tmp=$(umask 077; mktemp "$WIFI_NM_DIR/.zb-wifi.XXXXXX") || return 1
  {
    printf '[connection]\nid=%s\nuuid=%s\ntype=wifi\nautoconnect=true\n\n' "$id" "$uuid"
    printf '[wifi]\nmode=infrastructure\nssid=%s\n' "$(wifi_kf_escape "$ssid")"
    [ "$hidden" != 1 ] || printf 'hidden=true\n'
    if [ -n "$psk" ]; then printf '\n[wifi-security]\nkey-mgmt=%s\npsk=%s\n' "$km" "$(wifi_kf_escape "$psk")"; fi
    printf '\n[ipv4]\nmethod=auto\nroute-metric=%s\n\n[ipv6]\nmethod=auto\nroute-metric=%s\n' "$WIFI_METRIC" "$WIFI_METRIC"
  } > "$tmp"
  chmod 600 "$tmp"; mv -f "$tmp" "$f"
  [ "${ZB_SKIP_SERVICES:-}" = 1 ] || nmcli connection reload >/dev/null 2>&1 || true
  printf '%s' "$id"
}

wifi_saved() {   # "UUID<TAB>NAME" of every saved Wi-Fi profile on this Pi (also ones made by Imager / raspi-config)
  nmcli -t -f UUID,TYPE,NAME connection show 2>/dev/null | awk -F: '$2=="802-11-wireless" { n=$0; sub(/^[^:]*:[^:]*:/, "", n); gsub(/\\:/, ":", n); printf "%s\t%s\n", $1, n }'
}
wifi_profile_ssid()    { nmcli -g 802-11-wireless.ssid connection show uuid "$1" 2>/dev/null; }
wifi_profile_hidden()  { [ "$(nmcli -g 802-11-wireless.hidden connection show uuid "$1" 2>/dev/null)" = yes ] && echo 1 || echo 0; }
wifi_profile_keymgmt() { nmcli -g 802-11-wireless-security.key-mgmt connection show uuid "$1" 2>/dev/null; }
wifi_forget() { nmcli connection delete uuid "$1" >/dev/null 2>&1; }   # wifi_forget UUID

# Save a network and try to join it. Returns 0 even if the network is just out of range (it is saved and will be used).
wifi_connect() {   # wifi_connect SSID PSK [hidden] [keymgmt]
  local id; id=$(wifi_write_profile "$@") || return 1
  if [ "${ZB_SKIP_SERVICES:-}" != 1 ]; then
    wifi_radio_on || wifi_set_radio on || true
    if nmcli connection up id "$id" >/dev/null 2>&1; then echo "Connected to \"$1\"."
    else warn "\"$1\" is saved and will be joined automatically when it is in range, but joining it now failed (wrong password, or out of range?)."; fi
  fi
}

# ------------------------------------------------------------------ status, wired priority, SSH safety
wifi_default_route_dev() { ip -o route show default 2>/dev/null | awk '{for (i=1;i<NF;i++) if ($i=="dev") {print $(i+1); exit}}'; }
# True when the SSH session we are in goes through Wi-Fi (changing Wi-Fi would cut it).
wifi_session_on_wifi() {
  [ -n "${SSH_CONNECTION:-}" ] || return 1
  local ip dev wl; ip="${SSH_CONNECTION%% *}"; wl=$(wifi_iface); [ -n "$wl" ] || return 1
  dev=$(ip -o route get "$ip" 2>/dev/null | awk '{for (i=1;i<NF;i++) if ($i=="dev") {print $(i+1); exit}}')
  [ "$dev" = "$wl" ]
}
wifi_wired_note() {
  if [ -n "$(wifi_eth_dev)" ]; then
    echo "Ethernet cable detected ($(wifi_eth_dev)). It stays the preferred connection: it carries all the traffic while plugged, and Wi-Fi only takes over if the cable is unplugged. Keep the cable in while you change Wi-Fi settings."
  else
    echo "No Ethernet cable detected. A cable is the most stable way to run a feeder; Wi-Fi works but can drop. If you are connected to the Pi through Wi-Fi right now, changing it can cut your session."
  fi
}
wifi_summary() {   # one short line for the Settings menu
  wifi_has_nm || { printf 'not managed by NetworkManager'; return; }
  [ -n "$(wifi_iface)" ] || { printf 'no adapter'; return; }
  if wifi_radio_on; then printf 'ON, %s' "$(wifi_active_ssid | sed 's/^$/not connected/')"; else printf 'OFF'; fi
}
wifi_status() {
  if ! wifi_has_nm; then echo "Wi-Fi: NetworkManager is not running (Raspberry Pi OS Bookworm or newer uses it)."; return 0; fi
  local wl ssid sig
  wl=$(wifi_iface)
  [ -n "$wl" ] || { echo "Wi-Fi: no Wi-Fi adapter found on this Pi."; return 0; }
  echo "Wi-Fi adapter:  $wl   radio: $(wifi_radio_on && echo ON || echo OFF)   country: $(wifi_country_now | sed 's/^$/not set/')"
  ssid=$(wifi_active_ssid); sig=$(wifi_active_signal)
  if [ -n "$ssid" ]; then echo "Connected to:   $ssid   signal $(wifi_bars "${sig:-0}") ${sig:-?}%   address: $(ip -4 -o addr show dev "$wl" 2>/dev/null | awk '{print $4; exit}')"
  else echo "Connected to:   (no Wi-Fi network)"; fi
  echo "Ethernet:       $( [ -n "$(wifi_eth_dev)" ] && echo "connected ($(wifi_eth_dev))" || echo "no cable")"
  echo "Routes (lowest metric wins):"; ip -o route show default 2>/dev/null | awk '{m="?"; d="?"; for(i=1;i<NF;i++){if($i=="dev")d=$(i+1); if($i=="metric")m=$(i+1)} printf "  %-8s metric %s\n", d, m}'
  echo "$(wifi_wired_note)"
}

# ------------------------------------------------------------------ menus
WIFI_COUNTRIES=(FR France BE Belgium CH Switzerland LU Luxembourg DE Germany AT Austria NL Netherlands IT Italy ES Spain PT Portugal GB "United Kingdom" IE Ireland DK Denmark SE Sweden NO Norway FI Finland PL Poland CZ Czechia GR Greece US "United States" CA Canada MX Mexico BR Brazil AU Australia NZ "New Zealand" JP Japan KR "South Korea" IN India ZA "South Africa" AE "United Arab Emirates")

wifi_pick_country() {   # prints the chosen 2-letter code
  local cur c; cur=$(wifi_country_now)
  c=$(wt_menu "Wi-Fi country (regulatory domain).\n\nIt decides which channels and power the radio may use, and is required by law. Choose the country where the Pi is. Current: ${cur:-not set}" "${WIFI_COUNTRIES[@]}" other "Another country: type its 2-letter code") || return 1
  if [ "$c" = other ]; then
    c=$(wt_input "2-letter country code in capitals (for example FR, BE, CH, DE, GB, US)." "$cur") || return 1
    valid_country "$c" || { wt_msg "Not a valid code. It must be exactly two capital letters, like FR." 8; return 1; }
  fi
  printf '%s' "$c"
}

wifi_need_country() {   # make sure a country is set before the radio is used
  [ -z "$(wifi_country_now)" ] || return 0
  wt_msg "Choose the Wi-Fi country first: the radio stays limited (or blocked) until it is set." 8
  local c; c=$(wifi_pick_country) || return 1
  wifi_set_country "$c"
}

wifi_require_on() { wifi_radio_on || { wt_msg "Wi-Fi is OFF. Turn it on first (first item of this menu)." 8; return 1; }; }

wifi_confirm_session_risk() {   # $1 = what is about to happen
  wifi_session_on_wifi || return 0
  wt_yesno "You are probably connected to this Pi through Wi-Fi.\n\n$1 may cut your connection. An Ethernet cable keeps you safe.\n\nContinue?" 12
}

wifi_ask_password() {   # wifi_ask_password "SSID" -> prints the password ("" = open network)
  local p
  while true; do
    p=$(wt_pass "Password for \"$1\"\n(8 to 63 characters; leave empty only for an open network).") || return 1
    [ -z "$p" ] && { wt_yesno "No password: this connects to \"$1\" as an OPEN network. Is it really open?" 8 && break; continue; }
    valid_wifi_psk "$p" && break
    wt_msg "A Wi-Fi password is 8 to 63 characters (or 64 hexadecimal digits)." 8
  done
  printf '%s' "$p"
}

wifi_connect_menu() {   # scan, pick, password
  local lines i=0 items=() ssid sig sec c p km
  wifi_require_on || return 0
  wifi_need_country || return 0
  wifi_confirm_session_risk "Joining another network" || return 0
  clear; echo "Scanning for Wi-Fi networks (a few seconds)..."
  mapfile -t lines < <(wifi_scan)
  [ "${#lines[@]}" -gt 0 ] || { wt_msg "No network found. Check the country, the antenna and that you are in range, or use \"hidden network\"." 10; return 0; }
  for l in "${lines[@]}"; do
    IFS=$'\t' read -r ssid sig sec <<<"$l"
    i=$((i + 1)); items+=("$i" "$(printf '%-6s %3s%%  %-26s %s' "$(wifi_bars "$sig")" "$sig" "$(printf '%s' "$ssid" | cut -c1-26)" "$sec")")
  done
  c=$(wt_menu "Networks in range, strongest first.\n\nOnly networks with a password (WPA2/WPA3 personal) and open networks are supported here, not company (802.1X) ones." "${items[@]}") || return 0
  IFS=$'\t' read -r ssid sig sec <<<"${lines[$((c - 1))]}"
  km=$(wifi_keymgmt "$sec")
  case "$sec" in *802.1X*) wt_msg "\"$ssid\" is a company (802.1X) network: not supported by this menu." 8; return 0 ;; esac
  p=""
  [ "$sec" = -- ] || p=$(wifi_ask_password "$ssid") || return 0
  clear; wifi_connect "$ssid" "$p" 0 "$km"; echo; read -rp "Press Enter to continue..." _
}

wifi_hidden_menu() {
  local ssid p
  wifi_require_on || return 0
  wifi_need_country || return 0
  wifi_confirm_session_risk "Joining another network" || return 0
  ssid=$(wt_input "Name (SSID) of the hidden network." "") || return 0
  valid_ssid "$ssid" || { wt_msg "A network name is 1 to 32 characters." 8; return 0; }
  p=$(wifi_ask_password "$ssid") || return 0
  clear; wifi_connect "$ssid" "$p" 1 wpa-psk; echo; read -rp "Press Enter to continue..." _
}

wifi_saved_menu() {
  local lines=() i=0 items=() uuid name c a ssid p
  mapfile -t lines < <(wifi_saved)
  [ "${#lines[@]}" -gt 0 ] || { wt_msg "No saved Wi-Fi network yet. Use \"Find and connect\"." 8; return 0; }
  for l in "${lines[@]}"; do IFS=$'\t' read -r uuid name <<<"$l"; i=$((i + 1)); items+=("$i" "$name"); done
  c=$(wt_menu "Saved networks (kept after a reboot)." "${items[@]}") || return 0
  IFS=$'\t' read -r uuid name <<<"${lines[$((c - 1))]}"
  a=$(wt_menu "$name" connect "Connect now" password "Change the password" auto "Auto-connect on/off" forget "Forget this network") || return 0
  case "$a" in
    connect) wifi_require_on || return 0; wifi_confirm_session_risk "Switching network" || return 0; clear; nmcli connection up uuid "$uuid" && echo "Connected." || warn "Could not join \"$name\"."; read -rp "Press Enter to continue..." _ ;;
    password)
      ssid=$(wifi_profile_ssid "$uuid"); [ -n "$ssid" ] || { wt_msg "Cannot read this network's name." 8; return 0; }
      wifi_confirm_session_risk "Changing the password" || return 0
      p=$(wifi_ask_password "$ssid") || return 0
      local km hid; km=$(wifi_profile_keymgmt "$uuid"); hid=$(wifi_profile_hidden "$uuid"); [ -n "$km" ] || km=wpa-psk
      wifi_forget "$uuid"; clear; wifi_connect "$ssid" "$p" "$hid" "$km"; read -rp "Press Enter to continue..." _ ;;
    auto)
      if wt_yesno "Join \"$name\" automatically whenever it is in range (and at every boot)?" 8; then nmcli connection modify uuid "$uuid" connection.autoconnect yes; else nmcli connection modify uuid "$uuid" connection.autoconnect no; fi ;;
    forget)
      wt_yesno "Forget \"$name\"? Its password is deleted from this Pi." 8 || return 0
      wifi_confirm_session_risk "Forgetting this network" || return 0
      wifi_forget "$uuid" && wt_msg "Forgotten." 6 ;;
  esac
}

wifi_toggle() {
  if wifi_radio_on; then
    wt_yesno "Turn Wi-Fi OFF?\n\nThe choice is kept after a reboot. Ethernet is not affected." 10 || return 0
    wifi_confirm_session_risk "Turning Wi-Fi off" || return 0
    wifi_set_radio off && wt_msg "Wi-Fi is OFF (and will stay off after a reboot)." 8
  else
    wifi_need_country || return 0
    wifi_set_radio on && wt_msg "Wi-Fi is ON (and will stay on after a reboot). Saved networks are joined automatically." 9
  fi
}

wifi_menu() {
  local c
  if ! wifi_has_nm; then wt_msg "The Wi-Fi menu needs NetworkManager, the default on Raspberry Pi OS Bookworm and newer. It is not running here, so nothing is changed. Set Wi-Fi with raspi-config instead." 11; return 0; fi
  [ -n "$(wifi_iface)" ] || { wt_msg "No Wi-Fi adapter found on this Pi." 7; return 0; }
  wt_msg "$(wifi_wired_note)" 13
  while true; do
    c=$(wt_menu "Wi-Fi\n\nRadio: $(wifi_radio_on && echo ON || echo OFF)    Country: $(wifi_country_now | sed 's/^$/not set/')\nConnected to: $(wifi_active_ssid | sed 's/^$/(no Wi-Fi network)/')    Ethernet: $( [ -n "$(wifi_eth_dev)" ] && echo cable || echo none )\nEverything here is saved and comes back after a crash or a reboot." \
      toggle "Wi-Fi: turn $(wifi_radio_on && echo OFF || echo ON)" \
      country "Country (regulatory domain)" \
      connect "Find and connect to a network (with signal strength)" \
      hidden "Connect to a hidden network" \
      saved "Saved networks: connect, change password, forget" \
      status "Status and wired / Wi-Fi priority" \
      back "Back") || return 0
    case "$c" in
      toggle) wifi_toggle ;;
      country) local cc; cc=$(wifi_pick_country) && wifi_set_country "$cc" && wt_msg "Country saved: $cc." 7 ;;
      connect) wifi_connect_menu ;;
      hidden) wifi_hidden_menu ;;
      saved) wifi_require_on && wifi_saved_menu ;;
      status) clear; wifi_status; echo; read -rp "Press Enter to continue..." _ ;;
      *) return 0 ;;
    esac
  done
}
