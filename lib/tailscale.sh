# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Tailscale (0.45.0, off by default): the wall, the receiver map, graphs1090 and, if you choose, the web console, from
# anywhere, with no port opened in the router. Asked for by the owner on 21 October 2026, after the menu's
# "From outside your home, safely" screen named it.
#
# Installed the way Tailscale's own page for this system says (pkgs.tailscale.com/stable, read on 21 October 2026):
# its signing key in /usr/share/keyrings/tailscale-archive-keyring.gpg, its list in /etc/apt/sources.list.d/, then apt.
# The package is checked by apt against that key: signature checking is never switched off. Tailscale publishes no
# fingerprint to pin (the page gives the key file only), so the key is taken over HTTPS from pkgs.tailscale.com, as
# its own install script does.
#
# The account is yours and is made on tailscale.com: ZenithBoard never makes one and never sees a password. `on` runs
# `tailscale up --qr`, which prints a sign-in link (and its QR code): open it on any device, sign in, approve the Pi.
#
#   on       install if needed, connect, let the wall answer Tailscale's addresses (100.64.0.0/10)
#   off      disconnect (tailscale down), the wall back to what it answered before; installed and signed in still
#   remove   sign out (the Pi's key expires), stop it, uninstall what ZenithBoard installed: a typed word
#   console on|off   the web console over Tailscale too (off by default: home networks only otherwise)

TS_STATE="${ZB_ETC:-/etc/zenithboard}/tailscale.state"
TS_LIST="${ZB_APT_DIR:-/etc/apt}/sources.list.d/tailscale.list"
TS_KEY="${ZB_KEYRING_DIR:-/usr/share/keyrings}/tailscale-archive-keyring.gpg"
TS_VAR="${ZB_TAILSCALE_VAR:-/var/lib/tailscale}"
TS_RANGE="100.64.0.0/10"                      # Tailscale's addresses (tailscale.com/kb/1015)
TS_ADMIN="https://login.tailscale.com/admin/machines"

ts_installed() { command -v tailscale >/dev/null 2>&1; }
# pkgs.tailscale.com's folder for this system: raspbian for the 32-bit Raspberry Pi OS, debian for the 64-bit one
ts_repo_path() {
  local id="" code=""
  local f="${ZB_OS_RELEASE:-/etc/os-release}"      # read, never sourced
  id=$(sed -n 's/^ID=//p' "$f" 2>/dev/null | tr -d '"'); code=$(sed -n 's/^VERSION_CODENAME=//p' "$f" 2>/dev/null | tr -d '"')
  [ "$id" = raspbian ] || id=debian
  [ -n "$code" ] && printf '%s/%s' "$id" "$code"
}
ts_backend() { tailscale status --json 2>/dev/null | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("BackendState", ""))
except Exception: print("")' 2>/dev/null; }
ts_state() { ts_installed || { echo "not installed"; return; }; case "$(ts_backend)" in Running) echo on ;; NeedsLogin) echo "not signed in" ;; *) echo off ;; esac; }
ts_ip() { tailscale ip -4 2>/dev/null | head -1; }
ts_name() { tailscale status --json 2>/dev/null | python3 -c 'import json,sys
try: print((json.load(sys.stdin).get("Self") or {}).get("DNSName", "").rstrip("."))
except Exception: print("")' 2>/dev/null; }

# ALLOW_FROM as a list: "private" (home networks), "any", or networks. Tailscale's range added and taken away as one
# item, whatever else is in it, so `off` puts back exactly what was there.
ts_allow_add() {
  local cur; cur=$(cfg_get ALLOW_FROM private); [ -n "$cur" ] || cur=private
  case ",$cur," in *",$TS_RANGE,"*|*",any,"*) return 0 ;; esac
  cfg_set ALLOW_FROM "$cur,$TS_RANGE"
}
ts_allow_del() {
  local cur new; cur=$(cfg_get ALLOW_FROM private)
  new=$(printf '%s' "$cur" | tr ',' '\n' | grep -vxF "$TS_RANGE" | paste -sd, -)
  cfg_set ALLOW_FROM "${new:-private}"
}

