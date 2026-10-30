#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_radarbox.sh
# AirNav Radar (RadarBox), 0.99.6, with a throw-away GPG key, a fake /etc/apt and stand-ins for apt and systemctl (no
# network, no root). What matters: AirNav's key goes in only with its pinned fingerprint and a refused repository leaves
# nothing behind; rbfeeder reads the decoder's Beast port with its MLAT off (ADSB Exchange keeps the only MLAT client),
# and the MLAT guard switches it off again; its sharing key is the station, kept by a backup, by a removal and put back
# by the next install; what ZenithBoard added for it goes when it is removed, and nothing else.
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc" ZB_SKIP_SERVICES=1 ZB_BACKUP_DATA="$t/data" RB24_INI="$t/rbfeeder.ini" ZB_OS_RELEASE="$t/os-release" \
  ZB_ADSBX_UUID="$t/adsbx-uuid" ZB_PIAWARE_ID_CACHE="$t/piaware-cache" FR24_INI="$t/fr24feed.ini"
mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/data"; touch "$ZENITHBOARD_ETC/config.env" "$t/adsbx-uuid" "$t/piaware-cache"
printf '#!/bin/bash\necho "systemctl $*" >> "%s/systemctl.log"\n' "$t" > "$t/bin/systemctl"; chmod +x "$t/bin/systemctl"
export PATH="$t/bin:$PATH"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/adsb.sh
. lib/adsb.sh
for l in adsbxstats stats graphs reliability patches gain logs social settings wifi console backup; do
  # shellcheck disable=SC1090
  . "lib/$l.sh"
done
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }

export GNUPGHOME="$t/gnupg"; mkdir -m 700 "$GNUPGHOME"
gpg --batch --quiet --passphrase '' --quick-gen-key "AirNav test <test@example.invalid>" ed25519 sign never 2>/dev/null
FPR=$(gpg --batch --with-colons --list-keys 2>/dev/null | awk -F: '$1=="fpr"{print $10; exit}')
[ -n "$FPR" ] || { echo "could not make a test key"; exit 1; }
gpg --batch --armor --export "$FPR" > "$t/good.asc"
gpg --batch --quiet --passphrase '' --quick-gen-key "Someone else <other@example.invalid>" ed25519 sign never 2>/dev/null
OTHER=$(gpg --batch --with-colons --list-keys 2>/dev/null | awk -F: '$1=="fpr"{print $10}' | grep -vx "$FPR" | head -1)
gpg --batch --armor --export "$OTHER" > "$t/other.asc"

fetch() { cp "${1#file://}" "$2"; }                 # the real one is https-only: the test hands it the local key
APT_SAYS=""                                          # what the stand-in apt-get update prints about AirNav's repository
apt-get() { if [ "${1:-}" = update ]; then printf '%s\n' "$APT_SAYS"; fi; echo "apt-get $*" >> "$t/apt.log"; return 0; }
apt_install() { echo "apt_install $*" >> "$t/apt.log"; }
apt_remove() { echo "apt_remove $*" >> "$t/apt.log"; }
fresh() { rm -rf "$t/apt"; mkdir -p "$t/apt/sources.list.d"; export ZB_APT_DIR="$t/apt"; APT_SAYS=""; }
fpr_of() { gpg --batch --show-keys --with-colons "$1" 2>/dev/null | awk -F: '$1=="fpr"{print $10; exit}'; }
RB24_KEY_FPR="$FPR"; RB24_KEY_URL="file://$t/good.asc"
echo 'VERSION_CODENAME=bookworm' > "$ZB_OS_RELEASE"

