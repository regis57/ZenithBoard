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

# ---- several keys: GitHub publishes its old (expired) key and its current one in the same file
check "a key anywhere in the recorded list passes" '[ "$(zb_verify_decide G "$KEY" "$OTHER"$'"'"'\n'"'"'"$KEY")" = ok ]'
check "a good signature by an EXPIRED key is not enough" '[ "$(zb_verify_decide Y "$KEY" "$KEY")" = unknown ]'
check "nor a signature that has itself expired"      '[ "$(zb_verify_decide X "$KEY" "$KEY")" = unknown ]'
check "a fingerprint that only contains a recorded one is not it" '[ "$(zb_verify_decide G "${KEY}00" "$KEY")" = unknown ]'

# real keys, made here: one already expired (made "in 2020", valid one year), one current
kg=$(mktemp -d "$t/kg.XXXX"); chmod 700 "$kg"
GNUPGHOME="$kg" gpg --batch --quiet --passphrase '' --faked-system-time 20200101T000000 --quick-gen-key "Old key <old@example.invalid>" rsa2048 sign 1y 2>/dev/null
GNUPGHOME="$kg" gpg --batch --quiet --passphrase '' --quick-gen-key "New key <new@example.invalid>" ed25519 sign never 2>/dev/null
GNUPGHOME="$kg" gpg --batch --armor --export > "$t/github.gpg" 2>/dev/null
OLDK=$(GNUPGHOME="$kg" gpg --batch --with-colons --list-keys old@example.invalid 2>/dev/null | awk -F: '$1=="fpr"{print $10; exit}')
NEWK=$(GNUPGHOME="$kg" gpg --batch --with-colons --list-keys new@example.invalid 2>/dev/null | awk -F: '$1=="fpr"{print $10; exit}')
mkdir -p "$ZB_TRUST_GPG"; chmod 700 "$ZB_TRUST_GPG"
keys=$(zb_keys_in "$t/github.gpg")
check "both keys of the file are listed"     'grep -q "^$OLDK " <<<"$keys" && grep -q "^$NEWK " <<<"$keys"'
check "the old one is seen as expired"       'grep -q "^$OLDK e " <<<"$keys"'
check "the current one is not"               '! grep -q "^$NEWK e " <<<"$keys"'

# what the first-time screen shows, with the download replaced by the local file (and nobody to answer)
fetch() { cp "$1" "$2"; }
GITHUB_SIGNING_KEY_URL="$t/github.gpg"
mv "$t/var/trust/signer.fpr" "$t/var/trust/signer.fpr.keep" 2>/dev/null || true
shown=$(zb_trust_setup </dev/null 2>&1)
check "every key in the file is shown"       'grep -q "$OLDK" <<<"$shown" && grep -q "$NEWK" <<<"$shown"'
check "the expired one is marked as not trusted" 'grep "$OLDK" <<<"$shown" | grep -q "expired, will NOT be trusted"'
check "it explains how to compare with GitHub"   'grep -q "LAST 16 characters" <<<"$shown"'
check "with nobody to answer, nothing is recorded" '[ ! -f "$t/var/trust/signer.fpr" ]'
mv "$t/var/trust/signer.fpr.keep" "$t/var/trust/signer.fpr" 2>/dev/null || true

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

# ---- a Pi from 0.12.0/0.12.1: only the OLD key recorded, the current one imported but not recorded
printf '%s\n' "$OLDK" > "$t/var/trust/signer.fpr"
GNUPGHOME="$ZB_TRUST_GPG" gpg --batch --quiet --import "$t/github.gpg" 2>/dev/null
mk_git "G $NEWK"
out=$(zb_verify_source "$t" origin/main </dev/null 2>&1)
check "it names the key and the mistake"     'grep -q "$NEWK" <<<"$out" && grep -q "only the first key" <<<"$out"'
check "with nobody to answer, it is not installed" '! zb_verify_source "$t" origin/main </dev/null >/dev/null 2>&1'
check "and nothing was added behind your back" '[ "$(cat "$t/var/trust/signer.fpr")" = "$OLDK" ]'
mk_git "G $OTHER"
out=$(zb_verify_source "$t" origin/main </dev/null 2>&1)
check "a key that was never in the approved file gets no such offer" '! grep -q "only the first key" <<<"$out"'
printf '%s\n%s\n' "$OLDK" "$NEWK" > "$t/var/trust/signer.fpr"
mk_git "G $NEWK"
check "once both are recorded: silent"       'out=$(zb_verify_source "$t" origin/main 2>&1); [ -z "$out" ]'
printf '%s\n' "$KEY" > "$t/var/trust/signer.fpr"

# ---- the way out, for a fork or your own branch
cfg_set UPDATE_VERIFY 0
mk_git "N "
check "UPDATE_VERIFY=0 skips the whole check"  'zb_verify_source "$t" origin/main >/dev/null 2>&1'
cfg_set UPDATE_VERIFY 1
check "and turning it back on restores it"     '! zb_verify_source "$t" origin/main >/dev/null 2>&1'

# ---- the download folder outlives the subshell that asked for it
# (regression: zb_tmp made the folder inside $( ), whose EXIT trap removed it before curl could write)
zb_tmp_init
f=$(zb_tmp thing.sh)
check "zb_tmp gives a path in a private folder" '[ -d "$(dirname "$f")" ] && [ "$(stat -c %a "$(dirname "$f")")" = 700 ]'
check "the folder is STILL there after the subshell ended" 'echo hello > "$f" && [ "$(cat "$f")" = hello ]'
second=$(zb_tmp other.sh)
check "a second call uses the same folder"     '[ "$(dirname "$second")" = "$(dirname "$f")" ]'
check "and the first file survived it"         '[ -f "$f" ]'
zb_tmp_clean
check "cleaning removes the whole folder"      '[ ! -d "$(dirname "$f")" ]'

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
