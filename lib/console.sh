# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# The web console (0.39.0, a test the owner may take out again; off by default): ZenithBoard's settings from a
# browser on the home network, at http://PI:8080/console, next to the wall, the menu and the command, which stay.
#
# How it is kept safe (wiki: Web-console):
#   * it answers home networks only (10/8, 172.16/12, 192.168/16, link-local, the Pi itself), whatever ALLOW_FROM
#     says, and only to an address or a local name (a page elsewhere that points its own name at the Pi gets nothing);
#   * a password set here, over SSH, kept as a scrypt hash in /etc/zenithboard/console.env (root:zenithboard 0640,
#     never in config.env); or a phone paired by a QR code that works once, for five minutes;
#   * the wall's server cannot change anything itself: it writes a job naming one action from a fixed list
#     (flightinfo/console_actions.py) into a folder only it can write; a root helper started by systemd checks the
#     job against the same list and runs that one `zenithboard` command, as arguments, never through a shell;
#   * left out: uninstalling, Wi-Fi and fixed addresses, anything asking for a password or a key, posting.
#
# `off` stops the helper and closes the pages at once; the password stays for a later `on` (`forget` deletes it).
CONSOLE_ENV="${ZENITHBOARD_CONSOLE_ENV:-${ZB_ETC:-/etc/zenithboard}/console.env}"
CONSOLE_DIR="${ZB_CONSOLE_DIR:-/var/lib/zenithboard/console}"
CONSOLE_UNIT=zenithboard-console
CONSOLE_UNIT_DIR="${ZB_SYSTEMD_DIR:-/etc/systemd/system}"
CONSOLE_PW_MIN=10
CONSOLE_PAIR_S=300

console_state() { [ "$(cfg_get CONSOLE 0)" = 1 ] && echo on || echo off; }
console_secret_get() { [ -r "$CONSOLE_ENV" ] || return 0; sed -n -E "s/^$1=\"?([^\"]*)\"?$/\1/p" "$CONSOLE_ENV" | head -1; }
console_has_password() { [ -n "$(console_secret_get CONSOLE_PASSWORD_HASH)" ]; }
console_url() { echo "http://$(local_ip):$(cfg_get PORT 8080)/console"; }

# root:zenithboard 0640, like the Bluesky secret: the wall reads it, nobody else does
console_env_write() {   # console_env_write KEY=VALUE...  (the whole file)
  local old tmp
  install -d -m 755 "$(dirname "$CONSOLE_ENV")"
  old=$(umask); umask 077
  tmp=$(mktemp "${CONSOLE_ENV}.XXXXXX") || { umask "$old"; return 1; }
  printf '# ZenithBoard web console: the password as a scrypt hash, and when everyone was last signed out. root:%s, mode 0640.\n' "$ZB_USER" > "$tmp"
  printf '%s\n' "$@" | sed -E 's/^([A-Z_]+)=(.*)$/\1="\2"/' >> "$tmp"
  umask "$old"
  chown "root:$ZB_USER" "$tmp" 2>/dev/null || true; chmod 640 "$tmp"
  mv "$tmp" "$CONSOLE_ENV"
}

# Folders: state/ belongs to the wall (its sessions, and the spool it drops jobs in: the only place on the card the
# wall's sandbox may write); out/ belongs to root and is only read by the wall (what the helper ran and said).
console_prepare_dirs() {
  local own=1; [ "$(id -u)" -eq 0 ] || own=0
  [ "$own" = 0 ] || ensure_zb_user || return 1
  install -d -m 750 "$CONSOLE_DIR" "$CONSOLE_DIR/out" || return 1
  install -d -m 700 "$CONSOLE_DIR/state" "$CONSOLE_DIR/state/spool" || return 1
  if [ "$own" = 1 ]; then
    chown "root:$ZB_USER" "$CONSOLE_DIR" "$CONSOLE_DIR/out"
    chown "$ZB_USER:$ZB_USER" "$CONSOLE_DIR/state" "$CONSOLE_DIR/state/spool"
  fi
}