tailscale_install() {
  local path tmp
  path=$(ts_repo_path) || { err "This system does not say its Debian version (/etc/os-release): Tailscale was not installed."; return 1; }
  tmp=$(mktemp -d) || return 1
  log "Installing Tailscale from pkgs.tailscale.com/stable/$path (its own repository, checked by apt)"
  if ! fetch "$TAILSCALE_PKGS/$path.noarmor.gpg" "$tmp/key.gpg" || ! fetch "$TAILSCALE_PKGS/$path.tailscale-keyring.list" "$tmp/list"; then
    rm -rf "$tmp"; err "Tailscale's repository could not be read: nothing was changed."; return 1
  fi
  # the list goes into apt's sources: every line must be Tailscale's own repository, signed by its key, and no other
  if ! grep -v '^[[:space:]]*#' "$tmp/list" | grep -q 'pkgs.tailscale.com' || \
     grep -v '^[[:space:]]*#' "$tmp/list" | grep -v '^[[:space:]]*$' | grep -qv '^deb \[signed-by=/usr/share/keyrings/tailscale-archive-keyring.gpg\] https://pkgs.tailscale.com/stable/'; then
    rm -rf "$tmp"; err "Tailscale's repository list does not look as expected: nothing was changed."; return 1
  fi
  install -d -m 755 "$(dirname "$TS_KEY")" "$(dirname "$TS_LIST")"
  install -m 644 "$tmp/key.gpg" "$TS_KEY"; install -m 644 "$tmp/list" "$TS_LIST"; rm -rf "$tmp"
  { [ "${ZB_SKIP_SERVICES:-}" = 1 ] || apt-get update -qq; } && apt_install tailscale || {
    rm -f "$TS_LIST" "$TS_KEY"; err "apt did not install Tailscale (above); its repository was taken away again."; return 1; }
  printf 'BY_ZB=1\n' > "$TS_STATE"
}

tailscale_on() {
  if ! ts_installed; then tailscale_install || return 1; fi
  [ "${ZB_SKIP_SERVICES:-}" = 1 ] || systemctl enable --now tailscaled >/dev/null 2>&1 || true
  if [ "$(ts_backend)" != Running ]; then
    echo
    echo "Tailscale asks you to sign in, once. Open the link it prints below (or scan its QR code with your phone),"
    echo "sign in to YOUR Tailscale account (made on tailscale.com: free for personal use; ZenithBoard never makes"
    echo "one and never sees its password), then approve this Pi. Install Tailscale on your phone or computer too,"
    echo "signed in to the same account. This waits until the sign-in is done (Ctrl+C stops it, nothing is lost)."
    echo
    [ "${ZB_SKIP_SERVICES:-}" = 1 ] || tailscale up --qr || { err "Tailscale did not connect (above). Try again: sudo zenithboard tailscale on"; return 1; }
  fi
  ts_allow_add; restart_flightinfo
  cfg_set TAILSCALE 1
  tailscale_where
}

tailscale_where() {
  local ip name port; ip=$(ts_ip); name=$(ts_name); port=$(cfg_get PORT 8080)
  echo "Tailscale is ON. From any device signed in to your Tailscale account, wherever it is:"
  [ -z "$ip" ] || echo "    the wall:        http://$ip:$port/      statistics: http://$ip:$port/stats"
  [ -z "$name" ] || echo "    or by its name:  http://$name:$port/"
  is_graphs 2>/dev/null && [ -n "$ip" ] && echo "    graphs1090:      http://$ip:$GRAPHS_PORT/"
  if [ "$(cfg_get CONSOLE_TAILSCALE 0)" = 1 ]; then
    [ -z "$ip" ] || echo "    the web console: http://$ip:$port/console"
  else
    echo "    The web console stays for your home network. Over Tailscale too: sudo zenithboard tailscale console on"
  fi
  echo "    Nothing is open in your router. Off: sudo zenithboard tailscale off   Removed: sudo zenithboard tailscale remove"
}

tailscale_off() {
  ts_installed || { echo "Tailscale is not installed."; ts_allow_del; cfg_set TAILSCALE 0; return 0; }
  [ "${ZB_SKIP_SERVICES:-}" = 1 ] || tailscale down || true
  ts_allow_del; restart_flightinfo; cfg_set TAILSCALE 0
  echo "Tailscale is OFF: this Pi left your Tailscale network; the wall answers what it answered before ($(cfg_get ALLOW_FROM private))."
  echo "It stays installed and signed in: back on with  sudo zenithboard tailscale on  (no new sign-in). Removed: sudo zenithboard tailscale remove"
}

tailscale_remove() {   # tailscale_remove [--yes]
  local w
  if [ "${1:-}" != --yes ]; then
    echo "This signs the Pi out of Tailscale (its key expires), stops Tailscale and uninstalls what ZenithBoard installed"
    echo "(the package, its repository and key, its state in $TS_VAR). Your Tailscale account and your other devices stay."
    read -r -p "Type remove to go on: " w || w=""
    [ "$w" = remove ] || { echo "Nothing was changed."; return 1; }
  fi
  if ts_installed && [ "${ZB_SKIP_SERVICES:-}" != 1 ]; then
    tailscale logout >/dev/null 2>&1 || true
    systemctl disable --now tailscaled >/dev/null 2>&1 || true
  fi
  if [ "$(sed -n 's/^BY_ZB=//p' "$TS_STATE" 2>/dev/null)" = 1 ]; then
    DEBIAN_FRONTEND=noninteractive apt-get remove -y tailscale || warn "apt did not remove tailscale (above)."
    rm -f "$TS_LIST" "$TS_KEY"; rm -rf "${TS_VAR:?}"
    echo "Tailscale is removed: package, repository, key and its state on this Pi."
  else
    echo "Tailscale was installed before ZenithBoard looked after it: signed out and stopped, but left installed (sudo apt remove tailscale)."
  fi
  rm -f "$TS_STATE"
  ts_allow_del; cfg_set TAILSCALE 0; cfg_set CONSOLE_TAILSCALE 0; restart_flightinfo
  echo "Last, in your Tailscale account: remove this Pi from the list of machines ($TS_ADMIN)."
}

