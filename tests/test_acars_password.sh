#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_acars_password.sh   Grafana's admin / admin is closed by ZenithBoard itself. Grafana is not here,
# so curl, grafana-cli, runuser and systemctl are stubs that record what they were asked; what is checked is the
# decision (is the default still open?), the password that is set, where it is kept and with what mode.
# shellcheck disable=SC2034
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC" "$t/bin"; touch "$ZENITHBOARD_ETC/config.env"
export ZB_SKIP_SERVICES=1 ZB_GRAFANA_URL="http://stub:3000"
# ---- stubs: curl answers what $t/grafana-code says; grafana-cli records the password; dpkg says grafana is installed
cat > "$t/bin/curl" <<'S'
#!/bin/bash
cat "$T/grafana-code"
S
cat > "$t/bin/grafana-cli" <<'S'
#!/bin/bash
echo "$@" >> "$T/grafana-cli.log"; printf '%s' "$3" > "$T/set-password"; echo 200 > "$T/grafana-code"
S
cat > "$t/bin/runuser" <<'S'
#!/bin/bash
echo "runuser $1 $2" >> "$T/runuser.log"; shift 3; exec "$@"
S
printf '#!/bin/bash\necho "systemctl $*" >> "$T/systemctl.log"\n' > "$t/bin/systemctl"
printf '#!/bin/bash\n[ "$2" = grafana ] && exit 0; exit 1\n' > "$t/bin/dpkg"
printf '#!/bin/bash\necho 192.168.1.50\n' > "$t/bin/hostname"
chmod +x "$t"/bin/*; export T="$t" PATH="$t/bin:$PATH"
echo 200 > "$t/grafana-code"            # admin / admin logs in: the hole is open
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/acars.sh
. lib/acars.sh
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

check "admin/admin open: detected"                  'grafana_default_password_works'
echo 401 > "$t/grafana-code"
check "admin/admin refused: not flagged"            '! grafana_default_password_works'
echo 000 > "$t/grafana-code"
check "Grafana down: not flagged (nothing to fix)"  '! grafana_default_password_works'

pw=$(grafana_new_password)
check "a drawn password has 20 characters"          '[ ${#pw} -eq 20 ]'
check "and none of 0 O 1 l (it is typed from a screen)" '! printf "%s" "$pw" | grep -q "[0O1l]"'
check "two draws differ"                            '[ "$(grafana_new_password)" != "$(grafana_new_password)" ]'

echo 200 > "$t/grafana-code"
out=$(grafana_secure_password)
check "install/update: closes the hole and says so" 'printf "%s" "$out" | grep -q "a password was set"'
set_pw=$(cat "$t/set-password")
check "grafana-cli received a 20-character password" '[ ${#set_pw} -eq 20 ]'
check "grafana-cli ran as the grafana user"         'grep -q "runuser -u grafana" "$t/runuser.log"'
check "the server was stopped before and started after" 'grep -q "stop grafana-server" "$t/systemctl.log" && grep -q "start grafana-server" "$t/systemctl.log"'
check "the password is kept root-only"              '[ "$(stat -c %a "$GRAFANA_PASS_FILE")" = 600 ]'
check "and it is the one Grafana got"               '[ "$(cat "$GRAFANA_PASS_FILE")" = "$set_pw" ]'
check "nothing in the config file (it stays safe to paste)" '! grep -q "$set_pw" "$ZENITHBOARD_ETC/config.env"'

echo 401 > "$t/grafana-code"
out=$(grafana_secure_password)
check "second run: nothing to do, says nothing"     '[ -z "$out" ]'

out=$(grafana_password_cmd show)
check "password show: prints admin and the password" 'printf "%s" "$out" | grep -q "admin / $set_pw"'
out=$(grafana_password_cmd new); new_pw=$(cat "$t/set-password")
check "password new: a different one, applied and kept" '[ "$new_pw" != "$set_pw" ] && [ "$(cat "$GRAFANA_PASS_FILE")" = "$new_pw" ]'
out=$(grafana_apply_password short 2>&1); r=$?
check "a short password is refused"                 '[ $r -ne 0 ] && printf "%s" "$out" | grep -q "8 characters"'
check "and the kept one is untouched"               '[ "$(cat "$GRAFANA_PASS_FILE")" = "$new_pw" ]'

printf '#!/bin/bash\nexit 1\n' > "$t/bin/dpkg"
out=$(grafana_password_cmd show); r=$?
check "without Grafana: says so, no file touched"   '[ $r -ne 0 ] && printf "%s" "$out" | grep -q "not installed"'

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
