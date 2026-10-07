# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Network settings (menu 4 Settings -> Network -> Fixed IP, and `zenithboard net ...`).
#
# A fixed address is written into the NetworkManager profile of ONE connection (the Ethernet or the Wi-Fi profile you pick).
# Nothing else about that profile is touched: it keeps its auto-connect setting and its route metric, so the cable stays
# the preferred link (metric 100 wired, 600 Wi-Fi) and Wi-Fi stays a fallback exactly as before. Going back to automatic
# (DHCP) is one menu entry, or `sudo zenithboard net dhcp`.
# Needs NetworkManager (Raspberry Pi OS Bookworm and newer). Written and unit-tested without a Pi at hand.

# ------------------------------------------------------------------ pure helpers (no network access, easy to test)
net_valid_ip() {   # four numbers 0-255
  local a x; IFS=. read -ra a <<<"$1"
  [ "${#a[@]}" -eq 4 ] || return 1
  for x in "${a[@]}"; do [[ $x =~ ^[0-9]{1,3}$ ]] && [ "$((10#$x))" -le 255 ] || return 1; done
}
net_valid_host_ip() {   # an address a machine can really have: not 0.x, 127.x, multicast or broadcast
  net_valid_ip "$1" || return 1
  local first=${1%%.*}; first=$((10#$first))
  [ "$first" -ne 0 ] && [ "$first" -ne 127 ] && [ "$first" -lt 224 ]
}
net_ip_int() { local a; IFS=. read -ra a <<<"$1"; echo $(( (10#${a[0]} << 24) | (10#${a[1]} << 16) | (10#${a[2]} << 8) | 10#${a[3]} )); }
net_int_ip() { echo "$(( ($1 >> 24) & 255 )).$(( ($1 >> 16) & 255 )).$(( ($1 >> 8) & 255 )).$(( $1 & 255 ))"; }
net_prefix_to_mask() { net_int_ip $(( (0xFFFFFFFF << (32 - $1)) & 0xFFFFFFFF )); }
net_to_prefix() {   # accepts 24, /24 or 255.255.255.0 and prints the prefix length (8-30)
  local m=${1#/} p
  if [[ $m =~ ^[0-9]{1,2}$ ]]; then [ "$((10#$m))" -ge 8 ] && [ "$((10#$m))" -le 30 ] && echo "$((10#$m))"; return; fi
  net_valid_ip "$m" || return 1
  for p in $(seq 8 30); do [ "$(net_ip_int "$m")" = "$(net_ip_int "$(net_prefix_to_mask "$p")")" ] && { echo "$p"; return 0; }; done
  return 1
}
net_same_subnet() {   # net_same_subnet IP1 IP2 PREFIX
  local m=$(( (0xFFFFFFFF << (32 - $3)) & 0xFFFFFFFF ))
  [ $(( $(net_ip_int "$1") & m )) -eq $(( $(net_ip_int "$2") & m )) ]
}
net_guess_gateway() {   # the usual router address of the subnet: first host (192.168.1.50 -> 192.168.1.1)
  local ip="$1" p="$2" m
  m=$(( (0xFFFFFFFF << (32 - p)) & 0xFFFFFFFF ))
  net_int_ip $(( ($(net_ip_int "$ip") & m) + 1 ))
}
net_default_mask() {   # a sensible mask to propose when nothing is known: /24 (what almost every home router uses)
  net_prefix_to_mask 24
}
net_dns_preset() {   # cloudflare | google | router GATEWAY | a custom list  ->  "A B"
  case "$1" in
    cloudflare) echo "1.1.1.1 1.0.0.1" ;;
    google) echo "8.8.8.8 8.8.4.4" ;;
    router) echo "${2:-}" ;;
    *) echo "$1" | tr ',' ' ' | xargs ;;
  esac
}
net_valid_dns_list() {   # one to four valid addresses
  local d n=0; for d in $1; do net_valid_ip "$d" || return 1; n=$((n + 1)); done
  [ "$n" -ge 1 ] && [ "$n" -le 4 ]
}

# ------------------------------------------------------------------ NetworkManager access
net_has_nm() { command -v nmcli >/dev/null 2>&1 && systemctl is-active --quiet NetworkManager 2>/dev/null; }
net_unesc() { sed -e 's/\\:/:/g' -e 's/\\\\/\\/g'; }

# "UUID<TAB>TYPE<TAB>NAME" of every saved Ethernet or Wi-Fi profile
net_profiles() {
  nmcli -t -f UUID,TYPE,NAME connection show 2>/dev/null | awk -F: '$2=="802-3-ethernet" || $2=="802-11-wireless" {
      name=$3; for (i=4;i<=NF;i++) name=name ":" $i; printf "%s\t%s\t%s\n", $1, ($2=="802-3-ethernet" ? "ethernet" : "wifi"), name }' | net_unesc
}
net_profile_device() { nmcli -t -f UUID,DEVICE connection show --active 2>/dev/null | awk -F: -v u="$1" '$1==u {print $2; exit}'; }   # empty when not active
net_profile_active() { [ -n "$(net_profile_device "$1")" ]; }
net_profile_method() { nmcli -g ipv4.method connection show uuid "$1" 2>/dev/null; }   # auto | manual | ...
net_profile_dev_ip() { ip -4 -o addr show dev "$1" 2>/dev/null | awk '{print $4; exit}'; }   # "192.168.1.50/24"
net_dev_gateway() { ip -4 -o route show default dev "$1" 2>/dev/null | awk '{for (i=1;i<NF;i++) if ($i=="via") {print $(i+1); exit}}'; }
net_default_profile() {   # the profile that carries the default route (what the Pi is using now)
  local dev u; dev=$(ip -o route show default 2>/dev/null | awk '{for (i=1;i<NF;i++) if ($i=="dev") {print $(i+1); exit}}' | head -1)
  [ -n "$dev" ] || return 1
  u=$(nmcli -t -f UUID,DEVICE connection show --active 2>/dev/null | awk -F: -v d="$dev" '$2==d {print $1; exit}')
  [ -n "$u" ] && echo "$u"
}
net_profile_summary() {   # "automatic 192.168.1.23/24" or "fixed 192.168.1.50/24"
  local u="$1" dev m ip
  m=$(net_profile_method "$u"); dev=$(net_profile_device "$u")
  ip=$( [ -n "$dev" ] && net_profile_dev_ip "$dev" )
  [ -n "$ip" ] || ip=$(nmcli -g ipv4.addresses connection show uuid "$u" 2>/dev/null | cut -d, -f1)
  case "$m" in manual) printf 'fixed %s' "${ip:-?}" ;; auto) printf 'automatic %s' "${ip:-(not connected)}" ;; *) printf '%s' "${m:-?}" ;; esac
}
# True when the SSH session we are in goes through this profile's device (changing the address cuts it).
net_session_uses() {
  [ -n "${SSH_CONNECTION:-}" ] || return 1
  local dev cdev; dev=$(net_profile_device "$1"); [ -n "$dev" ] || return 1
  cdev=$(ip -o route get "${SSH_CONNECTION%% *}" 2>/dev/null | awk '{for (i=1;i<NF;i++) if ($i=="dev") {print $(i+1); exit}}')
  [ "$cdev" = "$dev" ]
}

