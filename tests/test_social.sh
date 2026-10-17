#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_social.sh   The shell side of social sharing: the secrets file (owner, mode, what it holds
# and never shows), on/off/remove and what each leaves behind, the validators, and the security audit's line.
# The Python side (words, choice, networks, picture) is tests/test_social.py.
# shellcheck disable=SC2034
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/sysd" "$t/state"; touch "$ZENITHBOARD_ETC/config.env"
export ZB_SKIP_SERVICES=1 ZB_SYSTEMD_DIR="$t/sysd" ZENITHBOARD_SOCIAL_DIR="$t/state/social"
printf '#!/bin/bash\necho "systemctl $*" >> "%s/systemctl.log"\n' "$t" > "$t/bin/systemctl"
printf '#!/bin/bash\nexit 0\n' > "$t/bin/node"                      # "node is installed"
printf '#!/bin/bash\necho "apt $*" >> "%s/apt.log"\n' "$t" > "$t/bin/apt-get"
chmod +x "$t"/bin/*; export PATH="$t/bin:$PATH"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/social.sh
. lib/social.sh
ZB_HOME="$PWD"; SOCIAL_PY="$PWD/flightinfo/social.py"
ZB_USER=$(id -un)                   # chown to the wall's user is for a real Pi; here the file keeps the tester's group
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

check "off at first, no network"                   '[ "$(social_state)" = off ] && [ -z "$(social_networks)" ]'
check "on without an account refuses"              '! social_on >/dev/null 2>&1 && [ "$(cfg_get SOCIAL 0)" = 0 ]'

# ---- the secrets file
social_secrets_write "BLUESKY_HANDLE=zb.bsky.social" "BLUESKY_APP_PASSWORD=aaaa-bbbb-cccc-dddd" "MASTODON_URL=https://mastodon.social" "MASTODON_TOKEN=tok_123"
check "secrets: file written with mode 640"        '[ "$(stat -c %a "$SOCIAL_SECRETS")" = 640 ]'
check "secrets: values quoted, read back"          '[ "$(social_secret_get BLUESKY_APP_PASSWORD)" = aaaa-bbbb-cccc-dddd ] && [ "$(social_secret_get MASTODON_URL)" = https://mastodon.social ]'
check "secrets: not in config.env"                 '! grep -q "aaaa-bbbb\|tok_123" "$ZENITHBOARD_ETC/config.env"'
social_secrets_write "MASTODON_URL=https://m.example" "MASTODON_TOKEN=t2"
check "secrets: rewritten whole, the old network gone" '[ -z "$(social_secret_get BLUESKY_HANDLE)" ] && [ "$(social_secret_get MASTODON_TOKEN)" = t2 ]'

# ---- validators
check "handle: zb.bsky.social ok, no @"            'social_valid_handle zb.bsky.social && ! social_valid_handle "@zb" && ! social_valid_handle "zb"'
check "url: https only, host only"                 'social_valid_url https://mastodon.social && ! social_valid_url http://x.y && ! social_valid_url "https://x.y/path"'

# ---- on / off / remove
cfg_set SOCIAL_NETWORKS mastodon
out=$(social_on)
check "on: setting, service enabled, says the rules" '[ "$(cfg_get SOCIAL)" = 1 ] && grep -q "enable --now zenithboard-social.service" "$t/systemctl.log" && printf "%s" "$out" | grep -q "rules:"'
check "on: unit installed, state folder made"      '[ -f "$t/sysd/zenithboard-social.service" ] && [ -d "$ZENITHBOARD_SOCIAL_DIR" ]'
check "on: node present, apt not called"           '[ ! -f "$t/apt.log" ]'
social_off >/dev/null
check "off: setting, unit gone, secrets kept"      '[ "$(cfg_get SOCIAL)" = 0 ] && [ ! -f "$t/sysd/zenithboard-social.service" ] && [ -f "$SOCIAL_SECRETS" ]'
social_remove >/dev/null
check "remove: secrets, network list and state gone" '[ ! -f "$SOCIAL_SECRETS" ] && [ -z "$(social_networks)" ] && [ ! -d "$ZENITHBOARD_SOCIAL_DIR" ]'

# ---- node is installed on demand
rm -f "$t/bin/node"; hash -r
PATH="$t/bin:/usr/bin:/bin" social_need_node >/dev/null 2>&1 || true   # no node anywhere on that PATH
[ -f "$t/apt.log" ] || { printf '#!/bin/bash\nexit 0\n' > "$t/bin/node"; chmod +x "$t/bin/node"; }
check "node missing: apt is asked for nodejs"      'grep -q "install -y nodejs" "$t/apt.log"'

# ---- the security audit knows the file
# shellcheck source=lib/security.sh
. lib/security.sh
DDNS_CURL="$t/none.curl"; GRAFANA_PASS_FILE="$t/none.pass"    # the other two secrets the audit looks at: absent here
social_secrets_write "MASTODON_URL=https://m.example" "MASTODON_TOKEN=t2"
chmod 644 "$SOCIAL_SECRETS"
check "audit: a world-readable social.env is a WARN" 'sec_secrets 2>/dev/null | grep -q "WARN.*social.env"'
chmod 640 "$SOCIAL_SECRETS"
if [ "$(id -u)" -eq 0 ]; then
  chown "root:$ZB_USER" "$SOCIAL_SECRETS"
  check "audit: root:group 640 is OK"              'sec_secrets 2>/dev/null | grep -q "OK.*social.env"'
else
  echo "skip audit OK line (needs root to set root:$ZB_USER)"
fi

# ---- the Python command line answers without a Pi
check "status runs without a service"              'python3 "$SOCIAL_PY" status | grep -q "Social sharing: off"'
check "check with no account says so"              'rm -f "$SOCIAL_SECRETS"; python3 "$SOCIAL_PY" check | grep -q "No account configured"'
exit $fail