console_install_units() {
  local u
  for u in "$CONSOLE_UNIT.service" "$CONSOLE_UNIT.path"; do [ -f "$ZB_HOME/systemd/$u" ] || return 0; done
  install -d -m 755 "$CONSOLE_UNIT_DIR"
  install -m 644 "$ZB_HOME/systemd/$CONSOLE_UNIT.service" "$ZB_HOME/systemd/$CONSOLE_UNIT.path" "$CONSOLE_UNIT_DIR/"
  # the wall's own unit gives it the right to write its spool (ReadWritePaths) since 0.39.0
  if [ -f "$CONSOLE_UNIT_DIR/zenithboard-flightinfo.service" ] && ! cmp -s "$ZB_HOME/systemd/zenithboard-flightinfo.service" "$CONSOLE_UNIT_DIR/zenithboard-flightinfo.service"; then
    install -m 644 "$ZB_HOME/systemd/zenithboard-flightinfo.service" "$CONSOLE_UNIT_DIR/"
    systemctl daemon-reload; restart_flightinfo
  fi
  systemctl daemon-reload; systemctl enable --now "$CONSOLE_UNIT.path" >/dev/null 2>&1 || true
}
console_remove_units() {
  systemctl disable --now "$CONSOLE_UNIT.path" >/dev/null 2>&1 || true
  # turned off from the console itself, the helper is the one running this: it ends by itself, after writing so
  [ "${ZB_FROM_CONSOLE:-0}" = 1 ] || systemctl stop "$CONSOLE_UNIT.service" >/dev/null 2>&1 || true
  rm -f "$CONSOLE_UNIT_DIR/$CONSOLE_UNIT.service" "$CONSOLE_UNIT_DIR/$CONSOLE_UNIT.path"; systemctl daemon-reload 2>/dev/null || true
}

console_on() {
  # 0.43.0: the console is a page of the wall's server: without the wall there is nothing to answer it
  if ! is_flightinfo; then
    echo "The web console is a page of the wall, which is not installed yet: install it first (sudo zenithboard menu, then"
    echo "2 The wall, or Start here), then switch the console on. Its password can be set already: sudo zenithboard console password"
    return 1
  fi
  console_prepare_dirs || { echo "Could not make $CONSOLE_DIR"; return 1; }
  cfg_set CONSOLE 1; console_install_units
  # 0.39.2: the wall may write its console folder only if the folder existed when it started (its sandbox's
  # ReadWritePaths); a wall running from before `on` could not, and refused every pairing code (the reference Pi)
  systemctl try-restart zenithboard-flightinfo >/dev/null 2>&1 || true
  echo "The web console is ON: $(console_url)"
  echo "  It answers your home network only. Every change it makes runs the same zenithboard command as here."
  if console_has_password; then
    echo "  Sign in with the console password, or pair a phone:  sudo zenithboard console pair"
  else
    echo "  No password yet. Choose one:  sudo zenithboard console password"
    echo "  Or open it on your phone without one, once:  sudo zenithboard console pair   (a QR code to scan)"
  fi
  echo "  Off again:  sudo zenithboard console off"
}
console_off() {
  cfg_set CONSOLE 0; console_remove_units
  echo "The web console is OFF: its pages answer no more, its helper is stopped. The password is kept for a later 'on' (delete it: sudo zenithboard console forget)."
}
console_forget() {
  console_off >/dev/null
  rm -f "$CONSOLE_ENV"; rm -rf "${CONSOLE_DIR:?}/state" "${CONSOLE_DIR:?}/out"
  echo "The web console is OFF and forgotten: the password, the signed-in browsers and phones, and the record of what it ran are deleted."
}