# net_apply_static UUID IP PREFIX GATEWAY "DNS1 DNS2"
# Only the IPv4 address settings change: no autoconnect, no priority, no route metric argument at all.
net_apply_static() {
  local u="$1" ip="$2" p="$3" gw="$4" dns="$5"
  nmcli connection modify uuid "$u" ipv4.method manual ipv4.addresses "$ip/$p" ipv4.gateway "$gw" \
        ipv4.dns "$dns" ipv4.ignore-auto-dns yes || return 1
  if net_profile_active "$u"; then timeout 40 nmcli connection up uuid "$u" >/dev/null 2>&1 || return 2; fi
}
net_apply_dhcp() {   # net_apply_dhcp UUID
  local u="$1"
  nmcli connection modify uuid "$u" ipv4.method auto ipv4.addresses "" ipv4.gateway "" ipv4.dns "" ipv4.ignore-auto-dns no || return 1
  if net_profile_active "$u"; then timeout 40 nmcli connection up uuid "$u" >/dev/null 2>&1 || return 2; fi
}

net_wired_note() {
  if [ -n "$(wifi_eth_dev)" ]; then
    echo "Ethernet cable detected ($(wifi_eth_dev)). A fixed address changes nothing about which link is used: the cable stays the preferred connection and Wi-Fi stays the fallback."
  else
    echo "No Ethernet cable detected. A fixed address only sets the address of the connection you pick; it does not switch between Ethernet and Wi-Fi. A cable is still the most stable way to run a feeder."
  fi
}

