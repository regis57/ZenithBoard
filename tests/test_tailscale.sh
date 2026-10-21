#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_tailscale.sh   Tailscale (0.45.0, off by default): the repository of this system's version,
# a list refused unless it is Tailscale's own, signed; the wall told to answer Tailscale's range and told to stop
# again exactly; `remove` asks for the word, signs out, takes away what ZenithBoard installed and only that; the wall
# server's list syntax; the console over Tailscale only when chosen. Stubs: curl, apt-get, systemctl, tailscale.
# shellcheck disable=SC2034
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc" ZB_SKIP_SERVICES=1 ZB_APT_DIR="$t/apt" ZB_KEYRING_DIR="$t/keyrings" ZB_TAILSCALE_VAR="$t/var-ts" \
  ZB_OS_RELEASE="$t/os-release" T="$t"
mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/srv/debian" "$t/var-ts"; touch "$ZENITHBOARD_ETC/config.env"
printf 'ID=debian\nVERSION_CODENAME=bookworm\n' > "$t/os-release"
echo KEY > "$t/srv/debian/bookworm.noarmor.gpg"
echo "deb [signed-by=/usr/share/keyrings/tailscale-archive-keyring.gpg] https://pkgs.tailscale.com/stable/debian bookworm main" > "$t/srv/debian/bookworm.tailscale-keyring.list"
# curl: the last argument is the address; -o names the file
cat > "$t/bin/curl" <<'S'
#!/bin/bash
out=""; url=""; while [ $# -gt 0 ]; do case "$1" in -o) out=$2; shift ;; https://*) url=$1 ;; esac; shift; done
echo "curl $url" >> "$T/log"; f="$T/srv/${url#https://pkgs.tailscale.com/stable/}"; [ -f "$f" ] || exit 22; cp "$f" "$out"
S
cat > "$t/bin/apt-get" <<'S'
#!/bin/bash
echo "apt-get $*" >> "$T/log"
case "$*" in *"install -y tailscale"*) printf '#!/bin/bash\necho "tailscale $*" >> "$T/log"\n' > "$T/bin/tailscale"; chmod +x "$T/bin/tailscale" ;; *"remove -y tailscale"*) rm -f "$T/bin/tailscale" ;; esac
S
printf '#!/bin/bash\necho "systemctl $*" >> "$T/log"\n' > "$t/bin/systemctl"
chmod +x "$t"/bin/*; export PATH="$t/bin:$PATH"
for l in common graphs tailscale; do
  # shellcheck disable=SC1090
  . "lib/$l.sh"
done
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }

check "off by default, nothing installed"            '[ "$(cfg_get TAILSCALE 0)" = 0 ] && [ "$(ts_state)" = "not installed" ]'
check "the repository of this system: debian/bookworm" '[ "$(ts_repo_path)" = debian/bookworm ]'
check "32-bit Raspberry Pi OS: raspbian/<version>"    'printf "ID=raspbian\nVERSION_CODENAME=trixie\n" > "$t/os2"; [ "$(ZB_OS_RELEASE=$t/os2 ts_repo_path)" = raspbian/trixie ]'
check "its own repository, https"                    '[ "$TAILSCALE_PKGS" = https://pkgs.tailscale.com/stable ]'

# a list that adds anything else is refused, and nothing is left behind
cp "$t/srv/debian/bookworm.tailscale-keyring.list" "$t/good.list"
echo "deb http://evil.example/debian bookworm main" >> "$t/srv/debian/bookworm.tailscale-keyring.list"
check "a list naming another repository is refused" '! tailscale_on >/dev/null 2>&1 && [ ! -e "$t/apt/sources.list.d/tailscale.list" ] && ! grep -q "apt-get install" "$t/log"'
cp "$t/good.list" "$t/srv/debian/bookworm.tailscale-keyring.list"

out=$(tailscale_on 2>&1)
check "on: its key and its list, then apt"          '[ -f "$t/keyrings/tailscale-archive-keyring.gpg" ] && grep -q "pkgs.tailscale.com/stable/debian bookworm" "$t/apt/sources.list.d/tailscale.list" && grep -q "apt-get install -y tailscale" "$t/log"'
check "on: the wall answers Tailscale too, the setting kept" '[ "$(cfg_get ALLOW_FROM)" = "private,100.64.0.0/10" ] && [ "$(cfg_get TAILSCALE)" = 1 ] && grep -q "^BY_ZB=1" "$ZENITHBOARD_ETC/tailscale.state"'
check "on: says the account is the owner's, never made here" 'echo "$out" | grep -q "ZenithBoard never makes" && echo "$out" | grep -q "tailscale console on"'
tailscale_on >/dev/null 2>&1
check "on twice: the range once"                     '[ "$(cfg_get ALLOW_FROM)" = "private,100.64.0.0/10" ]'
cfg_set ALLOW_FROM "10.8.0.0/24"; ts_allow_add
check "another list keeps its own networks"          '[ "$(cfg_get ALLOW_FROM)" = "10.8.0.0/24,100.64.0.0/10" ] && ts_allow_del && [ "$(cfg_get ALLOW_FROM)" = "10.8.0.0/24" ]'
cfg_set ALLOW_FROM "private,100.64.0.0/10"
tailscale_off >/dev/null
check "off: the wall back to what it answered"       '[ "$(cfg_get ALLOW_FROM)" = private ] && [ "$(cfg_get TAILSCALE)" = 0 ] && [ -x "$t/bin/tailscale" ]'

tailscale_console on >/dev/null
check "console over Tailscale: only when chosen"     '[ "$(cfg_get CONSOLE_TAILSCALE)" = 1 ]'
check "remove: anything but the word changes nothing" 'echo no | tailscale_remove >/dev/null 2>&1; [ -x "$t/bin/tailscale" ] && [ -f "$t/apt/sources.list.d/tailscale.list" ]'
echo remove | tailscale_remove > "$t/rm.out" 2>&1
check "remove: package, list, key, state, console setting" '[ ! -e "$t/bin/tailscale" ] && [ ! -e "$t/apt/sources.list.d/tailscale.list" ] && [ ! -e "$t/keyrings/tailscale-archive-keyring.gpg" ] && [ ! -e "$t/var-ts" ] && [ "$(cfg_get CONSOLE_TAILSCALE)" = 0 ] && [ ! -e "$ZENITHBOARD_ETC/tailscale.state" ]'
check "remove: says to take the Pi out of the account" 'grep -q "login.tailscale.com/admin/machines" "$t/rm.out"'
# installed before ZenithBoard: signed out and stopped, never uninstalled
printf '#!/bin/bash\necho "tailscale $*" >> "$T/log"\n' > "$t/bin/tailscale"; chmod +x "$t/bin/tailscale"; mkdir -p "$t/var-ts"
tailscale_remove --yes >/dev/null 2>&1
check "one installed by hand stays installed"        '[ -x "$t/bin/tailscale" ] && [ -d "$t/var-ts" ]'

# the wall's server reads the list; the console answers Tailscale only when chosen, by address or *.ts.net name
check "server: private,100.64.0.0/10 is home and Tailscale, nothing else" 'python3 -c "
import sys; sys.path.insert(0, \"flightinfo\"); import server as s
p = \"private,100.64.0.0/10\"
assert s.client_allowed(\"192.168.1.5\", p) and s.client_allowed(\"100.101.2.3\", p) and not s.client_allowed(\"8.8.8.8\", p)
assert s.client_allowed(\"8.8.8.8\", \"private,any\") and not s.client_allowed(\"100.101.2.3\", \"private\")"'
check "console: Tailscale addresses and names only when on" 'python3 -c "
import sys; sys.path.insert(0, \"flightinfo\"); import console as c
assert not c.client_ok(\"100.101.2.3\") and c.client_ok(\"100.101.2.3\", True) and not c.client_ok(\"8.8.8.8\", True)
assert not c.host_ok(\"zb.tail1234.ts.net\") and c.host_ok(\"zb.tail1234.ts.net\", \"\", True)
assert c.tailscale_ok({\"CONSOLE_TAILSCALE\": \"1\"}) and not c.tailscale_ok({})"'
check "menu: 3 Connectivity, 4 Tailscale, with how and remove" 'grep -q "tailscale \"4  Tailscale" lib/menus.sh && grep -q "how \"1  How it works" lib/tailscale.sh && grep -q "remove \"5  Remove it completely" lib/tailscale.sh'

[ "$fail" = 0 ] && echo "ALL OK"
exit "$fail"
