#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_security.sh   `zenithboard security` reads the running Pi. Here the Pi is a set of stubs —
# ss, sshd, systemd-analyze, curl, dpkg, stat on real temp files — set first to a Pi with every hole open, then
# to one with every hole closed. Each line's verdict, its fix, and the exit status are what is checked.
# shellcheck disable=SC2034
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/apt" "$t/units"; touch "$ZENITHBOARD_ETC/config.env"
export ZB_SKIP_SERVICES=1 ZB_APT_CONF_DIR="$t/apt" ZB_GRAFANA_URL="http://stub:3000" T="$t"
cat > "$t/bin/ss" <<'S'
#!/bin/bash
cat "$T/ss.out"
S
cat > "$t/bin/sshd" <<'S'
#!/bin/bash
cat "$T/sshd.out"
S
cat > "$t/bin/systemd-analyze" <<'S'
#!/bin/bash
u="${*: -1}"; s=$(grep "^$u " "$T/scores" | awk '{print $2}'); echo "→ Overall exposure level for $u: ${s:-1.3} OK :-)"
S
cat > "$t/bin/curl" <<'S'
#!/bin/bash
cat "$T/grafana-code"
S
printf '#!/bin/bash\n[ "$2" = grafana ] && [ -f "$T/grafana-installed" ] && exit 0; exit 1\n' > "$t/bin/dpkg"
printf '#!/bin/bash\necho pi-test\n' > "$t/bin/hostname"
chmod +x "$t"/bin/*; export PATH="$t/bin:$PATH"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/versions.sh
. lib/versions.sh
# shellcheck source=lib/ddns.sh
. lib/ddns.sh
# shellcheck source=lib/acars.sh
. lib/acars.sh
# shellcheck source=lib/patches.sh
. lib/patches.sh
# shellcheck source=lib/security.sh
. lib/security.sh
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
line() { printf '%s\n' "$out" | grep -E "^  $1 " | grep -q -- "$2"; }   # line TAG "text"

# ================= a Pi with every hole open
cfg_set ALLOW_FROM any; cfg_set UPDATE_VERIFY 0; cfg_set DDNS_PROVIDER duckdns; cfg_set DDNS_HOST a.duckdns.org; cfg_set PORT 8080
touch "$t/grafana-installed"; echo 200 > "$t/grafana-code"
printf 'passwordauthentication yes\nport 22\n' > "$t/sshd.out"
# as ss prints it on a Pi: every service twice (IPv4 and IPv6), the feeders' MLAT returns, FR24's page, one stranger
printf 'LISTEN 0 128 0.0.0.0:8080 0.0.0.0:*\nLISTEN 0 128 [::]:8080 [::]:*\nLISTEN 0 128 0.0.0.0:22 0.0.0.0:*\nLISTEN 0 128 [::]:22 [::]:*\nLISTEN 0 128 0.0.0.0:3000 0.0.0.0:*\nLISTEN 0 128 0.0.0.0:30005 0.0.0.0:*\nLISTEN 0 128 0.0.0.0:30104 0.0.0.0:*\nLISTEN 0 128 0.0.0.0:30154 0.0.0.0:*\nLISTEN 0 128 0.0.0.0:31003 0.0.0.0:*\nLISTEN 0 128 0.0.0.0:8754 0.0.0.0:*\nLISTEN 0 128 127.0.0.1:5000 0.0.0.0:*\nLISTEN 0 128 [::1]:5001 [::]:*\nLISTEN 0 128 0.0.0.0:9000 0.0.0.0:*\n' > "$t/ss.out"
echo "zenithboard-ddns.service 9.4" > "$t/scores"
mkdir -p "$t/etc"; echo tok > "$DDNS_CURL"; chmod 644 "$DDNS_CURL"
# the units the Pi has installed: sec_units reads /etc/systemd/system, which a test cannot write, so it is wrapped
sec_units() { local u s bad="" n=0; for u in zenithboard-flightinfo.service zenithboard-ddns.service; do n=$((n+1)); s=$(systemd-analyze security --no-pager "$u" | sed -n 's/.*Overall exposure level for .*: \([0-9.]*\).*/\1/p'); awk -v s="$s" 'BEGIN{exit !(s>6.5)}' && bad="$bad ${u%.service}($s)"; done; if [ -z "$bad" ]; then sec_line OK "All $n ZenithBoard services run inside a sandbox (systemd-analyze security)"; else sec_line WARN "Service(s) outside the sandbox:$bad (an old unit file?)" "sudo zenithboard update"; fi; }

