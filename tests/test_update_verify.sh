#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_update_verify.sh
# The code is checked before `zenithboard update` runs it: good signature from the recorded key, or it stops and asks.
# shellcheck disable=SC2034  # variables are used inside the eval-ed check strings
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC" "$t/var" "$t/bin"; touch "$ZENITHBOARD_ETC/config.env"
export ZB_SKIP_SERVICES=1 ZB_VAR_DIR="$t/var"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/versions.sh
. lib/versions.sh
# shellcheck source=lib/update.sh
. lib/update.sh
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

KEY=ABCDEF0123456789ABCDEF0123456789ABCDEF01
OTHER=99999999999999999999999999999999999999FF

# ---- the decision itself
check "good signature from the recorded key passes"  '[ "$(zb_verify_decide G "$KEY" "$KEY")" = ok ]'
check "good-but-untrusted counts as good (our keyring IS the trust)" '[ "$(zb_verify_decide U "$KEY" "$KEY")" = ok ]'
check "lower case fingerprint still matches"         '[ "$(zb_verify_decide G "${KEY,,}" "$KEY")" = ok ]'
check "a BAD signature is bad, never a question"     '[ "$(zb_verify_decide B "$KEY" "$KEY")" = bad ]'
check "another key is not accepted"                  '[ "$(zb_verify_decide G "$OTHER" "$KEY")" = unknown ]'
check "an unsigned commit is unknown"                '[ "$(zb_verify_decide N "" "$KEY")" = unknown ]'
check "a signature that cannot be checked is unknown" '[ "$(zb_verify_decide E "" "$KEY")" = unknown ]'
check "nothing recorded yet: a good signature is still unknown" '[ "$(zb_verify_decide G "$KEY" "")" = unknown ]'

# ---- what the update does with that, with a stand-in git
mk_git() {  # mk_git "STATUS FPR"
  printf '#!/bin/bash\nfor a in "$@"; do [ "$a" = log ] && { echo "%s"; exit 0; }; done\nexit 0\n' "$1" > "$t/bin/git"
  chmod +x "$t/bin/git"
}
PATH="$t/bin:$PATH"
mkdir -p "$t/var/trust"; printf '%s\n' "$KEY" > "$t/var/trust/signer.fpr"

mk_git "G $KEY"
check "the usual case passes without a word"   'out=$(zb_verify_source "$t" origin/main 2>&1); [ -z "$out" ]'
mk_git "B $KEY"
check "a bad signature stops the update"       '! zb_verify_source "$t" origin/main >/dev/null 2>&1'
check "and says so plainly"                    'zb_verify_source "$t" origin/main 2>&1 | grep -q "BAD"'
check "a bad signature is never offered as a choice" '! zb_verify_source "$t" origin/main 2>&1 | grep -qi "anyway"'
mk_git "G $OTHER"
check "another key stops it and names both"    '! zb_verify_source "$t" origin/main >/dev/null 2>&1 && zb_verify_source "$t" origin/main 2>&1 | grep -q "not the key recorded"'
mk_git "N "
check "an unsigned commit stops it, with the honest reasons" 'zb_verify_source "$t" origin/main 2>&1 | grep -q "not signed" && zb_verify_source "$t" origin/main 2>&1 | grep -qi "fork"'
check "with nobody to ask, it does NOT install" '! zb_verify_source "$t" origin/main >/dev/null 2>&1'

# ---- the way out, for a fork or your own branch
cfg_set UPDATE_VERIFY 0
mk_git "N "
check "UPDATE_VERIFY=0 skips the whole check"  'zb_verify_source "$t" origin/main >/dev/null 2>&1'
cfg_set UPDATE_VERIFY 1
check "and turning it back on restores it"     '! zb_verify_source "$t" origin/main >/dev/null 2>&1'

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
