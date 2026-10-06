#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_fr24_key.sh
# The Flightradar24 signing-key repair, with a throw-away GPG key and a fake /etc/apt (no network, no root).
# What matters: the key lands where the FR24 source says, a key with the wrong fingerprint is REFUSED and leaves
# nothing behind, and signature checking is never turned off.
set -u
cd "$(dirname "$0")/.." || exit 1
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/versions.sh
. lib/versions.sh
# shellcheck source=lib/adsb.sh
. lib/adsb.sh
fail=0
ok()   { echo "ok   $1"; }
bad()  { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export GNUPGHOME="$t/gnupg"; mkdir -m 700 "$GNUPGHOME"
gpg --batch --quiet --passphrase '' --quick-gen-key "ZenithBoard test <test@example.invalid>" ed25519 sign never 2>/dev/null
FPR=$(gpg --batch --with-colons --list-keys 2>/dev/null | awk -F: '$1=="fpr"{print $10; exit}')
[ -n "$FPR" ] || { echo "could not make a test key"; exit 1; }
gpg --batch --armor --export "$FPR" > "$t/good.pub"

# a second, different key: the "wrong fingerprint" case
gpg --batch --quiet --passphrase '' --quick-gen-key "Someone else <other@example.invalid>" ed25519 sign never 2>/dev/null
OTHER=$(gpg --batch --with-colons --list-keys 2>/dev/null | awk -F: '$1=="fpr"{print $10}' | grep -vx "$FPR" | head -1)
gpg --batch --armor --export "$OTHER" > "$t/other.pub"

fresh() { rm -rf "$t/apt"; mkdir -p "$t/apt/sources.list.d"; export ZB_APT_DIR="$t/apt"; }
fpr_of() { gpg --batch --show-keys --with-colons "$1" 2>/dev/null | awk -F: '$1=="fpr"{print $10; exit}'; }

FR24_KEY_FPR="$FPR"; FR24_KEY_URL="file://$t/good.pub"

# 1. one-line source with [signed-by=...]
fresh
echo "deb [signed-by=$t/apt/custom/fr24.gpg] https://repo-feed.flightradar24.com flightradar24 raspberrypi-stable" > "$t/apt/sources.list.d/fr24.list"
fr24_repair_key >/dev/null 2>&1
check "one-line source: key goes where signed-by points" '[ -f "$t/apt/custom/fr24.gpg" ] && [ "$(fpr_of "$t/apt/custom/fr24.gpg")" = "$FPR" ]'
check "the keyring is world-readable (apt reads it as _apt)" '[ "$(stat -c %a "$t/apt/custom/fr24.gpg")" = 644 ]'

# 2. deb822 source with Signed-By:
fresh
printf 'Types: deb\nURIs: https://repo-feed.flightradar24.com\nSuites: flightradar24\nComponents: raspberrypi-stable\nSigned-By: %s/apt/keys/fr24.gpg\n' "$t" > "$t/apt/sources.list.d/fr24.sources"
fr24_repair_key >/dev/null 2>&1
check "deb822 source: key goes where Signed-By points" '[ "$(fpr_of "$t/apt/keys/fr24.gpg")" = "$FPR" ]'

# 3. .asc keyring stays armoured
fresh
echo "deb [signed-by=$t/apt/keys/fr24.asc] https://repo-feed.flightradar24.com flightradar24 raspberrypi-stable" > "$t/apt/sources.list.d/fr24.list"
fr24_repair_key >/dev/null 2>&1
check ".asc keyring stays armoured" 'grep -q "BEGIN PGP PUBLIC KEY BLOCK" "$t/apt/keys/fr24.asc"'

# 4. no source yet: the documented default path
fresh
fr24_repair_key >/dev/null 2>&1
check "no source: default keyrings/flightradar24.gpg" '[ "$(fpr_of "$t/apt/keyrings/flightradar24.gpg")" = "$FPR" ]'
check "a source for another repository is not mistaken for FR24's" '[ -z "$(fr24_source_file)" ]'

# 5. the key is replaced when it is already there (the old SHA1 key)
fresh
mkdir -p "$t/apt/keyrings"; echo "old key" > "$t/apt/keyrings/flightradar24.gpg"
fr24_repair_key >/dev/null 2>&1
check "an old keyring is replaced by the new key" '[ "$(fpr_of "$t/apt/keyrings/flightradar24.gpg")" = "$FPR" ]'

# 6. wrong fingerprint: refused, nothing written, non-zero exit
fresh
FR24_KEY_URL="file://$t/other.pub"
fr24_repair_key >"$t/out" 2>&1; rc=$?
check "a key with another fingerprint is refused" '[ "$rc" -ne 0 ]'
check "...and nothing is written" '[ ! -e "$t/apt/keyrings/flightradar24.gpg" ]'
check "...and the error names the expected fingerprint" 'grep -q "$FPR" "$t/out"'

# 7. download failure: non-zero, nothing written
fresh
FR24_KEY_URL="file://$t/does-not-exist.pub"
fr24_repair_key >/dev/null 2>&1; rc=$?
check "a failed download is an error, not a silent success" '[ "$rc" -ne 0 ] && [ ! -e "$t/apt/keyrings/flightradar24.gpg" ]'

# 8. signature checking is never switched off anywhere in the installer
check "no [trusted=yes] / allow-insecure / --allow-unauthenticated in the code" '! grep -rn -E "trusted=yes|allow-insecure|allow-unauthenticated|AllowInsecure|--force-yes" lib install.sh bin'

# 9. FR24's own wizard is kept: no key question of ours, receiver settings enforced afterwards
FR24_INI="$t/fr24feed.ini"; rm -f "$FR24_INI"
check "no key prompt of ours in the installer" '! grep -n "fr24_ask_key\|ZB_FR24_KEY" lib/adsb.sh'
check "no key -> fr24_has_key false"        '! fr24_has_key'
printf 'receiver="dvbt"\nmlat="yes"\nfr24key="0123456789abcdef"\n' > "$FR24_INI"
check "key saved by the wizard is detected" 'fr24_has_key'
fr24_write_ini
check "wrong wizard answers corrected, key kept" 'grep -qx "mlat=\"no\"" "$FR24_INI" && grep -qx "receiver=\"beast-tcp\"" "$FR24_INI" && grep -qx "host=\"127.0.0.1:30005\"" "$FR24_INI" && grep -qx "bs=\"no\"" "$FR24_INI" && grep -qx "fr24key=\"0123456789abcdef\"" "$FR24_INI"'

exit "$fail"