net_status() {
  if ! net_has_nm; then echo "Network: NetworkManager is not running (Raspberry Pi OS Bookworm or newer uses it)."; return 0; fi
  local u t n
  echo "Saved connections (Ethernet / Wi-Fi):"
  while IFS=$'\t' read -r u t n; do
    printf '  %-9s %-28s %s\n' "$t" "$n" "$(net_profile_summary "$u")"
  done < <(net_profiles)
  echo "Default route:"; ip -o route show default 2>/dev/null | awk '{m="-"; d="?"; g="?"; for(i=1;i<NF;i++){if($i=="dev")d=$(i+1); if($i=="via")g=$(i+1); if($i=="metric")m=$(i+1)} printf "  via %-15s on %-8s metric %s\n", g, d, m}'
  echo "DNS: $(resolvectl dns 2>/dev/null | sed 's/^Global: *//; s/^Link [0-9]* ([a-z0-9]*): *//' | tr '\n' ' ' | xargs)"
  net_wired_note
}

# ------------------------------------------------------------------ menu
net_pick_profile() {   # prints the chosen UUID
  local items=() u t n d; d=$(net_default_profile)
  while IFS=$'\t' read -r u t n; do
    items+=("$u" "$t: $n - $(net_profile_summary "$u")$( [ "$u" = "$d" ] && echo '  <- in use')")
  done < <(net_profiles)
  [ "${#items[@]}" -gt 0 ] || { wt_msg "No saved Ethernet or Wi-Fi connection found." 7; return 1; }
  wt_menu "Which connection gets the fixed address?\n\nThe one marked 'in use' is what the Pi is using right now." "${items[@]}"
}

net_ask_static() {   # net_ask_static UUID -> sets NET_IP NET_PREFIX NET_GW NET_DNS, returns 1 if cancelled
  local u="$1" dev cur curip curp gw mask def_gw v dnschoice
  dev=$(net_profile_device "$u")
  cur=$( [ -n "$dev" ] && net_profile_dev_ip "$dev" ); curip=${cur%/*}; curp=${cur#*/}
  [ -n "$cur" ] || { curip=""; curp=24; }
  gw=$( [ -n "$dev" ] && net_dev_gateway "$dev" )
  while true; do
    NET_IP=$(wt_input "Fixed IP address for this Pi.\n\nUse an address that is OUTSIDE your router's automatic (DHCP) range, or reserve it in the router, so no other device gets it. Typical: 192.168.1.50" "$curip") || return 1
    net_valid_host_ip "$NET_IP" && break; wt_msg "'$NET_IP' is not a valid IPv4 address (four numbers from 0 to 255)." 8
  done
  while true; do
    mask=$(wt_input "Subnet mask.\n\nPress Enter to accept the proposed one. You can type 255.255.255.0 or just 24." "$(net_prefix_to_mask "${curp:-24}")") || return 1
    NET_PREFIX=$(net_to_prefix "$mask") && break; wt_msg "'$mask' is not a usable mask (try 255.255.255.0, 255.255.0.0 or 24)." 8
  done
  def_gw=${gw:-$(net_guess_gateway "$NET_IP" "$NET_PREFIX")}
  while true; do
    NET_GW=$(wt_input "Gateway (your router's address, usually the first address of the network).\n\nPress Enter to accept the proposed one." "$def_gw") || return 1
    if ! net_valid_host_ip "$NET_GW"; then wt_msg "'$NET_GW' is not a valid address." 8; continue; fi
    net_same_subnet "$NET_IP" "$NET_GW" "$NET_PREFIX" && break
    wt_yesno "The gateway $NET_GW is not in the same network as $NET_IP/$NET_PREFIX. The Pi would lose its connection.\n\nUse it anyway?" 10 && break
  done
  dnschoice=$(wt_radio "DNS servers (they turn names like adsbexchange.com into addresses).\n\nCloudflare and Google are fast, free and independent of your provider." \
      cloudflare "Cloudflare  1.1.1.1 / 1.0.0.1  (fast, privacy-minded)" ON \
      google "Google  8.8.8.8 / 8.8.4.4" OFF \
      router "Your router ($NET_GW)  (what most boxes do by default)" OFF \
      custom "Type my own" OFF) || return 1
  if [ "$dnschoice" = custom ]; then
    while true; do
      v=$(wt_input "DNS servers, one or two addresses separated by a space (e.g. 9.9.9.9 149.112.112.112)." "1.1.1.1 1.0.0.1") || return 1
      NET_DNS=$(net_dns_preset "$v"); net_valid_dns_list "$NET_DNS" && break; wt_msg "Not a valid list of addresses." 8
    done
  else
    NET_DNS=$(net_dns_preset "$dnschoice" "$NET_GW")
  fi
}