# The password never goes on a command line (it would show in the process list): read here, handed to Python on
# its standard input, kept only as a scrypt hash. Setting it signs every browser and phone out.
console_password() {
  local a b h
  read -rsp "Console password ($CONSOLE_PW_MIN characters at least; not your Pi's or Bluesky's): " a; echo
  [ "${#a}" -ge "$CONSOLE_PW_MIN" ] || { echo "Too short: $CONSOLE_PW_MIN characters at least. Nothing was changed."; return 1; }
  read -rsp "The same again: " b; echo
  [ "$a" = "$b" ] || { echo "The two do not match. Nothing was changed."; return 1; }
  h=$(printf '%s' "$a" | python3 -c '
import base64, hashlib, os, sys
pw = sys.stdin.buffer.read(); salt = os.urandom(16)
h = hashlib.scrypt(pw, salt=salt, n=16384, r=8, p=1, dklen=32)
b = lambda x: base64.b64encode(x).decode()
print("scrypt$16384$8$1$%s$%s" % (b(salt), b(h)))') || { echo "Could not make the hash (python3)."; return 1; }
  console_env_write "CONSOLE_PASSWORD_HASH=$h" "CONSOLE_EPOCH=$(date +%s)" || { echo "Could not write $CONSOLE_ENV"; return 1; }
  echo "Console password saved (as a hash, in $CONSOLE_ENV). Every browser and phone signed in before is signed out."
  [ "$(console_state)" = on ] && echo "Sign in at $(console_url)" || echo "Turn the console on:  sudo zenithboard console on"
}
console_signout() {
  console_env_write "CONSOLE_PASSWORD_HASH=$(console_secret_get CONSOLE_PASSWORD_HASH)" "CONSOLE_EPOCH=$(date +%s)" || return 1
  echo "Every browser and phone is signed out of the console."
}

# A QR code for a phone: a link that signs it in once, within five minutes. qrencode draws it dark on a white
# square with its own margin (ANSIUTF8 sets both colours), so it scans on a black terminal too.
console_pair() {
  local tok url
  [ "$(console_state)" = on ] || { echo "The console is off. First:  sudo zenithboard console on"; return 1; }
  console_prepare_dirs || return 1
  tok=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))') || return 1
  printf '%s %s\n' "$(printf '%s' "$tok" | sha256sum | cut -d' ' -f1)" "$(( $(date +%s) + CONSOLE_PAIR_S ))" > "$CONSOLE_DIR/out/pair"
  chown "root:$ZB_USER" "$CONSOLE_DIR/out/pair" 2>/dev/null || true; chmod 640 "$CONSOLE_DIR/out/pair"
  url="$(console_url)/#pair=$tok"
  echo "Scan this with the phone's camera within $((CONSOLE_PAIR_S / 60)) minutes; it works once:"
  if command -v qrencode >/dev/null 2>&1; then
    echo; qrencode -t ANSIUTF8 -m 2 "$url"; echo
  else
    echo "  (to see a QR code here: sudo apt install qrencode)"
  fi
  echo "  $url"
  echo "The phone stays signed in as long as it opens the console once a month (a year at most). See or sign out phones: in the console, System -> Signed in."
}

# 0.40.0: a computer's sign-in page shows a QR code, a phone already signed in approves it (off by default)
console_phone_signin() {
  case "${1:-}" in
    on)  cfg_set CONSOLE_PHONE_SIGNIN 1
         echo "Signing in with a phone is ON: a computer's sign-in page shows a QR code; scan it with a phone already signed in to the console, check the four-digit code, say yes." ;;
    off) cfg_set CONSOLE_PHONE_SIGNIN 0; echo "Signing in with a phone is OFF: computers sign in with the password." ;;
    "")  echo "Signing computers in with a phone: $( [ "$(cfg_get CONSOLE_PHONE_SIGNIN 0)" = 1 ] && echo ON || echo OFF )" ;;
    *)   echo "Usage: zenithboard console phone-signin on|off"; return 1 ;;
  esac
}

console_status() {
  echo "Web console: $(console_state)$( [ "$(console_state)" = on ] && echo "   $(console_url)")"
  echo "  Computers signed in by a phone: $( [ "$(cfg_get CONSOLE_PHONE_SIGNIN 0)" = 1 ] && echo ON || echo "OFF (sudo zenithboard console phone-signin on)" )"
  echo "  Password: $(console_has_password && echo "set (as a hash in $CONSOLE_ENV)" || echo "none (sudo zenithboard console password)")"
  if [ -f "$CONSOLE_UNIT_DIR/$CONSOLE_UNIT.path" ]; then echo "  Helper: $(systemctl is-active "$CONSOLE_UNIT.path" 2>/dev/null || echo unknown)"
  elif [ "$(console_state)" = on ]; then echo "  Helper: not installed (run: sudo zenithboard console on)"; fi
  if [ -r "$CONSOLE_DIR/out/journal.log" ]; then echo "  Last changes from the console:"; tail -n 5 "$CONSOLE_DIR/out/journal.log" | sed 's/^/    /'; fi
}

