# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Domain name for your wall (menu 4 Settings -> Network -> Domain name, and `zenithboard ddns ...`).
#
# Most home internet connections change their public address from time to time. A dynamic-DNS service gives you a free
# name (for example myplanes.duckdns.org) and this Pi tells the service its current address every 5 minutes, so the name
# always points at your home. Three free services are supported: DuckDNS, No-IP and FreeDNS (afraid.org).
#
# The name alone does not open anything: your router must also forward a port to the Pi (see the README, "A name for your
# wall"). Nothing here opens a port, and nothing is sent anywhere until you switch it on.
#
# Secrets (the DuckDNS / FreeDNS token, the No-IP DDNS key) live only in $ZB_ETC/ddns.curl, a curl config file that is
# root-only (mode 600). They never appear on a command line, in config.env, or in the logs.

DDNS_UNIT=zenithboard-ddns
DDNS_CURL="${ZB_ETC:-/etc/zenithboard}/ddns.curl"
DDNS_STATE="${ZB_RUN_DIR:-/run}/zenithboard-ddns.status"   # in memory (tmpfs): the SD card is not written every 5 minutes

# ------------------------------------------------------------------ pure helpers
ddns_provider_name() {
  case "$1" in duckdns) echo "DuckDNS" ;; noip) echo "No-IP" ;; freedns) echo "FreeDNS (afraid.org)" ;; *) echo "off" ;; esac
}
ddns_valid_host() { [[ $1 =~ ^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$ ]]; }
ddns_valid_token() { [[ $1 =~ ^[A-Za-z0-9_-]{8,80}$ ]]; }
ddns_token_from() {   # accepts the bare token or the whole "direct URL" FreeDNS shows, and prints the token
  local t="${1%/}"; t="${t##*\?}"; t="${t##*/}"; printf '%s' "$t"
}
ddns_curl_quote() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }

# ddns_curl_config PROVIDER HOST USER SECRET  -> a curl config on stdout (url, and user for No-IP)
ddns_curl_config() {
  local p="$1" h="$2" u="$3" s="$4" sub
  case "$p" in duckdns|noip|freedns) ;; *) return 1 ;; esac
  printf 'silent\nshow-error\nmax-time = 25\nuser-agent = "ZenithBoard/%s"\n' "${ZB_VERSION:-0}"
  case "$p" in
    duckdns) sub="${h%.duckdns.org}"; printf 'url = "https://www.duckdns.org/update?domains=%s&token=%s&ip="\n' "$sub" "$s" ;;
    noip)    printf 'url = "https://dynupdate.no-ip.com/nic/update?hostname=%s"\nuser = "%s:%s"\n' "$h" "$(ddns_curl_quote "$u")" "$(ddns_curl_quote "$s")" ;;
    freedns) printf 'url = "https://sync.afraid.org/u/%s/"\n' "$s" ;;
    *) return 1 ;;
  esac
}
# ddns_interpret PROVIDER RESPONSE -> ok | nochg | fail   (and a short reason on stderr-free stdout line 2)
ddns_interpret() {
  local p="$1" r="$2"
  case "$p" in
    duckdns) case "$r" in OK*) echo ok ;; *) echo fail ;; esac ;;
    noip)    case "$r" in good*) echo ok ;; nochg*) echo nochg ;; *) echo fail ;; esac ;;
    freedns) case "$r" in *Updated*) echo ok ;; *"has not changed"*) echo nochg ;; *) echo fail ;; esac ;;
    *) echo fail ;;
  esac
}
ddns_reason() {   # a human sentence for a failed answer
  case "$1" in
    *badauth*) echo "the user name or key was refused" ;;
    *nohost*)  echo "that host name does not exist on this account" ;;
    *abuse*|*blocked*) echo "the service blocked this account (too many updates)" ;;
    KO*)       echo "DuckDNS refused it: check the sub-domain and the token" ;;
    *ERROR*)   echo "FreeDNS refused it: check the token" ;;
    "")        echo "no answer (no internet?)" ;;
    *)         echo "unexpected answer" ;;
  esac
}

