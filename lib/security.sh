# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# `zenithboard security`: what the Pi actually does right now, against what the Security page says it should.
#
# Every line is one fact read from the running system — a setting, a port, a file mode, a password that still
# works — never from what the installer intended. Each WARN names the command that closes it. It changes nothing.
# Exit status 1 when there is at least one WARN, so a cron job or a script can notice.
SEC_WARN=0

sec_line() {   # sec_line OK|WARN|INFO "what" ["how to fix"]
  local tag="$1" what="$2" fix="${3:-}"
  [ "$tag" = WARN ] && SEC_WARN=$((SEC_WARN + 1))
  printf '  %-5s %s\n' "$tag" "$what"
  [ -z "$fix" ] || printf '        -> %s\n' "$fix"
}

sec_wall() {
  local who; who=$(cfg_get ALLOW_FROM private)
  case "$who" in
    any) sec_line WARN "The wall answers anyone (ALLOW_FROM=any): with a forwarded port it is public, antenna position included" "sudo zenithboard config-set ALLOW_FROM private" ;;
    private|"") sec_line OK "The wall answers home networks only (ALLOW_FROM=private)" ;;
    *) sec_line OK "The wall answers only $who (ALLOW_FROM)" ;;
  esac
  [ "$(cfg_get DDNS_PROVIDER none)" = none ] || sec_line INFO "A domain name points at this Pi ($(cfg_get DDNS_HOST)); whatever your router forwards is reachable by name"
}

sec_updates() {
  if [ "$(cfg_get UPDATE_VERIFY 1)" = 1 ]; then sec_line OK "Updates are checked against GitHub's signature before anything runs (UPDATE_VERIFY=1)"
  else sec_line WARN "Updates are NOT verified (UPDATE_VERIFY=0): a changed repository would be installed as is" "sudo zenithboard config-set UPDATE_VERIFY 1   (keep 0 only for your own fork)"; fi
}

sec_legacy() {      # 0.30.0: ACARS and Grafana are no longer part of ZenithBoard; one left behind is no longer updated
  if [ -n "$(acars_leftovers)" ]; then
    sec_line WARN "ACARS / Grafana from an older ZenithBoard are still installed and no longer updated by it" "sudo zenithboard acars remove"
  else
    sec_line OK "No ACARS or Grafana left from an older ZenithBoard"
  fi
}

sec_patches() {
  if [ "$(patches_state)" = on ]; then sec_line OK "Debian security patches install themselves daily (feeders excluded, no reboot)"
  else sec_line WARN "Debian security patches are not installed automatically" "sudo zenithboard patches on"; fi
}

sec_ssh() {
  local pa
  command -v sshd >/dev/null 2>&1 || { sec_line INFO "No SSH server installed"; return 0; }
  pa=$(sshd -T 2>/dev/null | awk 'tolower($1)=="passwordauthentication"{print tolower($2)}')
  case "$pa" in
    no)  sec_line OK "SSH accepts keys only, not passwords" ;;
    yes) sec_line WARN "SSH accepts passwords: anyone on the network can try to guess yours" "once you log in with a key: set PasswordAuthentication no in /etc/ssh/sshd_config.d/zenithboard.conf, then sudo systemctl restart ssh" ;;
    *)   sec_line INFO "SSH: could not read its settings (sshd -T needs root)" ;;
  esac
}

sec_ports() {
  local port known="" other="" wall; wall=$(cfg_get PORT 8080)
  command -v ss >/dev/null 2>&1 || { sec_line INFO "ss is not available: open ports not listed"; return 0; }
  # one line per port: a service listening on IPv4 and IPv6 shows up twice in ss, and once here
  while read -r port; do
    [ -n "$port" ] || continue
    case "$port" in
      "$wall") known="$known $port(wall)" ;;
      80|443) known="$known $port(map)" ;;
      8504|8978) known="$known $port(skyaware)" ;;                   # FlightAware's map, also on these two ports (1090 and 978 MHz)
      22) known="$known $port(ssh)" ;;
      3000) known="$known $port(grafana, older ZenithBoard)" ;;
      300[0-9][0-9]|301[0-9][0-9]|31[0-9][0-9][0-9]|8754|8089) known="$known $port(decoder/feeder)" ;;   # readsb's beast/raw/SBS ports, the feeders' MLAT returns, FR24's and Plane Finder's pages
      5353|68|546) ;;                                                 # mDNS, DHCP: the system's own
      *) other="$other $port" ;;
    esac
  done < <(ss -H -ltn 2>/dev/null | awk '{print $4}' | grep -vE '^(127\.0\.0\.1|\[::1\]):' | sed 's/.*://' | sort -n -u)
  sec_line OK "Listening on the network:${known:- nothing}"
  [ -z "$other" ] || sec_line INFO "Also listening, not ZenithBoard's:$other (something you installed?)"
}

sec_units() {
  local u s bad="" n=0
  command -v systemd-analyze >/dev/null 2>&1 || { sec_line INFO "systemd-analyze is not available: sandboxes not measured"; return 0; }
  for u in /etc/systemd/system/zenithboard-*.service; do
    [ -f "$u" ] || continue
    u=$(basename "$u"); n=$((n + 1))
    s=$(systemd-analyze security --no-pager "$u" 2>/dev/null | sed -n 's/.*Overall exposure level for .*: \([0-9.]*\).*/\1/p')
    [ -n "$s" ] || continue
    awk -v s="$s" 'BEGIN{exit !(s>6.5)}' && bad="$bad ${u%.service}($s)"
  done
  [ "$n" -gt 0 ] || { sec_line INFO "No ZenithBoard service installed yet"; return 0; }
  if [ -z "$bad" ]; then sec_line OK "All $n ZenithBoard services run inside a sandbox (systemd-analyze security)"
  else sec_line WARN "Service(s) outside the sandbox:$bad (an old unit file?)" "sudo zenithboard update"; fi
}

sec_secrets() {
  local f m o
  for f in "$DDNS_CURL" "$GRAFANA_PASS_FILE"; do
    [ -f "$f" ] || continue
    m=$(stat -c %a "$f" 2>/dev/null)
    [ "$m" = 600 ] && sec_line OK "$(basename "$f") is root-only" || sec_line WARN "$(basename "$f") is mode $m: a secret readable by others" "sudo chmod 600 $f"
  done
  # the social secrets are read by the service, which runs as the wall's user: root-owned, group zenithboard, 0640, nothing for others
  f="${SOCIAL_SECRETS:-$ZB_ETC/social.env}"
  if [ -f "$f" ]; then
    m=$(stat -c %a "$f" 2>/dev/null); o=$(stat -c %U:%G "$f" 2>/dev/null)
    if [ "$m" = 640 ] && [ "$o" = "root:$ZB_USER" ]; then sec_line OK "social.env is root:$ZB_USER, mode 640 (the service reads it, nobody else)"
    else sec_line WARN "social.env is $o mode $m: the social account secrets may be readable by others" "sudo chown root:$ZB_USER $f && sudo chmod 640 $f"; fi
  fi
}

security_check() {
  SEC_WARN=0
  echo "Security check, ZenithBoard $ZB_VERSION on $(hostname 2>/dev/null)"
  echo
  sec_wall; sec_updates; sec_legacy; sec_patches; sec_ssh; sec_ports; sec_units; sec_secrets
  echo
  if [ "$SEC_WARN" = 0 ]; then echo "Nothing to fix."; else echo "$SEC_WARN thing(s) to look at. Each line above says how."; fi
  [ "$SEC_WARN" = 0 ]
}