out=$(security_check); r=$?
check "open Pi: exit status 1"                          '[ $r -eq 1 ]'
check "wall open to anyone: WARN, with the fix"          'line WARN "answers anyone" && printf "%s" "$out" | grep -q "config-set ALLOW_FROM private"'
check "domain name: noted as INFO"                       'line INFO "a.duckdns.org"'
check "updates unverified: WARN"                         'line WARN "NOT verified" && printf "%s" "$out" | grep -q "config-set UPDATE_VERIFY 1"'
check "grafana admin/admin: WARN, fix is password new"   'line WARN "admin / admin" && printf "%s" "$out" | grep -q "acars password new"'
check "patches off: WARN"                                'line WARN "security patches are not" && printf "%s" "$out" | grep -q "patches on"'
check "ssh passwords: WARN, says to get a key first"     'line WARN "SSH accepts passwords" && printf "%s" "$out" | grep -q "once you log in with a key"'
check "ports: wall, ssh, grafana, decoder named"         'line OK "8080(wall)" && line OK "22(ssh)" && line OK "3000(grafana)" && line OK "30005(decoder/feeder)"'
check "ports: 127.0.0.1 and ::1 ignored, 9000 noted as not ours" '! printf "%s" "$out" | grep -q "500[01]" && line INFO "9000"'
check "ports: each port once, not once per address family" '[ "$(printf "%s" "$out" | grep -o "22(ssh)" | wc -l)" = 1 ] && [ "$(printf "%s" "$out" | grep -o "8080(wall)" | wc -l)" = 1 ]'
check "ports: MLAT returns, feed ports and FR24 page are the feeders" 'line OK "30104(decoder/feeder)" && line OK "30154(decoder/feeder)" && line OK "31003(decoder/feeder)" && line OK "8754(decoder/feeder)" && ! line INFO "30104"'
check "old unit outside the sandbox: WARN, fix is update" 'line WARN "zenithboard-ddns(9.4)" && printf "%s" "$out" | grep -q "zenithboard update"'
check "ddns key readable by others: WARN with chmod"     'line WARN "ddns.curl is mode 644" && printf "%s" "$out" | grep -q "chmod 600"'
check "count of things to look at"                       'printf "%s" "$out" | grep -q "^7 thing"'

# ================= the same Pi, every hole closed
cfg_set ALLOW_FROM private; cfg_set UPDATE_VERIFY 1; cfg_set DDNS_PROVIDER none
echo 401 > "$t/grafana-code"; echo "x" > "$GRAFANA_PASS_FILE"; chmod 600 "$GRAFANA_PASS_FILE"
printf 'passwordauthentication no\n' > "$t/sshd.out"
printf 'LISTEN 0 128 0.0.0.0:8080 0.0.0.0:*\nLISTEN 0 128 0.0.0.0:22 0.0.0.0:*\n' > "$t/ss.out"
echo "zenithboard-ddns.service 1.7" > "$t/scores"; chmod 600 "$DDNS_CURL"
mkdir -p "$t/apt"; patches_conf_text > "$PATCHES_CONF"

out=$(security_check); r=$?
check "closed Pi: exit status 0"                         '[ $r -eq 0 ]'
check "closed Pi: no WARN at all"                        '! printf "%s" "$out" | grep -q "^  WARN"'
check "closed Pi: says nothing to fix"                   'printf "%s" "$out" | grep -q "Nothing to fix"'
check "wall private: OK"                                 'line OK "home networks only"'
check "grafana with its own password: OK"                'line OK "Grafana has its own password"'
check "ssh keys only: OK"                                'line OK "keys only"'
check "patches on: OK"                                   'line OK "install themselves daily"'
check "sandboxes: OK"                                    'line OK "inside a sandbox"'
check "secrets root-only: OK twice"                      '[ "$(printf "%s" "$out" | grep -c "is root-only")" = 2 ]'

# ================= things that are simply absent
# (the real sshd lives in /usr/sbin on a CI runner, so that directory is left out of PATH for this one call)
rm -f "$t/grafana-installed" "$t/bin/sshd"
out=$(PATH="$t/bin:/usr/bin:/bin" security_check)
check "no grafana: OK, not installed"                    'line OK "Grafana is not installed"'
check "no sshd: INFO"                                    'line INFO "No SSH server"'

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