# ---- the repository and its key
check "the pinned fingerprint is AirNav's, 40 hex digits"   '[[ "$(. lib/versions.sh; echo "$RB24_KEY_FPR")" =~ ^[0-9A-F]{40}$ ]] && grep -q "keyserver.ubuntu.com" lib/versions.sh'
fresh
rb24_add_repo >/dev/null 2>&1
check "key in: the keyring holds exactly the pinned key"    '[ "$(fpr_of "$(rb24_keyring)")" = "$FPR" ] && [ "$(stat -c %a "$(rb24_keyring)")" = 644 ]'
check "the source is signed-by that keyring, this suite"    'grep -qx "deb \[signed-by=$t/apt/keyrings/zenithboard-rb24.gpg\] https://apt.rb24.com/ bookworm main" "$(rb24_our_source)"'
fresh; echo 'VERSION_CODENAME=trixie' > "$ZB_OS_RELEASE"
APT_SAYS="E: The repository 'https://apt.rb24.com trixie Release' does not have a Release file."
apt-get() { if [ "${1:-}" = update ]; then grep -q " trixie " "$(rb24_our_source)" 2>/dev/null && printf '%s\n' "$APT_SAYS"; fi; return 0; }
rb24_add_repo >/dev/null 2>&1; rc=$?
check "no suite for this system: bookworm, as the container" '[ "$rc" = 0 ] && grep -q " bookworm main$" "$(rb24_our_source)"'
fresh; APT_SAYS="W: GPG error: https://apt.rb24.com bookworm InRelease: The following signatures were invalid"
apt-get() { if [ "${1:-}" = update ]; then printf '%s\n' "$APT_SAYS"; fi; return 0; }
rb24_add_repo >"$t/out" 2>&1; rc=$?
check "apt refuses it: an error, and nothing is left"       '[ "$rc" != 0 ] && [ ! -e "$(rb24_our_source)" ] && [ ! -e "$(rb24_keyring)" ] && grep -q "nothing was changed about signature checking" "$t/out"'
fresh; RB24_KEY_URL="file://$t/other.asc"
rb24_add_repo >"$t/out" 2>&1; rc=$?
check "another key: refused, nothing written, says why"     '[ "$rc" != 0 ] && [ ! -e "$(rb24_keyring)" ] && [ ! -e "$(rb24_our_source)" ] && grep -q "$FPR" "$t/out"'
fresh; echo "deb https://apt.rb24.com/ bookworm main" > "$t/apt/sources.list.d/rb24.list"
rb24_add_repo >/dev/null 2>&1
check "AirNav's own source already there: used, none added" '[ ! -e "$(rb24_our_source)" ] && [ ! -e "$(rb24_keyring)" ]'
RB24_KEY_URL="file://$t/good.asc"
check "signature checking is never switched off"            '! grep -n -E "trusted=yes|allow-insecure|allow-unauthenticated|--force-yes" lib/adsb.sh'

# ---- its settings: the decoder's Beast port, the antenna, MLAT off
cfg_set LAT 49.21; cfg_set LON 6.17; cfg_set ALT_M 212.6
printf '[client]\nnetwork_mode=false\nkey=a1b2c3d4e5f6a7b8\n\n[mlat]\nautostart_mlat=true\nmlat_cmd=/usr/bin/mlat-client\n' > "$RB24_INI"
rb24_write_ini
check "Beast on 127.0.0.1:30005, network mode"              '[ "$(ini_sec_get "$RB24_INI" network mode)" = beast ] && [ "$(ini_sec_get "$RB24_INI" network external_host)" = 127.0.0.1 ] && [ "$(ini_sec_get "$RB24_INI" network external_port)" = 30005 ] && [ "$(ini_sec_get "$RB24_INI" client network_mode)" = true ]'
check "the antenna, the altitude whole metres"              '[ "$(ini_sec_get "$RB24_INI" client lat)" = 49.21 ] && [ "$(ini_sec_get "$RB24_INI" client lon)" = 6.17 ] && [ "$(ini_sec_get "$RB24_INI" client alt)" = 213 ]'
check "MLAT off, its command and the key left as they were" '[ "$(ini_sec_get "$RB24_INI" mlat autostart_mlat)" = false ] && grep -qx "mlat_cmd=/usr/bin/mlat-client" "$RB24_INI" && [ "$(rb24_key)" = a1b2c3d4e5f6a7b8 ]'
check "plain key=value, never quoted"                       '! grep -q "\"" "$RB24_INI"'

# ---- the MLAT guard
is_radarbox() { return 0; }; is_piaware() { return 1; }; is_fr24() { return 1; }; unit_active() { return 0; }; sleep() { :; }; mlat_count() { echo 1; }
ini_sec_set "$RB24_INI" mlat autostart_mlat true; : > "$t/systemctl.log"
zb_mlat_guard >/dev/null 2>&1
check "the guard switches its MLAT off and restarts it"     '[ "$(ini_sec_get "$RB24_INI" mlat autostart_mlat)" = false ] && grep -q "systemctl restart rbfeeder" "$t/systemctl.log"'
: > "$t/systemctl.log"; zb_mlat_guard >/dev/null 2>&1
check "already off: not restarted for nothing"              '! grep -q "rbfeeder" "$t/systemctl.log"'