# What the console's overview shows, one KEY=value a line, read by the helper (as root) after each job.
console_state_lines() {
  local d t m u svc is_wifi
  printf 'version=%s\n' "$ZB_VERSION"
  printf 'model=%s\n' "$(pi_model || true)"
  printf 'uptime_s=%s\n' "$(cut -d. -f1 /proc/uptime 2>/dev/null)"
  t=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null); [ -z "$t" ] || printf 'temp_c=%s\n' "$((t / 1000))"
  command -v vcgencmd >/dev/null 2>&1 && printf 'throttled=%s\n' "$(vcgencmd get_throttled 2>/dev/null | cut -d= -f2)"
  printf 'mem_total_mb=%s\nmem_avail_mb=%s\n' "$(mem_total_mb)" "$(mem_avail_mb)"
  read -r m u < <(df -Pm / 2>/dev/null | awk 'NR==2 {print $2, $4}'); printf 'disk_total_mb=%s\ndisk_free_mb=%s\n' "$m" "$u"
  printf 'load=%s\n' "$(cut -d' ' -f1-3 /proc/loadavg 2>/dev/null)"
  printf 'ip=%s\n' "$(local_ip)"
  d=$(installed_decoder); printf 'decoder=%s\n' "$d"
  for svc in "$d" adsbexchange-feed piaware fr24feed pfclient dump978-fa zenithboard-flightinfo zenithboard-social graphs1090 lighttpd; do
    [ -n "$svc" ] || continue
    if systemctl list-unit-files "$svc.service" 2>/dev/null | grep -q "^$svc.service"; then
      printf 'svc_%s=%s\n' "${svc//-/_}" "$(systemctl is-active "$svc" 2>/dev/null || true)"
    fi
  done
  printf 'watchdog=%s\nnetwatch=%s\nkeeplogs=%s\nwifi_harden=%s\npatches=%s\ngraphs=%s\nlogs_auto=%s\n' \
    "$(watchdog_state)" "$(netwatch_state)" "$(keeplogs_state)" "$(wifi_harden_state)" "$(patches_state)" "$(graphs_state)" \
    "$( [ "$(cfg_get LOG_AUTOCLEAN 0)" = 1 ] && echo on || echo off)"
  printf 'bluesky=%s\n' "$(social_account)"
  if declare -F ts_state >/dev/null; then                 # 0.45.1: Tailscale on the overview and its own card
    printf 'tailscale=%s\n' "$(ts_state)"
    [ "$(ts_state)" != on ] || printf 'tailscale_ip=%s\ntailscale_name=%s\n' "$(ts_ip)" "$(ts_name)"
  fi
  for d in /usr/local/share/tar1090/html /usr/share/tar1090/html; do [ -d "$d" ] && { printf 'map=tar1090\n'; break; }; done
  [ -d /usr/share/skyaware/html ] || [ -d /usr/share/dump1090-fa/html ] && printf 'skyaware=1\n'
  is_wifi=$(wifi_has_nm && [ -n "$(wifi_iface)" ] && echo 1); [ -z "$is_wifi" ] || printf 'wifi=%s\n' "$(wifi_summary)"
  [ "$(cfg_get DDNS_PROVIDER none)" = none ] || printf 'ddns=%s\n' "$(ddns_summary)"
}

console_menu() {
  local c
  while true; do
    c=$(wt_menu "Web console: $(console_state)$( [ "$(console_state)" = on ] && echo "  -  $(console_url)")\nPassword: $(console_has_password && echo set || echo none)\n\nZenithBoard's settings from a browser or a phone on your home network. Changes run the same commands as this menu; uninstalling, Wi-Fi, fixed addresses and passwords stay here." \
      toggle "1  Switch the console $( [ "$(console_state)" = on ] && echo OFF || echo ON )" \
      password "2  Set the console password (signs everyone out)" \
      pair "3  Pair a phone: a QR code to scan, valid once for 5 minutes" \
      signout "4  Sign every browser and phone out" \
      status "5  Status" \
      phone "6  Sign computers in with a phone (a QR code on the computer): $( [ "$(cfg_get CONSOLE_PHONE_SIGNIN 0)" = 1 ] && echo ON || echo OFF )" \
      back "Return to the previous menu") || return 0
    case "$c" in
      toggle) clear; if [ "$(console_state)" = on ]; then console_off; else console_on; fi; read -rp "Press Enter to continue..." _ ;;
      password) clear; console_password || true; read -rp "Press Enter to continue..." _ ;;
      pair) clear; console_pair || true; read -rp "Press Enter when the phone is signed in..." _ ;;
      signout) clear; console_signout || true; read -rp "Press Enter to continue..." _ ;;
      status) clear; console_status; read -rp "Press Enter to continue..." _ ;;
      phone) if [ "$(cfg_get CONSOLE_PHONE_SIGNIN 0)" = 1 ]; then console_phone_signin off >/dev/null; else console_phone_signin on >/dev/null; fi
             wt_msg "$(console_phone_signin)" 8 ;;
      *) return 0 ;;
    esac
  done
}