# ------------------------------------------------------------------ run
# ddns_update [RETRIES]   one request; with RETRIES it asks again a few seconds later when the answer is a refusal or no answer
# (used right after the setup, when the network or the service may still be settling). The service's own short answer
# (OK, KO, good, badauth...) is kept in the status line: it never contains the token.
ddns_update() {
  local p r res tries="${1:-0}" n=0
  p=$(cfg_get DDNS_PROVIDER none)
  [ "$p" != none ] && [ -f "$DDNS_CURL" ] || return 0
  while :; do
    r=$(curl -K "$DDNS_CURL" 2>&1 | head -c 200 | tr -d '\r' | head -1)
    res=$(ddns_interpret "$p" "$r")
    [ "$res" != fail ] && break
    [ "$n" -lt "$tries" ] || break
    n=$((n + 1)); sleep "${ZB_DDNS_RETRY_SLEEP:-5}"
  done
  mkdir -p "$(dirname "$DDNS_STATE")" 2>/dev/null
  if [ "$res" = fail ]; then printf '%s FAILED: %s (answer: %s)\n' "$(date '+%F %T')" "$(ddns_reason "$r")" "${r:-none}" > "$DDNS_STATE" 2>/dev/null
  else printf '%s ok (%s)\n' "$(date '+%F %T')" "$res" > "$DDNS_STATE" 2>/dev/null; fi
  [ "$res" != fail ]
}
ddns_install_units() {
  [ -f "$ZB_HOME/systemd/$DDNS_UNIT.service" ] || return 0
  install -m 644 "$ZB_HOME/systemd/$DDNS_UNIT.service" "$ZB_HOME/systemd/$DDNS_UNIT.timer" /etc/systemd/system/
  systemctl daemon-reload; systemctl enable --now "$DDNS_UNIT.timer" >/dev/null 2>&1 || true
}
ddns_remove_units() {
  systemctl disable --now "$DDNS_UNIT.timer" >/dev/null 2>&1 || true
  rm -f "/etc/systemd/system/$DDNS_UNIT.service" "/etc/systemd/system/$DDNS_UNIT.timer"; systemctl daemon-reload 2>/dev/null || true
}
# ddns_set PROVIDER HOST USER SECRET : validates, stores, starts the 5-minute timer, does a first update (prints the result line)
ddns_set() {
  local p="$1" h="$2" u="$3" s="$4" old
  case "$p" in duckdns|noip|freedns) ;; *) echo "Unknown provider: $p (duckdns, noip, freedns)"; return 1 ;; esac
  ddns_valid_host "$h" || { echo "That is not a valid host name."; return 1; }
  if [ "$p" = noip ]; then
    [ -n "$u" ] && [ -n "$s" ] && [[ $u$s != *$'\n'* ]] || { echo "No-IP needs the DDNS key's user name and password."; return 1; }
  else
    s=$(ddns_token_from "$s"); ddns_valid_token "$s" || { echo "That does not look like a token (letters, digits, - and _)."; return 1; }
  fi
  old=$(umask); umask 077
  mkdir -p "$(dirname "$DDNS_CURL")"; ddns_curl_config "$p" "$h" "$u" "$s" > "$DDNS_CURL.new" && mv -f "$DDNS_CURL.new" "$DDNS_CURL"
  umask "$old"; chmod 600 "$DDNS_CURL"
  cfg_set DDNS_PROVIDER "$p"; cfg_set DDNS_HOST "$h"
  ddns_install_units
  if ddns_update 2; then echo "OK: $(cat "$DDNS_STATE" 2>/dev/null)"; else echo "Saved, but the first update failed (asked 3 times): $(cat "$DDNS_STATE" 2>/dev/null)  The timer asks again every 5 minutes. Check later with: zenithboard ddns status"; return 2; fi
}
ddns_off() {
  cfg_set DDNS_PROVIDER none; rm -f "$DDNS_CURL" "$DDNS_STATE"; ddns_remove_units
}
ddns_summary() {   # one short line for the menus
  local p; p=$(cfg_get DDNS_PROVIDER none)
  if [ "$p" = none ]; then printf 'off'; else printf '%s, %s' "$(ddns_provider_name "$p")" "$(cfg_get DDNS_HOST)"; fi
}
ddns_map_path() {   # the map page on port 80 (tar1090, or the ADSB Exchange interface)
  local d
  for d in /usr/local/share/tar1090/html /usr/share/tar1090/html; do [ -d "$d" ] && { echo "/tar1090/"; return; }; done
  for d in /usr/local/share/adsbexchange/html /usr/share/adsbexchange/html; do [ -d "$d" ] && { echo "/adsbx/"; return; }; done
  echo "/tar1090/"
}
ddns_status() {
  local p h pub res; p=$(cfg_get DDNS_PROVIDER none); h=$(cfg_get DDNS_HOST)
  if [ "$p" = none ]; then echo "Domain name: off"; return 0; fi
  echo "Domain name: $h  ($(ddns_provider_name "$p"))"
  echo "Last update: $(cat "$DDNS_STATE" 2>/dev/null || echo 'none yet')"
  echo "Timer:       $(systemctl is-active "$DDNS_UNIT.timer" 2>/dev/null || echo inactive)  (every 5 minutes)"
  pub=$(curl -fsS -m 8 https://api.ipify.org 2>/dev/null)
  res=$(getent hosts "${h%.}" 2>/dev/null | awk '{print $1; exit}')
  echo "Your public address (as the internet sees it): ${pub:-unknown}"
  echo "The name points to:                            ${res:-does not resolve yet}"
  if [ -n "$pub" ] && [ -n "$res" ] && [ "$pub" = "$res" ]; then echo "RESULT: the name points to your address, so it works (an older FAILED line above is only the last answer the service gave; the next refresh replaces it)."
  elif [ -n "$pub" ] && [ -n "$res" ]; then echo "They differ: wait a few minutes, or run  sudo zenithboard ddns update"; fi
  case "$pub" in 100.6[4-9].*|100.[7-9]*.*|100.1[01]*.*|100.12[0-7].*) echo "WARNING: $pub is a shared (CGNAT) address: your provider does not give you a public one, so a port cannot be opened to your Pi. Ask the provider for a public address, or use a VPN such as Tailscale." ;; esac
}
ddns_links() {   # the addresses once the router forwards the ports
  local h port; h=$(cfg_get DDNS_HOST); port=$(cfg_get PORT 8080)
  echo "ZenithBoard wall : http://$h:$port/"
  echo "Receiver map     : http://$h$(ddns_map_path)   (port 80)"
}