# ---- install, with a key from a backup or the one kept when it was removed
fresh; : > "$RB24_INI"
install -d -m 700 "$t/data/restore-pending"; echo "b4ckupk3yb4ckupk3y" > "$t/data/restore-pending/rb24key"
install_radarbox > "$t/out" 2>&1
check "install: from AirNav's repository, the backup's key" 'grep -q "apt_install --no-install-recommends rbfeeder" "$t/apt.log" && [ "$(rb24_key)" = b4ckupk3yb4ckupk3y ] && [ ! -e "$t/data/restore-pending/rb24key" ]'
check "...MLAT off and the claim page said"                 '[ "$(ini_sec_get "$RB24_INI" mlat autostart_mlat)" = false ] && grep -q "airnavradar.com/raspberry-pi/claim" "$t/out"'
remove_radarbox > /dev/null 2>&1
check "remove: the key kept (root only), our source gone"   '[ "$(cat "$(rb24_kept)")" = b4ckupk3yb4ckupk3y ] && [ "$(stat -c %a "$(rb24_kept)")" = 600 ] && [ ! -e "$(rb24_our_source)" ] && [ ! -e "$(rb24_keyring)" ] && grep -q "apt_remove rbfeeder" "$t/apt.log"'
check "...and not among a restore's waiting identities"     '[ ! -e "$t/data/restore-pending/rb24key" ]'
: > "$RB24_INI"
install_radarbox > /dev/null 2>&1
check "put back: the same station (the kept key)"           '[ "$(rb24_key)" = b4ckupk3yb4ckupk3y ] && [ ! -e "$(rb24_kept)" ]'
fresh; echo "deb https://apt.rb24.com/ bookworm main" > "$t/apt/sources.list.d/rb24.list"
remove_radarbox > /dev/null 2>&1
check "AirNav's own source stays when it is removed"        '[ -f "$t/apt/sources.list.d/rb24.list" ]'

# ---- the backup: the key read, put back now or kept for the installation
ini_sec_set "$RB24_INI" client key a1b2c3d4e5f6a7b8
check "a backup holds the sharing key"                      'bk_read_ids | grep -qx "RB24_KEY=a1b2c3d4e5f6a7b8"'
mkdir -p "$t/zb" "$t/before"; echo "RB24_KEY=f0e1d2c3b4a59687" > "$t/zb/feeders.env"
bk_apply_ids "$t/zb" "$t/before" > "$t/out" 2>&1
check "restore: the key back in rbfeeder.ini, old kept"     '[ "$(rb24_key)" = f0e1d2c3b4a59687 ] && grep -q "key=a1b2c3d4e5f6a7b8" "$t/before/rbfeeder.ini" && grep -q "AirNav Radar: your sharing key is back" "$t/out"'
rm -f "$RB24_INI"
bk_apply_ids "$t/zb" "$t/before" > /dev/null 2>&1
check "restore, not installed: it waits for menu 1"         '[ "$(cat "$t/data/restore-pending/rb24key")" = f0e1d2c3b4a59687 ]'
check "menu 1 ticks it then (the hook is in place)"         'grep -q "\$pend/rb24key\" \] && { st_rb=ON" lib/adsb.sh && grep -q "bk_pending_apply radarbox" lib/adsb.sh'

# ---- the position, everywhere
printf '[client]\nkey=a1b2c3d4e5f6a7b8\nlat=1\nlon=2\nalt=3\n' > "$RB24_INI"
is_readsb() { return 1; }; is_dump1090() { return 1; }; is_adsbx() { return 1; }; is_planefinder() { return 1; }; restart_flightinfo() { :; }
zb_apply_location 48.5 7.25 150 > "$t/out" 2>&1
check "location: AirNav Radar's position updated"           '[ "$(ini_sec_get "$RB24_INI" client lat)" = 48.5 ] && [ "$(ini_sec_get "$RB24_INI" client lon)" = 7.25 ] && [ "$(ini_sec_get "$RB24_INI" client alt)" = 150 ] && grep -q "AirNav Radar *updated" "$t/out"'

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