net_static_menu() {
  local u action n cur
  net_has_nm || { wt_msg "A fixed address is set through NetworkManager (default on Raspberry Pi OS Bookworm and newer). It is not running on this Pi.\n\nThe Wi-Fi menu can install it (Settings > Network > Wi-Fi)." 12; return 0; }
  wt_msg "$(net_wired_note)\n\nThis does not change which connection is used: only the address of the one you pick." 13
  u=$(net_pick_profile) || return 0
  n=$(net_profiles | awk -F'\t' -v u="$u" '$1==u {print $3}'); cur=$(net_profile_summary "$u")
  action=$(wt_menu "$n\nNow: $cur" \
      static "Set a fixed address (IP, mask, gateway, DNS)" \
      dhcp "Back to automatic (DHCP, from the router)" \
      back "Back") || return 0
  case "$action" in
    static)
      net_ask_static "$u" || return 0
      ping -c1 -W1 "$NET_IP" >/dev/null 2>&1 && ! ip -4 -o addr show 2>/dev/null | grep -q " $NET_IP/" \
        && { wt_yesno "Another device answers at $NET_IP. Two devices with the same address break the network.\n\nUse it anyway?" 10 || return 0; }
      local risk=""; net_session_uses "$u" && risk="\n\nYou are connected to the Pi through this connection: the session will drop. Reconnect at the NEW address ($NET_IP)."
      wt_yesno "Apply?\n\n  Address : $NET_IP/$NET_PREFIX ($(net_prefix_to_mask "$NET_PREFIX"))\n  Gateway : $NET_GW\n  DNS     : $NET_DNS\n  On      : $n$risk\n\nSaved: it stays after a reboot or a crash. To undo: choose 'Back to automatic' here, or run  sudo zenithboard net dhcp" 20 || return 0
      if net_apply_static "$u" "$NET_IP" "$NET_PREFIX" "$NET_GW" "$NET_DNS"; then
        wt_msg "Fixed address saved: $NET_IP\n\nThe wall is at  http://$NET_IP:$(cfg_get PORT 8080)/" 10
      else
        wt_msg "The address was saved but the connection could not be restarted with it. Check with  zenithboard net status.  To undo:  sudo zenithboard net dhcp" 11
      fi ;;
    dhcp)
      wt_yesno "Go back to an automatic address for '$n'?\n\nThe router will give the Pi an address (it may be a different one)." 10 || return 0
      net_apply_dhcp "$u" && wt_msg "Automatic address restored. Look at 'zenithboard status' for the new address." 9 || wt_msg "Could not restore it. Check  zenithboard net status." 8 ;;
  esac
}