# ------------------------------------------------------------------ menu
wt_scroll() { whiptail --title "$WT_TITLE" --scrolltext --msgbox "$1" 22 76; }   # long help text: scrolls on small screens
ddns_guide() {
  wt_scroll "WHICH SERVICE?  All three are free.\n\n DuckDNS (duckdns.org)  - the simplest. Sign in with Google, GitHub... pick a name such as myplanes -> myplanes.duckdns.org. It gives you a token. Never expires.\n\n No-IP (noip.com)  - the best known. Create an account, then a free hostname, then (Dynamic DNS > DDNS Keys) a DDNS key: a user name + password just for updates. The free plan asks you to confirm the hostname regularly (about once a month, by e-mail or button) or the name is released.\n\n FreeDNS (freedns.afraid.org)  - many domains to choose from. Create an account, add a Subdomain (type A), then open Dynamic DNS: copy the 'Direct URL' (or just its last part, the token).\n\nIf unsure: DuckDNS."
}
ddns_how_to_reach() {
  wt_scroll "A NAME ALONE OPENS NOTHING.\n\nTo reach your Pi from outside, three things:\n 1. A name that follows your home address (this menu).\n 2. A FIXED address for the Pi (Network > Fixed IP) so the router always sends traffic to the same machine.\n 3. In your router (often called 'port forwarding' or 'NAT'): forward a port to the Pi.\n      the wall: port $(cfg_get PORT 8080) -> the Pi, port $(cfg_get PORT 8080)\n      the receiver map (tar1090, optional): port 80 -> the Pi, port 80\n\nPRIVACY: these pages have no password and no encryption. The map shows where your antenna is. Forward only what you want public, or keep it private with a VPN (Tailscale / WireGuard) instead - no port to open.\n\nSome providers share one public address between many homes (CGNAT): no port can be opened then. 'Status' tells you."
}
ddns_setup() {
  local p h u="" s
  p=$(wt_radio "Which service did you create your free name with?\n\n(Press OK on 'Help me choose' to read how each one works.)" \
      duckdns "DuckDNS - simplest, never expires" ON noip "No-IP - best known, free name needs a monthly confirmation" OFF freedns "FreeDNS - afraid.org, many domains" OFF) || return 0
  h=$(wt_input "Your full name, e.g.\n  myplanes.duckdns.org\n  myplanes.ddns.net\n  myplanes.mooo.com" "$(cfg_get DDNS_HOST)") || return 0
  ddns_valid_host "$h" || { wt_msg "That is not a valid host name." 7; return 0; }
  case "$p" in
    noip) u=$(wt_input "No-IP DDNS key: USER NAME (Dynamic DNS > DDNS Keys on noip.com). Not your account login." "") || return 0
          s=$(wt_pass "No-IP DDNS key: PASSWORD (typed hidden, stored root-only).") || return 0 ;;
    duckdns) s=$(wt_pass "DuckDNS TOKEN (shown at the top of duckdns.org once signed in). Typed hidden, stored root-only.") || return 0 ;;
    freedns) s=$(wt_pass "FreeDNS token, or the whole 'Direct URL' from the Dynamic DNS page. Typed hidden, stored root-only.") || return 0 ;;
  esac
  local out rc; out=$(ddns_set "$p" "$h" "$u" "$s"); rc=$?
  if [ "$rc" -eq 0 ]; then wt_msg "$out\n\nThe Pi now refreshes it every 5 minutes, also after a reboot.\n\n$(ddns_links)\n\nNext: a fixed address for the Pi, then port forwarding in your router (read 'How to reach it')." 18
  else wt_msg "$out" 10; fi
}
ddns_menu() {
  local c
  while true; do
    c=$(wt_menu "Domain name for your wall\n\nNow: $(ddns_summary)\n\nGives the wall (and the receiver map) a name that follows your home address, so you can open them away from home." \
      guide "Help me choose: DuckDNS, No-IP or FreeDNS" \
      setup "Set up or change the name" \
      reach "How to reach it from outside (router, privacy)" \
      status "Status: last update, public address, links" \
      update "Update now" \
      off "Turn the domain name off (deletes the saved key)" \
      back "Return to the previous menu") || return 0
    case "$c" in
      guide) ddns_guide ;;
      setup) ddns_setup ;;
      reach) ddns_how_to_reach ;;
      status) clear; ddns_status; [ "$(cfg_get DDNS_PROVIDER none)" = none ] || { echo; ddns_links; }; echo; read -rp "Press Enter to continue..." _ ;;
      update) if [ "$(cfg_get DDNS_PROVIDER none)" = none ]; then wt_msg "Set up a name first." 7; elif ddns_update; then wt_msg "Updated: $(cat "$DDNS_STATE" 2>/dev/null)" 8; else wt_msg "Failed: $(cat "$DDNS_STATE" 2>/dev/null)" 9; fi ;;
      off) wt_yesno "Stop updating the name and delete the saved key?\n\nThe name itself stays on the service's website; it will just stop following your address." 10 && { ddns_off; wt_msg "Domain name is off." 7; } ;;
      *) return 0 ;;
    esac
  done
}