tailscale_console() {   # tailscale_console on|off
  case "${1:-}" in
    on) cfg_set CONSOLE_TAILSCALE 1
        echo "The web console now answers Tailscale's addresses too ($TS_RANGE), by address or by its Tailscale name (*.ts.net):"
        echo "only devices signed in to your Tailscale account reach it, and Tailscale encrypts the way. Its password still applies." ;;
    off) cfg_set CONSOLE_TAILSCALE 0; echo "The web console answers your home network only again." ;;
    *) err "Usage: zenithboard tailscale console on|off"; return 1 ;;
  esac
  restart_flightinfo
}

tailscale_status() {
  echo "Tailscale: $(ts_state)$( ts_installed && printf '  (%s)' "$(tailscale version 2>/dev/null | head -1)")"
  ts_installed || { echo "    Install and connect: sudo zenithboard tailscale on   (menu 3 Connectivity -> 4 Tailscale)"; return 0; }
  [ "$(ts_state)" = on ] && tailscale_where | tail -n +2
  echo "    The wall answers: $(cfg_get ALLOW_FROM private)    Web console over Tailscale: $( [ "$(cfg_get CONSOLE_TAILSCALE 0)" = 1 ] && echo on || echo off)"
}

tailscale_menu() {
  local c
  while true; do
    c=$(wt_menu "Tailscale: the wall, the statistics and graphs1090 from anywhere, with no port opened. Your phone or computer joins your own Tailscale network (free account on tailscale.com).\n\nNow: $(ts_state)$( [ "$(ts_state)" = on ] && echo "  -  http://$(ts_ip):$(cfg_get PORT 8080)/")    Console over it: $( [ "$(cfg_get CONSOLE_TAILSCALE 0)" = 1 ] && echo on || echo off)" \
      how "1  How it works, step by step (read first)" \
      on "2  Install and connect (a sign-in link to open)" \
      console "3  The web console over Tailscale too: $( [ "$(cfg_get CONSOLE_TAILSCALE 0)" = 1 ] && echo on || echo off)" \
      off "4  Disconnect (stays installed, back on in a second)" \
      remove "5  Remove it completely (asks for a typed word)" \
      status "6  Status and addresses" \
      back "Return to the previous menu") || return 0
    case "$c" in
      how) tailscale_how ;;
      on) clear; tailscale_on; menu_pause ;;
      console)
        if [ "$(cfg_get CONSOLE_TAILSCALE 0)" = 1 ]; then wt_yesno "The web console answers over Tailscale.\n\nBack to your home network only?" 9 && { clear; tailscale_console off; menu_pause; }
        else wt_yesno "Let the web console answer over Tailscale too?\n\nOnly devices signed in to your Tailscale account can reach it, Tailscale encrypts the way, and the console's password still applies. Off by default." 11 && { clear; tailscale_console on; menu_pause; }; fi ;;
      off) clear; tailscale_off; menu_pause ;;
      remove) clear; tailscale_remove ""; menu_pause ;;
      status) clear; tailscale_status; menu_pause ;;
      *) return 0 ;;
    esac
  done
}

tailscale_how() {
  wt_scroll "TAILSCALE, STEP BY STEP\n\nTailscale joins your devices into one private network over the internet, encrypted, with no port opened in your router (it even works behind a provider's shared address, CGNAT).\n\n1. Make a free account on tailscale.com (with a Google, Microsoft, GitHub or Apple account, among others). ZenithBoard never makes one.\n2. Install the Tailscale app on your phone and/or computer, and sign in to that account.\n3. Here, item 2 'Install and connect': it installs Tailscale from its own repository (checked by apt), then prints a sign-in link and its QR code. Open it on the phone or computer, sign in to the same account, approve this Pi.\n4. The addresses are then printed: http://100.x.y.z:$(cfg_get PORT 8080)/ for the wall, /stats, graphs1090 on port $GRAPHS_PORT, and a name like zenithboard.tailXXXX.ts.net. Open them from anywhere, with Tailscale on in the phone's app.\n5. The web console stays for your home network unless you choose item 3.\n\nWhat changes on the Pi: the Tailscale package and its repository; the wall answers Tailscale's addresses (100.64.0.0/10) on top of what it answered. Nothing else.\n\nTo stop: item 4 disconnects (back on in a second). Item 5 removes it all (sign-out, package, repository, its state), then remove the Pi from your account's machine list: $TS_ADMIN"
}
